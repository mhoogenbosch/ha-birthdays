"""Test setup and the YAML import."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.birthdays.const import (
    CONF_DATE_OF_BIRTH,
    CONF_NAME,
    DOMAIN,
    EVENT_BIRTHDAY,
    ISSUE_DEPRECATED_YAML,
    SUBENTRY_TYPE_BIRTHDAY,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from .conftest import setup_integration


async def test_setup_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The config entry sets up and creates entities for every person."""
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("calendar.birthdays") is not None
    assert hass.states.get("sensor.fynn_hoogenbosch_days_until_birthday") is not None
    assert hass.states.get("sensor.fynn_hoogenbosch_birthday") is not None
    assert hass.states.get("sensor.fynn_hoogenbosch_age") is not None
    assert hass.states.get("binary_sensor.fynn_hoogenbosch_birthday_today") is not None


async def test_entity_ids_follow_the_user_language(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A Dutch installation gets Dutch entity ids, not English ones.

    Home Assistant derives entity ids from the English entity names, so the
    integration suggests the entity id in the user's own language instead.
    """
    hass.config.language = "nl"

    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("sensor.fynn_hoogenbosch_dagen_tot_verjaardag") is not None
    assert hass.states.get("sensor.fynn_hoogenbosch_verjaardag") is not None
    assert hass.states.get("sensor.fynn_hoogenbosch_leeftijd") is not None
    assert hass.states.get("binary_sensor.fynn_hoogenbosch_jarig") is not None


async def test_unload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The config entry unloads cleanly."""
    await setup_integration(hass, mock_config_entry)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("calendar.birthdays").state == "unavailable"


@pytest.mark.parametrize(
    "yaml_config",
    [
        # Version 1 list format.
        {
            DOMAIN: [
                {"name": "Fynn Hoogenbosch", "date_of_birth": "2020-08-04"},
                {"name": "Martijn Hoogenbosch", "date_of_birth": "1982-06-20"},
            ]
        },
        # Version 1 dict format with global attributes.
        {
            DOMAIN: {
                "birthdays": [
                    {"name": "Fynn Hoogenbosch", "date_of_birth": "2020-08-04"},
                    {"name": "Martijn Hoogenbosch", "date_of_birth": "1982-06-20"},
                ],
                "config": {"attributes": {"source": "yaml"}},
            }
        },
    ],
    ids=["list_format", "dict_format"],
)
async def test_import_from_yaml(hass: HomeAssistant, yaml_config: dict) -> None:
    """YAML birthdays are imported as subentries and a repair issue is raised."""
    assert await async_setup_component(hass, DOMAIN, yaml_config)
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    subentries = [
        subentry
        for subentry in entries[0].subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_BIRTHDAY
    ]
    assert {subentry.data[CONF_NAME] for subentry in subentries} == {
        "Fynn Hoogenbosch",
        "Martijn Hoogenbosch",
    }
    assert all(
        isinstance(subentry.data[CONF_DATE_OF_BIRTH], str) for subentry in subentries
    )

    issue_registry = ir.async_get(hass)
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_DEPRECATED_YAML) is not None


async def test_import_skips_duplicate_names(hass: HomeAssistant) -> None:
    """Two YAML entries with the same name would collide, so one is skipped."""
    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: [
                {"name": "Fynn Hoogenbosch", "date_of_birth": "2020-08-04"},
                {"name": "fynn hoogenbosch", "date_of_birth": "2021-01-01"},
            ]
        },
    )
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries[0].subentries) == 1


async def test_birthday_event_is_fired(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The legacy `birthday` event still fires on the day itself."""
    freezer.move_to("2026-08-04 09:00:00+02:00")

    events = []
    hass.bus.async_listen(EVENT_BIRTHDAY, events.append)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {"name": "Fynn Hoogenbosch", "date_of_birth": "2020-08-04"},
                "subentry_type": SUBENTRY_TYPE_BIRTHDAY,
                "title": "Fynn Hoogenbosch",
                "unique_id": "fynn_hoogenbosch",
            }
        ],
    )
    await setup_integration(hass, entry)

    assert len(events) == 1
    assert events[0].data == {"name": "Fynn Hoogenbosch", "age": 6}
