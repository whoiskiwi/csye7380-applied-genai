"""Write docs/results.md from an experiment's summary.csv and decision records.

Usage:
    uv run python -m ers.eval.report runs/mvp
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ers.config import ROOT
from ers.eval.stats import paired

ORDER = ["B0", "B1", "MA-NoNeg", "MA"]
SHOW = [("served_rate", "Served in window (share)"), ("red_in_window_rate", "Red patients in window (share)"),
        ("unserved_critical_incidents", "Unserved critical incidents"), ("capability_match_rate", "Capability match (share)"),
        ("response_time_mean", "Mean response time (min)"), ("time_critical_response_mean", "Cardiac arrest / stroke response (min)"),
        ("ambulance_utilisation", "Ambulance utilisation")]


def _md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if pd.isna(v) else (f"{v:.3f}" if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp_dir")
    ap.add_argument("--out", default="docs/results.md")
    args = ap.parse_args()
    exp = ROOT / args.exp_dir if not Path(args.exp_dir).is_absolute() else Path(args.exp_dir)
    df = pd.read_csv(exp / "summary.csv")
    pols = [p for p in ORDER if p in set(df.policy)]
    lines = [f"# Results ({exp.name})", "",
             f"{df.scenario.nunique()} scenarios × {df.seed.nunique()} seeds; every method runs on the same generated "
             "instances. MA and MA-NoNeg use the same local model and prompts; the only difference is negotiation.", ""]

    lines += ["## Mean per scenario", ""]
    for col, label in SHOW:
        t = df.pivot_table(index="scenario", columns="policy", values=col, aggfunc="mean")[pols].reset_index()
        lines += [f"**{label}**", "", _md(t), ""]

    for a, b in [("MA", "MA-NoNeg"), ("MA", "B1"), ("MA-NoNeg", "B1")]:
        if a in pols and b in pols:
            p = paired(df, a, b, by_scenario=True)
            lines += [f"## Paired difference: {a} − {b}", "",
                      "Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; "
                      "Wilcoxon signed-rank p-value (n is small, so treat it as indicative).", "",
                      _md(p[["group", "metric", "n", f"{a}_mean", f"{b}_mean", "diff_mean", "ci95_low", "ci95_high",
                             "wilcoxon_p", "better"]]), ""]

    llm = df[df.policy.isin(["MA", "MA-NoNeg"])]
    if not llm.empty:
        cols = [c for c in ["llm_calls", "llm_failures", "fallbacks", "partial_fills", "fallback_rate", "tokens_in",
                            "tokens_out", "agent_escalations", "mean_rounds", "rule_retries", "rule_violations_kept",
                            "accept_mismatch", "redirects", "messages", "wall_seconds"] if c in llm]
        lines += ["## LLM usage per run (mean)", "", _md(llm.groupby("policy")[cols].mean().reset_index()), ""]

    rule_rows = []
    for mf in sorted(exp.glob("*/metrics.json")):
        m = json.loads(mf.read_text())
        for r in m.get("rule_log", []):
            rule_rows.append({"policy": m["policy"], "agent": r["agent"], "fixed": r["fixed_by_retry"]})
    if rule_rows:
        rr = pd.DataFrame(rule_rows).groupby(["policy", "agent"]).agg(
            violations=("fixed", "size"), fixed_by_retry=("fixed", "mean")).reset_index()
        lines += ["## Role-rule checks", "",
                  "An agent that breaks a rule of its own prompt is told which rule and answers once more; the second "
                  "answer is used either way. `fixed_by_retry` = share of violations the second answer corrected.", "",
                  _md(rr), ""]

    rows = []
    for d in sorted(exp.glob("*/decisions.jsonl")):
        man = json.loads((d.parent / "manifest.json").read_text())
        for line in open(d):
            r = json.loads(line)
            if r.get("final_destination"):
                rows.append({"policy": man["policy"], "rule": r["final_destination"] == r["rule_reference"],
                             "nearest": r["final_destination"] == r["baseline"],
                             "changed": r["final_destination"] != r["dispatch_proposal"], "red": r["lead_color"] == "red"})
    if rows:
        dr = pd.DataFrame(rows)
        g = dr.groupby("policy").agg(decisions=("rule", "size"), same_as_rule=("rule", "mean"),
                                     same_as_nearest=("nearest", "mean"),
                                     changed_by_negotiation=("changed", "mean")).reset_index()
        lines += ["## Transport decisions vs references", "",
                  "`changed_by_negotiation` = final destination differs from Dispatch's first proposal.", "", _md(g), ""]
    out = ROOT / args.out
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
