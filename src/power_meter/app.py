"""Monitoring loop and usage report."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from .config import Config
from .estimate import wall_watts
from .sensors import BatterySensor, LhmCpuSensor, NvidiaSensor
from .storage import UsageLog
from .tariff import OFF_PEAK, PEAK, TouTariff

PERIOD_LABEL = {PEAK: "Peak    ", OFF_PEAK: "Off-peak", "flat": ""}


def run(cfg: Config) -> None:
    battery = BatterySensor()
    gpu = NvidiaSensor()
    cpu = LhmCpuSensor(cfg.lhm_url)
    log = UsageLog(cfg.data_file)

    _print_status(cfg, battery, gpu, cpu)

    session_wh = session_baht = 0.0
    last = last_save = time.monotonic()
    try:
        while True:
            time.sleep(cfg.interval_sec)
            now_mono = time.monotonic()
            hours = (now_mono - last) / 3600
            last = now_mono

            watts, measured = wall_watts(
                battery.read(), cpu.read_watts(), gpu.read_watts(), cfg.estimate
            )
            now = datetime.now()
            period = cfg.tariff.period(now)
            price = cfg.tariff.price_per_kwh(period)
            wh = watts * hours
            baht = wh / 1000 * price

            log.add(now.date(), period, wh, baht)
            session_wh += wh
            session_baht += baht

            today = log.day_total(now.date())
            source = "แบต   " if measured else "ประมาณ"
            print(
                f"\r{now:%H:%M:%S} {PERIOD_LABEL[period]} {source} "
                f"{watts:6.1f} W  {watts / 1000 * price:5.2f} ฿/ชม. | "
                f"รอบนี้ {session_baht:6.3f} ฿ | "
                f"วันนี้ {today.wh / 1000:.3f} kWh {today.baht:6.2f} ฿ | "
                f"รวม {log.total_baht:7.2f} ฿   ",
                end="",
                flush=True,
            )

            if now_mono - last_save >= cfg.save_every_sec:
                log.save()
                last_save = now_mono
    except KeyboardInterrupt:
        pass
    finally:
        log.save()
        print(f"\n\nบันทึกแล้ว: รอบนี้ใช้ {session_wh / 1000:.3f} kWh = {session_baht:.2f} บาท")


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


def _print_status(cfg: Config, battery, gpu, cpu) -> None:
    def mark(ok: bool) -> str:
        return "ok" if ok else "ไม่พบ"

    print(
        f"แบต: {mark(battery.available)} | GPU: {mark(gpu.available)} | "
        f"CPU (LibreHardwareMonitor): {mark(cpu.read_watts() is not None)}"
    )
    t = cfg.tariff
    if isinstance(t, TouTariff):
        print(
            f"Peak {t.price_per_kwh(PEAK):.2f} ฿/หน่วย | "
            f"Off-peak {t.price_per_kwh(OFF_PEAK):.2f} ฿/หน่วย"
        )
        if not t.holidays:
            print("ไม่ได้ติดตั้ง holidays: วันหยุดราชการจะถูกคิดเป็น peak")
    else:
        print(f"ค่าไฟ {t.price_per_kwh('flat'):.2f} ฿/หน่วย")
    print(f"ข้อมูลเก็บที่ {cfg.data_file}\nกด Ctrl+C เพื่อหยุด\n")
