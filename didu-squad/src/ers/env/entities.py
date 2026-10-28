"""Plain data objects for the simulated emergency environment.

Everything here is mutable state owned by the simulator; agents only ever see
read-only views produced by the tools layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

Point = tuple[float, float]


class Color(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLACK = "black"


# Lower rank = more urgent; used for sorting.
COLOR_RANK = {Color.RED: 0, Color.YELLOW: 1, Color.GREEN: 2, Color.BLACK: 3}


class PatientStatus(str, Enum):
    WAITING = "waiting"            # on scene, not yet triaged
    TRAPPED = "trapped"            # triaged, needs extrication first
    EXTRICATING = "extricating"
    READY = "ready"                # triaged and free, waiting for transport
    ASSIGNED = "assigned"          # transport committed, being loaded
    TRANSPORTING = "transporting"
    IN_TREATMENT = "in_treatment"
    DISCHARGED = "discharged"      # treatment finished, resources released
    DECEASED = "deceased"          # black tag, never transported


class UnitStatus(str, Enum):
    IDLE = "idle"
    EN_ROUTE = "en_route"          # driving to a scene
    ON_SCENE = "on_scene"
    TRANSPORTING = "transporting"
    HANDOVER = "handover"
    WORKING = "working"            # rescue team extricating


@dataclass
class Vitals:
    can_walk: bool
    breathing: bool                # after airway repositioning
    resp_rate: int
    cap_refill_s: float
    follows_commands: bool


@dataclass
class Patient:
    id: str
    incident_id: str
    age: int
    category: str                  # adult_trauma, child_trauma, adult_burn, ... (see hospitals.yaml)
    vitals: Vitals
    needs_extrication: bool
    reported_color: Color          # what the call-taker heard (noisy)
    true_color: Color | None = None   # set by START on scene
    status: PatientStatus = PatientStatus.WAITING
    deteriorated_at: int | None = None
    hospital_id: str | None = None
    ambulance_id: str | None = None
    t_ready: int | None = None
    t_departed: int | None = None
    t_arrived: int | None = None
    t_treatment_end: int | None = None
    # resources held at the hospital from commit until treatment ends
    held_doctor_id: str | None = None

    @property
    def is_child(self) -> bool:
        return self.age < 16


@dataclass
class Incident:
    id: str
    t_call: int
    location: Point
    type: str                      # crash, poisoning, fire, collapse, cardiac_arrest, stroke, ...
    patients: list[Patient]
    reported_victims: int
    dispatch_code: str             # protocol determinant: OMEGA, A, B, C, D, E
    reported_colors: dict[str, int] = field(default_factory=dict)   # call-taker's (noisy) severity counts
    description: str = ""
    needs_rescue: bool = False     # entrapment / fire -> a rescue team must extricate
    is_major: bool = False
    priority: int | None = None    # rank set by the Incident Assessment Agent / policy (1 = most urgent)
    t_first_unit: int | None = None
    triaged: bool = False

    @property
    def victims(self) -> int:
        return len(self.patients)


@dataclass
class Ambulance:
    id: str
    location: Point
    als: bool
    capacity: int = 2
    status: UnitStatus = UnitStatus.IDLE
    incident_id: str | None = None
    hospital_id: str | None = None
    patient_ids: list[str] = field(default_factory=list)
    busy_until: int | None = None
    trips: int = 0
    busy_minutes: int = 0
    # current leg, for drawing movement on the map
    leg_from: Point | None = None
    leg_to: Point | None = None
    leg_start: int | None = None
    leg_end: int | None = None
    leg_seq: int = 0               # bumped on every new trip; a redirected trip's old arrival is ignored


@dataclass
class RescueTeam:
    id: str
    location: Point
    skills: list[str]              # rescue, fire, hazmat
    status: UnitStatus = UnitStatus.IDLE
    incident_id: str | None = None
    busy_until: int | None = None
    busy_minutes: int = 0
    leg_from: Point | None = None
    leg_to: Point | None = None
    leg_start: int | None = None
    leg_end: int | None = None


@dataclass
class Staff:
    id: str
    role: str                      # doctor | nurse
    skill: str                     # trauma, burn, emergency, pediatric, cardiology, nurse
    hospital_id: str | None        # None while in the regional pool
    workload_limit: float = 1.0
    load: float = 0.0
    on_duty_from: int = 0          # pool staff arrive after a delay

    def spare(self, t: int) -> float:
        return 0.0 if t < self.on_duty_from else self.workload_limit - self.load


@dataclass
class Hospital:
    id: str
    name: str
    location: Point
    er_beds: int
    beds_used: int = 0
    diversion: bool = False
    patient_ids: list[str] = field(default_factory=list)

    @property
    def beds_free(self) -> int:
        return self.er_beds - self.beds_used
