import ctypes

from power_meter import sensors


def test_battery_probe_failure_does_not_raise(monkeypatch):
    def broken():
        raise ctypes.ArgumentError("argument 1: wrong type")

    monkeypatch.setattr(sensors.sys, "platform", "win32")
    monkeypatch.setattr(sensors, "_battery_device_path", broken)

    battery = sensors.BatterySensor()

    assert not battery.available
    assert "ArgumentError" in battery.error
    assert battery.read() is None
