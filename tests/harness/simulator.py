from twilio.request_validator import RequestValidator

def compute_twilio_signature(url: str, params: dict, auth_token: str) -> str:
    validator = RequestValidator(auth_token)
    return validator.compute_signature(url, params)
