"""Hardware power sensors on Windows.

Each sensor degrades to "unavailable" instead of failing, because most
machines have only some of them (desktops have no battery, not every
laptop has an NVIDIA GPU, LibreHardwareMonitor may not be running).
"""

from __future__ import annotations

import contextlib
import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class BatteryReading:
    on_ac: bool
    discharge_w: float
    charge_w: float


class BatterySensor:
    """Reads the battery fuel gauge through WMI (root\\wmi BatteryStatus)."""

    def __init__(self) -> None:
        # COM objects belong to the thread that made them, and the monitor
        # reads from a worker thread, so each thread gets its own connection.
        self._local = threading.local()
        self.error: str | None = None
        try:
            self._status()
        except ImportError as exc:
            self.error = f"missing {exc.name}"
        except Exception as exc:  # pywin32 raises x_wmi / com_error, not a common base
            self.error = describe(exc)

    @property
    def available(self) -> bool:
        return self.error is None

    def _status(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            import pythoncom
            import wmi

            pythoncom.CoInitialize()
            conn = wmi.WMI(namespace="root\\wmi")
            self._local.conn = conn
        statuses = conn.BatteryStatus()
        if not statuses:
            raise LookupError("no battery")
        return statuses[0]

    def read(self) -> BatteryReading | None:
        if self.error is not None:
            return None
        try:
            status = self._status()
        except Exception:  # transient COM errors happen after sleep/resume
            self._local.conn = None
            return None
        # WMI reports rates in milliwatts.
        charge_mw = status.ChargeRate if status.Charging else 0
        return BatteryReading(
            on_ac=bool(status.PowerOnline),
            discharge_w=(status.DischargeRate or 0) / 1000,
            charge_w=(charge_mw or 0) / 1000,
        )


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
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            self._handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(count)]
        except pynvml.NVMLError as exc:  # no driver, or no NVIDIA GPU at all
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
