"""Paired comparison of policies on the same (scenario, seed) instances.

Usage:
    uv run python -m ers.eval.stats runs/mvp/summary.csv --a MA --b MA-NoNeg
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

METRICS = [  # (column, higher_is_better)
    ("served_rate", True), ("red_in_window_rate", True), ("unserved_critical_incidents", False),
    ("capability_match_rate", True), ("response_time_mean", False), ("time_critical_response_mean", False),
    ("ambulance_utilisation", None),
]


def bootstrap_ci(diff: np.ndarray, n: int = 5000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = rng.choice(diff, size=(n, len(diff)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired(df: pd.DataFrame, a: str, b: str, by_scenario: bool = False) -> pd.DataFrame:
    keys = ["scenario", "seed"]
    rows = []
    groups = [("all", df)] + (list(df.groupby("scenario")) if by_scenario else [])
    for name, g in groups:
        A = g[g.policy == a].set_index(keys)
        B = g[g.policy == b].set_index(keys)
        common = A.index.intersection(B.index)
        for col, better in METRICS:
            x, y = A.loc[common, col].astype(float), B.loc[common, col].astype(float)
            ok = x.notna() & y.notna()
            d = (x[ok] - y[ok]).to_numpy()
            if len(d) == 0:
                continue
            lo, hi = bootstrap_ci(d) if len(d) > 1 else (float(d[0]), float(d[0]))
            try:
                p = float(wilcoxon(d).pvalue) if np.any(d != 0) and len(d) >= 5 else float("nan")
            except ValueError:
                p = float("nan")
            rows.append({"group": name, "metric": col, "n": len(d), f"{a}_mean": round(float(x[ok].mean()), 3),
                         f"{b}_mean": round(float(y[ok].mean()), 3), "diff_mean": round(float(d.mean()), 3),
                         "ci95_low": round(lo, 3), "ci95_high": round(hi, 3), "wilcoxon_p": round(p, 4),
                         "better": None if better is None else ("A" if (d.mean() > 0) == better and d.mean() != 0 else
                                                                 "B" if d.mean() != 0 else "=")})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary")
    ap.add_argument("--a", default="MA")
    ap.add_argument("--b", default="MA-NoNeg")
    ap.add_argument("--by-scenario", action="store_true")
    args = ap.parse_args()
    df = pd.read_csv(args.summary)
    pd.set_option("display.width", 200)
    print(paired(df, args.a, args.b, args.by_scenario).to_string(index=False))


if __name__ == "__main__":
    main()
