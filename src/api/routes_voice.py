from fastapi import APIRouter, Request, Response, Depends, Query
from src.security.signature import validate_twilio_request
from src.services.webhook_service import WebhookService
from src.services.conversation import ConversationStateMachine

router = APIRouter(prefix="/api/v1/voice", tags=["Voice Webhooks"])

_conversation_machine = ConversationStateMachine()

def get_webhook_service() -> WebhookService:
    return WebhookService()

def get_conversation_machine() -> ConversationStateMachine:
    return _conversation_machine

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
    state: str = Query(default="GREETING"),
    service: WebhookService = Depends(get_webhook_service),
    machine: ConversationStateMachine = Depends(get_conversation_machine)
):
    form_data = await request.form()
    form_dict = dict(form_data)
    call_sid = form_dict.get("CallSid", "")
    speech_result = form_dict.get("SpeechResult", "")

    idempotency_key = f"{call_sid}:turn:{turn_id}"
    cached_twiml = service.event_repo.get_event(idempotency_key)
    if cached_twiml:
        return Response(content=cached_twiml, media_type="application/xml")

    twiml, next_state = await machine.process_turn(
        call_sid=call_sid,
        turn_id=turn_id,
        user_utterance=speech_result,
        current_state=state
    )

    import json
    service.event_repo.record_event(
        idempotency_key=idempotency_key,
        call_sid=call_sid,
        raw_payload=json.dumps(form_dict),
        response_twiml=twiml
    )

    return Response(content=twiml, media_type="application/xml")
