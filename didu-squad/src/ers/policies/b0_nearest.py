"""B0 baseline: first come first served, nearest ambulance, nearest hospital that can take the patient.
No priorities, no negotiation."""
from __future__ import annotations

from ers.env.actions import AssignUnits, CommitTransport
from ers.policies.common import admissible, ambulances_short, nearest, needs_team, pick_load


class NearestPolicy:
    name = "B0"

    def decide(self, sim) -> list:
        actions = []
        idle_a, idle_t = sim.idle_ambulances(), sim.idle_teams()
        for inc in sorted(sim.active_incidents(), key=lambda i: (i.t_call, i.id)):
            teams = []
            if needs_team(sim, inc) and idle_t:
                teams = nearest(sim, idle_t, inc.location)[:1]
                idle_t = [u for u in idle_t if u not in teams]
            n = ambulances_short(sim, inc)
            ambs = nearest(sim, idle_a, inc.location)[:n]
            idle_a = [u for u in idle_a if u not in ambs]
            if ambs or teams:
                sim.submit(AssignUnits(inc.id, [u.id for u in ambs], [u.id for u in teams], by=self.name))
        taken: set[str] = set()
        for amb, ready in sim.loading_queue():
            ready = [p for p in ready if p.id not in taken]
            if not ready:
                continue
            load = pick_load(sim, ready, amb.capacity)
            for hid in sorted(sim.board.ids, key=lambda h: sim.geo.travel_time(amb.location,
                                                                               sim.board.hospitals[h].location)):
                if admissible(sim, hid, load):
                    sim.submit(CommitTransport(amb.id, [p.id for p in load], hid, by=self.name))
                    taken.update(p.id for p in load)
                    break
        return actions
