from datetime import date

import pytest

from power_meter.storage import UsageLog


def test_roundtrip(tmp_path):
    path = tmp_path / "usage.json"
    log = UsageLog(path)
    log.add(date(2026, 10, 16), "peak", wh=100, baht=0.64)
    log.add(date(2026, 10, 16), "off_peak", wh=50, baht=0.15)
    log.save()

    reloaded = UsageLog(path)
    today = reloaded.day_total(date(2026, 10, 16))
    assert today.wh == pytest.approx(150)
    assert today.baht == pytest.approx(0.79)
    assert reloaded.total_baht == pytest.approx(0.79)


def test_unreadable_file_is_backed_up(tmp_path):
    path = tmp_path / "usage.json"
    path.write_text("not json", encoding="utf-8")

    log = UsageLog(path)

    assert log.days == {}
    assert (tmp_path / "usage.bak").read_text(encoding="utf-8") == "not json"
