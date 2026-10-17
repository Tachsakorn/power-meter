"""Daily usage log, stored as JSON.

Cost is stored alongside energy so that past days keep the price that
applied at the time, even after Ft changes.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FORMAT_VERSION = 1


@dataclass
class Usage:
    wh: float = 0.0
    baht: float = 0.0

    def add(self, wh: float, baht: float) -> None:
        self.wh += wh
        self.baht += baht


class UsageLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.days: dict[str, dict[str, Usage]] = self._load()
        self.total_baht = sum(u.baht for periods in self.days.values() for u in periods.values())

    def add(self, day: date, period: str, wh: float, baht: float) -> None:
        self.days.setdefault(day.isoformat(), {}).setdefault(period, Usage()).add(wh, baht)
        self.total_baht += baht

    def day_total(self, day: date) -> Usage:
        total = Usage()
        for u in self.days.get(day.isoformat(), {}).values():
            total.add(u.wh, u.baht)
        return total

    def save(self) -> None:
        data = {
            "version": FORMAT_VERSION,
            "days": {
                day: {
                    p: {"wh": round(u.wh, 4), "baht": round(u.baht, 6)} for p, u in periods.items()
                }
                for day, periods in sorted(self.days.items())
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def _load(self) -> dict[str, dict[str, Usage]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") != FORMAT_VERSION:
                raise ValueError(f"unsupported version {data.get('version')}")
            return {
                day: {p: Usage(**u) for p, u in periods.items()}
                for day, periods in data["days"].items()
            }
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            # Keep the unreadable file instead of silently overwriting it.
            backup = self.path.with_suffix(".bak")
            os.replace(self.path, backup)
            print(f"usage log unreadable ({exc}); moved to {backup}")
            return {}
