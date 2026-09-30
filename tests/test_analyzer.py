"""
Runs test_cases.json against services/analyzer.py.

    pytest tests/test_analyzer.py -v        # as tests
    python -m tests.test_analyzer           # as a readable table
"""
import json
from pathlib import Path

import pytest

from app.services.analyzer import analyze_message

CASES = json.loads((Path(__file__).parent / "test_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_analyzer_case(case):
    result = analyze_message(case["message"])
    assert result["category"] == case["expected_category"], result
    assert result["priority"] == case["expected_priority"], result
    if "expected_valid" in case:
        assert result["is_valid"] == case["expected_valid"]


if __name__ == "__main__":
    passed = 0
    print(f"{'ID':<5}{'Category':<17}{'Priority':<9}{'OK':<4}Message")
    print("-" * 80)
    for c in CASES:
        r = analyze_message(c["message"])
        ok = r["category"] == c["expected_category"] and r["priority"] == c["expected_priority"]
        passed += ok
        print(f"{c['id']:<5}{r['category']:<17}{r['priority']:<9}{'Y' if ok else 'N':<4}{c['message'][:45]!r}")
        if not ok:
            print(f"      expected {c['expected_category']}/{c['expected_priority']}  got {r['category']}/{r['priority']}  {r['priority_reasons']}")
    print("-" * 80)
    print(f"{passed}/{len(CASES)} passed")
