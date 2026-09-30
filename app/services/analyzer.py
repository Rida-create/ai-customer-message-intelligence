"""
services/analyzer.py  --  Owner: Areeha (AI/ML)

Rule-based classification: category + priority.
Fast, deterministic, no API calls, so it works even if the LLM is down.

Public API (this is what Rida's main.py should call):

    from app.services.analyzer import analyze_message
    result = analyze_message(cleaned_text, sentiment="Negative")   # sentiment optional

Returns a dict:
    {
      "is_valid": bool,
      "category": "Billing" | "Refund" | "Account" | "Technical"
                  | "Subscription" | "General Inquiry" | "Unclear",
      "priority": "Low" | "Medium" | "High",
      "confidence": float (0-1),
      "matched_signals": [str, ...],     # why the category was chosen
      "priority_reasons": [str, ...],    # why the priority was chosen
      "error": str | None
    }
"""

import re
from typing import Dict, List, Optional, Tuple

CATEGORIES = [
    "Billing", "Refund", "Account", "Technical",
    "Subscription", "General Inquiry", "Unclear",
]

# ---------------------------------------------------------------------------
# CATEGORY RULES: (regex, weight). Each rule counts at most 2 times.
# ---------------------------------------------------------------------------
CATEGORY_RULES: Dict[str, List[Tuple[str, float]]] = {
    "Billing": [
        (r"charged twice|double[- ]charged?|duplicate (charge|payment)|overcharg\w*|billed twice|charged (me )?(again|extra)", 4),
        (r"payment (failed|declined|didn'?t go through)|card (was )?declined", 4),
        (r"\bcharge[ds]?\b|\bbilling\b|\bbill\b|\binvoice\w*|\bpayment\w*|\btransaction\w*|\bdeducted\b|\breceipt\b", 2),
    ],
    "Refund": [
        (r"\brefund\w*", 3),
        (r"money back|reimburs\w*|chargeback|return my money|get my money", 3),
    ],
    "Account": [
        (r"password|log[- ]?in\b|logged out|sign[- ]?in|locked out|username|verification code|\botp\b|two[- ]factor|\b2fa\b", 3),
        (r"hacked|unauthori[sz]ed|someone (else )?(accessed|logged)|compromised", 3),
        (r"\baccount\b|\bprofile\b|\bemail address\b|\bphone number\b|delete my (data|account)", 1.5),
    ],
    "Technical": [
        (r"\berror\b|\bbug\b|crash\w*|not working|doesn'?t work|isn'?t working|won'?t (load|open|start|work)|\bglitch\w*|freez\w*|frozen|broken|stuck", 3),
        (r"outage|\bserver\b|\bdown\b|\bslow\b|timeout|timed out|\b50\d\b|\b404\b", 2.5),
        (r"\bapp\b|\bwebsite\b|\bpage\b|\bloading\b|\bscreen\b|\bsite\b", 1),
    ],
    "Subscription": [
        (r"subscri\w*|\bplan\b|renew\w*|upgrade|downgrade|\bcancel\w*|\btrial\b|membership|auto[- ]?pay", 2),
    ],
    "General Inquiry": [
        (r"\bhow (do|can|could|would) (i|we|you)\b|\bhow to (change|reset|use|get|update|set|cancel|upgrade|download|install|contact)\b|\bhow much\b|\bwhat is\b|\bwhat are\b|\bdo you (offer|have|support)\b|\bwhere (can|do|is)\b|\bwondering\b|\bquestion\b|\binformation\b|\bpricing\b|\bopening hours\b|\bcontact\b", 1.5),
        (r"\bthank(s| you)\b|\bfeedback\b|\bsuggest\w*", 1),
    ],
}

# ---------------------------------------------------------------------------
# PRIORITY RULES: (regex, points, reason)
#   >= 3.0  -> High
#   >= 1.0  -> Medium
#   else    -> Low
# ---------------------------------------------------------------------------
PRIORITY_RULES: List[Tuple[str, float, str]] = [
    # critical (+3)
    (r"\burgent\w*|\basap\b|immediately|emergency|right now|as soon as possible", 3, "urgency words"),
    (r"fraud\w*|hacked|unauthori[sz]ed|stolen|scam|compromised|someone (else )?(accessed|logged)", 3, "security / fraud risk"),
    (r"charged twice|double[- ]charged?|duplicate (charge|payment)|overcharg\w*|billed twice|charged (me )?(again|extra)", 3, "money lost through duplicate/wrong charge"),
    (r"lawyer|legal action|\bsue\b|\bcourt\b|report (you|this) to|consumer (court|protection)|chargeback", 3, "legal / escalation threat"),
    (r"outage|all (users|customers|our)|nobody can|entire (system|site|team)|production", 3, "widespread / business impact"),
    # moderate (+1.5)
    (r"\brefund\w*|money back", 1.5, "refund requested"),
    (r"locked out|can'?t (log|sign) ?in|cannot (log|sign) ?in|unable to (log|sign) ?in|can'?t access|cannot access", 1.5, "access blocked"),
    (r"not working|crash\w*|\berror\b|broken|won'?t (load|open|start)", 1.5, "service failure"),
    (r"\b(third|fourth|second) time\b|again and again|still (not|haven'?t|no)|no (reply|response)|ignored|\bweeks?\b|\b\d+ days\b", 1.5, "repeated / unresolved issue"),
    (r"\btoday\b|\btonight\b|deadline|by tomorrow", 1.5, "time-sensitive"),
    (r"payment (failed|declined)|card (was )?declined", 1.5, "payment failure"),
    # low (-1.5)
    (r"\bhow (do|can|could|would) (i|we|you)\b|\bhow to (change|reset|use|get|update|set|cancel|upgrade|download|install|contact)\b|\bwondering\b|\bjust (asking|curious)\b|\bwhat is\b|\bdo you (offer|have)\b", -1.5, "informational question"),
    (r"\bthank(s| you)\b|\bfeedback\b|\bsuggest\w*|no rush|whenever you can|not urgent", -1.5, "non-urgent tone"),
]

CATEGORY_BASE_PRIORITY = {
    "Billing": 1.0, "Refund": 1.0, "Account": 1.0, "Technical": 1.0,
    "Subscription": 0.5, "General Inquiry": 0.0, "Unclear": 0.0,
}

MIN_WORDS = 2


def _score_categories(text: str) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
    scores: Dict[str, float] = {c: 0.0 for c in CATEGORIES if c != "Unclear"}
    signals: Dict[str, List[str]] = {c: [] for c in scores}
    for category, rules in CATEGORY_RULES.items():
        for pattern, weight in rules:
            hits = [m.group(0) for m in re.finditer(pattern, text)]
            if hits:
                scores[category] += weight * min(len(hits), 2)
                signals[category].extend(hits[:2])
    return scores, signals


def classify_category(text: str) -> Tuple[str, float, List[str]]:
    """Return (category, confidence 0-1, matched signals)."""
    scores, signals = _score_categories(text)
    best = max(scores, key=lambda c: scores[c])  # ties -> first in dict order
    total = sum(scores.values())
    if scores[best] < 1.0 or total == 0:
        return "Unclear", 0.0, []
    return best, round(scores[best] / total, 2), signals[best]


def determine_priority(text: str, category: str,
                       sentiment: Optional[str] = None) -> Tuple[str, List[str]]:
    """Return (priority, reasons)."""
    points = CATEGORY_BASE_PRIORITY.get(category, 0.0)
    reasons: List[str] = []
    for pattern, pts, reason in PRIORITY_RULES:
        if re.search(pattern, text):
            points += pts
            reasons.append(reason)
    if sentiment and sentiment.strip().lower() == "negative":
        points += 1.0
        reasons.append("negative sentiment")
    # Shouting / heavy punctuation is a mild urgency signal
    if text.count("!") >= 3:
        points += 0.5
        reasons.append("heavy punctuation")

    if points >= 3.0:
        return "High", reasons
    if points >= 1.0:
        return "Medium", reasons
    return "Low", reasons


def analyze_message(text: Optional[str], sentiment: Optional[str] = None) -> Dict:
    """Main entry point. Never raises on bad input."""
    result = {
        "is_valid": True, "category": "Unclear", "priority": "Low",
        "confidence": 0.0, "matched_signals": [], "priority_reasons": [],
        "error": None,
    }

    if text is None or not isinstance(text, str) or not text.strip():
        result.update(is_valid=False, error="Empty message")
        return result

    original = text
    text = re.sub(r"\s+", " ", text.strip().lower())
    # crude noise squash: "helllp" -> "helllp" stays, but "!!!!!!!" -> "!!!"
    text = re.sub(r"([!?.])\1{3,}", r"\1\1\1", text)

    if len(re.findall(r"[a-z0-9]+", text)) < MIN_WORDS and len(original.strip()) < 15:
        # very short: still try to classify, but flag it
        result["error"] = "Message very short"

    category, confidence, signals = classify_category(text)
    priority, reasons = determine_priority(text, category, sentiment)

    result.update(category=category, priority=priority, confidence=confidence,
                  matched_signals=signals, priority_reasons=reasons)
    if category == "Unclear" and not result["error"]:
        result["error"] = "Could not determine category"
    return result


if __name__ == "__main__":
    import json, sys
    msg = " ".join(sys.argv[1:]) or "I was charged twice for my subscription and I want a refund."
    print(json.dumps(analyze_message(msg), indent=2))
