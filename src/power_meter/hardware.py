"""Find out what the machine is made of, without admin rights.

The model names come from WMI, which any user can query. Power ratings
aren't exposed anywhere, so they are guessed from the model name; the
guesses only set the scale for load-based estimates and can be overridden
in config.toml.
"""

from __future__ import annotations

import platform
import re
import sys
from dataclasses import dataclass

DEFAULT_CPU_TDP = 65.0
DEFAULT_DISCRETE_GPU = 150.0

_IGNORED_ADAPTERS = ("basic display", "basic render", "remote", "virtual", "parsec", "meta")


@dataclass(frozen=True)
class Hardware:
    cpu: str
    gpus: tuple[str, ...]
    laptop: bool


def detect() -> Hardware:
    if sys.platform != "win32":
        return Hardware(cpu=platform.processor() or "unknown CPU", gpus=(), laptop=False)

    cpu = platform.processor() or "unknown CPU"
    gpus: tuple[str, ...] = ()
    try:
        import pythoncom
        import wmi

        pythoncom.CoInitialize()
        conn = wmi.WMI()
        cpu = conn.Win32_Processor()[0].Name.strip()
        gpus = tuple(
            name.strip()
            for name in (v.Name or "" for v in conn.Win32_VideoController())
            if name and not any(word in name.lower() for word in _IGNORED_ADAPTERS)
        )
    except Exception:  # WMI can be broken or slow on some installs; names are a nicety
        pass
    return Hardware(cpu=cpu, gpus=gpus, laptop=_has_battery())


def _has_battery() -> bool:
    import ctypes

    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = SystemPowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return False
    no_battery, unknown = 128, 255
    return status.BatteryFlag not in (no_battery, unknown)


def _clean(name: str) -> str:
    name = re.sub(r"\((r|tm)\)", "", name.lower())
    return re.sub(r"\s+", " ", name).strip()


def guess_cpu_tdp(name: str) -> float:
    n = _clean(name)

    if "ryzen" in n:
        if re.search(r"\d{3,4}hx\b|ryzen ai .*hx", n):
            return 55.0
        if re.search(r"\d{4}h[s]?\b", n):
            return 45.0
        if re.search(r"\d{4}u\b|ryzen ai", n):
            return 28.0
        if re.search(r"\d{4}x3d\b", n):
            return 120.0
        if re.search(r"ryzen 9 \d{4}x\b", n):
            return 170.0
        if re.search(r"\d{4}xt?\b", n):
            return 105.0
        return 65.0

    if "intel" in n or "core" in n:
        if re.search(r"\d{3,5}k[fs]?\b", n):
            return 125.0
        if re.search(r"\d{3,5}hx\b", n):
            return 55.0
        if re.search(r"\d{3,5}h[k]?\b", n):
            return 45.0
        if re.search(r"\d{3,5}p\b", n):
            return 28.0
        if re.search(r"\d{3,5}[uv]\b", n):
            return 15.0
        if re.search(r"\d{3,5}t\b", n):
            return 35.0
        return 65.0

    return DEFAULT_CPU_TDP


def guess_gpu_watts(name: str) -> float:
    """Typical board power of a discrete card; 0 for graphics built into the CPU."""
    n = _clean(name)

    if m := re.search(r"rtx (\d)0(\d)0", n):
        tier = int(m.group(2))
        return {9: 420.0, 8: 320.0, 7: 220.0, 6: 140.0, 5: 100.0}.get(tier, 180.0)
    if "gtx" in n or "quadro" in n or "nvidia" in n:
        return 120.0

    if m := re.search(r"rx (\d)(\d)\d\d", n):
        tier = int(m.group(2))
        return {9: 320.0, 8: 250.0, 7: 200.0, 6: 140.0, 5: 100.0}.get(tier, 150.0)
    if "radeon" in n:
        return 0.0  # "Radeon Graphics" / "Radeon 780M" are integrated

    if re.search(r"arc a7|arc b5", n):
        return 200.0
    if re.search(r"arc a[35]", n):
        return 120.0
    if any(word in n for word in ("uhd", "iris", "intel graphics", "arc graphics")):
        return 0.0

    return DEFAULT_DISCRETE_GPU


def is_nvidia(name: str) -> bool:
    n = name.lower()
    return any(word in n for word in ("nvidia", "geforce", "rtx", "gtx", "quadro"))
