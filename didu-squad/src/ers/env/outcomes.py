"""Outcome model: a patient counts as served when they reach a capability-matched
hospital inside their treatment window."""
from __future__ import annotations

from ers.config import assumptions
from ers.env.entities import Color, Incident, Patient


def window_deadline(p: Patient, inc: Incident) -> int | None:
    """Latest arrival minute that still counts as served (None = no window)."""
    w = assumptions()["outcomes"]["window_min"]
    color = p.true_color or p.reported_color
    if color == Color.RED:
        start = p.deteriorated_at if p.deteriorated_at is not None else inc.t_call
        return start + w["red"]
    if color == Color.YELLOW:
        return inc.t_call + w["yellow"]
    return None


def is_served(p: Patient, inc: Incident, capability_level: int | None) -> bool:
    if p.true_color == Color.BLACK or p.t_arrived is None or capability_level is None:
        return False
    if p.true_color == Color.GREEN:
        return capability_level >= 1
    deadline = window_deadline(p, inc)
    return capability_level == 2 and p.t_arrived <= deadline
