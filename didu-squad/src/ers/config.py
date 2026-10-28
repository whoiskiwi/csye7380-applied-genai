"""Load the YAML configuration files."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"


@lru_cache(maxsize=None)
def load_yaml(name: str) -> dict:
    path = Path(name) if Path(name).is_absolute() else CONFIG_DIR / name
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def assumptions() -> dict:
    return load_yaml("assumptions.yaml")


def hospitals_cfg() -> dict:
    return load_yaml("hospitals.yaml")
