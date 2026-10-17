import threading

import pytest

from power_meter.config import Config
from power_meter.estimate import EstimateConfig
from power_meter.monitor import Monitor
from power_meter.tariff import FlatTariff


def test_run_accumulates_and_saves(tmp_path):
    cfg = Config(
        tariff=FlatTariff(rate=4.0, ft=0.0, vat=0.0),
        estimate=EstimateConfig(base_watts=88, cpu_fallback_watts=0, adapter_efficiency=1.0),
        interval_sec=0.01,
        data_file=tmp_path / "usage.json",
    )
    monitor = Monitor(cfg)
    stop = threading.Event()
    samples = []

    def on_sample(s):
        samples.append(s)
        if len(samples) == 5:
            stop.set()

    monitor.run(stop, on_sample)

    assert all(s.watts == pytest.approx(88) for s in samples)
    assert monitor.session.wh > 0
    assert monitor.session.baht == pytest.approx(monitor.session.wh / 1000 * 4.0)
    assert len(monitor.history) == 5
    assert (tmp_path / "usage.json").exists()
