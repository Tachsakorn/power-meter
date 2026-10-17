"""Turn individual sensor readings into whole-system wall power."""

from __future__ import annotations

from dataclasses import dataclass

from .sensors import BatteryReading


@dataclass(frozen=True)
class EstimateConfig:
    base_watts: float = 15.0  # display, RAM, SSD, fans, board: no sensor for these
    cpu_fallback_watts: float = 12.0  # used when LibreHardwareMonitor isn't running
    adapter_efficiency: float = 0.88


def wall_watts(
    battery: BatteryReading | None,
    cpu_w: float | None,
    gpu_w: float,
    cfg: EstimateConfig,
) -> tuple[float, bool]:
    """Return (watts drawn, measured).

    On battery the fuel gauge sees the whole machine, so that number is
    used as-is. On AC we add up the parts and account for adapter losses.
    """
    if battery is not None and not battery.on_ac and battery.discharge_w > 0:
        return battery.discharge_w, True

    cpu = cpu_w if cpu_w is not None else cfg.cpu_fallback_watts
    charging = battery.charge_w if battery is not None else 0.0
    dc_watts = cpu + gpu_w + cfg.base_watts + charging
    return dc_watts / cfg.adapter_efficiency, False
