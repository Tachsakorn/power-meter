"""Hardware power sensors on Windows.

Each sensor degrades to "unavailable" instead of failing, because most
machines have only some of them (desktops have no battery, not every
laptop has an NVIDIA GPU, LibreHardwareMonitor may not be running).
"""

from __future__ import annotations

import contextlib
import ctypes
import functools
import json
import os
import sys
import urllib.error
import urllib.request
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatteryReading:
    on_ac: bool
    discharge_w: float
    charge_w: float


class BatterySensor:
    """Reads the battery's charge/discharge rate straight from the driver.

    Uses IOCTL_BATTERY_QUERY_STATUS, the same call powercfg uses. Unlike the
    WMI BatteryStatus class, it exists on every laptop and needs no admin.
    """

    def __init__(self) -> None:
        self.error: str | None = None
        self._path: str | None = None
        if sys.platform != "win32":
            self.error = "Windows only"
            return
        try:
            self._path = _battery_device_path()
            self._query()
        # Probing talks to drivers through ctypes, which can fail in ways that
        # aren't OSError (e.g. ctypes.ArgumentError). A failed probe must only
        # mark the sensor unavailable, never stop the app from starting.
        except Exception as exc:
            self.error = describe(exc)

    @property
    def available(self) -> bool:
        return self.error is None

    def read(self) -> BatteryReading | None:
        if self.error is not None:
            return None
        try:
            state, rate_mw = self._query()
        except Exception:  # the handle can go stale after sleep/resume
            return None
        if rate_mw == _UNKNOWN_RATE:
            rate_mw = 0
        return BatteryReading(
            on_ac=bool(state & _POWER_ON_LINE),
            discharge_w=-rate_mw / 1000 if state & _DISCHARGING else 0.0,
            charge_w=rate_mw / 1000 if state & _CHARGING else 0.0,
        )

    def _query(self) -> tuple[int, int]:
        k32 = _kernel32()
        handle = k32.CreateFileW(self._path, 0xC0000000, 3, None, 3, 0, None)
        if handle in (None, _INVALID_HANDLE):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            tag = wintypes.ULONG()
            timeout = wintypes.ULONG(0)
            returned = wintypes.DWORD()
            if (
                not k32.DeviceIoControl(
                    handle,
                    _IOCTL_QUERY_TAG,
                    ctypes.byref(timeout),
                    4,
                    ctypes.byref(tag),
                    4,
                    ctypes.byref(returned),
                    None,
                )
                or not tag.value
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            wait = _BatteryWaitStatus(BatteryTag=tag.value)
            status = _BatteryStatus()
            if not k32.DeviceIoControl(
                handle,
                _IOCTL_QUERY_STATUS,
                ctypes.byref(wait),
                ctypes.sizeof(wait),
                ctypes.byref(status),
                ctypes.sizeof(status),
                ctypes.byref(returned),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            return status.PowerState, status.Rate
        finally:
            k32.CloseHandle(handle)


_IOCTL_QUERY_TAG = 0x294040
_INVALID_HANDLE = wintypes.HANDLE(-1).value
_IOCTL_QUERY_STATUS = 0x29404C
_POWER_ON_LINE = 0x1
_DISCHARGING = 0x2
_CHARGING = 0x4
_UNKNOWN_RATE = -0x80000000


class _BatteryWaitStatus(ctypes.Structure):
    _fields_ = [
        ("BatteryTag", ctypes.c_ulong),
        ("Timeout", ctypes.c_ulong),
        ("PowerState", ctypes.c_ulong),
        ("LowCapacity", ctypes.c_ulong),
        ("HighCapacity", ctypes.c_ulong),
    ]


class _BatteryStatus(ctypes.Structure):
    _fields_ = [
        ("PowerState", ctypes.c_ulong),
        ("Capacity", ctypes.c_ulong),
        ("Voltage", ctypes.c_ulong),
        ("Rate", ctypes.c_long),
    ]


class _Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _DeviceInterfaceData(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("InterfaceClassGuid", _Guid),
        ("Flags", ctypes.c_ulong),
        ("Reserved", ctypes.c_size_t),
    ]


@functools.cache
def _kernel32():
    # A private WinDLL so our argtypes can't clash with other users of windll,
    # and so 64-bit handles aren't truncated to int.
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    k32.DeviceIoControl.restype = wintypes.BOOL
    k32.DeviceIoControl.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    return k32


def _battery_device_path() -> str:
    """Device path of the first battery, found through SetupAPI."""
    setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
    setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
    setupapi.SetupDiGetClassDevsW.argtypes = [
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        wintypes.HWND,
        wintypes.DWORD,
    ]
    setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]

    guid = _Guid(
        0x72631E54,
        0x78A4,
        0x11D0,
        (ctypes.c_ubyte * 8)(0xBC, 0xF7, 0x00, 0xAA, 0x00, 0xB7, 0xB3, 0x2A),
    )
    present_interfaces = 0x2 | 0x10  # DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    devs = setupapi.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, present_interfaces)
    if devs in (None, _INVALID_HANDLE):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        iface = _DeviceInterfaceData(cbSize=ctypes.sizeof(_DeviceInterfaceData))
        if not setupapi.SetupDiEnumDeviceInterfaces(
            devs, None, ctypes.byref(guid), 0, ctypes.byref(iface)
        ):
            raise OSError("no battery found")
        needed = wintypes.DWORD()
        setupapi.SetupDiGetDeviceInterfaceDetailW(
            devs, ctypes.byref(iface), None, 0, ctypes.byref(needed), None
        )
        buf = ctypes.create_string_buffer(needed.value)
        # cbSize is the fixed part of SP_DEVICE_INTERFACE_DETAIL_DATA_W:
        # a DWORD and one WCHAR, padded to 8 bytes on 64-bit Windows.
        ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD))[0] = (
            8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
        )
        if not setupapi.SetupDiGetDeviceInterfaceDetailW(
            devs, ctypes.byref(iface), buf, needed, None, None
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return ctypes.wstring_at(ctypes.addressof(buf) + 4)
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(devs)


class NvidiaSensor:
    """Board power of all NVIDIA GPUs via NVML."""

    def __init__(self) -> None:
        self._nvml = None
        self._handles: list = []
        self.error: str | None = None
        try:
            import pynvml
        except ImportError as exc:
            self.error = f"missing {exc.name}"
            return
        try:
            _preload_nvml(pynvml)
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            self._handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(count)]
        except Exception as exc:  # no driver, no NVIDIA GPU, or the DLL search failed
            self.error = describe(exc)
            return
        self._nvml = pynvml

    @property
    def available(self) -> bool:
        return self._nvml is not None

    def read_watts(self) -> float:
        if self._nvml is None:
            return 0.0
        try:
            return sum(self._nvml.nvmlDeviceGetPowerUsage(h) for h in self._handles) / 1000
        except self._nvml.NVMLError:
            # A laptop dGPU that is powered down (Optimus) draws ~0 W.
            return 0.0


def _preload_nvml(pynvml) -> None:
    """Load nvml.dll ourselves when it isn't where pynvml looks.

    pynvml only tries System32 and the old NVSMI folder; some (DCH) drivers
    keep nvml.dll only inside the driver store.
    """
    if sys.platform != "win32" or pynvml.nvmlLib is not None:
        return
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [
        windir / "System32" / "nvml.dll",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "NVIDIA Corporation"
        / "NVSMI"
        / "nvml.dll",
        *(windir / "System32" / "DriverStore" / "FileRepository").glob("nv*/nvml.dll"),
    ]
    for dll in candidates:
        try:
            pynvml.nvmlLib = ctypes.CDLL(str(dll))
            return
        except OSError:
            continue


class CpuLoadSensor:
    """Overall CPU utilisation, 0..1. Needs no special rights."""

    def __init__(self) -> None:
        self.error: str | None = None
        try:
            import psutil
        except ImportError as exc:
            self._psutil = None
            self.error = f"missing {exc.name}"
            return
        self._psutil = psutil
        psutil.cpu_percent(None)  # the first call only sets the baseline

    def read(self) -> float | None:
        if self._psutil is None:
            return None
        return self._psutil.cpu_percent(None) / 100


class GpuLoadSensor:
    """Busiest-engine GPU utilisation, 0..1, from Windows performance counters.

    The same numbers Task Manager shows; available to any user and to any
    GPU vendor, so it covers cards NVML can't read.
    """

    PATH = r"\GPU Engine(*engtype_3D)\Utilization Percentage"

    def __init__(self) -> None:
        self.error: str | None = None
        self._pdh = None
        if sys.platform != "win32":
            self.error = "Windows only"
            return
        try:
            pdh = ctypes.WinDLL("pdh")
            for fn in ("PdhOpenQueryW", "PdhAddEnglishCounterW", "PdhCollectQueryData"):
                getattr(pdh, fn).restype = ctypes.c_uint32
            pdh.PdhGetFormattedCounterArrayW.restype = ctypes.c_uint32
            pdh.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, ctypes.c_void_p]
            pdh.PdhAddEnglishCounterW.argtypes = [
                wintypes.HANDLE,
                wintypes.LPCWSTR,
                ctypes.c_size_t,
                ctypes.c_void_p,
            ]
            pdh.PdhCollectQueryData.argtypes = [wintypes.HANDLE]
            pdh.PdhGetFormattedCounterArrayW.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.POINTER(wintypes.DWORD),
                ctypes.c_void_p,
            ]
            self._query = wintypes.HANDLE()
            self._counter = wintypes.HANDLE()
            _check_pdh(pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._query)))
            _check_pdh(
                pdh.PdhAddEnglishCounterW(self._query, self.PATH, 0, ctypes.byref(self._counter))
            )
            _check_pdh(pdh.PdhCollectQueryData(self._query))
            self._pdh = pdh
        except Exception as exc:
            self.error = describe(exc)

    @property
    def available(self) -> bool:
        return self._pdh is not None

    def read(self) -> float | None:
        if self._pdh is None:
            return None
        try:
            _check_pdh(self._pdh.PdhCollectQueryData(self._query))
            size = wintypes.DWORD(0)
            count = wintypes.DWORD(0)
            fmt_double = 0x200
            status = self._pdh.PdhGetFormattedCounterArrayW(
                self._counter, fmt_double, ctypes.byref(size), ctypes.byref(count), None
            )
            if status != _PDH_MORE_DATA:
                return 0.0  # no 3D engine is active right now
            buf = (ctypes.c_byte * size.value)()
            _check_pdh(
                self._pdh.PdhGetFormattedCounterArrayW(
                    self._counter, fmt_double, ctypes.byref(size), ctypes.byref(count), buf
                )
            )
            items = ctypes.cast(buf, ctypes.POINTER(_PdhCounterItem))
            # One instance per process per engine. Summing per process and
            # taking the total matches Task Manager's "3D" graph.
            busy = sum(items[i].value for i in range(count.value) if items[i].status in (0, 1))
        except Exception:
            return None
        return min(1.0, busy / 100)


_PDH_MORE_DATA = 0x800007D2


class _PdhCounterItem(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_wchar_p),
        ("status", wintypes.DWORD),
        ("value", ctypes.c_double),
    ]


def _check_pdh(status: int) -> None:
    if status != 0:
        raise OSError(f"PDH error 0x{status & 0xFFFFFFFF:08X}")


class LhmCpuSensor:
    """CPU package power from LibreHardwareMonitor's built-in web server."""

    def __init__(self, url: str, timeout: float = 1.0) -> None:
        self._url = url
        self._timeout = timeout

    def read_watts(self) -> float | None:
        try:
            with urllib.request.urlopen(self._url, timeout=self._timeout) as resp:
                tree = json.load(resp)
        except (urllib.error.URLError, TimeoutError, ValueError):
            return None
        return find_cpu_package_watts(tree)


def find_cpu_package_watts(tree: dict) -> float | None:
    """Pick the CPU "Package" power sensor out of LHM's data.json tree."""
    readings: list[float] = []

    def walk(node: dict, in_cpu: bool) -> None:
        ids = " ".join(str(node.get(k, "")) for k in ("ImageURL", "SensorId", "HardwareId"))
        in_cpu = in_cpu or "cpu" in ids.lower()
        value = str(node.get("Value", "")).strip()
        if in_cpu and "package" in node.get("Text", "").lower() and value.endswith("W"):
            with contextlib.suppress(ValueError):
                readings.append(float(value.removesuffix("W").replace(",", ".")))
        for child in node.get("Children", []):
            walk(child, in_cpu)

    walk(tree, in_cpu=False)
    return max(readings, default=None)


def describe(exc: BaseException) -> str:
    """One line explaining why a sensor isn't available, for the info panel."""
    text = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {text}"[:160] if text else type(exc).__name__
