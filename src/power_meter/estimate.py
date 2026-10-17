"""Turn individual sensor readings into whole-system wall power."""

from __future__ import annotations

from dataclasses import dataclass

from .sensors import BatteryReading


@dataclass(frozen=True)
class EstimateConfig:
    # Leave these unset to have them worked out from the detected hardware.
    base_watts: float | None = None
    cpu_tdp_watts: float | None = None
    gpu_board_watts: float | None = None
    cpu_fallback_watts: float = 12.0  # only if CPU load can't be read at all
    adapter_efficiency: float = 0.88  # laptop adapter or desktop PSU


def cpu_watts_from_load(load: float, tdp: float) -> float:
    """Package power from utilisation.

    Desktop and laptop CPUs idle at roughly a sixth of their TDP and can
    boost a little past it under full load.
    """
    load = min(1.0, max(0.0, load))
    return tdp * (0.15 + 1.05 * load)


def gpu_watts_from_load(load: float, board_watts: float) -> float:
    load = min(1.0, max(0.0, load))
    return board_watts * (0.08 + 0.92 * load)


def wall_watts(
    battery: BatteryReading | None,
    cpu_w: float,
    gpu_w: float,
    base_watts: float,
    efficiency: float,
) -> tuple[float, bool]:
    """Return (watts drawn, measured).

    On battery the fuel gauge sees the whole machine, so that number is
    used as-is. Otherwise we add up the parts and account for conversion
    losses in the adapter or power supply.
    """
    if battery is not None and not battery.on_ac and battery.discharge_w > 0:
        return battery.discharge_w, True

    charging = battery.charge_w if battery is not None else 0.0
    return (cpu_w + gpu_w + base_watts + charging) / efficiency, False
