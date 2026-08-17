"""Test the birthday calculations."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.birthdays.coordinator import occurrence_in_year


@pytest.mark.parametrize(
    ("date_of_birth", "year", "expected"),
    [
        # Ordinary date.
        (date(1982, 6, 20), 2026, date(2026, 6, 20)),
        # 29 February in a leap year.
        (date(2000, 2, 29), 2028, date(2028, 2, 29)),
        # 29 February in a non-leap year is celebrated on 1 March. Version 1
        # raised a ValueError here, which broke the whole integration.
        (date(2000, 2, 29), 2026, date(2026, 3, 1)),
        (date(2000, 2, 29), 2027, date(2027, 3, 1)),
    ],
)
def test_occurrence_in_year(date_of_birth: date, year: int, expected: date) -> None:
    """The celebrated date is calculated for every year, leap years included."""
    assert occurrence_in_year(date_of_birth, year) == expected
