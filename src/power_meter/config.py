"""Load settings from config.toml, falling back to built-in defaults."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .estimate import EstimateConfig
from .tariff import FlatTariff, Tariff, TouTariff, thai_holidays


@dataclass(frozen=True)
class Config:
    tariff: Tariff
    estimate: EstimateConfig = field(default_factory=EstimateConfig)
    interval_sec: float = 2.0
    save_every_sec: float = 30.0
    lhm_url: str = "http://localhost:8085/data.json"
    data_file: Path = field(default_factory=lambda: default_data_dir() / "usage.json")


def default_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share"
    return Path(base) / "power-meter"


def load(path: Path | None) -> Config:
    raw: dict = {}
    if path is not None and path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)

    app = raw.get("app", {})
    est = raw.get("estimate", {})
    kwargs = {}
    if "data_file" in app:
        kwargs["data_file"] = Path(app["data_file"]).expanduser()

    return Config(
        tariff=_load_tariff(raw.get("tariff", {})),
        estimate=EstimateConfig(**est),
        interval_sec=app.get("interval_sec", 2.0),
        save_every_sec=app.get("save_every_sec", 30.0),
        lhm_url=app.get("lhm_url", "http://localhost:8085/data.json"),
        **kwargs,
    )


def _load_tariff(t: dict) -> Tariff:
    # Defaults: MEA/PEA residential, Sep-Dec 2026 Ft.
    ft = t.get("ft", 0.1623)
    vat = t.get("vat", 0.07)
    kind = t.get("type", "tou")

    if kind == "flat":
        return FlatTariff(rate=t.get("flat_rate", 3.78), ft=ft, vat=vat)
    if kind != "tou":
        raise ValueError(f'tariff.type must be "tou" or "flat", got {kind!r}')

    start, end = t.get("peak_hours", [9, 22])
    return TouTariff(
        peak_rate=t.get("peak_rate", 5.7982),
        off_peak_rate=t.get("off_peak_rate", 2.6369),
        ft=ft,
        vat=vat,
        peak_start_hour=start,
        peak_end_hour=end,
        holidays=thai_holidays(),
    )
