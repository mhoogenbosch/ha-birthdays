"""Pytest fixtures."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.birthdays.const import (
    CONF_DATE_OF_BIRTH,
    CONF_NAME,
    DOMAIN,
    SUBENTRY_TYPE_BIRTHDAY,
)
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture(autouse=True)
async def set_time_zone(hass: HomeAssistant):
    """Run every test in a timezone with a DST offset.

    The daily rollover happens at local midnight, so tests that run in UTC
    would silently pass for the wrong reason.
    """
    await hass.config.async_set_time_zone("Europe/Amsterdam")


def make_subentry(name: str, date_of_birth: str) -> ConfigSubentryData:
    """Build a subentry for one person."""
    from homeassistant.util import slugify

    return ConfigSubentryData(
        data={CONF_NAME: name, CONF_DATE_OF_BIRTH: date_of_birth},
        subentry_type=SUBENTRY_TYPE_BIRTHDAY,
        title=name,
        unique_id=slugify(name),
    )


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry with two people."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Birthdays",
        data={},
        subentries_data=[
            make_subentry("Fynn Hoogenbosch", "2020-08-04"),
            make_subentry("Martijn Hoogenbosch", "1982-06-20"),
        ],
    )


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up a config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
