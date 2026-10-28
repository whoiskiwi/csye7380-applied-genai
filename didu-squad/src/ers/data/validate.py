"""Sanity checks on generated scenarios."""
from __future__ import annotations

from ers.env.simulator import Scenario
from ers.env.staff import HospitalBoard


def validate(s: Scenario) -> list[str]:
    problems = []
    ids = [i.id for i in s.incidents]
    pids = [p.id for i in s.incidents for p in i.patients]
    if len(set(ids)) != len(ids) or len(set(pids)) != len(pids):
        problems.append("duplicate ids")
    if not 10 <= len(s.incidents) <= 15:
        problems.append(f"{len(s.incidents)} incidents (expected 10-15)")
    for i in s.incidents:
        if not i.patients:
            problems.append(f"{i.id} has no victims")
        if i.reported_victims < 1 or sum(i.reported_colors.values()) != i.reported_victims:
            problems.append(f"{i.id} reported counts inconsistent")
        if not (0 <= i.location[0] <= 30 and 0 <= i.location[1] <= 30):
            problems.append(f"{i.id} outside map")
    board = HospitalBoard(s.board_overrides)
    for h in board.hospitals.values():
        if not 0 <= h.beds_used <= h.er_beds:
            problems.append(f"{h.id} bed count invalid")
    return problems
