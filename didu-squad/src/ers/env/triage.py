"""START triage (Simple Triage and Rapid Treatment), applied on scene by code."""
from __future__ import annotations

from ers.env.entities import Color, Vitals


def start_triage(v: Vitals) -> Color:
    if v.can_walk:
        return Color.GREEN
    if not v.breathing:
        return Color.BLACK
    if v.resp_rate > 30:
        return Color.RED
    if v.cap_refill_s > 2.0:
        return Color.RED
    if not v.follows_commands:
        return Color.RED
    return Color.YELLOW


def vitals_for(color: Color, rng) -> Vitals:
    """Generate vitals that START classifies as `color` (used by the data generator)."""
    if color == Color.GREEN:
        return Vitals(True, True, int(rng.integers(12, 25)), round(float(rng.uniform(0.8, 2.0)), 1), True)
    if color == Color.BLACK:
        return Vitals(False, False, 0, 4.0, False)
    if color == Color.YELLOW:
        return Vitals(False, True, int(rng.integers(12, 30)), round(float(rng.uniform(0.8, 2.0)), 1), True)
    # red: one of the three red criteria
    which = int(rng.integers(0, 3))
    rr = int(rng.integers(31, 40)) if which == 0 else int(rng.integers(12, 30))
    cr = round(float(rng.uniform(2.5, 4.0)), 1) if which == 1 else round(float(rng.uniform(0.8, 2.0)), 1)
    fc = which != 2
    return Vitals(False, True, rr, cr, fc)
