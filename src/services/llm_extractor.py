import json
import httpx
from typing import Optional
from src.schemas.extraction import ExtractedCallIntent
from src.config import get_settings
from src.logging import logger

EXTRACTION_SYSTEM_PROMPT = """
You are an extraction engine for a home services voice receptionist.
Analyze the user utterance and extract structured details strictly in JSON format.
Keys required:
- intent: ("request_appointment", "reschedule", "cancellation", "pricing_inquiry", "unknown")
- customer_name: string or null
- service_needed: string or null (e.g., "plumbing", "hvac", "electrical")
- requested_time_text: string or null (e.g., "tomorrow 2pm", "monday morning")
- confidence_score: float between 0.0 and 1.0

Return pure JSON only. No markdown fences.
"""

class LLMExtractor:
    def __init__(self, api_key: Optional[str] = None, timeout_seconds: Optional[float] = None, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.groq_api_key
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.groq_timeout_seconds
        self.model = model if model is not None else settings.groq_model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    async def extract_intent(self, caller_text: str) -> ExtractedCallIntent:
        fallback = ExtractedCallIntent(
            intent="unknown",
            customer_name=None,
            service_needed=None,
            requested_time_text=None,
            confidence_score=0.0,
            fallback_triggered=True
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": caller_text}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.warning(f"Groq API returned status {response.status_code}")
                    return fallback

                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                parsed = json.loads(raw_content)
                return ExtractedCallIntent(**parsed)

        except (httpx.TimeoutException, TimeoutError):
            logger.warning("Groq call hit deadline threshold. Falling back to deterministic flow.")
            return fallback
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Extraction failed due to format error: {str(e)}")
            return fallback
