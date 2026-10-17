"""Save file for the Build Your Reactor game.

Kept apart from the usage log on purpose: the game never reads or writes
real electricity data, and deleting one file never touches the other.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

MAX_BYTES = 256_000


def load(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save(path: Path, data: dict) -> None:
    if not isinstance(data, dict):
        raise TypeError("game save must be a JSON object")
    text = json.dumps(data, separators=(",", ":"))
    if len(text) > MAX_BYTES:
        raise ValueError("game save is too large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
