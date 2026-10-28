"""Generate a reproducible scenario instance from a scenario YAML and a seed.

Usage:
    uv run python -m ers.data.generate --scenario s1 --seed 0
    uv run python -m ers.data.generate --all --seeds 0-9
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ers.config import ROOT, assumptions, load_yaml
from ers.env.entities import Ambulance, Color, Incident, Patient, RescueTeam
from ers.env.simulator import Scenario
from ers.env.triage import start_triage, vitals_for

SEVERITY = [Color.RED, Color.YELLOW, Color.GREEN]
MVP_SCENARIOS = ["s1", "s3", "s5"]


def _flip(color: Color, rng, p: float) -> Color:
    """The call-taker hears a colour one level off with probability p."""
    if color == Color.BLACK or rng.random() >= p:
        return color
    i = SEVERITY.index(color)
    j = i + (1 if rng.random() < 0.5 else -1)
    return SEVERITY[min(max(j, 0), 2)]


def dispatch_code(inc_type: str, reported: dict[str, int], n_reported: int) -> str:
    """Protocol rules (MPDS-style determinant levels), not an AI judgement."""
    if inc_type == "cardiac_arrest":
        return "E"
    if reported.get("red", 0) > 0 or n_reported >= 5:
        return "D"
    if inc_type in ("stroke", "chest_pain", "breathing"):
        return "C"
    if reported.get("yellow", 0) > 0:
        return "B"
    if reported.get("green", 0) > 0:
        return "A"
    return "OMEGA"


def _child_category(cat: str) -> str:
    return {"adult_trauma": "child_trauma", "adult_medical": "child_medical", "adult_burn": "child_burn"}.get(cat, cat)


def _make_incident(iid: str, t_call: int, loc, inc_type: str, category: str, colors: list[Color], ages: list[int],
                   trapped: int, needs_rescue: bool, is_major: bool, rng) -> Incident:
    a = assumptions()["triage"]
    patients = []
    order = sorted(range(len(colors)), key=lambda k: (colors[k] != Color.RED, colors[k] != Color.YELLOW))
    trapped_idx = set(order[:trapped])          # the most hurt are the ones trapped
    for k, (c, age) in enumerate(zip(colors, ages)):
        cat = _child_category(category) if age < 16 else category
        v = vitals_for(c, rng)
        p = Patient(f"{iid}-P{k + 1:02d}", iid, age, cat, v, k in trapped_idx, _flip(c, rng, a["reported_severity_flip_p"]))
        p.true_color = start_triage(v)
        patients.append(p)
    n_true = len(patients)
    err = rng.uniform(-a["reported_count_error"], a["reported_count_error"]) if n_true > 1 else 0.0
    n_rep = max(1, int(round(n_true * (1 + err))))
    rep = {c.value: sum(p.reported_color == c for p in patients) for c in Color}
    rep["green"] = max(0, rep["green"] + (n_rep - n_true))   # extra / missing people are reported as walking
    n_rep = sum(rep.values())
    return Incident(iid, int(t_call), (round(float(loc[0]), 2), round(float(loc[1]), 2)), inc_type, patients,
                    reported_victims=n_rep, dispatch_code=dispatch_code(inc_type, rep, n_rep),
                    reported_colors={k: v for k, v in rep.items() if v}, needs_rescue=needs_rescue, is_major=is_major)


def _hotspot(rng, hotspots, size):
    w = np.array([h[3] for h in hotspots])
    h = hotspots[rng.choice(len(hotspots), p=w / w.sum())]
    x, y = rng.normal(h[0], h[2]), rng.normal(h[1], h[2])
    return min(max(x, 0.5), size - 0.5), min(max(y, 0.5), size - 0.5)


def build_scenario(name: str, seed: int, n_ambulances: int | None = None) -> Scenario:
    sc = load_yaml(f"scenarios/{name}.yaml")
    res = load_yaml("resources.yaml")
    size = assumptions()["map"]["size_km"]
    window = assumptions()["simulation"]["call_window_min"]
    rng = np.random.default_rng(seed * 1000 + sum(map(ord, name)))

    incidents: list[Incident] = []
    for m in sc["majors"]:
        colors = [Color(c) for c, n in m["colors"].items() for _ in range(n)]
        ages = [int(rng.integers(18, 80)) for _ in colors]
        incidents.append(_make_incident(m["id"], m["t_call"], m["location"], m["type"], m["category"], colors, ages,
                                        m.get("trapped", 0), m.get("needs_rescue", False), True, rng))

    mix = res["background_mix"]
    types = list(mix.keys())
    shares = np.array([mix[t]["share"] for t in types])
    forced = list(sc.get("background_force", []))
    for k in range(sc["background_calls"]):
        t_type = forced[k] if k < len(forced) else types[rng.choice(len(types), p=shares / shares.sum())]
        spec = mix[t_type]
        cw = spec["colors"]
        color = Color(list(cw)[rng.choice(len(cw), p=np.array(list(cw.values())) / sum(cw.values()))])
        child = t_type not in ("cardiac_arrest", "stroke", "chest_pain") and rng.random() < res["child_share"]
        age = int(rng.integers(2, 15)) if child else int(rng.integers(70, 92) if t_type == "fall" else rng.integers(25, 85))
        incidents.append(_make_incident(f"B{k + 1:02d}", rng.integers(0, window), _hotspot(rng, res["hotspots"], size),
                                        t_type, spec["category"], [color], [age], 0, False, False, rng))
    incidents.sort(key=lambda i: (i.t_call, i.id))
    for k, inc in enumerate(incidents):               # stable ids in call order
        old = inc.id
        inc.id = f"I{k + 1:02d}"
        for j, p in enumerate(inc.patients):
            p.id, p.incident_id = f"{inc.id}-P{j + 1:02d}", inc.id
        inc.description = f"{old}"

    n_amb = n_ambulances or sc.get("ambulances", 5)
    ambs = [Ambulance(a["id"], tuple(a["location"]), a["als"]) for a in res["ambulances"][:n_amb]]
    teams = [RescueTeam(t["id"], tuple(t["location"]), list(t["skills"])) for t in res["teams"]]
    return Scenario(sc["name"], seed, incidents, ambs, teams, board_overrides=sc.get("hospitals", {}),
                    congestion=sc.get("congestion", "normal"), bridge_closed=sc.get("bridge_closed", False))


def scenario_to_dict(s: Scenario) -> dict:
    return {
        "name": s.name, "seed": s.seed, "congestion": s.congestion,
        "incidents": [{
            "id": i.id, "t_call": i.t_call, "location": list(i.location), "type": i.type, "is_major": i.is_major,
            "needs_rescue": i.needs_rescue, "reported_victims": i.reported_victims, "reported_colors": i.reported_colors,
            "dispatch_code": i.dispatch_code, "description": i.description,
            "patients": [{"id": p.id, "age": p.age, "category": p.category, "true_color": p.true_color.value,
                          "reported_color": p.reported_color.value, "needs_extrication": p.needs_extrication}
                         for p in i.patients],
        } for i in s.incidents],
        "ambulances": [{"id": a.id, "location": list(a.location), "als": a.als} for a in s.ambulances],
        "teams": [{"id": t.id, "location": list(t.location), "skills": t.skills} for t in s.teams],
        "hospital_overrides": s.board_overrides,
    }


def _seeds(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--seed", default="0")
    ap.add_argument("--seeds")
    args = ap.parse_args()
    names = MVP_SCENARIOS if args.all else [args.scenario]
    out = ROOT / "data" / "generated"
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        for seed in _seeds(args.seeds or args.seed):
            s = build_scenario(name, seed)
            path = out / f"{name}_seed{seed}.json"
            path.write_text(json.dumps(scenario_to_dict(s), indent=1, ensure_ascii=False))
            print(path.relative_to(ROOT), len(s.incidents), "incidents", sum(i.victims for i in s.incidents), "victims")


if __name__ == "__main__":
    main()
