"""Console output: a live status line and a daily report."""

from __future__ import annotations

import contextlib
import dataclasses
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path

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


def check(cfg: Config, samples: int = 5) -> None:
    """Print what the app can see on this machine, then take a few readings.

    Readings go to a throwaway log so the check never adds to real usage.
    """
    with tempfile.TemporaryDirectory() as tmp:
        cfg = dataclasses.replace(cfg, data_file=Path(tmp) / "usage.json")
        monitor = Monitor(cfg)
        hw = monitor.hw
        drives = ", ".join(hw.drives) or "ไม่ทราบ"
        print(f"เครื่อง:      {'โน้ตบุ๊ก' if hw.laptop else 'คอมตั้งโต๊ะ'}")
        print(f"CPU:         {hw.cpu} (ใช้ {monitor.cpu_tdp:.0f} W เป็นค่าเต็มกำลัง)")
        print(f"การ์ดจอที่เจอ: {', '.join(hw.gpus) or 'ไม่พบ'}")
        print(f"การ์ดจอที่คิด: {monitor.gpu_name or 'ไม่มี (ใช้กราฟิกในตัว CPU)'}")
        if monitor.gpu is not None:
            name = type(monitor.gpu).__name__
            print(f"  {name}: {'วัดจริงได้' if monitor.gpu.available else monitor.gpu.error}")
            if hasattr(monitor.gpu, "read_sensors") and monitor.gpu.available:
                print(f"  ADL sensors: {monitor.gpu.read_sensors()}")
        if monitor.gpu_load is not None:
            print(
                f"  GPU load:  {'ใช้ได้' if monitor.gpu_load.available else monitor.gpu_load.error}"
            )
        if monitor.battery is not None:
            print(f"แบต:         {'ใช้ได้' if monitor.battery.available else monitor.battery.error}")
        print(
            f"CPU load:    {'ใช้ได้' if monitor.cpu_load.error is None else monitor.cpu_load.error}"
        )
        print(f"RAM:         {hw.ram_modules} แถว | ไดรฟ์: {drives}")
        print(f"ส่วนอื่น:      {monitor.base_watts:.0f} W")
        meter = cfg.meter if cfg.meter_chosen else f"{cfg.meter} (ยังไม่ได้เลือกในแอป)"
        print(f"มิเตอร์:      {meter} | Ft {cfg.tariff.ft} | อัตราอัปเดต {cfg.rates['updated']}")
        print()

        for _ in range(samples):
            time.sleep(1)
            s = monitor.step()
            cpu = f"{monitor.cpu_util:.0%}" if monitor.cpu_util is not None else "-"
            gpu = f"{monitor.gpu_util:.0%}" if monitor.gpu_util is not None else "-"
            print(
                f"{s.watts:6.1f} W  {s.baht_per_hour:.2f} ฿/ชม. | "
                f"CPU {cpu} ({monitor.cpu_source}) | GPU {gpu} ({monitor.gpu_source})"
            )
        monitor.save()


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
    hw = monitor.hw
    print(f"{'โน้ตบุ๊ก' if hw.laptop else 'คอมตั้งโต๊ะ'} | CPU: {hw.cpu} (~{monitor.cpu_tdp:.0f} W)")
    if monitor.gpu_name:
        measured = monitor.gpu is not None and monitor.gpu.available
        how = "วัดจริง" if measured else f"ประมาณจาก % ใช้งาน (~{monitor.gpu_board:.0f} W)"
        print(f"การ์ดจอ: {monitor.gpu_name} {how}")
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
