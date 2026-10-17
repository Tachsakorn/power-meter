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


def test_amd_sensor_prefers_board_power(monkeypatch):
    monkeypatch.setattr(sensors.sys, "platform", "win32")
    monkeypatch.setattr(sensors.AmdGpuSensor, "_open", lambda self: setattr(self, "_adl", object()))
    readings = {8: 44, 23: 20, 52: 28, 73: 16}
    monkeypatch.setattr(sensors.AmdGpuSensor, "read_sensors", lambda self: readings)

    gpu = sensors.AmdGpuSensor()

    assert gpu.available
    assert gpu.read_watts() == 16


def test_amd_sensor_without_power_lists_what_it_saw(monkeypatch):
    monkeypatch.setattr(sensors.sys, "platform", "win32")
    monkeypatch.setattr(sensors.AmdGpuSensor, "_open", lambda self: setattr(self, "_adl", object()))
    monkeypatch.setattr(sensors.AmdGpuSensor, "read_sensors", lambda self: {8: 44})

    gpu = sensors.AmdGpuSensor()

    assert not gpu.available
    assert "{8: 44}" in gpu.error
