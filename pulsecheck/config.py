from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    data["_config_path"] = str(config_path)
    data["_config_dir"] = str(config_path.parent)
    return data


def resolve_from_config(config: dict[str, Any], value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return Path(config["_config_dir"]).joinpath(candidate).resolve()


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]
