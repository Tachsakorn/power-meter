"""Desktop window: a web UI in a native window via pywebview."""

from __future__ import annotations

import calendar
import threading
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config
from .monitor import Monitor
from .storage import Usage
from .tariff import OFF_PEAK, PEAK, TouTariff

WEB_DIR = Path(__file__).parent / "web"
HISTORY_DAYS = 7
FULL_SIZE = (960, 760)
COMPACT_SIZE = (340, 190)


class Api:
    """Methods here are callable from JavaScript as window.pywebview.api.*"""

    def __init__(self, monitor: Monitor) -> None:
        self._monitor = monitor
        self._window = None

    def attach(self, window) -> None:
        self._window = window

    def get_state(self) -> dict:
        return build_state(self._monitor, datetime.now())

    def set_compact(self, compact: bool) -> None:
        """Shrink to a small always-on-top widget, or back to the full window."""
        if self._window is None:
            return
        width, height = COMPACT_SIZE if compact else FULL_SIZE
        self._window.on_top = compact
        self._window.resize(width, height)


def build_state(monitor: Monitor, now: datetime) -> dict:
    tariff = monitor.cfg.tariff
    is_tou = isinstance(tariff, TouTariff)
    period = tariff.period(now)
    next_change = tariff.next_change(now)

    with monitor.lock:
        latest = monitor.latest
        today = monitor.log.day_total(now.date())
        month, month_days = monitor.month_usage(now.date())
        days = []
        for offset in range(HISTORY_DAYS - 1, -1, -1):
            day = now.date() - timedelta(days=offset)
            peak, off = Usage(), Usage()
            for p, u in monitor.log.days.get(day.isoformat(), {}).items():
                (peak if p == PEAK else off).add(u.wh, u.baht)
            days.append(
                {
                    "date": day.isoformat(),
                    "peak_kwh": peak.wh / 1000,
                    "off_kwh": off.wh / 1000,
                    "peak_baht": peak.baht,
                    "off_baht": off.baht,
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
            "today_baht": today.baht,
            "today_kwh": today.wh / 1000,
            "month_baht": month.baht,
            "month_kwh": month.wh / 1000,
            "month_days": month_days,
            # Average day so far, scaled to the whole month.
            "month_projection": (
                month.baht / month_days * calendar.monthrange(now.year, now.month)[1]
                if month_days
                else 0.0
            ),
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
        state["holiday"] = now.date() in tariff.holidays
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

    api = Api(monitor)
    window = webview.create_window(
        "มิเตอร์ไฟคอม",
        url=str(WEB_DIR / "index.html"),
        js_api=api,
        width=FULL_SIZE[0],
        height=FULL_SIZE[1],
        min_size=(300, 170),
        background_color="#1c2046",
    )
    api.attach(window)
    window.events.closed += stop.set

    worker.start()
    # Serve the web folder over localhost; file:// pages can't always load fonts.
    webview.start(http_server=True)
    stop.set()
    worker.join(timeout=5)
