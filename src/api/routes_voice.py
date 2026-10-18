from fastapi import APIRouter, Request, Response, Depends, Query
from src.security.signature import validate_twilio_request
from src.services.webhook_service import WebhookService

router = APIRouter(prefix="/api/v1/voice", tags=["Voice Webhooks"])

def get_webhook_service() -> WebhookService:
    return WebhookService()

@router.post("/incoming", dependencies=[Depends(validate_twilio_request)])
async def voice_incoming(
    request: Request,
    service: WebhookService = Depends(get_webhook_service)
):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    caller_phone = form_data.get("From", "")

    twiml = service.handle_incoming_call(call_sid=call_sid, caller_phone=caller_phone)
    return Response(content=twiml, media_type="application/xml")

@router.post("/turn", dependencies=[Depends(validate_twilio_request)])
async def voice_turn(
    request: Request,
    turn_id: int = Query(default=1),
    service: WebhookService = Depends(get_webhook_service)
):
    form_data = await request.form()
    form_dict = dict(form_data)
    call_sid = form_dict.get("CallSid", "")
    speech_result = form_dict.get("SpeechResult", "")

    twiml = service.handle_turn(
        call_sid=call_sid,
        turn_id=turn_id,
        speech_result=speech_result,
        form_data=form_dict
    )
    return Response(content=twiml, media_type="application/xml")
