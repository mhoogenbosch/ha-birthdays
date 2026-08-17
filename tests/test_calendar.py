"""Test the birthday calendar."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.birthdays.const import DOMAIN, SUBENTRY_TYPE_BIRTHDAY
from homeassistant.core import HomeAssistant

from .conftest import setup_integration

ENTITY_ID = "calendar.birthdays"


def _subentry(name: str, date_of_birth: str) -> dict:
    from homeassistant.util import slugify

    return {
        "data": {"name": name, "date_of_birth": date_of_birth},
        "subentry_type": SUBENTRY_TYPE_BIRTHDAY,
        "title": name,
        "unique_id": slugify(name),
    }


async def _get_events(hass: HomeAssistant, start: str, end: str) -> list[dict]:
    """Ask the calendar for the events between two local dates."""
    return await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": ENTITY_ID,
            "start_date_time": start,
            "end_date_time": end,
        },
        blocking=True,
        return_response=True,
    )


@pytest.fixture(autouse=True)
def _freeze(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    """Freeze time in the middle of December."""
    freezer.move_to("2026-12-15 12:00:00+01:00")
    return freezer


async def test_entity_id_is_preserved(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The calendar keeps the entity id used by version 1."""
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(ENTITY_ID) is not None


async def test_next_event(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The state points at the next birthday, sorted numerically.

    Version 1 sorted on the string state, so 10 days sorted before 9 days.
    """
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ID)
    # Martijn (20 June) comes before Fynn (4 August).
    assert state.attributes["message"] == "Martijn Hoogenbosch, 45"
    assert state.attributes["start_time"] == "2027-06-20 00:00:00"


async def test_events_across_new_year(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Looking ahead across new year's eve returns next year's birthdays.

    Version 1 only generated events for the current calendar year, so a
    dashboard looking two months ahead in December showed nothing.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[_subentry("Milan Hoogenbosch", "2010-01-12")],
    )
    await setup_integration(hass, entry)

    response = await _get_events(
        hass, "2026-12-15T00:00:00+01:00", "2027-02-15T00:00:00+01:00"
    )
    events = response[ENTITY_ID]["events"]

    assert len(events) == 1
    assert events[0]["start"] == "2027-01-12"
    assert events[0]["summary"] == "Milan Hoogenbosch, 17"


async def test_events_span_multiple_years(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A multi-year range returns one event per person per year."""
    await setup_integration(hass, mock_config_entry)

    response = await _get_events(
        hass, "2026-01-01T00:00:00+01:00", "2029-01-01T00:00:00+01:00"
    )
    events = response[ENTITY_ID]["events"]

    # 2 people x 3 years.
    assert len(events) == 6
    assert [event["start"] for event in events] == [
        "2026-06-20",
        "2026-08-04",
        "2027-06-20",
        "2027-08-04",
        "2028-06-20",
        "2028-08-04",
    ]


async def test_no_events_before_birth(hass: HomeAssistant) -> None:
    """Nobody has a birthday before they were born."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[_subentry("Fynn Hoogenbosch", "2020-08-04")],
    )
    await setup_integration(hass, entry)

    response = await _get_events(
        hass, "2018-01-01T00:00:00+01:00", "2021-01-01T00:00:00+01:00"
    )
    events = response[ENTITY_ID]["events"]

    assert [event["start"] for event in events] == ["2020-08-04"]


async def test_leap_day_birthday(hass: HomeAssistant) -> None:
    """A 29 February birthday is celebrated on 1 March in non-leap years."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[_subentry("Leap Person", "2000-02-29")],
    )
    await setup_integration(hass, entry)

    response = await _get_events(
        hass, "2027-01-01T00:00:00+01:00", "2029-01-01T00:00:00+01:00"
    )
    events = response[ENTITY_ID]["events"]

    assert [event["start"] for event in events] == ["2027-03-01", "2028-02-29"]
