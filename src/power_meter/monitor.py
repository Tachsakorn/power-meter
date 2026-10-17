"""Sampling loop shared by the console and the desktop app."""

from __future__ import annotations

import dataclasses
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from . import hardware
from . import rates as rates_mod
from . import settings as settings_mod
from .config import Config, build_tariff
from .estimate import (
    cpu_watts_from_load,
    gpu_watts_from_load,
    wall_watts,
)
from .sensors import (
    AmdGpuSensor,
    BatterySensor,
    CpuLoadSensor,
    GpuLoadSensor,
    LhmCpuSensor,
    NvidiaSensor,
)
from .storage import Usage, UsageLog

HISTORY_SEC = 600


@dataclass(frozen=True)
class Sample:
    time: datetime
    watts: float
    measured: bool
    period: str
    price: float  # baht per kWh

    @property
    def baht_per_hour(self) -> float:
        return self.watts / 1000 * self.price


class Monitor:
    def __init__(self, cfg: Config, hw: hardware.Hardware | None = None) -> None:
        self.cfg = cfg
        self.hw = hw or hardware.detect()
        est = cfg.estimate

        self.battery = BatterySensor() if self.hw.laptop else None
        self.base_watts = est.base_watts or hardware.base_watts(self.hw)

        self.cpu = LhmCpuSensor(cfg.lhm_url)
        self.cpu_load = CpuLoadSensor()
        self.cpu_tdp = est.cpu_tdp_watts or hardware.guess_cpu_tdp(self.hw.cpu)

        # Real GPU power where NVML can give it; otherwise scale the card's
        # typical board power by how busy Windows says it is.
        self.gpu_name = next((g for g in self.hw.gpus if hardware.guess_gpu_watts(g)), None)
        self.gpu = _gpu_power_sensor(self.gpu_name)
        self.gpu_board = est.gpu_board_watts or (
            hardware.guess_gpu_watts(self.gpu_name) if self.gpu_name else 0.0
        )
        needs_load = self.gpu_board and not (self.gpu and self.gpu.available)
        self.gpu_load = GpuLoadSensor() if needs_load else None

        self.log = UsageLog(cfg.data_file)
        self.session = Usage()
        self.latest: Sample | None = None
        self.cpu_source = "none"
        self.gpu_source = "none"
        self.cpu_util: float | None = None
        self.gpu_util: float | None = None
        self.history: deque[tuple[float, float]] = deque(
            maxlen=int(HISTORY_SEC / cfg.interval_sec) + 1
        )
        # The desktop app reads state from the UI thread while we write it here.
        self.lock = threading.Lock()
        self._last = time.monotonic()
        self._tariff_day = date.today()

    # Tariff upkeep: the meter type is picked in the app, Ft follows the date
    # and the rates file can be updated over the network while we run.

    def set_meter(self, kind: str) -> None:
        if kind not in settings_mod.METER_TYPES:
            raise ValueError(f"unknown meter type {kind!r}")
        stored = settings_mod.load(self.cfg.settings_file)
        settings_mod.save(self.cfg.settings_file, {**stored, "meter": kind})
        self._rebuild_tariff(kind=kind, chosen=True)

    def reload_rates(self) -> None:
        self._rebuild_tariff(rates=rates_mod.load(self.cfg.rates_file))

    def _rebuild_tariff(self, kind=None, rates=None, chosen=None, day=None) -> None:
        cfg = self.cfg
        rates = rates or cfg.rates
        tariff = build_tariff(
            kind or cfg.meter, rates, day or date.today(), overrides=cfg.tariff_overrides
        )
        self.cfg = dataclasses.replace(
            cfg,
            tariff=tariff,
            rates=rates,
            meter_chosen=cfg.meter_chosen if chosen is None else chosen,
        )

    def step(self) -> Sample:
        now_mono = time.monotonic()
        hours = (now_mono - self._last) / 3600
        self._last = now_mono

        watts, measured = wall_watts(
            self.battery.read() if self.battery else None,
            self._cpu_watts(),
            self._gpu_watts(),
            self.base_watts,
            self.cfg.estimate.adapter_efficiency,
        )
        now = datetime.now()
        if now.date() != self._tariff_day:
            self._tariff_day = now.date()
            self._rebuild_tariff(day=now.date())  # a new Ft period may have started
        tariff = self.cfg.tariff
        period = tariff.period(now)
        sample = Sample(now, watts, measured, period, tariff.price_per_kwh(period))

        wh = watts * hours
        baht = wh / 1000 * sample.price
        with self.lock:
            self.log.add(now.date(), period, wh, baht)
            self.session.add(wh, baht)
            self.latest = sample
            self.history.append((now.timestamp(), watts))
        return sample

    def _cpu_watts(self) -> float:
        self.cpu_util = self.cpu_load.read()
        watts = self.cpu.read_watts()
        if watts is not None:
            self.cpu_source = "measured"
            return watts
        if self.cpu_util is not None:
            self.cpu_source = "load"
            return cpu_watts_from_load(self.cpu_util, self.cpu_tdp)
        self.cpu_source = "fixed"
        return self.cfg.estimate.cpu_fallback_watts

    def _gpu_watts(self) -> float:
        if self.gpu and self.gpu.available:
            self.gpu_source = "measured"
            return self.gpu.read_watts()
        self.gpu_util = self.gpu_load.read() if self.gpu_load else None
        if self.gpu_util is not None:
            self.gpu_source = "load"
            return gpu_watts_from_load(self.gpu_util, self.gpu_board)
        self.gpu_source = "none"
        return 0.0

    def run(self, stop: threading.Event, on_sample: Callable[[Sample], None] | None = None) -> None:
        last_save = time.monotonic()
        self._last = last_save
        try:
            while not stop.wait(self.cfg.interval_sec):
                sample = self.step()
                if on_sample is not None:
                    on_sample(sample)
                if time.monotonic() - last_save >= self.cfg.save_every_sec:
                    self.save()
                    last_save = time.monotonic()
        finally:
            self.save()

    def save(self) -> None:
        with self.lock:
            self.log.save()

    def month_usage(self, day: date) -> tuple[Usage, int]:
        """Usage so far in `day`'s month, and how many days of it have data."""
        prefix = day.isoformat()[:7]
        total = Usage()
        days = 0
        for d, periods in self.log.days.items():
            if d.startswith(prefix):
                days += 1
                for u in periods.values():
                    total.add(u.wh, u.baht)
        return total, days


def _gpu_power_sensor(name: str | None) -> NvidiaSensor | AmdGpuSensor | None:
    """A sensor that reports the card's real power draw, if its vendor offers one."""
    if not name:
        return None
    if hardware.is_nvidia(name):
        return NvidiaSensor()
    if hardware.is_amd_gpu(name):
        return AmdGpuSensor()
    return None
