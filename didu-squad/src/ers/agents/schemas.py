"""Structured outputs of each agent (used as the SDK `output_type`)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ers.messaging.schema import ReasonCode


# ---------- Incident Assessment Agent ----------
class IncidentPriority(BaseModel):
    incident_id: str
    priority: int                       # 1 = most urgent
    urgency: Literal["critical", "high", "medium", "low"]
    reason: str


class PreAlert(BaseModel):
    incident_id: str
    expected_red: int
    expected_yellow: int
    expected_green: int


class Escalation(BaseModel):
    incident_id: str
    reason: str


class AssessmentOutput(BaseModel):
    ranking: list[str]                  # every incident id, most urgent first
    critical: list[str]                 # ids that are life-threatening right now
    pre_alerts: list[PreAlert]
    escalations: list[Escalation]


# ---------- Dispatch Agent ----------
class UnitAssignment(BaseModel):
    incident_id: str
    ambulance_ids: list[str]
    team_ids: list[str]
    reason: str


class DispatchUnitsOutput(BaseModel):
    assignments: list[UnitAssignment]
    conflict: bool                      # True if two incidents need the same scarce unit
    conflict_note: str


class TransportProposal(BaseModel):
    ambulance_id: str
    hospital_id: str
    reason_code: ReasonCode
    rationale: str


class TransportProposalsOutput(BaseModel):
    proposals: list[TransportProposal]


class TransportReply(BaseModel):
    ambulance_id: str
    verdict: Literal["ACCEPT", "COUNTER"]
    hospital_id: str
    reason_code: ReasonCode
    rationale: str


class TransportRepliesOutput(BaseModel):
    replies: list[TransportReply]


# ---------- Hospital agents ----------
class HospitalReport(BaseModel):
    hospital_id: str
    accept_red: int
    accept_yellow: int
    accept_green: int
    divert: bool
    reason_code: ReasonCode
    request_nurses: int
    request_doctors: int
    note: str


class PoolReply(BaseModel):
    hospital_id: str
    verdict: Literal["ACCEPT", "COUNTER"]
    min_nurses: int
    min_doctors: int
    reason: str


# ---------- Hospital Coordination Agent ----------
class AdmissionDecision(BaseModel):
    ambulance_id: str
    verdict: Literal["ACCEPT", "REJECT", "COUNTER"]
    hospital_id: str                    # proposed hospital for ACCEPT, alternative for COUNTER, "" for REJECT
    reason_code: ReasonCode
    rationale: str


class AdmissionDecisionsOutput(BaseModel):
    decisions: list[AdmissionDecision]


class PoolAllocation(BaseModel):
    hospital_id: str
    nurses: int
    doctors: int


class PoolPlanOutput(BaseModel):
    allocations: list[PoolAllocation]
    rationale: str


# ---------- Resource Allocation Agent ----------
class TransportRuling(BaseModel):
    ambulance_id: str
    hospital_id: str


class RulingOutput(BaseModel):
    unit_assignments: list[UnitAssignment]
    transport_rulings: list[TransportRuling]
    pool_allocations: list[PoolAllocation]
    rationale: str
