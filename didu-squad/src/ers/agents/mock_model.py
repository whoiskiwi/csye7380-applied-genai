"""A deterministic stand-in for an LLM that implements the Agents SDK `Model` interface.

It reads the JSON task the orchestrator sends and answers with simple rules, so the
whole agent pipeline (SDK runs, structured outputs, messages, negotiation, CAD checks)
can be tested in seconds without any API. Its results are NOT reported as LLM results.
"""
from __future__ import annotations

import json

from openai.types.responses import ResponseOutputMessage, ResponseOutputText

from agents.items import ModelResponse
from agents.models.interface import Model
from agents.usage import Usage

CODE_RANK = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "OMEGA": 5}


def _assess(x):
    incs = sorted(x["incidents"], key=lambda i: (CODE_RANK.get(i["dispatch_code"], 9), -i["red"], i["t_call"], i["id"]))
    ranking = [i["id"] for i in incs]
    critical = [i["id"] for i in incs if i["dispatch_code"] == "E" or i["red"]]
    alerts = [{"incident_id": i["id"], "expected_red": i["red"], "expected_yellow": i["yellow"],
               "expected_green": i["green"]} for i in x["incidents"] if i.get("needs_pre_alert")]
    esc = [{"incident_id": i["id"], "reason": "mass casualty"} for i in x["incidents"]
           if i.get("just_triaged") and (i["victims"] >= 8 or i["red"] >= 3)]
    return {"ranking": ranking, "critical": critical, "pre_alerts": alerts, "escalations": esc}


def _dispatch_units(x):
    used, out, short_total = set(), [], 0
    for inc in sorted(x["incidents"], key=lambda i: i["priority"]):
        short_total += inc["ambulances_short"]
        ambs = [c["unit_id"] for c in inc["ambulance_candidates"] if c["unit_id"] not in used
                and (not c.get("reassignable") or c["current_incident_priority"] > inc["priority"])][: inc["ambulances_short"]]
        teams = []
        if inc["needs_team"]:
            teams = [c["unit_id"] for c in inc["team_candidates"] if c["unit_id"] not in used][:1]
        used.update(ambs + teams)
        if ambs or teams:
            out.append({"incident_id": inc["id"], "ambulance_ids": ambs, "team_ids": teams, "reason": "priority order"})
    short = [i for i in x["incidents"] if i["ambulances_short"] > 0]
    conflict = len(short) >= 2 and short_total > x["idle_ambulances"]
    return {"assignments": out, "conflict": conflict, "conflict_note": "more demand than idle ambulances" if conflict else ""}


def _best_option(opts, red, room=None):
    ok = [o for o in opts if o["suitability"] != "cannot_take" and o.get("room_ok", True)
          and o.get("max_possible_ok", True)]
    if red:
        inwin = [o for o in ok if o["suitability"] == "match_in_window"]
        if inwin:
            return min(inwin, key=lambda o: o["eta"])
    best2 = [o for o in ok if o["suitability"] in ("match", "match_in_window", "match_late")]
    pool = best2 or ok
    return min(pool, key=lambda o: o["eta"]) if pool else None


def _transport_propose(x):
    props = []
    for a in x["ambulances"]:
        # the dispatcher's own goal: the closest hospital that can take the load right now
        ok = [o for o in a["options"] if o["suitability"] != "cannot_take"]
        o = min(ok or a["options"], key=lambda o: o["eta"])
        props.append({"ambulance_id": a["ambulance_id"], "hospital_id": o["hospital_id"],
                      "reason_code": "CAPABILITY_REQUIRED" if a["has_red"] else "CLOSER_ALTERNATIVE",
                      "rationale": "closest suitable"})
    return {"proposals": props}


def _transport_reply(x):
    reps = []
    for c in x["counters"]:
        risk = c["has_red"] and not c["counter_fits_window"]
        reps.append({"ambulance_id": c["ambulance_id"], "verdict": "COUNTER" if risk else "ACCEPT",
                     "hospital_id": c["own_hospital_id"] if risk else c["counter_hospital_id"],
                     "reason_code": "WINDOW_RISK" if risk else "OK", "rationale": "window" if risk else "fine"})
    return {"replies": reps}


def _hospital_report(x):
    m = x["max_possible"]
    reserve = 1 if x.get("expected_red_incoming", 0) > 0 and m["red"] > 1 else 0
    need_n = 1 if x["beds_free"] > 0 and m["yellow"] == 0 else 0
    return {"hospital_id": x["hospital_id"], "accept_red": m["red"] - reserve, "accept_yellow": m["yellow"],
            "accept_green": m["green"], "divert": False,
            "reason_code": "RESERVE_FOR_CRITICAL" if reserve else "OK", "request_nurses": need_n, "request_doctors": 0,
            "note": "keep one red bed" if reserve else ""}


def _admission(x):
    room = {h["hospital_id"]: dict(h["accept"]) for h in x["hospital_reports"]}
    out = []
    for p in x["proposals"]:
        need = p["load_colors"]

        def fits(hid):
            r = room.get(hid, {})
            return all(r.get(c, 0) >= n for c, n in need.items())

        prop = next(o for o in p["options"] if o["hospital_id"] == p["proposed_hospital_id"])
        good = "match_in_window" if p["has_red"] else "match"
        if prop["suitability"] == good and fits(prop["hospital_id"]):
            verdict, hid, code = "ACCEPT", prop["hospital_id"], "OK"
        else:
            alts = [o for o in p["options"] if o["suitability"] != "cannot_take" and fits(o["hospital_id"])]
            alt = _best_option(alts, p["has_red"])
            if alt is None:
                verdict, hid, code = "REJECT", "", "NO_BED"
            elif alt["hospital_id"] == prop["hospital_id"]:
                verdict, hid, code = "ACCEPT", alt["hospital_id"], "OK"
            else:
                verdict, hid, code = "COUNTER", alt["hospital_id"], "CAPABILITY_REQUIRED" if p["has_red"] else "LOAD_BALANCE"
        if verdict != "REJECT":
            for c, n in need.items():
                room[hid][c] = room[hid].get(c, 0) - n
        out.append({"ambulance_id": p["ambulance_id"], "verdict": verdict, "hospital_id": hid, "reason_code": code,
                    "rationale": "rules"})
    return {"decisions": out}


def _pool_plan(x):
    left_n, left_d = x["pool"]["nurses"], x["pool"]["doctors"]
    allocs = []
    for r in sorted(x["requests"], key=lambda r: -r["unlocks"]):
        n, d = min(r["nurses"], left_n), min(r["doctors"], left_d)
        left_n, left_d = left_n - n, left_d - d
        allocs.append({"hospital_id": r["hospital_id"], "nurses": n, "doctors": d})
    return {"allocations": allocs, "rationale": "most admissions unlocked first"}


def _pool_reply(x):
    return {"hospital_id": x["hospital_id"], "verdict": "ACCEPT", "min_nurses": x["offered_nurses"],
            "min_doctors": x["offered_doctors"], "reason": "ok"}


def _ruling(x):
    out = {"unit_assignments": [], "transport_rulings": [], "pool_allocations": [], "rationale": "fixed objective"}
    if x["kind"] == "units":
        out["unit_assignments"] = _dispatch_units(x)["assignments"]
    elif x["kind"] == "transport":
        for a in x["ambulances"]:
            opts = [o for o in a["options"] if o["max_possible_ok"]]
            o = _best_option(opts, a["has_red"])
            if o:
                out["transport_rulings"].append({"ambulance_id": a["ambulance_id"], "hospital_id": o["hospital_id"]})
    elif x["kind"] == "pool":
        out["pool_allocations"] = _pool_plan(x)["allocations"]
    return out


TASKS = {"assess": _assess, "dispatch_units": _dispatch_units, "transport_propose": _transport_propose,
         "transport_reply": _transport_reply, "hospital_report": _hospital_report, "admission": _admission,
         "pool_plan": _pool_plan, "pool_reply": _pool_reply, "ruling": _ruling}


class MockModel(Model):
    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                           tracing, **kwargs) -> ModelResponse:
        text = input if isinstance(input, str) else next(
            i["content"] for i in reversed(input) if isinstance(i, dict) and i.get("role") == "user")
        if isinstance(text, list):
            text = "".join(part.get("text", "") for part in text)
        task, _ = json.JSONDecoder().raw_decode(text)      # a retry appends a note after the JSON
        out = TASKS[task["task"]](task)
        msg = ResponseOutputMessage(id="mock", type="message", role="assistant", status="completed",
                                    content=[ResponseOutputText(type="output_text", text=json.dumps(out), annotations=[])])
        return ModelResponse(output=[msg], usage=Usage(requests=1), response_id=None)

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError
