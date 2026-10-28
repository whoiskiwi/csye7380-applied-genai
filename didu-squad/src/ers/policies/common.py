"""Helpers shared by all policies (baselines and agents)."""
from __future__ import annotations

import math

from ers.config import assumptions

from ers.env.entities import COLOR_RANK, Ambulance, Color, Incident, Patient, PatientStatus, RescueTeam, UnitStatus

CODE_RANK = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "OMEGA": 5}


def load_units() -> dict[str, float]:
    return assumptions()["units"]["load_units"]


def trips_needed(sim, inc: Incident) -> int:
    """Ambulance trips still needed, using load units (red fills an ambulance, two yellows, three greens)."""
    u = load_units()
    if not inc.triaged:
        counts = dict(inc.reported_colors)
    else:
        left = [p for p in inc.patients if p.status in (PatientStatus.TRAPPED, PatientStatus.EXTRICATING,
                                                         PatientStatus.READY)]
        counts = {c.value: sum(p.true_color == c for p in left) for c in Color}
    units = sum(u.get(c, 0) * n for c, n in counts.items() if c != "black")
    return math.ceil(units / 2 - 1e-9)


def ambulances_short(sim, inc: Incident) -> int:
    ambs, _ = sim.units_at(inc)
    empty = [a for a in ambs if not a.patient_ids]
    return max(0, trips_needed(sim, inc) - len(empty))


def needs_team(sim, inc: Incident) -> bool:
    if not inc.needs_rescue:
        return False
    _, teams = sim.units_at(inc)
    if teams:
        return False
    if not inc.triaged:
        return True
    return any(p.status == PatientStatus.TRAPPED for p in inc.patients)


def nearest(sim, units: list, target) -> list:
    return sorted(units, key=lambda u: (sim.geo.travel_time(u.location, target), u.id))


def pick_load(sim, ready: list[Patient], capacity: int = 2) -> list[Patient]:
    """Most severe first, filling the ambulance by load units (red 2, yellow 1, green 2/3; capacity 2)."""
    u = load_units()
    ready = sorted(ready, key=lambda p: (COLOR_RANK[p.true_color], p.t_ready or 0, p.id))
    load, used = [], 0.0
    for p in ready:
        need = u[p.true_color.value]
        if used + need <= capacity + 1e-9:
            load.append(p)
            used += need
    return load


def admissible(sim, hid: str, patients: list[Patient]) -> bool:
    """Would the hospital accept this whole load right now? (pure check, no side effects)"""
    board, t = sim.board, sim.t
    admitted = []
    ok = True
    for p in patients:
        good, _ = board.can_admit(hid, p, p.true_color, t)
        if not good:
            ok = False
            break
        board.admit(hid, p, p.true_color, t)
        admitted.append(p)
    for p in admitted:
        board.release(hid, p, p.true_color)
        board.hospitals[hid].patient_ids.remove(p.id)
    return ok


def eta(sim, a, b) -> int:
    return sim.geo.travel_time(a, b)
