"""Settings, worked out automatically wherever possible.

Nothing has to be configured: rates come from rates.py, hardware from
hardware.py, and the meter type is picked once inside the app. config.toml
is still read if present, for people who want to override something.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import rates as rates_mod
from . import settings as settings_mod
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
    rates: dict = field(default_factory=lambda: rates_mod.BUILT_IN)
    meter_chosen: bool = True  # False until the user has said which meter they have
    tariff_overrides: dict = field(default_factory=dict)  # [tariff] from config.toml

    @property
    def meter(self) -> str:
        return "tou" if isinstance(self.tariff, TouTariff) else "flat"

    @property
    def settings_file(self) -> Path:
        return self.data_file.with_name("settings.json")

    @property
    def rates_file(self) -> Path:
        return self.data_file.with_name("rates.json")


def default_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share"
    return Path(base) / "power-meter"


def load(path: Path | None) -> Config:
    raw: dict = {}
    if path is not None and path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)

    app = raw.get("app", {})
    t = raw.get("tariff", {})
    data_file = (
        Path(app["data_file"]).expanduser()
        if "data_file" in app
        else default_data_dir() / "usage.json"
    )
    rates = rates_mod.load(data_file.with_name("rates.json"))
    chosen = settings_mod.load(data_file.with_name("settings.json")).get("meter")
    kind = t.get("type") or chosen or "flat"
    if kind not in settings_mod.METER_TYPES:
        raise ValueError(f'tariff.type must be "tou" or "flat", got {kind!r}')

    return Config(
        tariff=build_tariff(kind, rates, date.today(), overrides=t),
        estimate=EstimateConfig(**raw.get("estimate", {})),
        interval_sec=app.get("interval_sec", 2.0),
        save_every_sec=app.get("save_every_sec", 30.0),
        lhm_url=app.get("lhm_url", "http://localhost:8085/data.json"),
        data_file=data_file,
        rates=rates,
        meter_chosen=bool(t.get("type") or chosen),
        tariff_overrides=t,
    )


def build_tariff(kind: str, rates: dict, day: date, overrides: dict | None = None) -> Tariff:
    o = overrides or {}
    ft = o.get("ft", rates_mod.ft_on(rates, day))
    vat = o.get("vat", rates["vat"])
    if kind == "flat":
        return FlatTariff(rate=o.get("flat_rate", rates["flat_rate"]), ft=ft, vat=vat)
    tou = rates["tou"]
    start, end = o.get("peak_hours", tou["peak_hours"])
    return TouTariff(
        peak_rate=o.get("peak_rate", tou["peak"]),
        off_peak_rate=o.get("off_peak_rate", tou["off_peak"]),
        ft=ft,
        vat=vat,
        peak_start_hour=start,
        peak_end_hour=end,
        holidays=thai_holidays(),
    )
