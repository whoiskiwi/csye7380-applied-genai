"""Actions a policy (or an agent, via its policy) can submit to the CAD."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class AssignUnits:
    incident_id: str
    ambulance_ids: list[str] = field(default_factory=list)
    team_ids: list[str] = field(default_factory=list)
    by: str = "policy"


@dataclass
class ReassignUnit:
    """Redirect an ambulance that is assigned but carries no patients to another incident."""
    ambulance_id: str
    incident_id: str
    by: str = "policy"


@dataclass
class CommitTransport:
    ambulance_id: str
    patient_ids: list[str]
    hospital_id: str
    by: str = "policy"


@dataclass
class AllocatePoolStaff:
    staff_id: str
    hospital_id: str
    by: str = "policy"


@dataclass
class SetDiversion:
    hospital_id: str
    on: bool
    by: str = "policy"


@dataclass
class SetPriority:
    incident_id: str
    priority: int
    by: str = "policy"


Action = AssignUnits | ReassignUnit | CommitTransport | AllocatePoolStaff | SetDiversion | SetPriority


def action_to_dict(a: Action) -> dict:
    return {"action": type(a).__name__, **asdict(a)}
