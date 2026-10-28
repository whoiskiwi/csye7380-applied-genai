"""B1 rule reference: field-triage guideline rules computed in code, no AI.

- Incidents ranked by dispatch code, then (after triage) by red count.
- ALS ambulances preferred for incidents with red patients or E/D codes.
- Destination: the closest capability-matched hospital that keeps the patient inside the
  window; otherwise the closest hospital that can accept. Green patients avoid the
  trauma center when another hospital can take them.
- A hospital that can no longer take yellow patients for lack of nurses gets pool staff first-come.
"""
from __future__ import annotations

from ers.config import assumptions
from ers.env.actions import AllocatePoolStaff, AssignUnits, CommitTransport
from ers.env.entities import Color, PatientStatus
from ers.env.outcomes import window_deadline
from ers.policies.common import CODE_RANK, admissible, ambulances_short, nearest, needs_team, pick_load


def incident_rank(sim, inc):
    reds = (sum(p.true_color == Color.RED and p.status != PatientStatus.DECEASED for p in inc.patients)
            if inc.triaged else inc.reported_colors.get("red", 0))
    return (CODE_RANK.get(inc.dispatch_code, 9), -reds, inc.t_call, inc.id)


def choose_hospital(sim, amb, load):
    board = sim.board
    scene_time = assumptions()["units"]["scene_time_min"]
    lead = max(load, key=lambda p: (p.true_color == Color.RED, p.true_color == Color.YELLOW))
    inc = sim.incidents[lead.incident_id]
    by_eta = sorted(board.ids, key=lambda h: (sim.geo.travel_time(amb.location, board.hospitals[h].location), h))
    deadline = window_deadline(lead, inc)
    if lead.true_color == Color.GREEN:
        non_trauma = [h for h in by_eta if h != "H1" and all(board.level(h, p.category) >= 1 for p in load)]
        for hid in non_trauma + by_eta:
            if admissible(sim, hid, load):
                return hid
        return None
    for hid in by_eta:
        arrive = sim.t + scene_time + sim.geo.travel_time(amb.location, board.hospitals[hid].location)
        if all(board.level(hid, p.category) == 2 for p in load) and (deadline is None or arrive <= deadline) \
                and admissible(sim, hid, load):
            return hid
    for hid in by_eta:
        if admissible(sim, hid, load):
            return hid
    return None


class RulePolicy:
    name = "B1"

    def decide(self, sim) -> list:
        actions = []
        idle_a, idle_t = sim.idle_ambulances(), sim.idle_teams()
        for inc in sorted(sim.active_incidents(), key=lambda i: incident_rank(sim, i)):
            teams = []
            if needs_team(sim, inc) and idle_t:
                teams = nearest(sim, idle_t, inc.location)[:1]
                idle_t = [u for u in idle_t if u not in teams]
            n = ambulances_short(sim, inc)
            urgent = inc.dispatch_code in ("E", "D") or incident_rank(sim, inc)[1] < 0
            pool = sorted(idle_a, key=lambda u: (not (urgent and u.als), sim.geo.travel_time(u.location, inc.location), u.id))
            ambs = pool[:n]
            idle_a = [u for u in idle_a if u not in ambs]
            if ambs or teams:
                sim.submit(AssignUnits(inc.id, [u.id for u in ambs], [u.id for u in teams], by=self.name))
        taken: set[str] = set()
        for amb, ready in sim.loading_queue():
            ready = [p for p in ready if p.id not in taken]
            if not ready:
                continue
            load = pick_load(sim, ready, amb.capacity)
            hid = choose_hospital(sim, amb, load)
            if hid is None and len(load) > 1:
                load = load[:1]
                hid = choose_hospital(sim, amb, load)
            if hid:
                sim.submit(CommitTransport(amb.id, [p.id for p in load], hid, by=self.name))
                taken.update(p.id for p in load)
        # staff pool: first come, first served to a hospital that has beds but no nurse capacity left
        for hid in sim.board.ids:
            lim = sim.board.intake_limits(hid, sim.t)
            if lim["yellow"] == 0 and sim.board.hospitals[hid].beds_free > 0:
                pool = sim.board.pool_available("nurse")
                if pool:
                    sim.submit(AllocatePoolStaff(pool[0].id, hid, by=self.name))
        return actions
