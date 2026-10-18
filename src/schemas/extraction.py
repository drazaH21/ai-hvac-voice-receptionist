from typing import Optional
from pydantic import BaseModel, Field

class ExtractedCallIntent(BaseModel):
    intent: str = Field(default="unknown", description="Primary caller intent (e.g., request_appointment, inquiry, cancel)")
    customer_name: Optional[str] = Field(default=None, description="Full name of caller if provided")
    service_needed: Optional[str] = Field(default=None, description="Specific trade or task requested (e.g., plumbing, HVAC)")
    requested_time_text: Optional[str] = Field(default=None, description="Raw date or time string spoken by caller")
    confidence_score: float = Field(default=0.0, description="Confidence extraction estimate between 0 and 1")
    fallback_triggered: bool = Field(default=False, description="Flag indicating deterministic fallback engaged")
