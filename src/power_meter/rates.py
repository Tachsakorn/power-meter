"""Thai electricity rates, kept current without anyone editing a file.

The Ft surcharge changes every four months. The app ships with the rates it
knows about and, on start, quietly fetches rates.json from the project's
GitHub repo; whoever maintains the repo updates that one file and every
copy of the app picks it up. Without a connection the built-in or last
downloaded rates are used.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

UPDATE_URL = "https://raw.githubusercontent.com/Tachsakorn/power-meter/main/rates.json"

BUILT_IN = {
    "updated": "2026-10-17",
    "vat": 0.07,
    # Base energy rates for residential meters, baht per kWh before Ft and VAT.
    "flat_rate": 3.78,
    "tou": {"peak": 5.7982, "off_peak": 2.6369, "peak_hours": [9, 22]},
    # Ft by the first day it applies (ERC announcements).
    "ft": [{"from": "2026-09-01", "ft": 0.1623}],
}


def load(cache: Path) -> dict:
    """The newest rates we have: downloaded ones if newer than the built-in."""
    try:
        cached = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return BUILT_IN
    if _valid(cached) and cached["updated"] > BUILT_IN["updated"]:
        return cached
    return BUILT_IN


def refresh(cache: Path, timeout: float = 4.0) -> bool:
    """Download rates.json into the cache. Returns True if something new arrived."""
    try:
        with urllib.request.urlopen(UPDATE_URL, timeout=timeout) as resp:
            data = json.loads(resp.read(64_000).decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False
    if not _valid(data) or data["updated"] <= load(cache)["updated"]:
        return False
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return True


def ft_on(rates: dict, day: date) -> float:
    current = None
    for entry in sorted(rates["ft"], key=lambda e: e["from"]):
        if entry["from"] <= day.isoformat():
            current = entry["ft"]
    return current if current is not None else rates["ft"][0]["ft"]


def _valid(data: object) -> bool:
    try:
        return (
            isinstance(data["updated"], str)
            and 0 < data["vat"] < 1
            and data["flat_rate"] > 0
            and data["tou"]["peak"] > 0
            and data["tou"]["off_peak"] > 0
            and len(data["tou"]["peak_hours"]) == 2
            and all(isinstance(e["from"], str) and -5 < e["ft"] < 5 for e in data["ft"])
            and len(data["ft"]) > 0
        )
    except (KeyError, TypeError):
        return False
