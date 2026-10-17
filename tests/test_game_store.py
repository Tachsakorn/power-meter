import pytest

from power_meter import game_store
from power_meter.config import Config
from power_meter.gui import Api
from power_meter.monitor import Monitor
from power_meter.tariff import FlatTariff


def test_roundtrip(tmp_path):
    path = tmp_path / "reactor-save.json"
    assert game_store.load(path) is None

    game_store.save(path, {"v": 1, "credits": 12.5})

    assert game_store.load(path) == {"v": 1, "credits": 12.5}


def test_rejects_non_objects_and_huge_saves(tmp_path):
    path = tmp_path / "reactor-save.json"
    with pytest.raises(TypeError):
        game_store.save(path, [1, 2, 3])
    with pytest.raises(ValueError):
        game_store.save(path, {"junk": "x" * (game_store.MAX_BYTES + 1)})
    assert not path.exists()


def test_corrupt_save_loads_as_new_game(tmp_path):
    path = tmp_path / "reactor-save.json"
    path.write_text("{not json", encoding="utf-8")
    assert game_store.load(path) is None


def test_game_save_is_separate_from_usage_log(tmp_path):
    monitor = Monitor(Config(tariff=FlatTariff(rate=4, ft=0), data_file=tmp_path / "usage.json"))
    api = Api(monitor)

    api.save_game({"v": 1, "credits": 99})

    assert (tmp_path / "reactor-save.json").exists()
    assert not (tmp_path / "usage.json").exists()
    assert api.load_game() == {"v": 1, "credits": 99}
    assert monitor.log.total_baht == 0
