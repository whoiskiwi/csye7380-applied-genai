"""Read-only tools for each agent. They query the simulation; none of them can change it."""
from __future__ import annotations

import json

from agents import function_tool

from ers.env.entities import Color


def incident_assessment_tools(sim):
    @function_tool
    def incident_details(incident_id: str) -> str:
        """Full record of one incident: type, call time, dispatch code, reported and (if triaged) true severities."""
        i = sim.incidents.get(incident_id)
        if i is None:
            return "unknown incident"
        d = {"id": i.id, "type": i.type, "t_call": i.t_call, "dispatch_code": i.dispatch_code,
             "reported_victims": i.reported_victims, "reported_colors": i.reported_colors, "triaged": i.triaged}
        if i.triaged:
            d["true_colors"] = {c.value: sum(p.true_color == c for p in i.patients) for c in Color}
        return json.dumps(d)
    return [incident_details]


def dispatch_tools(sim):
    @function_tool
    def unit_eta(unit_id: str, incident_id: str) -> str:
        """Travel minutes for an ambulance or rescue team to reach an incident."""
        u = sim.ambulances.get(unit_id) or sim.teams.get(unit_id)
        i = sim.incidents.get(incident_id)
        return "unknown" if u is None or i is None else str(sim.geo.travel_time(u.location, i.location))

    @function_tool
    def hospital_eta(ambulance_id: str, hospital_id: str) -> str:
        """Travel minutes for an ambulance to reach a hospital."""
        u = sim.ambulances.get(ambulance_id)
        h = sim.board.hospitals.get(hospital_id)
        return "unknown" if u is None or h is None else str(sim.geo.travel_time(u.location, h.location))
    return [unit_eta, hospital_eta]


def hospital_coordination_tools(sim, reports: dict):
    @function_tool
    def hospital_board() -> str:
        """Latest capacity report of every hospital (what each says it will still accept)."""
        return json.dumps(reports)

    @function_tool
    def capability(hospital_id: str, category: str) -> str:
        """Capability level of a hospital for a patient category: 2 match, 1 acceptable, 0 cannot treat."""
        try:
            return str(sim.board.level(hospital_id, category))
        except Exception:
            return "unknown"
    return [hospital_board, capability]


def hospital_tools(sim, hid: str):
    @function_tool
    def my_capacity() -> str:
        """Your ED beds in use, total beds, and the most red/yellow/green patients you could physically take now."""
        h = sim.board.hospitals[hid]
        return json.dumps({"beds_used": h.beds_used, "beds_total": h.er_beds,
                           "max_possible": sim.board.intake_limits(hid, sim.t)})

    @function_tool
    def my_staff() -> str:
        """Your doctors and nurses with their skill and spare workload (1.0 = fully free)."""
        return json.dumps([{"id": s.id, "role": s.role, "skill": s.skill, "spare": round(s.spare(sim.t), 2)}
                           for s in sim.board.staff if s.hospital_id == hid])
    return [my_capacity, my_staff]


def resource_allocation_tools(conflict: dict):
    @function_tool
    def conflict_summary() -> str:
        """The current conflict: both sides' positions and the resources involved."""
        return json.dumps(conflict)
    return [conflict_summary]
