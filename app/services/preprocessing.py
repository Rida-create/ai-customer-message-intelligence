"""
Customer Message Preprocessing
-------------------------------
This module prepares raw customer messages before they are sent to the
AI/LLM analysis layer.

This file intentionally has:
- No API keys
- No LLM/provider code
- No external dependencies

It works with any LLM provider because it only accepts and returns text.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


# These limits can be adjusted later without changing the rest of the project.
DEFAULT_MAX_LENGTH = 8000
DEFAULT_MIN_LENGTH = 2


@dataclass
class PreprocessingResult:
    """Result returned after preprocessing a customer message."""

    text: str
    is_valid: bool
    warning: Optional[str] = None


def validate_message(message: object, min_length: int = DEFAULT_MIN_LENGTH) -> tuple[bool, Optional[str]]:
    """
    Validate the raw customer message.

    Returns:
        (True, None) when the message is usable.
        (False, reason) when the message cannot be processed.
    """

    if message is None:
        return False, "Customer message is missing."

    if not isinstance(message, str):
        return False, "Customer message must be a string."

    if not message.strip():
        return False, "Customer message cannot be empty."

    if len(message.strip()) < min_length:
        return False, "Customer message is too short to analyze reliably."

    return True, None


def _normalize_unicode(text: str) -> str:
    """
    Normalize Unicode characters without removing useful customer content.

    Emojis and meaningful punctuation are preserved.
    """
    return unicodedata.normalize("NFKC", text)


def _normalize_whitespace(text: str) -> str:
    """Remove unnecessary spaces while preserving readable line breaks."""

    # Normalize tabs/spaces around line breaks.
    text = re.sub(r"[ \t]+", " ", text)

    # Prevent excessive blank lines.
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove spaces at the beginning/end of each line.
    text = "\n".join(line.strip() for line in text.splitlines())

    return text.strip()


def _reduce_repeated_characters(text: str, max_repeats: int = 3) -> str:
    """
    Reduce extreme character repetition.

    Examples:
        "heyyyyyyyy" -> "heyyy"
        "NOOOOOOO"   -> "NOOO"

    This is deliberately conservative so that emphasis is not completely lost.
    """

    pattern = rf"(.)\1{{{max_repeats},}}"
    return re.sub(pattern, lambda match: match.group(1) * max_repeats, text)


def _limit_length(text: str, max_length: int) -> str:
    """
    Limit very long messages while preserving both the beginning and end.

    The beginning often contains the problem description and the end may contain
    the customer's requested action or additional details.
    """

    if len(text) <= max_length:
        return text

    marker = "\n[...middle of message shortened for analysis...]\n"

    available = max_length - len(marker)

    if available <= 0:
        return text[:max_length]

    beginning_length = available // 2
    ending_length = available - beginning_length

    return (
        text[:beginning_length]
        + marker
        + text[-ending_length:]
    )


def preprocess_message(
    message: object,
    max_length: int = DEFAULT_MAX_LENGTH,
) -> PreprocessingResult:
    """
    Validate and clean a customer message.

    This function does NOT perform AI analysis. It only prepares the message
    for the LLM layer.

    Args:
        message: Raw customer message.
        max_length: Maximum number of characters passed to the AI layer.

    Returns:
        PreprocessingResult containing cleaned text, validity, and an optional
        warning.

    Raises:
        ValueError: If the message is missing, empty, or not a string.
    """

    is_valid, error = validate_message(message)

    if not is_valid:
        raise ValueError(error)

    text = _normalize_unicode(message)
    text = _normalize_whitespace(text)
    text = _reduce_repeated_characters(text)

    warning = None

    if len(text) > max_length:
        text = _limit_length(text, max_length)
        warning = (
            "Message was very long and the middle portion was shortened "
            "before AI analysis."
        )

    # Re-check after normalization.
    if not text.strip():
        raise ValueError("Customer message became empty after preprocessing.")

    return PreprocessingResult(
        text=text,
        is_valid=True,
        warning=warning,
    )


if __name__ == "__main__":
    # Simple local test. This section does not call any API or LLM.
    examples = [
        "   I was charged TWICE!!! 😡😡   ",
        "   ",
        "Hi",
        "I cannot login\t\tto my account.\n\n\nPlease help!!!",
        "heyyyyyyyyyyyy, I need a refund!!!!!!!!",
    ]

    for example in examples:
        try:
            result = preprocess_message(example)
            print("INPUT: ", repr(example))
            print("OUTPUT:", repr(result.text))
            print("WARNING:", result.warning)
            print("-" * 50)
        except ValueError as error:
            print("INPUT: ", repr(example))
            print("ERROR: ", error)
            print("-" * 50)
