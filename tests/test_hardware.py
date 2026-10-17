import pytest

from power_meter.hardware import guess_cpu_tdp, guess_gpu_watts, is_nvidia


@pytest.mark.parametrize(
    ("name", "tdp"),
    [
        ("AMD Ryzen 7 7700X 8-Core Processor", 105),
        ("AMD Ryzen 9 7950X 16-Core Processor", 170),
        ("AMD Ryzen 7 7800X3D 8-Core Processor", 120),
        ("AMD Ryzen 5 5600G with Radeon Graphics", 65),
        ("AMD Ryzen 5 5600 6-Core Processor", 65),
        ("AMD Ryzen AI 9 HX 370 w/ Radeon 890M", 55),
        ("AMD Ryzen 7 7840HS w/ Radeon 780M Graphics", 45),
        ("12th Gen Intel(R) Core(TM) i5-12400F", 65),
        ("13th Gen Intel(R) Core(TM) i7-13700K", 125),
        ("Intel(R) Core(TM) Ultra 7 265K", 125),
        ("13th Gen Intel(R) Core(TM) i7-1355U", 15),
        ("12th Gen Intel(R) Core(TM) i7-12700H", 45),
        ("Something Else", 65),
    ],
)
def test_cpu_tdp_guess(name, tdp):
    assert guess_cpu_tdp(name) == tdp


@pytest.mark.parametrize(
    ("name", "watts"),
    [
        ("NVIDIA GeForce RTX 4070", 220),
        ("NVIDIA GeForce RTX 4090", 420),
        ("NVIDIA GeForce RTX 3060", 140),
        ("NVIDIA GeForce RTX 5070 Laptop GPU", 220),
        ("AMD Radeon RX 7800 XT", 250),
        ("AMD Radeon RX 6600", 140),
        ("AMD Radeon(TM) Graphics", 0),
        ("AMD Radeon 780M Graphics", 0),
        ("Intel(R) UHD Graphics 770", 0),
        ("Intel(R) Arc(TM) A770 Graphics", 200),
    ],
)
def test_gpu_watts_guess(name, watts):
    assert guess_gpu_watts(name) == watts


def test_is_nvidia():
    assert is_nvidia("NVIDIA GeForce RTX 4070")
    assert not is_nvidia("AMD Radeon RX 7800 XT")
