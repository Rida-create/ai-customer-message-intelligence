import json
from pathlib import Path

import requests


API_URL = "http://localhost:8000"
ANALYZE_ENDPOINT = f"{API_URL}/analyze"

TEST_CASES_FILE = Path(__file__).parent / "test_cases.json"


def load_test_cases():
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def test_test_cases_file_exists():
    assert TEST_CASES_FILE.exists()


def test_api_connection():
    response = requests.get(
        f"{API_URL}/docs",
        timeout=10
    )

    assert response.status_code == 200


def test_customer_messages():
    test_cases = load_test_cases()

    for case in test_cases:

        message = case["message"]

        if not message.strip():
            continue

        response = requests.post(
            ANALYZE_ENDPOINT,
            json={"message": message},
            timeout=30
        )

        assert response.status_code == 200

        result = response.json()

        assert "category" in result
        assert "intent" in result
        assert "priority" in result
        assert "sentiment" in result
        assert "key_information" in result
        assert "suggested_response" in result


def test_empty_message():
    response = requests.post(
        ANALYZE_ENDPOINT,
        json={"message": ""},
        timeout=30
    )

    assert response.status_code in [400, 422]


def test_response_structure():
    message = (
        "I was charged twice for my subscription "
        "and I want a refund."
    )

    response = requests.post(
        ANALYZE_ENDPOINT,
        json={"message": message},
        timeout=30
    )

    assert response.status_code == 200

    result = response.json()

    assert isinstance(result["category"], str)
    assert isinstance(result["intent"], str)
    assert isinstance(result["priority"], str)
    assert isinstance(result["sentiment"], str)
    assert isinstance(result["key_information"], list)
    assert isinstance(result["suggested_response"], str)