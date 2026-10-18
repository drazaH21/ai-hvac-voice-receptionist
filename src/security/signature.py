from fastapi import Request, HTTPException, status, Depends
from twilio.request_validator import RequestValidator
from src.config import get_settings, Settings

async def validate_twilio_request(request: Request, settings: Settings = Depends(get_settings)):
    if settings.environment == "development":
        return True

    signature = request.headers.get("X-Twilio-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Twilio-Signature header"
        )

    form_data = await request.form()
    params = dict(form_data)
    url = str(request.url)

    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, params, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature"
        )
    return True
