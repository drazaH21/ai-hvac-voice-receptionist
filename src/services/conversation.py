from typing import Tuple, Dict, Any
from src.db.models import AppointmentRepository, CallRepository
from src.services.llm_extractor import LLMExtractor
from src.schemas.extraction import ExtractedCallIntent
from src.logging import logger

class ConversationStateMachine:
    def __init__(self, db_path: str = None, extractor: LLMExtractor = None):
        self.db_path = db_path
        self.appointment_repo = AppointmentRepository(db_path)
        self.call_repo = CallRepository(db_path)
        self.extractor = extractor or LLMExtractor()
        self.session_store: Dict[str, Dict[str, Any]] = {}

    async def process_turn(
        self,
        call_sid: str,
        turn_id: int,
        user_utterance: str,
        current_state: str = "GREETING"
    ) -> Tuple[str, str]:
        extracted: ExtractedCallIntent = await self.extractor.extract_intent(user_utterance)
        next_turn = turn_id + 1

        if current_state in ("GREETING", "COLLECTING_INFO"):
            session = self.session_store.setdefault(call_sid, {})
            if extracted.customer_name:
                session["customer_name"] = extracted.customer_name
            if extracted.service_needed:
                session["service_needed"] = extracted.service_needed
            if extracted.requested_time_text:
                session["slot_start"] = extracted.requested_time_text

            name = session.get("customer_name")
            service = session.get("service_needed")
            time_text = session.get("slot_start")

            if name and service:
                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    f'    <Gather input="speech" action="/api/v1/voice/turn?turn_id={next_turn}&amp;state=CONFIRMING" method="POST" timeout="3">\n'
                    f'        <Say>Thank you, {name}. I have you down for {service} at {time_text or "our next opening"}. Can you confirm if you would like me to book this?</Say>\n'
                    '    </Gather>\n'
                    '    <Say>We did not hear back. Goodbye.</Say>\n'
                    '</Response>'
                )
                return twiml, "CONFIRMING"
            else:
                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    f'    <Gather input="speech" action="/api/v1/voice/turn?turn_id={next_turn}&amp;state=COLLECTING_INFO" method="POST" timeout="3">\n'
                    '        <Say>Could you please provide your full name and the specific service you need?</Say>\n'
                    '    </Gather>\n'
                    '    <Say>We did not receive your details. Goodbye.</Say>\n'
                    '</Response>'
                )
                return twiml, "COLLECTING_INFO"

        elif current_state == "CONFIRMING":
            affirmative = any(word in user_utterance.lower() for word in ["yes", "confirm", "sure", "correct", "perfect", "okay"])
            if affirmative:
                session = self.session_store.get(call_sid, {})
                customer_name = session.get("customer_name", "Caller")
                service_needed = session.get("service_needed", "General Service")
                slot_start = session.get("slot_start", "2026-10-19T09:00:00Z")

                try:
                    self.appointment_repo.create_appointment(
                        call_sid=call_sid,
                        customer_name=customer_name,
                        service_needed=service_needed,
                        slot_start=slot_start
                    )
                except Exception as e:
                    logger.error(f"Failed to record appointment: {e}")

                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    f'    <Say>Your appointment for {service_needed} has been confirmed. Thank you for choosing Premier Home Services. Goodbye!</Say>\n'
                    '    <Hangup/>\n'
                    '</Response>'
                )
                return twiml, "BOOKED"
            else:
                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    f'    <Gather input="speech" action="/api/v1/voice/turn?turn_id={next_turn}&amp;state=COLLECTING_INFO" method="POST" timeout="3">\n'
                    '        <Say>Understood. What would you like to update or change?</Say>\n'
                    '    </Gather>\n'
                    '    <Say>Goodbye.</Say>\n'
                    '</Response>'
                )
                return twiml, "COLLECTING_INFO"

        return '<Response><Say>Goodbye.</Say><Hangup/></Response>', "CLOSED"
