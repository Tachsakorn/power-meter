"""Console output: a live status line and a daily report."""

from __future__ import annotations

import contextlib
import threading
from datetime import date, timedelta

from .config import Config
from .monitor import Monitor, Sample
from .storage import UsageLog
from .tariff import OFF_PEAK, PEAK, TouTariff

PERIOD_LABEL = {PEAK: "Peak    ", OFF_PEAK: "Off-peak", "flat": ""}


def run(cfg: Config) -> None:
    monitor = Monitor(cfg)
    _print_status(monitor)

    def show(s: Sample) -> None:
        today = monitor.log.day_total(s.time.date())
        source = "แบต   " if s.measured else "ประมาณ"
        print(
            f"\r{s.time:%H:%M:%S} {PERIOD_LABEL[s.period]} {source} "
            f"{s.watts:6.1f} W  {s.baht_per_hour:5.2f} ฿/ชม. | "
            f"รอบนี้ {monitor.session.baht:6.3f} ฿ | "
            f"วันนี้ {today.wh / 1000:.3f} kWh {today.baht:6.2f} ฿ | "
            f"รวม {monitor.log.total_baht:7.2f} ฿   ",
            end="",
            flush=True,
        )

    with contextlib.suppress(KeyboardInterrupt):
        monitor.run(threading.Event(), on_sample=show)
    s = monitor.session
    print(f"\n\nบันทึกแล้ว: รอบนี้ใช้ {s.wh / 1000:.3f} kWh = {s.baht:.2f} บาท")


def report(cfg: Config, days: int) -> None:
    log = UsageLog(cfg.data_file)
    today = date.today()
    print(f"{'วันที่':<12}{'kWh':>8}{'Peak':>8}{'Off-peak':>10}{'บาท':>10}")

    total_wh = total_baht = 0.0
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        periods = log.days.get(day.isoformat(), {})
        usage = log.day_total(day)
        peak_kwh = periods[PEAK].wh / 1000 if PEAK in periods else 0.0
        off_kwh = periods[OFF_PEAK].wh / 1000 if OFF_PEAK in periods else 0.0
        print(
            f"{day.isoformat():<12}{usage.wh / 1000:>8.3f}"
            f"{peak_kwh:>8.3f}{off_kwh:>10.3f}{usage.baht:>10.2f}"
        )
        total_wh += usage.wh
        total_baht += usage.baht

    print(f"{'รวม':<12}{total_wh / 1000:>8.3f}{'':>18}{total_baht:>10.2f}")


def _print_status(monitor: Monitor) -> None:
    def mark(ok: bool) -> str:
        return "ok" if ok else "ไม่พบ"

    print(
        f"แบต: {mark(monitor.battery.available)} | GPU: {mark(monitor.gpu.available)} | "
        f"CPU (LibreHardwareMonitor): {mark(monitor.cpu.read_watts() is not None)}"
    )
    t = monitor.cfg.tariff
    if isinstance(t, TouTariff):
        print(
            f"Peak {t.price_per_kwh(PEAK):.2f} ฿/หน่วย | "
            f"Off-peak {t.price_per_kwh(OFF_PEAK):.2f} ฿/หน่วย"
        )
        if not t.holidays:
            print("ไม่ได้ติดตั้ง holidays: วันหยุดราชการจะถูกคิดเป็น peak")
    else:
        print(f"ค่าไฟ {t.price_per_kwh('flat'):.2f} ฿/หน่วย")
    print(f"ข้อมูลเก็บที่ {monitor.cfg.data_file}\nกด Ctrl+C เพื่อหยุด\n")
