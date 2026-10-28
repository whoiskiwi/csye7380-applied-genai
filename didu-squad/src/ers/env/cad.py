"""CAD + hospital status board: checks every action against the rules and executes it.

The CAD makes no decisions. It only refuses actions that break a rule and applies
the ones that do not, scheduling the follow-up events in the simulator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ers.env.actions import (Action, AllocatePoolStaff, AssignUnits, CommitTransport, ReassignUnit, SetDiversion,
                             SetPriority, action_to_dict)
from ers.env.entities import Color, PatientStatus, UnitStatus

if TYPE_CHECKING:
    from ers.env.simulator import Simulation


@dataclass
class Result:
    ok: bool
    reason: str = "OK"


class CAD:
    def __init__(self, sim: "Simulation"):
        self.sim = sim
        self.violations = 0

    def apply(self, a: Action) -> Result:
        handler = {
            AssignUnits: self._assign,
            ReassignUnit: self._reassign,
            CommitTransport: self._transport,
            AllocatePoolStaff: self._pool,
            SetDiversion: self._diversion,
            SetPriority: self._priority,
        }[type(a)]
        res = handler(a)
        if not res.ok:
            self.violations += 1
        self.sim.log("action", ok=res.ok, reason=res.reason, **action_to_dict(a))
        return res

    # ---------- dispatch ----------
    def _assign(self, a: AssignUnits) -> Result:
        sim, t = self.sim, self.sim.t
        inc = sim.incidents.get(a.incident_id)
        if inc is None or inc.t_call > t:
            return Result(False, "UNKNOWN_INCIDENT")
        if not a.ambulance_ids and not a.team_ids:
            return Result(False, "EMPTY_ASSIGNMENT")
        for uid in a.ambulance_ids:
            amb = sim.ambulances.get(uid)
            if amb is None:
                return Result(False, "UNKNOWN_UNIT")
            if amb.status != UnitStatus.IDLE:
                return Result(False, "UNIT_BUSY")
        for uid in a.team_ids:
            team = sim.teams.get(uid)
            if team is None:
                return Result(False, "UNKNOWN_UNIT")
            if team.status != UnitStatus.IDLE:
                return Result(False, "UNIT_BUSY")
        if len(set(a.ambulance_ids)) != len(a.ambulance_ids) or len(set(a.team_ids)) != len(a.team_ids):
            return Result(False, "DUPLICATE_UNIT")
        for uid in a.ambulance_ids:
            sim.dispatch_ambulance(sim.ambulances[uid], inc)
        for uid in a.team_ids:
            sim.dispatch_team(sim.teams[uid], inc)
        return Result(True)

    def _reassign(self, a: ReassignUnit) -> Result:
        sim, t = self.sim, self.sim.t
        amb = sim.ambulances.get(a.ambulance_id)
        inc = sim.incidents.get(a.incident_id)
        if amb is None:
            return Result(False, "UNKNOWN_UNIT")
        if inc is None or inc.t_call > t or sim.incident_done(inc):
            return Result(False, "UNKNOWN_INCIDENT")
        if amb.status not in (UnitStatus.EN_ROUTE, UnitStatus.ON_SCENE) or amb.patient_ids:
            return Result(False, "UNIT_BUSY")          # only an empty, assigned ambulance can be redirected
        if amb.incident_id == inc.id:
            return Result(False, "SAME_INCIDENT")
        sim.log("redirect", unit=amb.id, from_incident=amb.incident_id, to_incident=inc.id)
        sim.dispatch_ambulance(amb, inc)
        return Result(True)

    # ---------- transport ----------
    def _transport(self, a: CommitTransport) -> Result:
        sim, t = self.sim, self.sim.t
        amb = sim.ambulances.get(a.ambulance_id)
        if amb is None:
            return Result(False, "UNKNOWN_UNIT")
        if amb.status != UnitStatus.ON_SCENE or amb.patient_ids:
            return Result(False, "UNIT_NOT_ON_SCENE")
        if not a.patient_ids:
            return Result(False, "NO_PATIENTS")
        if a.hospital_id not in sim.board.hospitals:
            return Result(False, "UNKNOWN_HOSPITAL")
        patients = []
        for pid in a.patient_ids:
            p = sim.patients.get(pid)
            if p is None or p.incident_id != amb.incident_id:
                return Result(False, "PATIENT_NOT_AT_SCENE")
            if p.status != PatientStatus.READY:
                return Result(False, "PATIENT_NOT_READY")
            patients.append(p)
        units = sim.cfg["units"]["load_units"]
        if sum(units[p.true_color.value] for p in patients) > amb.capacity + 1e-9:
            return Result(False, "OVER_CAPACITY")   # red fills an ambulance; two yellows; three greens
        # admission check for the whole load (resources are reserved now; no refusal after departure)
        reserved = []
        for p in patients:
            ok, reason = sim.board.can_admit(a.hospital_id, p, p.true_color, t)
            if not ok:
                for q in reserved:
                    sim.board.release(a.hospital_id, q, q.true_color)
                return Result(False, reason)
            sim.board.admit(a.hospital_id, p, p.true_color, t)
            reserved.append(p)
        sim.start_transport(amb, patients, a.hospital_id)
        return Result(True)

    # ---------- staff pool ----------
    def _pool(self, a: AllocatePoolStaff) -> Result:
        sim = self.sim
        s = next((s for s in sim.board.staff if s.id == a.staff_id), None)
        if s is None:
            return Result(False, "UNKNOWN_STAFF")
        if s.hospital_id is not None:
            return Result(False, "STAFF_NOT_IN_POOL")
        if a.hospital_id not in sim.board.hospitals:
            return Result(False, "UNKNOWN_HOSPITAL")
        sim.board.assign_pool(a.staff_id, a.hospital_id, sim.t)
        return Result(True)

    def _diversion(self, a: SetDiversion) -> Result:
        h = self.sim.board.hospitals.get(a.hospital_id)
        if h is None:
            return Result(False, "UNKNOWN_HOSPITAL")
        h.diversion = a.on      # patients already committed keep their reservation
        return Result(True)

    def _priority(self, a: SetPriority) -> Result:
        inc = self.sim.incidents.get(a.incident_id)
        if inc is None:
            return Result(False, "UNKNOWN_INCIDENT")
        inc.priority = a.priority
        return Result(True)
