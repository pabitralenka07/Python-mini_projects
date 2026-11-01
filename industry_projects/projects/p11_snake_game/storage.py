"""Atomic JSON storage for Snake Game high scores."""

import json
import os
from pathlib import Path


def load_high_score(storage_path: Path) -> int:
    """Reads high score from JSON file; returns 0 if absent or corrupt."""
    if not storage_path.exists():
        return 0
    try:
        with open(storage_path, encoding="utf-8") as f:
            data = json.load(f)
            return int(data.get("high_score", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        return 0


def save_high_score(storage_path: Path, score: int) -> None:
    """Atomically persists high score to disk using a temporary file replacement."""
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = storage_path.with_suffix(".tmp")

    payload = {"high_score": max(0, score)}
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_path, storage_path)
