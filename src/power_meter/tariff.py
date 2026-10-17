"""Electricity pricing for Thai residential tariffs."""

from __future__ import annotations

from collections.abc import Container
from dataclasses import dataclass, field
from datetime import date, datetime

PEAK = "peak"
OFF_PEAK = "off_peak"
FLAT = "flat"


@dataclass(frozen=True)
class TouTariff:
    """Time-of-use tariff: weekday daytime is peak, everything else is off-peak."""

    peak_rate: float
    off_peak_rate: float
    ft: float
    vat: float = 0.07
    peak_start_hour: int = 9
    peak_end_hour: int = 22
    holidays: Container[date] = field(default_factory=frozenset, compare=False)

    def period(self, when: datetime) -> str:
        if when.weekday() >= 5 or when.date() in self.holidays:
            return OFF_PEAK
        if self.peak_start_hour <= when.hour < self.peak_end_hour:
            return PEAK
        return OFF_PEAK

    def price_per_kwh(self, period: str) -> float:
        base = self.peak_rate if period == PEAK else self.off_peak_rate
        return (base + self.ft) * (1 + self.vat)


@dataclass(frozen=True)
class FlatTariff:
    """Single average rate, for ordinary (non-TOU) meters."""

    rate: float
    ft: float
    vat: float = 0.07

    def period(self, when: datetime) -> str:
        return FLAT

    def price_per_kwh(self, period: str) -> float:
        return (self.rate + self.ft) * (1 + self.vat)


Tariff = TouTariff | FlatTariff


def thai_holidays() -> Container[date]:
    """Thai public holidays, or an empty set if the `holidays` package is missing."""
    try:
        import holidays
    except ImportError:
        return frozenset()
    # Pre-fill the current year so an installed package is never mistaken for
    # an empty set; later years are added on lookup.
    return holidays.Thailand(years=date.today().year)
