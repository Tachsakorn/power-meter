"""Desktop window: a web UI in a native window via pywebview."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config
from .monitor import Monitor
from .tariff import OFF_PEAK, PEAK, TouTariff

WEB_DIR = Path(__file__).parent / "web"
HISTORY_DAYS = 7


class Api:
    """Methods here are callable from JavaScript as window.pywebview.api.*"""

    def __init__(self, monitor: Monitor) -> None:
        self._monitor = monitor

    def get_state(self) -> dict:
        return build_state(self._monitor, datetime.now())


def build_state(monitor: Monitor, now: datetime) -> dict:
    tariff = monitor.cfg.tariff
    is_tou = isinstance(tariff, TouTariff)
    period = tariff.period(now)
    next_change = tariff.next_change(now)

    with monitor.lock:
        latest = monitor.latest
        today = monitor.log.day_total(now.date())
        days = []
        for offset in range(HISTORY_DAYS - 1, -1, -1):
            day = now.date() - timedelta(days=offset)
            periods = monitor.log.days.get(day.isoformat(), {})
            days.append(
                {
                    "date": day.isoformat(),
                    "peak_kwh": periods[PEAK].wh / 1000 if PEAK in periods else 0.0,
                    "off_kwh": sum(u.wh for p, u in periods.items() if p != PEAK) / 1000,
                    "baht": sum(u.baht for u in periods.values()),
                }
            )
        state = {
            "now": now.timestamp() * 1000,
            "is_tou": is_tou,
            "period": period,
            "price": tariff.price_per_kwh(period),
            "watts": latest.watts if latest else None,
            "measured": latest.measured if latest else False,
            "baht_per_hour": latest.baht_per_hour if latest else None,
            "session_baht": monitor.session.baht,
            "today_baht": today.baht,
            "today_kwh": today.wh / 1000,
            "month_baht": monitor.month_baht(now.date()),
            "history": [[t * 1000, w] for t, w in monitor.history],
            "days": days,
        }

    if next_change is not None:
        state["next_change"] = next_change.timestamp() * 1000
        state["next_price"] = tariff.price_per_kwh(tariff.period(next_change))
    if is_tou:
        state["peak_price"] = tariff.price_per_kwh(PEAK)
        state["off_peak_price"] = tariff.price_per_kwh(OFF_PEAK)
        state["peak_hours"] = [tariff.peak_start_hour, tariff.peak_end_hour]
        noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
        state["off_peak_all_day"] = tariff.period(noon) == OFF_PEAK
    state["sensors"] = {
        "battery": monitor.battery.available,
        "gpu": monitor.gpu.available,
        "cpu": monitor.cpu_available,
    }
    return state


def run(cfg: Config) -> None:
    import webview

    monitor = Monitor(cfg)
    stop = threading.Event()
    worker = threading.Thread(target=monitor.run, args=(stop,), daemon=True)

    window = webview.create_window(
        "Power Meter",
        url=str(WEB_DIR / "index.html"),
        js_api=Api(monitor),
        width=960,
        height=720,
        min_size=(380, 560),
        background_color="#1c2046",
    )
    window.events.closed += stop.set

    worker.start()
    # Serve the web folder over localhost; file:// pages can't always load fonts.
    webview.start(http_server=True)
    stop.set()
    worker.join(timeout=5)
