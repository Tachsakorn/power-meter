from datetime import date, datetime

import pytest

from power_meter.config import Config
from power_meter.gui import build_state
from power_meter.monitor import Monitor, Sample
from power_meter.tariff import FlatTariff, TouTariff

TOU = TouTariff(peak_rate=5.7982, off_peak_rate=2.6369, ft=0.1623)


def make_monitor(tmp_path, tariff=TOU) -> Monitor:
    return Monitor(Config(tariff=tariff, data_file=tmp_path / "usage.json"))


def test_state_before_first_sample(tmp_path):
    state = build_state(make_monitor(tmp_path), datetime(2026, 10, 16, 19, 40))
    assert state["watts"] is None
    assert state["period"] == "peak"
    assert len(state["days"]) == 7
    assert state["next_change"] == datetime(2026, 10, 16, 22).timestamp() * 1000
    assert state["next_price"] == pytest.approx(TOU.price_per_kwh("off_peak"))


def test_state_totals(tmp_path):
    m = make_monitor(tmp_path)
    m.log.add(date(2026, 10, 1), "off_peak", 1000, 3.0)
    m.log.add(date(2026, 10, 16), "peak", 500, 3.19)
    m.log.add(date(2026, 9, 30), "peak", 500, 3.19)
    m.latest = Sample(datetime(2026, 10, 16, 12), 100.0, True, "peak", 6.38)

    state = build_state(m, datetime(2026, 10, 16, 12))

    assert state["month_baht"] == pytest.approx(6.19)
    assert state["today_kwh"] == pytest.approx(0.5)
    assert state["baht_per_hour"] == pytest.approx(0.638)
    assert state["days"][-1]["peak_kwh"] == pytest.approx(0.5)


def test_weekend_is_off_peak_all_day(tmp_path):
    state = build_state(make_monitor(tmp_path), datetime(2026, 10, 17, 11, 40))
    assert state["off_peak_all_day"]
    assert state["next_change"] == datetime(2026, 10, 19, 9).timestamp() * 1000


def test_flat_tariff_has_no_next_change(tmp_path):
    m = make_monitor(tmp_path, FlatTariff(rate=3.78, ft=0.1623))
    state = build_state(m, datetime(2026, 10, 16, 12))
    assert not state["is_tou"]
    assert "next_change" not in state
