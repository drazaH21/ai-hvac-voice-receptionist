import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.schemas.extraction import ExtractedCallIntent
from src.services.llm_extractor import LLMExtractor

def test_schema_validates_fields():
    data = {
        "intent": "request_appointment",
        "customer_name": "John Doe",
        "service_needed": "HVAC Repair",
        "requested_time_text": "tomorrow at 3 PM",
        "confidence_score": 0.95
    }
    extracted = ExtractedCallIntent(**data)
    assert extracted.intent == "request_appointment"
    assert extracted.customer_name == "John Doe"
    assert extracted.service_needed == "HVAC Repair"

@pytest.mark.asyncio
async def test_extractor_parses_valid_payload():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "{\"intent\": \"request_appointment\", \"customer_name\": \"Jane Smith\", \"service_needed\": \"plumbing\", \"requested_time_text\": \"Friday noon\", \"confidence_score\": 0.9}"
                }
            }
        ]
    }

    extractor = LLMExtractor(api_key="mock_key", timeout_seconds=2.5)
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await extractor.extract_intent("Hi, this is Jane Smith. I need plumbing help on Friday noon.")
    
    assert result.intent == "request_appointment"
    assert result.customer_name == "Jane Smith"
    assert result.service_needed == "plumbing"
    assert result.fallback_triggered is False

@pytest.mark.asyncio
async def test_extractor_handles_timeout_with_deterministic_fallback():
    async def slow_post(*args, **kwargs):
        await asyncio.sleep(0.05)
        raise TimeoutError()

    extractor = LLMExtractor(api_key="mock_key", timeout_seconds=0.01)
    with patch("httpx.AsyncClient.post", side_effect=slow_post):
        result = await extractor.extract_intent("Need urgent repair")

    assert result.intent == "unknown"
    assert result.service_needed is None
    assert result.fallback_triggered is True

@pytest.mark.asyncio
async def test_extractor_handles_malformed_json_with_fallback():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Sorry, I am just an AI and cannot format JSON"}}]
    }

    extractor = LLMExtractor(api_key="mock_key", timeout_seconds=2.5)
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await extractor.extract_intent("Hello")

    assert result.intent == "unknown"
    assert result.fallback_triggered is True
