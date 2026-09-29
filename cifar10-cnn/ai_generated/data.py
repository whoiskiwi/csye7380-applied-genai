"""CIFAR-10 data loaders for Part B, using the shared train/val split.

Train transform = standard augmentation (random crop + horizontal flip) plus
per-channel normalization. Val/test transform = normalization only. The train
and val Subsets are drawn from the same underlying CIFAR-10 training set but
carry different transforms, so we materialize two dataset objects.
"""
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset
from torchvision import transforms
from torchvision.datasets import CIFAR10

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "data"
SPLIT_FILE = REPO / "common" / "val_split.json"

# CIFAR-10 per-channel mean/std (standard values)
MEAN = (0.4914, 0.4822, 0.4465)
STD = (0.2470, 0.2435, 0.2616)

CLASSES = [
    "airplane", "automobile", "bird", "cat", "deer",
    "dog", "frog", "horse", "ship", "truck",
]

_train_tf = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])

_eval_tf = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])


def _load_split() -> dict:
    if not SPLIT_FILE.exists():
        raise FileNotFoundError(
            f"{SPLIT_FILE} not found. Run: python common/make_split.py"
        )
    return json.loads(SPLIT_FILE.read_text())


def get_loaders(batch_size: int = 128, quick: bool = False, num_workers: int = 0):
    """Return (train_loader, val_loader, test_loader).

    quick=True uses a small subset for a fast smoke test.
    """
    split = _load_split()
    train_idx = split["train_indices"]
    val_idx = split["val_indices"]

    # two views of the training set: augmented (train) and clean (val)
    train_full = CIFAR10(root=str(DATA_DIR), train=True, download=True, transform=_train_tf)
    val_full = CIFAR10(root=str(DATA_DIR), train=True, download=True, transform=_eval_tf)
    test_set = CIFAR10(root=str(DATA_DIR), train=False, download=True, transform=_eval_tf)

    if quick:
        train_idx = train_idx[:2000]
        val_idx = val_idx[:1000]
        test_set = Subset(test_set, list(range(1000)))

    train_set = Subset(train_full, train_idx)
    val_set = Subset(val_full, val_idx)

    common = dict(batch_size=batch_size, num_workers=num_workers, pin_memory=False)
    train_loader = DataLoader(train_set, shuffle=True, **common)
    val_loader = DataLoader(val_set, shuffle=False, **common)
    test_loader = DataLoader(test_set, shuffle=False, **common)
    return train_loader, val_loader, test_loader


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")
