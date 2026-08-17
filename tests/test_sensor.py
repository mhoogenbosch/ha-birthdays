"""Test the sensors and the daily rollover."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.birthdays.const import (
    CONF_AGE_AT_NEXT_BIRTHDAY,
    CONF_DATE_OF_BIRTH,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import setup_integration

# Fynn: 2020-08-04, Martijn: 1982-06-20.
DAYS_UNTIL = "sensor.fynn_hoogenbosch_days_until_birthday"
NEXT_BIRTHDAY = "sensor.fynn_hoogenbosch_birthday"
AGE = "sensor.fynn_hoogenbosch_age"
IS_BIRTHDAY = "binary_sensor.fynn_hoogenbosch_birthday_today"


@pytest.fixture(autouse=True)
def _freeze(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    """Freeze time a fortnight before Fynn's birthday."""
    freezer.move_to("2026-07-21 12:00:00+02:00")
    return freezer


async def test_sensor_values(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The sensors report the days left, the date and the current age."""
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(DAYS_UNTIL).state == "14"
    assert hass.states.get(NEXT_BIRTHDAY).state == "2026-08-04"
    assert hass.states.get(AGE).state == "5"
    assert hass.states.get(IS_BIRTHDAY).state == "off"


async def test_days_until_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The version 1 attributes are still available."""
    await setup_integration(hass, mock_config_entry)

    attributes = hass.states.get(DAYS_UNTIL).attributes
    assert attributes[CONF_DATE_OF_BIRTH] == "2020-08-04"
    assert attributes[CONF_AGE_AT_NEXT_BIRTHDAY] == 6


async def test_next_year_after_the_birthday_has_passed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, _freeze
) -> None:
    """After the birthday the sensors point at next year."""
    _freeze.move_to("2026-08-05 12:00:00+02:00")
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(NEXT_BIRTHDAY).state == "2027-08-04"
    assert hass.states.get(DAYS_UNTIL).state == "364"
    assert hass.states.get(AGE).state == "6"


async def test_state_updates_at_midnight(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, _freeze
) -> None:
    """The countdown drops without a restart when the date rolls over."""
    _freeze.move_to("2026-08-03 23:59:00+02:00")
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(DAYS_UNTIL).state == "1"
    assert hass.states.get(IS_BIRTHDAY).state == "off"

    _freeze.move_to("2026-08-04 00:00:01+02:00")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()

    assert hass.states.get(DAYS_UNTIL).state == "0"
    assert hass.states.get(IS_BIRTHDAY).state == "on"
    assert hass.states.get(AGE).state == "6"


async def test_days_until_has_no_decimals(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A whole number of days must not render as "352.00 d".

    Duration is a convertible device class, so Home Assistant assigns it a
    default display precision of 2 unless the entity suggests otherwise.
    """
    await setup_integration(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(DAYS_UNTIL)

    assert entry.options["sensor"]["suggested_display_precision"] == 0
