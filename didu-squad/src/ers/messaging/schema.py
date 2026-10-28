"""Structured inter-agent messages (the five required fields plus threading metadata)."""
from __future__ import annotations

import itertools
from typing import Any, Literal

from pydantic import BaseModel, Field

MessageType = Literal["REQUEST", "PROPOSE", "ACCEPT", "REJECT", "COUNTER", "COMMIT", "INFORM"]

ReasonCode = Literal[
    "OK", "NO_BED", "NO_STAFF", "CAPABILITY_REQUIRED", "CAPABILITY_MISSING", "DIVERSION",
    "RESERVE_FOR_CRITICAL", "CLOSER_ALTERNATIVE", "HIGHER_PRIORITY", "UNIT_BUSY", "WINDOW_RISK",
    "STAFF_POOL", "LOAD_BALANCE", "ESCALATION",
]

AGENTS = ("IncidentAssessment", "Dispatch", "HospitalCoordination", "ResourceAllocation", "H1", "H2", "H3", "CAD")


class Message(BaseModel):
    message_id: str
    sim_time: int
    sender: str
    recipient: str
    message_type: MessageType
    incident_id: str | None = None
    proposed_action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    in_reply_to: str | None = None
    thread_id: str | None = None
    round: int = 1
    reason_code: str = "OK"


class MessageBus:
    """Creates messages with unique ids and writes every message to the simulation log."""

    def __init__(self, sim):
        self.sim = sim
        self._ids = itertools.count(1)
        self._threads = itertools.count(1)

    def new_thread(self) -> str:
        return f"T{next(self._threads):04d}"

    def send(self, sender: str, recipient: str, message_type: str, proposed_action: str, *,
             incident_id: str | None = None, payload: dict | None = None, in_reply_to: str | None = None,
             thread_id: str | None = None, round: int = 1, reason_code: str = "OK") -> Message:
        m = Message(message_id=f"M{next(self._ids):05d}", sim_time=self.sim.t, sender=sender, recipient=recipient,
                    message_type=message_type, incident_id=incident_id, proposed_action=proposed_action,
                    payload=payload or {}, in_reply_to=in_reply_to, thread_id=thread_id, round=round,
                    reason_code=reason_code)
        self.sim.log_message(m.model_dump())
        return m
