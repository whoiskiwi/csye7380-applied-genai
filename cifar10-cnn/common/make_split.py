"""Build a fixed, stratified train/val split shared by Part A and Part B.

Splits the 50k CIFAR-10 *training* set into 45k train / 5k val (stratified by
class, seed 42) and writes the index lists to ``common/val_split.json``. The
10k test set is never touched. Both implementations load this same file so the
validation and test sets are identical -> a fair A-vs-B comparison.

Run once:  python common/make_split.py
"""
import json
from pathlib import Path

import numpy as np
from torchvision.datasets import CIFAR10

SEED = 42
VAL_PER_CLASS = 500  # 500 * 10 classes = 5000 val images
REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "data"
OUT = Path(__file__).resolve().parent / "val_split.json"


def main() -> None:
    # download=True so the split can be built on a fresh checkout
    ds = CIFAR10(root=str(DATA_DIR), train=True, download=True)
    targets = np.array(ds.targets)

    rng = np.random.default_rng(SEED)
    train_idx, val_idx = [], []
    for cls in range(10):
        cls_idx = np.where(targets == cls)[0]
        rng.shuffle(cls_idx)
        val_idx.extend(cls_idx[:VAL_PER_CLASS].tolist())
        train_idx.extend(cls_idx[VAL_PER_CLASS:].tolist())

    train_idx.sort()
    val_idx.sort()

    payload = {
        "seed": SEED,
        "val_per_class": VAL_PER_CLASS,
        "train_indices": train_idx,
        "val_indices": val_idx,
    }
    OUT.write_text(json.dumps(payload))
    print(f"Wrote {OUT}")
    print(f"  train: {len(train_idx)}  val: {len(val_idx)}")


if __name__ == "__main__":
    main()
