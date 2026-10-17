import json
from datetime import date

from power_meter import rates
from power_meter.config import Config, build_tariff, load
from power_meter.hardware import Hardware
from power_meter.monitor import Monitor
from power_meter.tariff import FlatTariff, TouTariff


def newer(**changes):
    data = json.loads(json.dumps(rates.BUILT_IN))
    data["updated"] = "2099-01-01"
    data.update(changes)
    return data


def test_ft_follows_the_date():
    r = newer(ft=[{"from": "2026-09-01", "ft": 0.16}, {"from": "2027-01-01", "ft": 0.2}])
    assert rates.ft_on(r, date(2026, 12, 31)) == 0.16
    assert rates.ft_on(r, date(2027, 1, 1)) == 0.2
    assert rates.ft_on(r, date(2020, 1, 1)) == 0.16


def test_newer_cache_wins_and_bad_cache_is_ignored(tmp_path):
    cache = tmp_path / "rates.json"
    assert rates.load(cache) is rates.BUILT_IN
    cache.write_text(json.dumps(newer(flat_rate=4.0)), encoding="utf-8")
    assert rates.load(cache)["flat_rate"] == 4.0
    cache.write_text(json.dumps({"updated": "2099-01-01", "vat": 7}), encoding="utf-8")
    assert rates.load(cache) is rates.BUILT_IN


def test_repo_rates_file_matches_built_in():
    with open("rates.json", encoding="utf-8") as f:
        assert json.load(f) == rates.BUILT_IN


def test_meter_defaults_to_flat_until_chosen(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    cfg = load(None)
    assert isinstance(cfg.tariff, FlatTariff)
    assert not cfg.meter_chosen

    monitor = Monitor(cfg, Hardware(cpu="x", gpus=(), laptop=False))
    monitor.set_meter("tou")
    assert isinstance(monitor.cfg.tariff, TouTariff)

    again = load(None)
    assert again.meter_chosen
    assert isinstance(again.tariff, TouTariff)


def test_config_file_overrides_still_apply():
    t = build_tariff("tou", rates.BUILT_IN, date(2026, 10, 17), overrides={"ft": 0.5})
    assert t.ft == 0.5
    assert isinstance(t, TouTariff)


def test_config_type_counts_as_chosen(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = tmp_path / "config.toml"
    path.write_text('[tariff]\ntype = "tou"\n', encoding="utf-8")
    cfg: Config = load(path)
    assert cfg.meter_chosen
    assert cfg.meter == "tou"
