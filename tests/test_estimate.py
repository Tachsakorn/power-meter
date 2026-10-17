import pytest

from power_meter.estimate import EstimateConfig, wall_watts
from power_meter.sensors import BatteryReading, find_cpu_package_watts

CFG = EstimateConfig(base_watts=15, cpu_fallback_watts=12, adapter_efficiency=0.8)


def test_on_battery_uses_fuel_gauge():
    reading = BatteryReading(on_ac=False, discharge_w=42.0, charge_w=0)
    assert wall_watts(reading, cpu_w=30, gpu_w=50, cfg=CFG) == (42.0, True)


def test_on_ac_sums_parts_and_adapter_loss():
    reading = BatteryReading(on_ac=True, discharge_w=0, charge_w=5)
    watts, measured = wall_watts(reading, cpu_w=30, gpu_w=50, cfg=CFG)
    assert watts == pytest.approx((30 + 50 + 15 + 5) / 0.8)
    assert not measured


def test_no_sensors_falls_back_to_defaults():
    watts, _ = wall_watts(None, cpu_w=None, gpu_w=0, cfg=CFG)
    assert watts == pytest.approx((12 + 15) / 0.8)


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
