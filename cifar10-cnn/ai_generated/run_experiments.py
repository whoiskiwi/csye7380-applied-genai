"""Run the full Part B experiment matrix and write results.

Three studies, one factor varied at a time from a fixed baseline
(3 conv blocks, BN on, dropout 0.5, ReLU):

  Set 1 -- BN & Dropout:  {none, dropout-only, bn-only, both}
  Set 2 -- Depth:         num_blocks in {1, 2, 3, 4}
  Set 3 -- Activation:    {relu, leaky_relu, elu, tanh, sigmoid}
  Bonus -- sigmoid without BN vs with BN (vanishing-gradient demo)

The baseline config is shared across sets, so we run each *unique* config once
and expand it into the per-set result tables afterwards.

Usage:
  python run_experiments.py            # full run (~25 epochs each)
  python run_experiments.py --quick    # smoke test (tiny subset, 1 epoch)
"""
import argparse
import csv
from pathlib import Path

import torch

from data import get_device, get_loaders
from models import ConfigurableCNN, count_params
from train import train_model

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "results"
HISTORY_DIR = RESULTS_DIR / "history"
CSV_PATH = RESULTS_DIR / "part_b_results.csv"

CSV_COLUMNS = [
    "experiment_set", "run_name", "num_blocks", "use_bn", "dropout", "activation",
    "num_params", "epochs", "train_time_s", "final_train_loss", "final_val_loss",
    "best_val_acc", "test_acc",
]

BASELINE = dict(num_blocks=3, use_bn=True, dropout=0.5, activation="relu")


def load_done(epochs: int) -> dict:
    """Return {run_name: row} for configs already saved at this epoch count."""
    if not CSV_PATH.exists():
        return {}
    done = {}
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            if int(row["epochs"]) == epochs:
                done[row["run_name"]] = row
    return done


def _cfg(**overrides):
    c = dict(BASELINE)
    c.update(overrides)
    return c


# (experiment_set, run_name, config). run_name is unique and shared with Part A.
EXPERIMENTS = [
    # Set 1 -- BatchNorm & Dropout
    ("bn_dropout", "reg_none",         _cfg(use_bn=False, dropout=0.0)),
    ("bn_dropout", "reg_dropout_only", _cfg(use_bn=False, dropout=0.5)),
    ("bn_dropout", "reg_bn_only",      _cfg(use_bn=True,  dropout=0.0)),
    ("bn_dropout", "reg_bn_dropout",   _cfg(use_bn=True,  dropout=0.5)),  # == baseline
    # Set 2 -- Depth (number of conv/pool blocks)
    ("depth", "depth_1block", _cfg(num_blocks=1)),
    ("depth", "depth_2block", _cfg(num_blocks=2)),
    ("depth", "depth_3block", _cfg(num_blocks=3)),  # == baseline
    ("depth", "depth_4block", _cfg(num_blocks=4)),
    # Set 3 -- Activation function
    ("activation", "act_relu",       _cfg(activation="relu")),  # == baseline
    ("activation", "act_leaky_relu", _cfg(activation="leaky_relu")),
    ("activation", "act_elu",        _cfg(activation="elu")),
    ("activation", "act_tanh",       _cfg(activation="tanh")),
    ("activation", "act_sigmoid",    _cfg(activation="sigmoid")),
    # Bonus -- vanishing-gradient demo: sigmoid without BN vs with BN
    ("vanishing", "vg_sigmoid_no_bn", _cfg(activation="sigmoid", use_bn=False)),
    ("vanishing", "vg_sigmoid_bn",    _cfg(activation="sigmoid", use_bn=True)),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fast smoke test")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--force", action="store_true", help="re-run all, ignore saved results")
    args = ap.parse_args()

    quick = args.quick
    epochs = args.epochs or (1 if quick else 25)

    device = get_device()
    print(f"device: {device}  |  quick={quick}  epochs={epochs}")
    loaders = get_loaders(batch_size=128, quick=quick)

    RESULTS_DIR.mkdir(exist_ok=True)
    HISTORY_DIR.mkdir(exist_ok=True)

    # resume: reuse rows already computed at this epoch count (crash-safe / skip done)
    done = load_done(epochs) if not args.force else {}
    if done:
        print(f"resume: {len(done)} config(s) already done at {epochs} epochs -> will skip")

    def flush(rows):
        with CSV_PATH.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            w.writeheader()
            w.writerows(rows)

    rows = []
    for i, (exp_set, run_name, cfg) in enumerate(EXPERIMENTS, 1):
        if run_name in done:
            print(f"\n[{i}/{len(EXPERIMENTS)}] {run_name}  -- SKIP (already done)")
            rows.append(done[run_name])
            continue
        print(f"\n[{i}/{len(EXPERIMENTS)}] {exp_set} :: {run_name}  {cfg}")
        torch.manual_seed(42)
        model = ConfigurableCNN(**cfg)
        n_params = count_params(model)
        history, metrics = train_model(model, loaders, device, epochs=epochs)

        # per-epoch history for plotting
        hpath = HISTORY_DIR / f"{run_name}.csv"
        with hpath.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["epoch", "train_loss", "train_acc", "val_loss", "val_acc"])
            for e in range(len(history["train_loss"])):
                w.writerow([
                    e + 1,
                    history["train_loss"][e], history["train_acc"][e],
                    history["val_loss"][e], history["val_acc"][e],
                ])

        rows.append({
            "experiment_set": exp_set,
            "run_name": run_name,
            "num_blocks": cfg["num_blocks"],
            "use_bn": cfg["use_bn"],
            "dropout": cfg["dropout"],
            "activation": cfg["activation"],
            "num_params": n_params,
            **metrics,
        })
        flush(rows)  # incremental write -> a crash keeps every finished config
        print(f"    -> test_acc {metrics['test_acc']:.4f}  best_val_acc {metrics['best_val_acc']:.4f}")

    flush(rows)
    print(f"\nDone. Wrote {CSV_PATH} ({len(rows)} runs) and per-run history to {HISTORY_DIR}")


if __name__ == "__main__":
    main()
