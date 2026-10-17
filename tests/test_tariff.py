from datetime import date, datetime

import pytest

from power_meter.tariff import FLAT, OFF_PEAK, PEAK, FlatTariff, TouTariff

TOU = TouTariff(peak_rate=5.7982, off_peak_rate=2.6369, ft=0.1623, holidays={date(2026, 10, 23)})


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        ("2026-10-16 08:59", OFF_PEAK),  # Friday, before peak
        ("2026-10-16 09:00", PEAK),
        ("2026-10-16 21:59", PEAK),
        ("2026-10-16 22:00", OFF_PEAK),
        ("2026-10-17 14:00", OFF_PEAK),  # Saturday
        ("2026-10-18 14:00", OFF_PEAK),  # Sunday
        ("2026-10-23 14:00", OFF_PEAK),  # Chulalongkorn Day, a Friday
    ],
)
def test_tou_period(when, expected):
    assert TOU.period(datetime.fromisoformat(when)) == expected


def test_tou_price_includes_ft_and_vat():
    assert TOU.price_per_kwh(PEAK) == pytest.approx((5.7982 + 0.1623) * 1.07)
    assert TOU.price_per_kwh(OFF_PEAK) == pytest.approx((2.6369 + 0.1623) * 1.07)


def test_flat_tariff():
    flat = FlatTariff(rate=3.78, ft=0.1623)
    assert flat.period(datetime(2026, 10, 16, 12)) == FLAT
    assert flat.price_per_kwh(FLAT) == pytest.approx(3.9423 * 1.07)
