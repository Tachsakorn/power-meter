import pytest

from power_meter.estimate import cpu_watts_from_load, gpu_watts_from_load, wall_watts
from power_meter.sensors import BatteryReading, find_cpu_package_watts


def test_on_battery_uses_fuel_gauge():
    reading = BatteryReading(on_ac=False, discharge_w=42.0, charge_w=0)
    assert wall_watts(reading, cpu_w=30, gpu_w=50, base_watts=15, efficiency=0.8) == (42.0, True)


def test_on_ac_sums_parts_and_conversion_loss():
    reading = BatteryReading(on_ac=True, discharge_w=0, charge_w=5)
    watts, measured = wall_watts(reading, cpu_w=30, gpu_w=50, base_watts=15, efficiency=0.8)
    assert watts == pytest.approx((30 + 50 + 15 + 5) / 0.8)
    assert not measured


def test_desktop_without_battery():
    watts, measured = wall_watts(None, cpu_w=20, gpu_w=0, base_watts=40, efficiency=0.9)
    assert watts == pytest.approx(60 / 0.9)
    assert not measured


def test_load_models_scale_between_idle_and_full():
    assert cpu_watts_from_load(0, 100) == pytest.approx(15)
    assert cpu_watts_from_load(1, 100) == pytest.approx(120)
    assert cpu_watts_from_load(2, 100) == pytest.approx(120)
    assert gpu_watts_from_load(0, 200) == pytest.approx(16)
    assert gpu_watts_from_load(0.5, 200) == pytest.approx(108)


def test_find_cpu_package_in_lhm_tree():
    tree = {
        "Text": "Sensor",
        "Children": [
            {
                "Text": "AMD Ryzen AI 9 HX",
                "ImageURL": "images_icon/cpu.png",
                "Children": [
                    {"Text": "Powers", "Children": [{"Text": "Package", "Value": "28,4 W"}]}
                ],
            },
            {
                "Text": "NVIDIA GeForce RTX 5070",
                "ImageURL": "images_icon/nvidia.png",
                "Children": [{"Text": "GPU Package", "Value": "60.0 W"}],
            },
        ],
    }
    assert find_cpu_package_watts(tree) == pytest.approx(28.4)


def test_find_cpu_package_missing():
    assert find_cpu_package_watts({"Text": "Sensor", "Children": []}) is None
