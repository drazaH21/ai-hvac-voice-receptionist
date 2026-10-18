import json
from src.db.models import CallRepository, WebhookEventRepository

class WebhookService:
    def __init__(self, db_path: str = None):
        self.call_repo = CallRepository(db_path)
        self.event_repo = WebhookEventRepository(db_path)

    def handle_incoming_call(self, call_sid: str, caller_phone: str) -> str:
        idempotency_key = f"{call_sid}:incoming:0"
        cached_twiml = self.event_repo.get_event(idempotency_key)
        if cached_twiml:
            return cached_twiml

        self.call_repo.get_or_create_call(call_sid, caller_phone)
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Response>\n'
            '    <Gather input="speech" action="/api/v1/voice/turn?turn_id=1" method="POST" timeout="3">\n'
            '        <Say>Thanks for calling Premier Home Services. How can we help you today?</Say>\n'
            '    </Gather>\n'
            '    <Say>We did not receive any input. Please call back soon. Goodbye.</Say>\n'
            '</Response>'
        )

        payload_json = json.dumps({"CallSid": call_sid, "From": caller_phone})
        self.event_repo.record_event(idempotency_key, call_sid, payload_json, twiml)
        return twiml

    def handle_turn(self, call_sid: str, turn_id: int, speech_result: str, form_data: dict) -> str:
        idempotency_key = f"{call_sid}:turn:{turn_id}"
        cached_twiml = self.event_repo.get_event(idempotency_key)
        if cached_twiml:
            return cached_twiml

        next_turn = turn_id + 1
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Response>\n'
            f'    <Gather input="speech" action="/api/v1/voice/turn?turn_id={next_turn}" method="POST" timeout="3">\n'
            f'        <Say>Got it. You said: {speech_result}. Could I also get your full name?</Say>\n'
            '    </Gather>\n'
            '    <Say>We did not receive a response. Goodbye.</Say>\n'
            '</Response>'
        )

        self.event_repo.record_event(idempotency_key, call_sid, json.dumps(form_data), twiml)
        return twiml
