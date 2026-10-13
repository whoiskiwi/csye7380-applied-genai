"""Prepare gretelai/synthetic_text_to_sql for chat-style LLM fine-tuning.

Outputs:
  data/test.jsonl         - stratified subset of the official test split whose gold SQL
                            executes in SQLite; SHARED by every version (before/after comparison)
  data/<name>/train.jsonl - stratified subset of the official train split (fine-tuning)
  data/<name>/val.jsonl   - held-out slice of the train split (eval loss during training)
  data/<name>/stats.json  - split sizes and category distributions

Each row keeps the raw fields plus a `messages` list (system/user/assistant)
that works with any chat template (Qwen, Llama, Phi, ...).

Usage (local or Colab):
  python prepare_data.py                  # v1: raw data      -> data/v1/ + data/test.jsonl
  python prepare_data.py --sqlite-only    # v2: SQLite-only   -> data/v2/ + data/test.jsonl
"""
import argparse
import json
import os
import sqlite3

import pandas as pd
from datasets import load_dataset

SYSTEM_PROMPT = (
    "You are an expert SQL assistant. Given a database schema and a question, "
    "write a correct SQLite query that answers the question, then briefly "
    "explain what the query does."
)

KEEP_COLS = ["id", "domain", "sql_complexity", "sql_task_type",
             "sql_prompt", "sql_context", "sql", "sql_explanation"]


def build_user(context, question):
    return f"### Database schema:\n{context}\n\n### Question:\n{question}"


def build_assistant(sql, explanation):
    return f"```sql\n{sql}\n```\n\nExplanation: {explanation}"


def to_messages(row):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user(row["sql_context"], row["sql_prompt"])},
        {"role": "assistant", "content": build_assistant(row["sql"], row["sql_explanation"])},
    ]


def run_sql(context, sql, timeout_ops=200_000):
    """Run schema + query in a fresh in-memory SQLite DB. Returns rows or None on error."""
    conn = sqlite3.connect(":memory:")
    # Abort pathological queries instead of hanging.
    steps = {"n": 0}

    def guard():
        steps["n"] += 1
        return 1 if steps["n"] > timeout_ops else 0

    conn.set_progress_handler(guard, 1000)
    try:
        conn.executescript(context)
        cur = conn.execute(sql)
        return cur.fetchall()
    except Exception:
        return None
    finally:
        conn.close()


def clean(df):
    df = df[KEEP_COLS].copy()
    for c in ["sql_prompt", "sql_context", "sql", "sql_explanation"]:
        df[c] = df[c].astype(str).str.strip()
    df = df[(df[["sql_prompt", "sql_context", "sql", "sql_explanation"]] != "").all(axis=1)]
    df = df.drop_duplicates(subset=["sql_prompt", "sql_context"])
    return df


def stratified_sample(df, n, seed, col="sql_complexity"):
    """Sample n rows keeping the `col` distribution (each class gets >= 1 row)."""
    if n >= len(df):
        return df.sample(frac=1, random_state=seed)
    frac = n / len(df)
    parts = [g.sample(max(1, round(len(g) * frac)), random_state=seed)
             for _, g in df.groupby(col)]
    out = pd.concat(parts)
    if len(out) < n:  # per-class rounding can come up a row or two short
        out = pd.concat([out, df.drop(out.index).sample(n - len(out), random_state=seed)])
    return out.sample(frac=1, random_state=seed).head(n)


def save_jsonl(df, path):
    with open(path, "w") as f:
        for row in df.to_dict(orient="records"):
            row["messages"] = to_messages(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-train", type=int, default=10_000)
    p.add_argument("--n-val", type=int, default=500)
    p.add_argument("--n-test", type=int, default=300)
    p.add_argument("--max-context-chars", type=int, default=1500,
                   help="drop very long schemas to keep sequences short")
    p.add_argument("--sqlite-only", action="store_true",
                   help="keep only train/val rows whose gold SQL runs in SQLite (drops MySQL/Postgres-only syntax)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="data", help="data root; test.jsonl goes here")
    p.add_argument("--name", default=None, help="train/val subfolder (default: v2 if --sqlite-only else v1)")
    args = p.parse_args()

    args.name = args.name or ("v2" if args.sqlite_only else "v1")
    split_dir = os.path.join(args.out, args.name)
    os.makedirs(split_dir, exist_ok=True)
    ds = load_dataset("gretelai/synthetic_text_to_sql")
    train_all = clean(ds["train"].to_pandas())
    test_all = clean(ds["test"].to_pandas())
    print(f"after cleaning: train={len(train_all)} test={len(test_all)}")

    train_all = train_all[train_all["sql_context"].str.len() <= args.max_context_chars]
    test_all = test_all[test_all["sql_context"].str.len() <= args.max_context_chars]

    # Make sure no test question/schema pair leaks into training.
    test_keys = set(zip(test_all["sql_prompt"], test_all["sql_context"]))
    train_all = train_all[[k not in test_keys for k in zip(train_all["sql_prompt"], train_all["sql_context"])]]

    if args.sqlite_only:
        ok = [run_sql(c, s) is not None for c, s in zip(train_all["sql_context"], train_all["sql"])]
        print(f"sqlite-only: kept {sum(ok)}/{len(ok)} train rows whose gold SQL runs in SQLite")
        train_all = train_all[ok]

    # Train / val come from the official train split.
    val = stratified_sample(train_all, args.n_val, args.seed)
    rest = train_all.drop(val.index)
    train = stratified_sample(rest, args.n_train, args.seed)

    # Test: only keep SELECT-style rows whose gold SQL runs in SQLite and returns
    # something, so we can score by execution accuracy (not just string match).
    cand = test_all[test_all["sql"].str.lstrip().str.upper().str.startswith(("SELECT", "WITH"))].copy()
    cand["gold_result"] = [run_sql(c, s) for c, s in zip(cand["sql_context"], cand["sql"])]
    executable = cand[cand["gold_result"].map(lambda r: r is not None and len(r) > 0)].copy()
    print(f"test candidates: {len(cand)} SELECT/WITH, {len(executable)} executable in SQLite")
    test = stratified_sample(executable, args.n_test, args.seed).drop(columns=["gold_result"])

    save_jsonl(train, os.path.join(split_dir, "train.jsonl"))
    save_jsonl(val, os.path.join(split_dir, "val.jsonl"))
    save_jsonl(test, os.path.join(args.out, "test.jsonl"))   # same seed/filter -> identical for every version

    stats = {
        "args": vars(args),
        "sizes": {"train": len(train), "val": len(val), "test": len(test)},
        "test_executable_pool": len(executable),
        "complexity": {n: d["sql_complexity"].value_counts().to_dict()
                       for n, d in [("train", train), ("val", val), ("test", test)]},
        "task_type": {n: d["sql_task_type"].value_counts().to_dict()
                      for n, d in [("train", train), ("val", val), ("test", test)]},
    }
    with open(os.path.join(split_dir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats["sizes"], indent=2))
    print(json.dumps(stats["complexity"], indent=2))


if __name__ == "__main__":
    main()
