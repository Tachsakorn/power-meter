"""Sampling loop shared by the console and the desktop app."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from .config import Config
from .estimate import wall_watts
from .sensors import BatterySensor, LhmCpuSensor, NvidiaSensor
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
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.battery = BatterySensor()
        self.gpu = NvidiaSensor()
        self.cpu = LhmCpuSensor(cfg.lhm_url)
        self.log = UsageLog(cfg.data_file)
        self.session = Usage()
        self.latest: Sample | None = None
        self.cpu_available = False
        self.history: deque[tuple[float, float]] = deque(
            maxlen=int(HISTORY_SEC / cfg.interval_sec) + 1
        )
        # The desktop app reads state from the UI thread while we write it here.
        self.lock = threading.Lock()
        self._last = time.monotonic()

    def step(self) -> Sample:
        now_mono = time.monotonic()
        hours = (now_mono - self._last) / 3600
        self._last = now_mono

        cpu_w = self.cpu.read_watts()
        self.cpu_available = cpu_w is not None
        watts, measured = wall_watts(
            self.battery.read(), cpu_w, self.gpu.read_watts(), self.cfg.estimate
        )
        now = datetime.now()
        period = self.cfg.tariff.period(now)
        sample = Sample(now, watts, measured, period, self.cfg.tariff.price_per_kwh(period))

        wh = watts * hours
        baht = wh / 1000 * sample.price
        with self.lock:
            self.log.add(now.date(), period, wh, baht)
            self.session.add(wh, baht)
            self.latest = sample
            self.history.append((now.timestamp(), watts))
        return sample

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
