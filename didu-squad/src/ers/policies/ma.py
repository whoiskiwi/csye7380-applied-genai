"""Multi-agent policy: the Python orchestrator that runs the five agent types each minute.

Flow per minute (numbers match the workflow figure):
  ①–③  Incident Assessment ranks incidents, informs Dispatch, pre-alerts Hospital Coordination
  ④     Dispatch proposes units                      (Ⓐ conflict -> Resource Allocation)
  ⑦–⑪  Dispatch proposes destinations, Hospital Coordination asks hospitals and accepts /
        rejects / counters, up to 3 rounds         (Ⓒ no deal -> Resource Allocation)
  ⑫ ⑬  commits go to the CAD; pool staff negotiated between hospitals via Hospital Coordination

`negotiate=False` gives MA-NoNeg: same agents, one round, no counters, no commander,
pool staff first come first served.
"""
from __future__ import annotations

from ers.agents import tools as T
from ers.agents.runtime import AgentRuntime, prompt
from ers.agents.schemas import (AdmissionDecisionsOutput, AssessmentOutput, DispatchUnitsOutput, HospitalReport,
                                PoolPlanOutput, PoolReply, RulingOutput, TransportProposalsOutput,
                                TransportRepliesOutput)
from ers.config import assumptions
from ers.env.actions import AllocatePoolStaff, AssignUnits, CommitTransport, ReassignUnit, SetPriority
from ers.env.entities import Color, PatientStatus
from ers.env.outcomes import window_deadline
from ers.messaging.schema import MessageBus
from ers.policies.b1_rules import choose_hospital, incident_rank
from ers.policies.common import admissible, ambulances_short, needs_team, pick_load, trips_needed

COLORS = ("red", "yellow", "green")


# lower is better; match_in_window and match are the same tier (match is the label for loads without red)
SUIT_RANK = {"match_in_window": 0, "match": 0, "match_late": 1, "acceptable_not_match": 2, "cannot_take": 9}


def _rank(opts: dict, hid: str) -> int:
    return SUIT_RANK.get(opts.get(hid, {}).get("suitability"), 9)


class MultiAgentPolicy:
    def __init__(self, negotiate: bool = True, backend: str | None = None, cache_mode: str | None = None,
                 report_ttl: int = 20):
        self.negotiate = negotiate
        self.name = "MA" if negotiate else "MA-NoNeg"
        self.rt = AgentRuntime(backend, cache_mode)
        self.max_rounds = assumptions()["negotiation"]["max_rounds"]
        self.scene_time = assumptions()["units"]["scene_time_min"]
        self.report_ttl = report_ttl
        self.bus: MessageBus | None = None
        self.decisions: list[dict] = []
        self.reports: dict[str, dict] = {}
        self._report_sig: dict[str, tuple] = {}
        self.pre_alerts: dict[str, dict] = {}
        self._assessed_calls: set[str] = set()
        self._assessed_triage: set[str] = set()
        self.fallbacks = 0
        self.escalations = 0
        self.conflicts = 0
        self.rounds_used: list[int] = []
        self._last_unit_sig = None
        self.partial_fills = 0
        self._last_unit_t = -99
        self._last_retask_sig = None
        self.redirects = 0
        self.accept_mismatch = 0

    # ------------------------------------------------------------------ public
    def model_info(self) -> dict:
        return {**self.rt.info(), "negotiate": self.negotiate}

    def stats(self) -> dict:
        return {"llm_calls": self.rt.calls, "llm_failures": self.rt.failures, "llm_retries": self.rt.retries,
                "rule_retries": self.rt.soft_retries, "rule_violations_kept": self.rt.soft_violations,
                "fallbacks": self.fallbacks, "partial_fills": self.partial_fills, "fallback_rate": round(self.fallbacks / max(1, self.rt.calls), 4),
                "tokens_in": self.rt.tokens_in, "tokens_out": self.rt.tokens_out,
                "agent_escalations": self.escalations, "redirects": self.redirects, "accept_mismatch": self.accept_mismatch, "allocation_conflicts": self.conflicts,
                "mean_rounds": round(sum(self.rounds_used) / len(self.rounds_used), 2) if self.rounds_used else 0,
                "calls_per_agent": dict(self.rt.per_agent), "rule_log": list(self.rt.rule_log)}

    def decide(self, sim) -> list:
        if self.bus is None:
            self.bus = MessageBus(sim)
        self._assess(sim)
        self._dispatch_units(sim)
        if self.negotiate:
            self._retask(sim)
        self._transport(sim)
        self._staff_pool(sim)
        return []

    # ------------------------------------------------------------------ helpers
    def _run(self, key, name, instr, out_type, task, tools=None, validate=None, soft=None):
        return self.rt.run(key, name, instr, out_type, task, tools, validate, soft)

    def _fallback(self, sim, what: str):
        self.fallbacks += 1
        sim.log("fallback", what=what)

    @staticmethod
    def _counts(sim, inc) -> dict:
        if inc.triaged:
            left = [p for p in inc.patients if p.status != PatientStatus.DECEASED]
            return {c: sum(p.true_color.value == c for p in left) for c in COLORS}
        return {c: inc.reported_colors.get(c, 0) for c in COLORS}

    # ------------------------------------------------------------------ ①–③ incident assessment
    def _assess(self, sim):
        active = sim.active_incidents()
        new_calls = [i for i in active if i.id not in self._assessed_calls]
        new_triage = [i for i in active if i.triaged and i.id not in self._assessed_triage]
        if not new_calls and not new_triage:
            return
        rows = []
        for i in active:
            c = self._counts(sim, i)
            ambs, teams = sim.units_at(i)
            rows.append({"id": i.id, "type": i.type, "t_call": i.t_call, "dispatch_code": i.dispatch_code,
                         "triaged": i.triaged, "victims": sum(c.values()), **c, "waited": sim.t - i.t_call,
                         "units_assigned": len(ambs) + len(teams),
                         "needs_pre_alert": (i in new_calls or i in new_triage) and sum(c.values()) >= 3,
                         "just_triaged": i in new_triage})
        ids = {r["id"] for r in rows}

        def check(o: AssessmentOutput):
            got = set(o.ranking) & ids
            if len(got) < max(1, len(ids) / 2):
                return f"priorities must rank every incident; missing {sorted(ids - got)}"
            return None

        out = self._run("IncidentAssessment", "IncidentAssessment", prompt("incident_assessment"), AssessmentOutput,
                        {"task": "assess", "t": sim.t, "incident_ids": sorted(ids), "incidents": rows},
                        T.incident_assessment_tools(sim), check)
        if out is None:
            self._fallback(sim, "assess")
            ranked = sorted(active, key=lambda i: incident_rank(sim, i))
            out = AssessmentOutput(ranking=[], critical=[], pre_alerts=[], escalations=[])
            prio = {i.id: k + 1 for k, i in enumerate(ranked)}
        else:
            # agent's ranking first; incidents it left out follow in rule order
            ranked = [iid for iid in out.ranking if iid in ids]
            ranked = list(dict.fromkeys(ranked))
            missing = [i.id for i in sorted(active, key=lambda i: incident_rank(sim, i)) if i.id not in ranked]
            if missing:
                self.partial_fills += 1
            prio = {iid: k + 1 for k, iid in enumerate(ranked + missing)}
        for i in active:
            sim.submit(SetPriority(i.id, int(prio.get(i.id, 99)), by="IncidentAssessment"))
            if i in new_calls or i in new_triage:
                self.bus.send("IncidentAssessment", "Dispatch", "INFORM", f"priority {prio.get(i.id)} for {i.id}",
                              incident_id=i.id, payload={"priority": prio.get(i.id)})
        for a in out.pre_alerts:
            if a.incident_id in ids:
                self.pre_alerts[a.incident_id] = {"red": a.expected_red, "yellow": a.expected_yellow,
                                                  "green": a.expected_green}
                self.bus.send("IncidentAssessment", "HospitalCoordination", "INFORM",
                              f"pre-alert {a.incident_id}: {a.expected_red}R {a.expected_yellow}Y {a.expected_green}G",
                              incident_id=a.incident_id, payload=self.pre_alerts[a.incident_id])
        self._assessed_calls |= {i.id for i in new_calls}
        self._assessed_triage |= {i.id for i in new_triage}
        for e in out.escalations:
            if e.incident_id in ids:
                self.bus.send("IncidentAssessment", "ResourceAllocation", "INFORM", f"escalation: {e.reason}",
                              incident_id=e.incident_id, reason_code="ESCALATION")
                if self.negotiate:
                    self.escalations += 1
                    self._units_ruling(sim, None, f"escalation of {e.incident_id}: {e.reason}")

    # ------------------------------------------------------------------ ④ dispatch units
    def _unit_task(self, sim):
        idle_a, idle_t = sim.idle_ambulances(), sim.idle_teams()
        if not idle_a and not idle_t:
            return None
        rows = []
        for i in sorted(sim.active_incidents(), key=lambda i: (i.priority or 99, i.t_call)):
            short, team = ambulances_short(sim, i), needs_team(sim, i)
            if short <= 0 and not team:
                continue
            c = self._counts(sim, i)
            rows.append({
                "id": i.id, "priority": i.priority or 99, "dispatch_code": i.dispatch_code, "type": i.type, **c,
                "ambulances_short": short, "needs_team": team,
                "ambulance_candidates": [{"unit_id": u.id, "eta": sim.geo.travel_time(u.location, i.location),
                                          "als": u.als} for u in sorted(idle_a, key=lambda u: sim.geo.travel_time(
                                              u.location, i.location))[:4]],
                "team_candidates": [{"unit_id": u.id, "eta": sim.geo.travel_time(u.location, i.location)}
                                    for u in sorted(idle_t, key=lambda u: sim.geo.travel_time(u.location, i.location))[:2]]
                if team else [],
            })
        if not rows or (not idle_a and not any(r["needs_team"] for r in rows)):
            return None
        return {"t": sim.t, "idle_ambulances": len(idle_a), "idle_teams": len(idle_t), "incidents": rows}

    def _valid_assignments(self, sim, assignments, inc_ids):
        used, ok = set(), []
        idle_a = {u.id for u in sim.idle_ambulances()}
        idle_t = {u.id for u in sim.idle_teams()}
        for a in assignments:
            if a.incident_id not in inc_ids:
                continue
            ambs = [u for u in a.ambulance_ids if u in idle_a and u not in used]
            teams = [u for u in a.team_ids if u in idle_t and u not in used]
            used.update(ambs + teams)
            if ambs or teams:
                ok.append((a.incident_id, ambs, teams, a.reason))
        return ok

    def _dispatch_units(self, sim):
        task = self._unit_task(sim)
        if task is None:
            return
        # ask again only when the situation changed (or every 5 minutes if Dispatch chose to hold units)
        sig = (tuple(u.id for u in sim.idle_ambulances()), tuple(u.id for u in sim.idle_teams()),
               tuple((r["id"], r["ambulances_short"], r["needs_team"], r["priority"]) for r in task["incidents"]))
        if sig == self._last_unit_sig and sim.t - self._last_unit_t < 5:
            return
        self._last_unit_sig, self._last_unit_t = sig, sim.t
        inc_ids = {r["id"] for r in task["incidents"]}
        out = self._run("Dispatch", "Dispatch", prompt("dispatch_units"), DispatchUnitsOutput,
                        {"task": "dispatch_units", **task}, T.dispatch_tools(sim))
        if out is None:
            self._fallback(sim, "dispatch_units")
            self._rule_dispatch(sim)
            return
        proposal = self._valid_assignments(sim, out.assignments, inc_ids)
        # conflict: Dispatch says so, or a more urgent short incident got nothing while a less urgent one got units
        served = {iid for iid, a, t, _ in proposal}
        prio = {r["id"]: r["priority"] for r in task["incidents"]}
        starved = [r for r in task["incidents"] if r["id"] not in served and r["ambulances_short"] > 0
                   and any(prio[s] > r["priority"] for s in served)]
        conflict = out.conflict or bool(starved)
        if conflict:
            self.conflicts += 1
        if conflict and self.negotiate:
            thread = self.bus.new_thread()
            self.bus.send("Dispatch", "ResourceAllocation", "REQUEST",
                          f"unit conflict: {out.conflict_note or 'urgent incident left without units'}",
                          payload={"proposal": [{"incident_id": i, "ambulances": a, "teams": t} for i, a, t, _ in proposal]},
                          thread_id=thread, reason_code="HIGHER_PRIORITY")
            self.escalations += 1
            if self._units_ruling(sim, task, out.conflict_note or "starved incident", thread, proposal):
                return
        for iid, ambs, teams, reason in proposal:
            self.bus.send("Dispatch", "CAD", "PROPOSE", f"send {ambs + teams} to {iid}", incident_id=iid,
                          payload={"ambulances": ambs, "teams": teams}, reason_code="OK")
            sim.submit(AssignUnits(iid, ambs, teams, by="Dispatch"))

    def _units_ruling(self, sim, task, note, thread=None, proposal=None) -> bool:
        task = task or self._unit_task(sim)
        if task is None:
            return False
        inc_ids = {r["id"] for r in task["incidents"]}
        conflict = {"kind": "units", "note": note, "dispatch_proposal": [
            {"incident_id": i, "ambulances": a, "teams": t} for i, a, t, _ in (proposal or [])]}
        out = self._run("ResourceAllocation", "ResourceAllocation", prompt("resource_allocation"), RulingOutput,
                        {"task": "ruling", "kind": "units", "note": note, "dispatch_proposal": conflict["dispatch_proposal"],
                         **task}, T.resource_allocation_tools(conflict))
        if out is None:
            self._fallback(sim, "ruling_units")
            return False
        ruling = self._valid_assignments(sim, out.unit_assignments, inc_ids)
        for iid, ambs, teams, _ in ruling:
            self.bus.send("ResourceAllocation", "CAD", "COMMIT", f"ruling: send {ambs + teams} to {iid}",
                          incident_id=iid, payload={"ambulances": ambs, "teams": teams}, thread_id=thread,
                          reason_code="HIGHER_PRIORITY")
            sim.submit(AssignUnits(iid, ambs, teams, by="ResourceAllocation"))
        if thread:
            self.bus.send("CAD", "Dispatch", "INFORM", f"ruling executed: {out.rationale}", thread_id=thread)
        return bool(ruling)

    # ------------------------------------------------------------------ Ⓐ redirect waiting units (full MA only)
    def _waiting_units(self, sim):
        """Assigned ambulances that carry nobody and are surplus where they are: an incident keeps as many empty
        ambulances as it still needs trips (the closest ones), because trapped patients, often the most hurt,
        still need a ride when they are freed. Only the rest may be redirected."""
        out = []
        for inc in sim.active_incidents():
            ambs, _ = sim.units_at(inc)
            empty = [a for a in ambs if not a.patient_ids and a.status.value in ("en_route", "on_scene")]
            if any(a.status.value == "on_scene" for a in empty) and \
                    any(p.status == PatientStatus.READY for p in inc.patients):
                continue                                  # patients are ready to load right now
            empty.sort(key=lambda a: sim.geo.travel_time(sim.position(a), inc.location))
            for amb in empty[trips_needed(sim, inc):]:
                why = "surplus_on_scene" if amb.status.value == "on_scene" else "surplus_en_route"
                out.append({"amb": amb, "why": why, "incident": inc})
        return out

    def _retask(self, sim):
        if sim.idle_ambulances():
            return
        starving = [i for i in sim.active_incidents()
                    if ambulances_short(sim, i) > 0 and not sim.units_at(i)[0]
                    and (i.dispatch_code in ("E", "D") or self._counts(sim, i)["red"] > 0)]
        waiting = self._waiting_units(sim)
        if not starving or not waiting:
            return
        sig = (tuple(i.id for i in starving), tuple(w["amb"].id for w in waiting))
        if sig == self._last_retask_sig:
            return
        self._last_retask_sig = sig
        rows = []
        for i in sorted(starving, key=lambda i: (i.priority or 99, i.t_call)):
            c = self._counts(sim, i)
            rows.append({"id": i.id, "priority": i.priority or 99, "dispatch_code": i.dispatch_code, "type": i.type, **c,
                         "waited": sim.t - i.t_call, "ambulances_short": ambulances_short(sim, i), "needs_team": False,
                         "team_candidates": [],
                         "ambulance_candidates": [{
                             "unit_id": w["amb"].id, "eta": sim.geo.travel_time(sim.position(w["amb"]), i.location),
                             "als": w["amb"].als, "reassignable": True, "currently_at": w["incident"].id,
                             "current_incident_priority": w["incident"].priority or 99, "why_free": w["why"]}
                             for w in sorted(waiting, key=lambda w: sim.geo.travel_time(sim.position(w["amb"]), i.location))]})
        thread = self.bus.new_thread()
        self.conflicts += 1
        self.escalations += 1
        self.bus.send("Dispatch", "ResourceAllocation", "REQUEST",
                      f"no ambulance for urgent {[r['id'] for r in rows]}; units waiting elsewhere: "
                      f"{[w['amb'].id for w in waiting]}", payload={"starving": [r["id"] for r in rows]},
                      thread_id=thread, reason_code="HIGHER_PRIORITY")
        conflict = {"kind": "units", "note": "redirect waiting units", "incidents": rows}
        out = self._run("ResourceAllocation", "ResourceAllocation", prompt("resource_allocation"), RulingOutput,
                        {"task": "ruling", "kind": "units", "note": "no idle ambulance; you may redirect waiting units",
                         "t": sim.t, "idle_ambulances": 0, "incidents": rows, "dispatch_proposal": []},
                        T.resource_allocation_tools(conflict))
        if out is None:
            self._fallback(sim, "ruling_redirect")
            return
        allowed = {w["amb"].id for w in waiting}
        used = set()
        for a in out.unit_assignments:
            if a.incident_id not in {r["id"] for r in rows}:
                continue
            for uid in a.ambulance_ids:
                if uid in allowed and uid not in used:
                    used.add(uid)
                    res = sim.submit(ReassignUnit(uid, a.incident_id, by="ResourceAllocation"))
                    if res.ok:
                        self.redirects += 1
                        self.bus.send("ResourceAllocation", "CAD", "COMMIT", f"redirect {uid} to {a.incident_id}",
                                      incident_id=a.incident_id, payload={"ambulance_id": uid}, thread_id=thread,
                                      reason_code="HIGHER_PRIORITY")
        if not used:
            self.bus.send("ResourceAllocation", "Dispatch", "REJECT", f"no redirect: {out.rationale}",
                          thread_id=thread, reason_code="HIGHER_PRIORITY")

    def _rule_dispatch(self, sim):
        idle_a, idle_t = sim.idle_ambulances(), sim.idle_teams()
        for inc in sorted(sim.active_incidents(), key=lambda i: incident_rank(sim, i)):
            teams = []
            if needs_team(sim, inc) and idle_t:
                teams = sorted(idle_t, key=lambda u: sim.geo.travel_time(u.location, inc.location))[:1]
                idle_t = [u for u in idle_t if u not in teams]
            n = ambulances_short(sim, inc)
            ambs = sorted(idle_a, key=lambda u: sim.geo.travel_time(u.location, inc.location))[:n]
            idle_a = [u for u in idle_a if u not in ambs]
            if ambs or teams:
                sim.submit(AssignUnits(inc.id, [u.id for u in ambs], [u.id for u in teams], by="Dispatch(rule)"))

    # ------------------------------------------------------------------ hospital reports (⑨ ⑩)
    def _material_change(self, sim, hid) -> bool:
        """A hospital re-posts its report only when its limits change materially (status-board style)."""
        old = self.reports[hid]["max_possible"]
        new = sim.board.intake_limits(hid, sim.t)
        return any((old[c] == 0) != (new[c] == 0) or abs(old[c] - new[c]) >= 3 for c in COLORS)

    def _refresh_reports(self, sim):
        incoming_red = sum(a["red"] for iid, a in self.pre_alerts.items()
                           if not sim.incident_done(sim.incidents[iid]))
        for hid in sim.board.ids:
            r = self.reports.get(hid)
            if r and sim.t - r["t"] < self.report_ttl and not self._material_change(sim, hid):
                # keep the report but never let it exceed what the hospital can physically take now
                lim = sim.board.intake_limits(hid, sim.t)
                r["accept"] = {c: min(r["accept"][c], lim[c]) for c in COLORS}
                continue
            h, b = sim.board.hospitals[hid], sim.board
            limits = b.intake_limits(hid, sim.t)
            task = {"task": "hospital_report", "t": sim.t, "hospital_id": hid, "hospital_name": h.name,
                    "beds_free": h.beds_free, "beds_total": h.er_beds, "max_possible": limits,
                    "doctors": [{"skill": s.skill, "spare": round(s.spare(sim.t), 2)} for s in b.members(hid, "doctor")],
                    "nurse_spare": round(b.nurse_spare(hid, sim.t), 2), "expected_red_incoming": incoming_red,
                    "pool_available": {"nurses": len(b.pool_available("nurse")), "doctors": len(b.pool_available("doctor"))}}
            out = self._run("Hospital", hid, prompt("hospital", hospital_id=hid, hospital_name=h.name), HospitalReport,
                            task, T.hospital_tools(sim, hid))
            if out is None:
                self._fallback(sim, f"report_{hid}")
                out = HospitalReport(hospital_id=hid, accept_red=limits["red"], accept_yellow=limits["yellow"],
                                     accept_green=limits["green"], divert=False, reason_code="OK", request_nurses=0,
                                     request_doctors=0, note="rule fallback")
            accept = {"red": max(0, min(out.accept_red, limits["red"])),
                      "yellow": max(0, min(out.accept_yellow, limits["yellow"])),
                      "green": max(0, min(out.accept_green, limits["green"]))}
            if out.divert:
                accept = {c: 0 for c in COLORS}
            self.reports[hid] = {"t": sim.t, "hospital_id": hid, "accept": accept, "max_possible": limits,
                                 "reason_code": out.reason_code, "note": out.note,
                                 "request_nurses": max(0, out.request_nurses), "request_doctors": max(0, out.request_doctors),
                                 "pool_handled": False}
            self.bus.send(hid, "HospitalCoordination", "INFORM",
                          f"accept R{accept['red']} Y{accept['yellow']} G{accept['green']}"
                          + (f", need {out.request_nurses} nurses" if out.request_nurses else ""),
                          payload=self.reports[hid], reason_code=out.reason_code)

    # ------------------------------------------------------------------ ⑦–⑫ transport negotiation
    def _options(self, sim, amb, load):
        opts = []
        for hid in sim.board.ids:
            h = sim.board.hospitals[hid]
            eta = sim.geo.travel_time(amb.location, h.location)
            arrive = sim.t + self.scene_time + eta
            fits = all(arrive <= (window_deadline(p, sim.incidents[p.incident_id]) or 10**9) for p in load
                       if p.true_color == Color.RED)
            cap = min(sim.board.level(hid, p.category) for p in load)
            ok_now = admissible(sim, hid, load)
            has_red = any(p.true_color == Color.RED for p in load)
            green_only = all(p.true_color == Color.GREEN for p in load)
            if green_only and cap >= 1:
                cap_label = 2                       # a green patient is served by any hospital that can treat them
            else:
                cap_label = cap
            if cap == 0 or not ok_now:
                label = "cannot_take"
            elif cap_label == 2 and (fits or not has_red):
                label = "match_in_window" if has_red else "match"
            elif cap_label == 2:
                label = "match_late"
            else:
                label = "acceptable_not_match"
            opts.append({"hospital_id": hid, "eta": eta, "capability": cap, "fits_window": fits,
                         "max_possible_ok": ok_now, "suitability": label})
        return sorted(opts, key=lambda o: (o["eta"], o["hospital_id"]))     # nearest first

    def _hold(self, sim, hid, load) -> bool:
        """Reserve a load tentatively until commit time; False if the hospital can no longer take it."""
        if not admissible(sim, hid, load):
            return False
        for p in load:
            sim.board.admit(hid, p, p.true_color, sim.t)
            self._held.append((hid, p))
        return True

    def _release_holds(self, sim):
        for hid, p in self._held:
            sim.board.release(hid, p, p.true_color)
            sim.board.hospitals[hid].patient_ids.remove(p.id)
        self._held = []

    def _transport(self, sim):
        self._held = []
        taken: set[str] = set()
        queue = []
        for amb, ready in sim.loading_queue():
            ready = [p for p in ready if p.id not in taken]
            if not ready:
                continue
            load = pick_load(sim, ready, amb.capacity)
            # the status board shows no hospital can take this load right now: the ambulance waits, nobody is asked
            if not any(sim.board.level(h, p.category) >= 1 for h in sim.board.ids for p in load) or \
                    not any(admissible(sim, h, load) for h in sim.board.ids):
                if len(load) > 1:
                    load = load[:1]
                    if not any(admissible(sim, h, load) for h in sim.board.ids):
                        continue
                else:
                    continue
            taken.update(p.id for p in load)
            queue.append((amb, load))
        if not queue:
            return
        self._refresh_reports(sim)
        items = {}
        for amb, load in queue:
            colors = {c: sum(p.true_color.value == c for p in load) for c in COLORS}
            items[amb.id] = {"amb": amb, "load": load, "colors": {c: n for c, n in colors.items() if n},
                             "has_red": colors["red"] > 0, "options": self._options(sim, amb, load),
                             "incident_id": load[0].incident_id, "thread": self.bus.new_thread()}

        # ⑧ Dispatch proposes destinations
        amb_rows = [{"ambulance_id": k, "incident_id": v["incident_id"], "has_red": v["has_red"],
                     "patients": [{"id": p.id, "color": p.true_color.value, "category": p.category,
                                   "minutes_left_in_window": (window_deadline(p, sim.incidents[p.incident_id]) - sim.t)
                                   if window_deadline(p, sim.incidents[p.incident_id]) else None} for p in v["load"]],
                     "options": [{k2: o[k2] for k2 in ("hospital_id", "eta", "suitability")}
                                 for o in v["options"]]} for k, v in items.items()]

        def check_props(o: TransportProposalsOutput):
            got = {p.ambulance_id for p in o.proposals}
            return f"propose a hospital for every ambulance; missing {sorted(set(items) - got)}" if set(items) - got else None

        out = self._run("Dispatch", "Dispatch", prompt("dispatch_transport"), TransportProposalsOutput,
                        {"task": "transport_propose", "t": sim.t, "ambulances": amb_rows}, T.dispatch_tools(sim),
                        check_props)
        proposal: dict[str, str] = {}
        if out is None:
            self._fallback(sim, "transport_propose")
        else:
            for p in out.proposals:
                if p.ambulance_id in items and p.hospital_id in sim.board.hospitals:
                    proposal[p.ambulance_id] = p.hospital_id
                    items[p.ambulance_id]["dispatch_rationale"] = p.rationale
        for k, v in items.items():
            if k not in proposal:
                proposal[k] = choose_hospital(sim, v["amb"], v["load"]) or min(v["options"], key=lambda o: o["eta"])["hospital_id"]
            v["dispatch_proposal"] = proposal[k]
            self.bus.send("Dispatch", "HospitalCoordination", "PROPOSE",
                          f"transport {[p.id for p in v['load']]} to {proposal[k]}", incident_id=v["incident_id"],
                          payload={"ambulance_id": k, "hospital_id": proposal[k], "load": v["colors"]},
                          thread_id=v["thread"], round=1)

        final: dict[str, tuple[str, str]] = {}       # amb -> (hospital, decided_by)
        pending = dict(proposal)
        room = {hid: dict(r["accept"]) for hid, r in self.reports.items()}
        rounds = 0
        for rnd in range(1, (self.max_rounds if self.negotiate else 1) + 1):
            if not pending:
                break
            rounds = rnd
            decisions = self._admission_round(sim, items, pending, room, rnd)
            counters = {}
            for amb_id, (verdict, hid, code, why) in decisions.items():
                v = items[amb_id]
                self.bus.send("HospitalCoordination", "Dispatch", verdict, f"{verdict} {amb_id} -> {hid or '-'}: {why}",
                              incident_id=v["incident_id"], payload={"ambulance_id": amb_id, "hospital_id": hid},
                              thread_id=v["thread"], round=rnd, reason_code=code)
                v.setdefault("hc_decisions", []).append({"round": rnd, "verdict": verdict, "hospital_id": hid,
                                                         "reason_code": code, "rationale": why})
                if verdict == "ACCEPT":
                    final[amb_id] = (hid, "Dispatch+HospitalCoordination")
                    pending.pop(amb_id)
                elif not self.negotiate:
                    pending.pop(amb_id)          # MA-NoNeg: rejected loads go to the nearest hospital that can take them
                else:
                    counters[amb_id] = (verdict, hid, code)
            if not counters or not self.negotiate:
                break
            replies = self._dispatch_replies(sim, items, counters, pending)
            for amb_id, (verdict, hid, code, why) in replies.items():
                v = items[amb_id]
                self.bus.send("Dispatch", "HospitalCoordination", verdict, f"{verdict} {amb_id} -> {hid}: {why}",
                              incident_id=v["incident_id"], payload={"ambulance_id": amb_id, "hospital_id": hid},
                              thread_id=v["thread"], round=rnd, reason_code=code)
                if verdict == "ACCEPT" and hid and self._hold(sim, hid, v["load"]):
                    final[amb_id] = (hid, "HospitalCoordination counter accepted")
                    pending.pop(amb_id, None)
                    for c, n in v["colors"].items():
                        room.setdefault(hid, {}).setdefault(c, 0)
                        room[hid][c] -= n
                else:
                    pending[amb_id] = hid or pending[amb_id]
        if pending and self.negotiate:
            final.update(self._transport_ruling(sim, items, pending))
        self.rounds_used.append(rounds)
        self._release_holds(sim)

        # ⑫ commit through the CAD
        for amb_id, v in items.items():
            hid, by = final.get(amb_id, (None, None))
            if hid is None and not self.negotiate:
                hid = next((o["hospital_id"] for o in sorted(v["options"], key=lambda o: o["eta"])
                            if o["capability"] >= 1 and admissible(sim, o["hospital_id"], v["load"])), None)
                by = "nearest after rejection"
            self._commit(sim, v, hid, by, rounds)

    def _admission_round(self, sim, items, pending, room, rnd):
        def room_ok(hid, need):
            return all(room.get(hid, {}).get(c, 0) >= n for c, n in need.items())
        rows = [{"ambulance_id": k, "incident_id": items[k]["incident_id"], "proposed_hospital_id": hid,
                 "has_red": items[k]["has_red"], "load_colors": items[k]["colors"],
                 "options": [{"hospital_id": o["hospital_id"], "eta": o["eta"], "suitability": o["suitability"],
                              "room_ok": room_ok(o["hospital_id"], items[k]["colors"])} for o in items[k]["options"]]}
                for k, hid in pending.items()]
        reports = [{"hospital_id": hid, "accept": dict(room.get(hid, {})), "note": self.reports[hid]["note"]}
                   for hid in sim.board.ids]

        def check(o: AdmissionDecisionsOutput):
            got = {d.ambulance_id for d in o.decisions}
            return f"decide every proposal; missing {sorted(set(pending) - got)}" if set(pending) - got else None

        by_amb = {r["ambulance_id"]: {o["hospital_id"]: o for o in r["options"]} for r in rows}

        def role_rules(o: AdmissionDecisionsOutput):
            """Rules 1-3 of the hospital_coordination prompt."""
            bad = []
            for d in o.decisions:
                if d.ambulance_id not in pending:
                    continue
                opts, prop = by_amb[d.ambulance_id], pending[d.ambulance_id]
                usable = [h for h, x in opts.items() if x["room_ok"] and _rank(opts, h) < 9]
                best = min((_rank(opts, h) for h in usable), default=None)
                prop_ok = prop in usable
                should_accept = prop_ok and _rank(opts, prop) <= best
                if d.verdict == "ACCEPT" and d.hospital_id not in ("", prop):
                    bad.append(f"{d.ambulance_id}: ACCEPT must name the proposed hospital {prop}")
                elif d.verdict == "ACCEPT" and not prop_ok:
                    bad.append(f"{d.ambulance_id}: {prop} has no room_ok or cannot take this load")
                elif d.verdict in ("COUNTER", "REJECT") and should_accept:
                    bad.append(f"{d.ambulance_id}: {prop} has room and no option is strictly better, so ACCEPT")
                elif d.verdict == "COUNTER" and (d.hospital_id not in usable or _rank(opts, d.hospital_id) > best):
                    bad.append(f"{d.ambulance_id}: COUNTER must name the best-suitability option with room_ok")
                elif d.verdict == "REJECT" and self.negotiate and usable:
                    bad.append(f"{d.ambulance_id}: {usable} still have room, so COUNTER instead of REJECT")
            return "; ".join(bad[:3]) or None

        out = self._run("HospitalCoordination", "HospitalCoordination", prompt("hospital_coordination"),
                        AdmissionDecisionsOutput,
                        {"task": "admission", "t": sim.t, "round": rnd, "negotiation_allowed": self.negotiate,
                         "hospital_reports": reports, "proposals": rows},
                        T.hospital_coordination_tools(sim, {r["hospital_id"]: r for r in reports}), check, role_rules)
        decisions = {}
        if out is None:
            self._fallback(sim, "admission")
            for k, hid in pending.items():
                ok = admissible(sim, hid, items[k]["load"])
                decisions[k] = ("ACCEPT", hid, "OK", "rule fallback") if ok else ("REJECT", "", "NO_BED", "rule fallback")
        else:
            for d in out.decisions:
                if d.ambulance_id in pending:
                    verdict, hid = d.verdict, d.hospital_id
                    if verdict == "ACCEPT" and hid != pending[d.ambulance_id]:
                        # ACCEPT means the proposed hospital; naming another one is a counter-proposal
                        self.accept_mismatch += 1
                        verdict, hid = ("COUNTER", hid) if self.negotiate else ("ACCEPT", pending[d.ambulance_id])
                    if verdict == "COUNTER" and hid == pending[d.ambulance_id]:
                        verdict = "ACCEPT"                  # a counter naming the proposed hospital agrees with it
                    if verdict == "COUNTER" and not self.negotiate:
                        verdict = "REJECT"
                    decisions[d.ambulance_id] = (verdict, hid if verdict != "REJECT" else "", d.reason_code,
                                                 d.rationale)
        # hospitals' reported limits are binding: an acceptance beyond them is refused by the hospital.
        # Accepted loads are held tentatively (until commit) so later checks see them.
        for k, (verdict, hid, code, why) in list(decisions.items()):
            if verdict in ("ACCEPT", "COUNTER") and hid:
                need = items[k]["colors"]
                cap = min(sim.board.level(hid, p.category) for p in items[k]["load"]) if hid in sim.board.hospitals else 0
                if hid not in room or cap == 0 or any(room[hid].get(c, 0) < n for c, n in need.items()) \
                        or not admissible(sim, hid, items[k]["load"]):
                    self.bus.send(hid if hid in sim.board.hospitals else "CAD", "HospitalCoordination", "REJECT",
                                  f"cannot take {need} ({'reported limit' if cap else 'no capability'})",
                                  incident_id=items[k]["incident_id"], thread_id=items[k]["thread"], round=rnd,
                                  reason_code="RESERVE_FOR_CRITICAL" if cap else "CAPABILITY_MISSING")
                    decisions[k] = ("REJECT", "", "RESERVE_FOR_CRITICAL" if cap else "CAPABILITY_MISSING",
                                    "over the hospital's reported limit")
                    continue
                if verdict == "ACCEPT":
                    self._hold(sim, hid, items[k]["load"])
                    for c, n in need.items():
                        room[hid][c] -= n
        return decisions

    def _dispatch_replies(self, sim, items, counters, pending):
        rows = []
        for k, (verdict, hid, code) in counters.items():
            opt = {o["hospital_id"]: o for o in items[k]["options"]}
            rows.append({"ambulance_id": k, "own_hospital_id": pending[k], "hc_verdict": verdict,
                         "counter_hospital_id": hid, "reason_code": code, "has_red": items[k]["has_red"],
                         "counter_fits_window": opt.get(hid, {}).get("fits_window", False),
                         "own_suitability": opt.get(pending[k], {}).get("suitability"),
                         "counter_suitability": opt.get(hid, {}).get("suitability"),
                         "options": [{k2: o[k2] for k2 in ("hospital_id", "eta", "suitability")}
                                     for o in items[k]["options"]]})
        def role_rules(o: TransportRepliesOutput):
            """Reply rule of the dispatch_transport prompt: accept a counter unless it is worse for a red patient."""
            bad = []
            for r in o.replies:
                if r.ambulance_id not in counters or counters[r.ambulance_id][0] != "COUNTER":
                    continue
                opts = {x["hospital_id"]: x for x in items[r.ambulance_id]["options"]}
                hc_hid = counters[r.ambulance_id][1]
                worse = items[r.ambulance_id]["has_red"] and _rank(opts, hc_hid) > _rank(opts, pending[r.ambulance_id])
                if r.verdict == "COUNTER" and not worse:
                    bad.append(f"{r.ambulance_id}: the counter {hc_hid} is not worse for a red patient, so ACCEPT it")
                elif r.verdict == "ACCEPT" and r.hospital_id != hc_hid:
                    bad.append(f"{r.ambulance_id}: ACCEPT must name the counter-proposed hospital {hc_hid}")
            return "; ".join(bad[:3]) or None

        out = self._run("Dispatch", "Dispatch", prompt("dispatch_transport"), TransportRepliesOutput,
                        {"task": "transport_reply", "t": sim.t, "counters": rows}, T.dispatch_tools(sim),
                        soft=role_rules)
        replies = {}
        if out is None:
            self._fallback(sim, "transport_reply")
            out_list = []
        else:
            out_list = out.replies
        for r in out_list:
            if r.ambulance_id in counters:
                replies[r.ambulance_id] = (r.verdict, r.hospital_id, r.reason_code, r.rationale)
        for k, (verdict, hid, code) in counters.items():
            if k not in replies:            # default: accept a counter, keep own proposal after a rejection
                replies[k] = ("ACCEPT", hid, "OK", "default") if verdict == "COUNTER" and hid else \
                             ("COUNTER", pending[k], "WINDOW_RISK", "default")
        return replies

    def _transport_ruling(self, sim, items, pending) -> dict:
        rows = [{"ambulance_id": k, "has_red": items[k]["has_red"], "dispatch_wants": hid,
                 "hc_history": items[k].get("hc_decisions", []), "load_colors": items[k]["colors"],
                 "options": items[k]["options"]} for k, hid in pending.items()]
        thread = items[next(iter(pending))]["thread"]
        self.bus.send("HospitalCoordination", "ResourceAllocation", "REQUEST",
                      f"no agreement after {self.max_rounds} rounds for {sorted(pending)}",
                      payload={"ambulances": sorted(pending)}, thread_id=thread, reason_code="ESCALATION")
        self.escalations += 1
        self.conflicts += 1
        conflict = {"kind": "transport", "ambulances": rows}
        def role_rules(o: RulingOutput):
            """Transport rule of the resource_allocation prompt: best suitability, then shortest ETA."""
            bad = []
            for r in o.transport_rulings:
                if r.ambulance_id not in pending:
                    continue
                opts = [x for x in items[r.ambulance_id]["options"]
                        if x["max_possible_ok"] and x["suitability"] != "cannot_take"]
                if not opts:
                    continue
                best = min(SUIT_RANK[x["suitability"]] for x in opts)
                want = min((x for x in opts if SUIT_RANK[x["suitability"]] == best), key=lambda x: x["eta"])
                if r.hospital_id != want["hospital_id"]:
                    bad.append(f"{r.ambulance_id}: {want['hospital_id']} has the best suitability and the shortest ETA")
            return "; ".join(bad[:3]) or None

        out = self._run("ResourceAllocation", "ResourceAllocation", prompt("resource_allocation"), RulingOutput,
                        {"task": "ruling", "kind": "transport", "t": sim.t, "ambulances": rows},
                        T.resource_allocation_tools(conflict), soft=role_rules)
        final = {}
        if out is None:
            self._fallback(sim, "ruling_transport")
            return final
        for r in out.transport_rulings:
            if r.ambulance_id in pending and r.hospital_id in sim.board.hospitals \
                    and self._hold(sim, r.hospital_id, items[r.ambulance_id]["load"]):
                final[r.ambulance_id] = (r.hospital_id, "ResourceAllocation ruling")
                self.bus.send("ResourceAllocation", "CAD", "COMMIT", f"ruling: {r.ambulance_id} -> {r.hospital_id}",
                              payload={"ambulance_id": r.ambulance_id, "hospital_id": r.hospital_id},
                              thread_id=items[r.ambulance_id]["thread"], reason_code="ESCALATION")
        return final

    def _commit(self, sim, v, hid, by, rounds):
        amb, load = v["amb"], v["load"]
        rule_ref = choose_hospital(sim, amb, load)
        baseline = next((h for h in sorted(sim.board.ids, key=lambda h: sim.geo.travel_time(
            amb.location, sim.board.hospitals[h].location)) if admissible(sim, h, load)), None)
        res = None
        if hid:
            res = sim.submit(CommitTransport(amb.id, [p.id for p in load], hid, by="Dispatch"))
        if res is not None and not res.ok and res.reason in ("NO_STAFF", "NO_BED"):
            hid, by = None, (by or "") + " -> capacity taken this minute, waits"
        elif res is None or not res.ok:
            alt = rule_ref
            if hid:
                self._fallback(sim, f"commit_{res.reason if res else 'none'}")
            if alt:
                res2 = sim.submit(CommitTransport(amb.id, [p.id for p in load], alt, by="Dispatch(rule)"))
                if res2.ok:
                    hid, by = alt, (by or "") + " -> rule fallback"
                else:
                    hid = None
            else:
                hid = None
        if hid:
            self.bus.send("Dispatch", "CAD", "COMMIT", f"transport {[p.id for p in load]} to {hid}",
                          incident_id=v["incident_id"], payload={"ambulance_id": amb.id, "hospital_id": hid},
                          thread_id=v["thread"])
        lead = max(load, key=lambda p: (p.true_color == Color.RED, p.true_color == Color.YELLOW))
        self.decisions.append({
            "time_min": sim.t, "incident_id": v["incident_id"], "ambulance": amb.id,
            "patients": [{"id": p.id, "color": p.true_color.value, "category": p.category} for p in load],
            "lead_color": lead.true_color.value,
            "candidates": [{**{k: o[k] for k in ("hospital_id", "eta", "capability", "fits_window", "max_possible_ok")},
                            "reported_room": self.reports.get(o["hospital_id"], {}).get("accept")} for o in v["options"]],
            "dispatch_proposal": v.get("dispatch_proposal"), "dispatch_rationale": v.get("dispatch_rationale"),
            "hospital_coordination": v.get("hc_decisions", []), "final_destination": hid, "decided_by": by,
            "rounds": rounds, "rule_reference": rule_ref, "baseline": baseline, "thread": v["thread"],
            "fallback": bool(by and "fallback" in by),
        })

    # ------------------------------------------------------------------ ⑬ staff pool
    def _staff_pool(self, sim):
        b = sim.board
        requests = [r for r in self.reports.values() if not r["pool_handled"]
                    and (r["request_nurses"] > 0 or r["request_doctors"] > 0)]
        pool_n, pool_d = b.pool_available("nurse"), b.pool_available("doctor")
        if not requests or (not pool_n and not pool_d):
            return
        for r in requests:
            r["pool_handled"] = True
        thread = self.bus.new_thread()
        reqs = []
        for r in requests:
            lim = r["max_possible"]
            reqs.append({"hospital_id": r["hospital_id"], "nurses": r["request_nurses"], "doctors": r["request_doctors"],
                         "beds_free": b.hospitals[r["hospital_id"]].beds_free, "current_limits": lim,
                         "unlocks": b.hospitals[r["hospital_id"]].beds_free - lim["yellow"]})
            self.bus.send(r["hospital_id"], "HospitalCoordination", "REQUEST",
                          f"need {r['request_nurses']} nurses, {r['request_doctors']} doctors", thread_id=thread,
                          payload={"nurses": r["request_nurses"], "doctors": r["request_doctors"]}, reason_code="NO_STAFF")
        pool = {"nurses": len(pool_n), "doctors": len(pool_d)}
        if not self.negotiate:                      # MA-NoNeg: first come, first served
            plan = []
            n_left, d_left = pool["nurses"], pool["doctors"]
            for r in reqs:
                n, d = min(r["nurses"], n_left), min(r["doctors"], d_left)
                n_left, d_left = n_left - n, d_left - d
                plan.append((r["hospital_id"], n, d))
            self._apply_pool(sim, plan, "HospitalCoordination", thread)
            return
        task = {"task": "pool_plan", "t": sim.t, "pool": pool, "requests": reqs}
        out = self._run("HospitalCoordination", "HospitalCoordination", prompt("hospital_coordination"), PoolPlanOutput,
                        task, T.hospital_coordination_tools(sim, self.reports))
        if out is None:
            self._fallback(sim, "pool_plan")
            return
        plan = self._clip_pool([(a.hospital_id, a.nurses, a.doctors) for a in out.allocations
                                if a.hospital_id in sim.board.hospitals], pool)
        # requesting hospitals reply; a hospital that needs more than offered counters
        disputed = False
        for r in reqs:
            got = next(((n, d) for h, n, d in plan if h == r["hospital_id"]), (0, 0))
            self.bus.send("HospitalCoordination", r["hospital_id"], "PROPOSE", f"pool offer: {got[0]} nurses, {got[1]} doctors",
                          thread_id=thread, payload={"nurses": got[0], "doctors": got[1]}, reason_code="STAFF_POOL")
            if got[0] >= r["nurses"] and got[1] >= r["doctors"]:
                self.bus.send(r["hospital_id"], "HospitalCoordination", "ACCEPT", "offer accepted", thread_id=thread)
                continue
            rep = self._run("Hospital", r["hospital_id"], prompt("hospital", hospital_id=r["hospital_id"],
                                                                 hospital_name=b.hospitals[r["hospital_id"]].name),
                            PoolReply, {"task": "pool_reply", "hospital_id": r["hospital_id"], "offered_nurses": got[0],
                                        "offered_doctors": got[1], "requested": {"nurses": r["nurses"], "doctors": r["doctors"]},
                                        "beds_free": r["beds_free"], "pool": pool})
            if rep is None or rep.verdict == "ACCEPT":
                self.bus.send(r["hospital_id"], "HospitalCoordination", "ACCEPT", "offer accepted", thread_id=thread)
            else:
                disputed = True
                self.bus.send(r["hospital_id"], "HospitalCoordination", "COUNTER",
                              f"need at least {rep.min_nurses} nurses, {rep.min_doctors} doctors: {rep.reason}",
                              thread_id=thread, reason_code="NO_STAFF")
        if disputed and sum(r["nurses"] for r in reqs) > pool["nurses"]:
            self.bus.send("HospitalCoordination", "ResourceAllocation", "REQUEST", "staff pool dispute",
                          thread_id=thread, reason_code="ESCALATION")
            self.escalations += 1
            self.conflicts += 1
            conflict = {"kind": "pool", "pool": pool, "requests": reqs, "coordination_plan": plan}
            ro = self._run("ResourceAllocation", "ResourceAllocation", prompt("resource_allocation"), RulingOutput,
                           {"task": "ruling", "kind": "pool", "t": sim.t, "pool": pool, "requests": reqs,
                            "coordination_plan": [{"hospital_id": h, "nurses": n, "doctors": d} for h, n, d in plan]},
                           T.resource_allocation_tools(conflict))
            if ro is not None and ro.pool_allocations:
                plan = self._clip_pool([(a.hospital_id, a.nurses, a.doctors) for a in ro.pool_allocations
                                        if a.hospital_id in sim.board.hospitals], pool)
                self._apply_pool(sim, plan, "ResourceAllocation", thread)
                return
            self._fallback(sim, "ruling_pool")
        self._apply_pool(sim, plan, "HospitalCoordination", thread)

    @staticmethod
    def _clip_pool(plan, pool):
        n_left, d_left, out = pool["nurses"], pool["doctors"], []
        for h, n, d in plan:
            n, d = max(0, min(n, n_left)), max(0, min(d, d_left))
            n_left, d_left = n_left - n, d_left - d
            out.append((h, n, d))
        return out

    def _apply_pool(self, sim, plan, by, thread):
        for hid, n, d in plan:
            for s in sim.board.pool_available("nurse")[:n] + sim.board.pool_available("doctor")[:d]:
                sim.submit(AllocatePoolStaff(s.id, hid, by=by))
            if n or d:
                self.bus.send(by, "CAD", "COMMIT", f"pool staff to {hid}: {n} nurses, {d} doctors", thread_id=thread,
                              payload={"hospital_id": hid, "nurses": n, "doctors": d}, reason_code="STAFF_POOL")
