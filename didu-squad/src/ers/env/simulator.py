"""Discrete-event simulator with a 1-minute clock.

Each minute: due events fire, new calls arrive, yellow patients left on scene may
deteriorate, then the policy is asked for actions, which go through the CAD.
Decisions take no simulated time.
"""
from __future__ import annotations

import heapq
import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from ers.config import assumptions
from ers.env.cad import CAD
from ers.env.entities import (Ambulance, Color, Incident, Patient, PatientStatus, RescueTeam,
                              UnitStatus)
from ers.env.geo import Geo
from ers.env.staff import HospitalBoard
from ers.env.triage import start_triage


@dataclass
class Scenario:
    name: str
    seed: int
    incidents: list[Incident]
    ambulances: list[Ambulance]
    teams: list[RescueTeam]
    board_overrides: dict = field(default_factory=dict)
    congestion: str = "normal"
    bridge_closed: bool = False


class Policy(Protocol):
    name: str

    def decide(self, sim: "Simulation") -> list: ...


class Simulation:
    def __init__(self, scenario: Scenario, policy: Policy):
        a = assumptions()
        self.cfg = a
        self.scenario = scenario
        self.policy = policy
        self.rng = np.random.default_rng(scenario.seed + 1)   # extrication durations etc.
        self.geo = Geo(scenario.congestion, scenario.bridge_closed)
        self.board = HospitalBoard(scenario.board_overrides)
        self.incidents: dict[str, Incident] = {i.id: i for i in scenario.incidents}
        self.patients: dict[str, Patient] = {p.id: p for i in scenario.incidents for p in i.patients}
        self.ambulances: dict[str, Ambulance] = {u.id: u for u in scenario.ambulances}
        self.teams: dict[str, RescueTeam] = {u.id: u for u in scenario.teams}
        self.cad = CAD(self)
        self.t = 0
        self.events: list = []
        self._seq = itertools.count()
        self.logs: list[dict] = []
        self.snapshots: list[dict] = []
        self.messages: list[dict] = []
        for p in self.patients.values():
            if p.true_color is None:
                p.true_color = start_triage(p.vitals)

    # ---------------- logging ----------------
    def log(self, type_: str, **data) -> None:
        self.logs.append({"t": self.t, "type": type_, **data})

    def log_message(self, msg: dict) -> None:
        self.messages.append({"sim_time": self.t, **msg})
        self.log("message", **msg)

    def submit(self, action):
        """Send one action to the CAD right away; later checks in the same minute see its effect."""
        return self.cad.apply(action)

    def schedule(self, t: int, fn: Callable[[], None]) -> None:
        heapq.heappush(self.events, (t, next(self._seq), fn))

    # ---------------- read-only helpers for policies ----------------
    def active_incidents(self) -> list[Incident]:
        return [i for i in self.incidents.values() if i.t_call <= self.t and not self.incident_done(i)]

    def incident_done(self, inc: Incident) -> bool:
        return all(p.status not in (PatientStatus.WAITING, PatientStatus.TRAPPED, PatientStatus.EXTRICATING,
                                    PatientStatus.READY) for p in inc.patients)

    def remaining_patients(self, inc: Incident) -> list[Patient]:
        """Patients still to be transported (black excluded once triaged)."""
        return [p for p in inc.patients if p.status in (PatientStatus.WAITING, PatientStatus.TRAPPED,
                                                         PatientStatus.EXTRICATING, PatientStatus.READY)]

    def units_at(self, inc: Incident) -> tuple[list[Ambulance], list[RescueTeam]]:
        ambs = [u for u in self.ambulances.values() if u.incident_id == inc.id
                and u.status in (UnitStatus.EN_ROUTE, UnitStatus.ON_SCENE)]
        teams = [u for u in self.teams.values() if u.incident_id == inc.id
                 and u.status in (UnitStatus.EN_ROUTE, UnitStatus.ON_SCENE, UnitStatus.WORKING)]
        return ambs, teams

    def visible_color(self, p: Patient) -> Color:
        """What a decision maker can know: the reported colour until the scene is triaged."""
        return p.true_color if self.incidents[p.incident_id].triaged else p.reported_color

    def idle_ambulances(self) -> list[Ambulance]:
        return [u for u in self.ambulances.values() if u.status == UnitStatus.IDLE]

    def idle_teams(self) -> list[RescueTeam]:
        return [u for u in self.teams.values() if u.status == UnitStatus.IDLE]

    def loading_queue(self) -> list[tuple[Ambulance, list[Patient]]]:
        """Ambulances on scene and empty, with the ready patients at their incident."""
        out = []
        for amb in self.ambulances.values():
            if amb.status == UnitStatus.ON_SCENE and not amb.patient_ids:
                ready = [p for p in self.incidents[amb.incident_id].patients if p.status == PatientStatus.READY]
                if ready:
                    out.append((amb, ready))
        return out

    # ---------------- unit movement (called by the CAD) ----------------
    def dispatch_ambulance(self, amb: Ambulance, inc: Incident) -> None:
        if amb.status == UnitStatus.EN_ROUTE:          # redirected mid-trip: start from where it is now
            amb.location = self.position(amb)
        amb.status, amb.incident_id = UnitStatus.EN_ROUTE, inc.id
        eta = self.t + self.geo.travel_time(amb.location, inc.location)
        amb.busy_until = eta
        self._leg(amb, amb.location, inc.location, eta)
        amb.leg_seq += 1
        seq = amb.leg_seq
        self.schedule(eta, lambda: self._ambulance_arrives(amb, inc, seq))

    def dispatch_team(self, team: RescueTeam, inc: Incident) -> None:
        team.status, team.incident_id = UnitStatus.EN_ROUTE, inc.id
        eta = self.t + self.geo.travel_time(team.location, inc.location)
        team.busy_until = eta
        self._leg(team, team.location, inc.location, eta)
        self.schedule(eta, lambda: self._team_arrives(team, inc))

    def start_transport(self, amb: Ambulance, patients: list[Patient], hid: str) -> None:
        for p in patients:
            p.status, p.hospital_id, p.ambulance_id = PatientStatus.ASSIGNED, hid, amb.id
        amb.patient_ids = [p.id for p in patients]
        amb.hospital_id = hid
        depart = self.t + self.cfg["units"]["scene_time_min"]
        self.schedule(depart, lambda: self._depart(amb, patients, hid))

    def _leg(self, unit, a, b, eta) -> None:
        unit.leg_from, unit.leg_to, unit.leg_start, unit.leg_end = a, b, self.t, eta

    def position(self, unit) -> tuple[float, float]:
        """Linear interpolation along the current leg (for the map only)."""
        if unit.leg_start is None or self.t >= unit.leg_end or unit.leg_end == unit.leg_start:
            return unit.location if unit.leg_to is None or self.t >= (unit.leg_end or 0) else unit.leg_from
        f = (self.t - unit.leg_start) / (unit.leg_end - unit.leg_start)
        return (round(unit.leg_from[0] + f * (unit.leg_to[0] - unit.leg_from[0]), 2),
                round(unit.leg_from[1] + f * (unit.leg_to[1] - unit.leg_from[1]), 2))

    def snapshot(self) -> dict:
        b = self.board
        return {
            "t": self.t,
            "ambulances": [{"id": u.id, "status": u.status.value, "pos": list(self.position(u)), "incident": u.incident_id,
                            "hospital": u.hospital_id, "patients": list(u.patient_ids), "als": u.als}
                           for u in self.ambulances.values()],
            "teams": [{"id": u.id, "status": u.status.value, "pos": list(self.position(u)), "incident": u.incident_id}
                      for u in self.teams.values()],
            "hospitals": [{"id": h.id, "beds_used": h.beds_used, "beds": h.er_beds, "diversion": h.diversion,
                           "doctors": len(b.members(h.id, "doctor")), "nurses": len(b.members(h.id, "nurse")),
                           "doctor_load": round(sum(s.load for s in b.members(h.id, "doctor")), 2),
                           "nurse_load": round(sum(s.load for s in b.members(h.id, "nurse")), 2),
                           "limits": b.intake_limits(h.id, self.t)} for h in b.hospitals.values()],
            "pool": {"doctors": len(b.pool_available("doctor")), "nurses": len(b.pool_available("nurse"))},
            "incidents": [{"id": i.id, "pos": list(i.location), "type": i.type, "priority": i.priority,
                           "code": i.dispatch_code, "triaged": i.triaged, "major": i.is_major,
                           "patients": {s.value: sum(p.status == s for p in i.patients) for s in PatientStatus
                                        if any(p.status == s for p in i.patients)},
                           "colors": ({c.value: sum(p.true_color == c for p in i.patients) for c in Color}
                                      if i.triaged else i.reported_colors)}
                          for i in self.incidents.values() if i.t_call <= self.t],
        }

    # ---------------- events ----------------
    def _first_on_scene(self, inc: Incident) -> None:
        if inc.triaged:
            return
        inc.triaged, inc.t_first_unit = True, self.t
        counts = {c.value: 0 for c in Color}
        for p in inc.patients:
            counts[p.true_color.value] += 1
            if p.true_color == Color.BLACK:
                p.status = PatientStatus.DECEASED
            elif p.needs_extrication:
                p.status = PatientStatus.TRAPPED
            else:
                p.status, p.t_ready = PatientStatus.READY, self.t
        self.log("scene_report", incident_id=inc.id, victims=inc.victims, colors=counts,
                 trapped=sum(p.status == PatientStatus.TRAPPED for p in inc.patients))

    def _ambulance_arrives(self, amb: Ambulance, inc: Incident, seq: int | None = None) -> None:
        if seq is not None and seq != amb.leg_seq:      # this trip was cancelled by a redirect
            return
        amb.status, amb.location = UnitStatus.ON_SCENE, inc.location
        self.log("unit_on_scene", unit=amb.id, incident_id=inc.id)
        self._first_on_scene(inc)

    def _team_arrives(self, team: RescueTeam, inc: Incident) -> None:
        team.status, team.location = UnitStatus.ON_SCENE, inc.location
        self.log("unit_on_scene", unit=team.id, incident_id=inc.id)
        self._first_on_scene(inc)
        self._next_extrication(team, inc)

    def _next_extrication(self, team: RescueTeam, inc: Incident) -> None:
        trapped = [p for p in inc.patients if p.status == PatientStatus.TRAPPED]
        if not trapped:
            team.status, team.incident_id, team.busy_until = UnitStatus.IDLE, None, None
            self.log("unit_free", unit=team.id)
            return
        trapped.sort(key=lambda p: (p.true_color != Color.RED, p.id))
        p = trapped[0]
        lo, hi = self.cfg["units"]["extrication_min"].get(inc.type, [10, 30])
        dur = int(self.rng.integers(lo, hi + 1))
        p.status, team.status = PatientStatus.EXTRICATING, UnitStatus.WORKING
        team.busy_until = self.t + dur

        def done():
            p.status, p.t_ready = PatientStatus.READY, self.t
            self.log("extricated", patient=p.id, incident_id=inc.id, unit=team.id)
            self._next_extrication(team, inc)
        self.schedule(self.t + dur, done)

    def _depart(self, amb: Ambulance, patients: list[Patient], hid: str) -> None:
        amb.status = UnitStatus.TRANSPORTING
        for p in patients:
            p.status, p.t_departed = PatientStatus.TRANSPORTING, self.t
        h = self.board.hospitals[hid]
        eta = self.t + self.geo.travel_time(amb.location, h.location)
        amb.busy_until = eta
        self._leg(amb, amb.location, h.location, eta)
        self.log("depart", unit=amb.id, patients=[p.id for p in patients], hospital_id=hid, eta=eta)
        self.schedule(eta, lambda: self._arrive_hospital(amb, patients, hid))

    def _arrive_hospital(self, amb: Ambulance, patients: list[Patient], hid: str) -> None:
        h = self.board.hospitals[hid]
        amb.status, amb.location = UnitStatus.HANDOVER, h.location
        tr = self.cfg["outcomes"]["treatment_min"]
        for p in patients:
            p.status, p.t_arrived = PatientStatus.IN_TREATMENT, self.t
            p.t_treatment_end = self.t + tr[p.true_color.value]
            self.schedule(p.t_treatment_end, lambda p=p: self._treatment_end(p))
        self.log("arrive_hospital", unit=amb.id, patients=[p.id for p in patients], hospital_id=hid)
        free_at = self.t + self.cfg["units"]["handover_time_min"]
        amb.busy_until = free_at
        self.schedule(free_at, lambda: self._ambulance_free(amb))

    def _ambulance_free(self, amb: Ambulance) -> None:
        amb.status, amb.incident_id, amb.hospital_id, amb.patient_ids, amb.busy_until = \
            UnitStatus.IDLE, None, None, [], None
        amb.trips += 1
        self.log("unit_free", unit=amb.id)

    def _treatment_end(self, p: Patient) -> None:
        self.board.release(p.hospital_id, p, p.true_color)
        p.status = PatientStatus.DISCHARGED
        self.log("treatment_end", patient=p.id, hospital_id=p.hospital_id)

    def _deteriorate(self) -> None:
        limit = self.cfg["outcomes"]["yellow_deteriorates_after_min"]
        for inc in self.incidents.values():
            if inc.t_call > self.t:
                continue
            for p in inc.patients:
                if (p.true_color == Color.YELLOW and p.deteriorated_at is None
                        and p.status in (PatientStatus.WAITING, PatientStatus.TRAPPED,
                                         PatientStatus.EXTRICATING, PatientStatus.READY)
                        and self.t - inc.t_call >= limit):
                    p.true_color, p.deteriorated_at = Color.RED, self.t
                    self.log("deteriorated", patient=p.id, incident_id=inc.id)

    # ---------------- main loop ----------------
    def run(self) -> "Simulation":
        call_window = self.cfg["simulation"]["call_window_min"]
        max_t = self.cfg["simulation"]["max_time_min"]
        calls = sorted(self.incidents.values(), key=lambda i: (i.t_call, i.id))
        for self.t in range(max_t + 1):
            while self.events and self.events[0][0] <= self.t:
                _, _, fn = heapq.heappop(self.events)
                fn()
            for inc in calls:
                if inc.t_call == self.t:
                    self.log("call", incident_id=inc.id, incident_type=inc.type, location=list(inc.location),
                             reported_victims=inc.reported_victims, dispatch_code=inc.dispatch_code)
            self._deteriorate()
            for action in self.policy.decide(self) or []:
                self.cad.apply(action)
            self._release_unneeded()
            self._tick_utilisation()
            self.snapshots.append(self.snapshot())
            if self.t >= call_window and all(p.status in (PatientStatus.IN_TREATMENT, PatientStatus.DISCHARGED,
                                                          PatientStatus.DECEASED) for p in self.patients.values()):
                break
        self.log("end")
        return self

    def _release_unneeded(self) -> None:
        """An empty ambulance on a scene with nobody left to carry goes back into service."""
        for amb in self.ambulances.values():
            if amb.status == UnitStatus.ON_SCENE and not amb.patient_ids:
                inc = self.incidents[amb.incident_id]
                waiting = [p for p in inc.patients if p.status in (PatientStatus.TRAPPED, PatientStatus.EXTRICATING,
                                                                   PatientStatus.READY)]
                if inc.triaged and not waiting:
                    amb.status, amb.incident_id, amb.busy_until = UnitStatus.IDLE, None, None
                    self.log("unit_free", unit=amb.id)

    def _tick_utilisation(self) -> None:
        for u in self.ambulances.values():
            if u.status != UnitStatus.IDLE:
                u.busy_minutes += 1
        for u in self.teams.values():
            if u.status != UnitStatus.IDLE:
                u.busy_minutes += 1

    def save_log(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for row in self.logs:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
