"""Find out what the machine is made of, without admin rights.

The model names come from WMI, which any user can query. Power ratings
aren't exposed anywhere, so they are guessed from the model name; the
guesses only set the scale for load-based estimates and can be overridden
in config.toml.
"""

from __future__ import annotations

import contextlib
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
    ram_modules: int = 0
    drives: tuple[str, ...] = ()  # "nvme", "ssd", "hdd" or "unknown"


def detect() -> Hardware:
    if sys.platform != "win32":
        return Hardware(cpu=platform.processor() or "unknown CPU", gpus=(), laptop=False)

    cpu = platform.processor() or "unknown CPU"
    gpus: tuple[str, ...] = ()
    ram_modules = 0
    drives: tuple[str, ...] = ()
    # Each query is optional: a broken WMI class shouldn't hide the others.
    try:
        import pythoncom
        import wmi

        pythoncom.CoInitialize()
        conn = wmi.WMI()
    except Exception:
        return Hardware(cpu=cpu, gpus=gpus, laptop=_has_battery())
    with contextlib.suppress(Exception):
        cpu = conn.Win32_Processor()[0].Name.strip()
    with contextlib.suppress(Exception):
        gpus = tuple(
            name.strip()
            for name in (v.Name or "" for v in conn.Win32_VideoController())
            if name and not any(word in name.lower() for word in _IGNORED_ADAPTERS)
        )
    with contextlib.suppress(Exception):
        ram_modules = len(conn.Win32_PhysicalMemory())
    with contextlib.suppress(Exception):
        storage = wmi.WMI(namespace="root\\Microsoft\\Windows\\Storage")
        drives = tuple(_drive_kind(d.BusType, d.MediaType) for d in storage.MSFT_PhysicalDisk())
    return Hardware(
        cpu=cpu, gpus=gpus, laptop=_has_battery(), ram_modules=ram_modules, drives=drives
    )


def _drive_kind(bus_type: int, media_type: int) -> str:
    # MSFT_PhysicalDisk: BusType 17 = NVMe; MediaType 3 = HDD, 4 = SSD.
    if bus_type == 17:
        return "nvme"
    return {3: "hdd", 4: "ssd"}.get(media_type, "unknown")


_DRIVE_WATTS = {"nvme": 4.0, "ssd": 3.0, "hdd": 7.0, "unknown": 4.0}


def base_watts(hw: Hardware) -> float:
    """Everything other than CPU and GPU, built up from the parts we can see."""
    if hw.laptop:
        # Built-in screen, board, RAM and storage are all low-power parts.
        return 9.0 + 1.5 * hw.ram_modules + 2.0 * len(hw.drives)
    ram = hw.ram_modules or 2
    drives = hw.drives or ("unknown",)
    # Motherboard, chipset, USB, case fans and the AIO pump if there is one.
    return 22.0 + 3.0 * ram + sum(_DRIVE_WATTS[d] for d in drives)


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


# Rated board power of common cards. Longer names first so "4070 ti super"
# wins over "4070 ti" and "4070".
_GPU_WATTS = {
    "rtx 5090": 575, "rtx 5080": 360, "rtx 5070 ti": 300, "rtx 5070": 250,
    "rtx 5060 ti": 180, "rtx 5060": 145, "rtx 4090": 450, "rtx 4080 super": 320,
    "rtx 4080": 320, "rtx 4070 ti super": 285, "rtx 4070 ti": 285, "rtx 4070 super": 220,
    "rtx 4070": 200, "rtx 4060 ti": 160, "rtx 4060": 115, "rtx 3090 ti": 450,
    "rtx 3090": 350, "rtx 3080 ti": 350, "rtx 3080": 320, "rtx 3070 ti": 290,
    "rtx 3070": 220, "rtx 3060 ti": 200, "rtx 3060": 170, "rtx 3050": 130,
    "rtx 2080 ti": 250, "rtx 2080": 215, "rtx 2070": 175, "rtx 2060": 160,
    "gtx 1660 super": 125, "gtx 1660 ti": 120, "gtx 1660": 120, "gtx 1650": 75,
    "gtx 1080 ti": 250, "gtx 1080": 180, "gtx 1070": 150, "gtx 1060": 120,
    "rx 9070 xt": 304, "rx 9070": 220, "rx 9060 xt": 160, "rx 7900 xtx": 355,
    "rx 7900 xt": 315, "rx 7900 gre": 260, "rx 7800 xt": 263, "rx 7700 xt": 245,
    "rx 7600 xt": 190, "rx 7600": 165, "rx 6950 xt": 335, "rx 6900 xt": 300,
    "rx 6800 xt": 300, "rx 6800": 250, "rx 6750 xt": 250, "rx 6700 xt": 230,
    "rx 6700": 175, "rx 6650 xt": 180, "rx 6600 xt": 160, "rx 6600": 132,
    "rx 6500 xt": 107, "rx 6400": 53, "rx 5700 xt": 225, "rx 5700": 180,
    "rx 5600 xt": 150, "rx 5500 xt": 130, "rx 580": 185, "rx 570": 150,
    "arc b580": 190, "arc b570": 150, "arc a770": 225, "arc a750": 225,
    "arc a580": 185, "arc a380": 75,
}  # fmt: skip


def guess_gpu_watts(name: str) -> float:
    """Typical board power of a discrete card; 0 for graphics built into the CPU."""
    n = _clean(name)
    # Laptop chips run at a fraction of the desktop card with the same name.
    scale = 0.5 if "laptop" in n or "mobile" in n else 1.0
    for model, watts in sorted(_GPU_WATTS.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"{model}\b", n):
            return watts * scale

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


def is_amd_gpu(name: str) -> bool:
    n = name.lower()
    return "radeon" in n or "amd" in n


def is_nvidia(name: str) -> bool:
    n = name.lower()
    return any(word in n for word in ("nvidia", "geforce", "rtx", "gtx", "quadro"))
