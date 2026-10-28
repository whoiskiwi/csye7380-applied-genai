"""Outcome metrics computed from a finished simulation."""
from __future__ import annotations

import numpy as np

from ers.env.entities import Color, PatientStatus
from ers.env.outcomes import is_served


def compute_metrics(sim) -> dict:
    incidents = list(sim.incidents.values())
    patients = list(sim.patients.values())
    board = sim.board
    end_t = max(sim.t, 1)

    def level(p):
        return board.level(p.hospital_id, p.category) if p.hospital_id and p.t_arrived is not None else None

    response = [i.t_first_unit - i.t_call for i in incidents if i.t_first_unit is not None]
    transportable = [p for p in patients if p.true_color != Color.BLACK]
    served = [p for p in transportable if is_served(p, sim.incidents[p.incident_id], level(p))]
    reds = [p for p in transportable if p.true_color == Color.RED]
    red_served = [p for p in reds if p in served]
    arrived = [p for p in transportable if p.t_arrived is not None]
    matched = [p for p in arrived if level(p) == 2]

    unserved_critical = 0
    for inc in incidents:
        inc_reds = [p for p in inc.patients if p.true_color == Color.RED]
        if inc_reds and not all(p in served for p in inc_reds):
            unserved_critical += 1

    time_critical = [i for i in incidents if i.type in ("cardiac_arrest", "stroke")]
    tc_response = [i.t_first_unit - i.t_call for i in time_critical if i.t_first_unit is not None]

    n_amb = max(1, len(sim.ambulances))
    n_team = max(1, len(sim.teams))
    actions = [r for r in sim.logs if r["type"] == "action"]
    rejected = [r for r in actions if not r["ok"]]
    msgs = sim.messages
    threads = {m.get("thread_id") for m in msgs if m.get("thread_id")}
    escalations = [m for m in msgs if m.get("recipient") == "ResourceAllocation" and m.get("message_type") == "REQUEST"]

    return {
        "policy": sim.policy.name,
        "scenario": sim.scenario.name,
        "seed": sim.scenario.seed,
        "end_time_min": sim.t,
        "incidents": len(incidents),
        "victims": len(patients),
        "victims_transportable": len(transportable),
        "victims_served": len(served),
        "served_rate": round(len(served) / max(1, len(transportable)), 4),
        "red_total": len(reds),
        "red_in_window_rate": round(len(red_served) / max(1, len(reds)), 4),
        "unserved_critical_incidents": unserved_critical,
        "not_transported": sum(p.t_arrived is None for p in transportable),
        "capability_match_rate": round(len(matched) / max(1, len(arrived)), 4),
        "response_time_mean": round(float(np.mean(response)), 2) if response else None,
        "response_time_p90": round(float(np.percentile(response, 90)), 2) if response else None,
        "red_call_to_hospital_mean": round(float(np.mean([p.t_arrived - sim.incidents[p.incident_id].t_call
                                                          for p in reds if p.t_arrived is not None])), 2)
        if any(p.t_arrived is not None for p in reds) else None,
        "time_critical_response_mean": round(float(np.mean(tc_response)), 2) if tc_response else None,
        "ambulance_utilisation": round(sum(u.busy_minutes for u in sim.ambulances.values()) / (n_amb * end_t), 4),
        "team_utilisation": round(sum(u.busy_minutes for u in sim.teams.values()) / (n_team * end_t), 4),
        "cad_rejections": len(rejected),
        "negotiation_threads": len(threads),
        "escalations": len(escalations),
        "messages": len(msgs),
        "deteriorated": sum(p.deteriorated_at is not None for p in patients),
        "deceased_on_scene": sum(p.status == PatientStatus.DECEASED for p in patients),
    }
