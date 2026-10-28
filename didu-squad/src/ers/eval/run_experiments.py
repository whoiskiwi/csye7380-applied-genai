"""Run a grid of (scenario x seed x policy) and save logs, snapshots, decisions and metrics.

Usage:
    uv run python -m ers.eval.run_experiments --config configs/exp_baselines.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

import pandas as pd
import yaml

from ers.config import ROOT
from ers.data.generate import build_scenario
from ers.env.simulator import Simulation
from ers.eval.metrics import compute_metrics


def make_policy(name: str, options: dict | None = None):
    options = options or {}
    if name == "B0":
        from ers.policies.b0_nearest import NearestPolicy
        return NearestPolicy()
    if name == "B1":
        from ers.policies.b1_rules import RulePolicy
        return RulePolicy()
    if name in ("MA", "MA-NoNeg"):
        from ers.policies.ma import MultiAgentPolicy
        return MultiAgentPolicy(negotiate=(name == "MA"), **options)
    raise ValueError(f"unknown policy {name}")


def _git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def _config_hash() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "configs").rglob("*.yaml")):
        if p.name.startswith("."):          # skip macOS "._" metadata files
            continue
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def run_one(scenario: str, seed: int, policy: str, out_root: Path, options: dict | None = None,
            n_ambulances: int | None = None) -> dict:
    pol = make_policy(policy, options)
    sim = Simulation(build_scenario(scenario, seed, n_ambulances=n_ambulances), pol)
    t0 = time.time()
    sim.run()
    m = compute_metrics(sim)
    m["wall_seconds"] = round(time.time() - t0, 1)
    if hasattr(pol, "stats"):
        m.update(pol.stats())
    run_id = f"{scenario}_seed{seed}_{policy}" + (f"_amb{n_ambulances}" if n_ambulances else "")
    d = out_root / run_id
    d.mkdir(parents=True, exist_ok=True)
    sim.save_log(d / "events.jsonl")
    with open(d / "snapshots.jsonl", "w", encoding="utf-8") as f:
        for s in sim.snapshots:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with open(d / "decisions.jsonl", "w", encoding="utf-8") as f:
        for r in getattr(pol, "decisions", []):
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    (d / "metrics.json").write_text(json.dumps(m, indent=1))
    manifest = {"run_id": run_id, "scenario": scenario, "seed": seed, "policy": policy, "options": options or {},
                "n_ambulances": n_ambulances, "git": _git_rev(), "config_hash": _config_hash(),
                "model": getattr(pol, "model_info", lambda: {})()}
    (d / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / args.config if not Path(args.config).is_absolute() else args.config))
    out_root = ROOT / "runs" / cfg.get("name", "exp")
    rows = []
    for sc in cfg["scenarios"]:
        for seed in cfg["seeds"]:
            for pol in cfg["policies"]:
                for n_amb in cfg.get("ambulances", [None]):
                    m = run_one(sc, seed, pol, out_root, cfg.get("options", {}).get(pol), n_amb)
                    m["n_ambulances"] = n_amb
                    rows.append(m)
                    print(f"{sc} seed={seed} {pol:8s} served={m['served_rate']:.2f} red_win={m['red_in_window_rate']:.2f} "
                          f"resp={m['response_time_mean']} ({m['wall_seconds']}s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_root / "summary.csv", index=False)
    print(f"\nsaved {len(df)} runs to {out_root.relative_to(ROOT)}/summary.csv")


if __name__ == "__main__":
    main()
