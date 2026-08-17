"""Test the config and subentry flows."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.birthdays.const import (
    CONF_DATE_OF_BIRTH,
    CONF_ICON,
    CONF_NAME,
    DOMAIN,
    SUBENTRY_TYPE_BIRTHDAY,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import setup_integration

PERSON = {
    CONF_NAME: "Lieke Heinsbroek",
    CONF_DATE_OF_BIRTH: "1985-04-21",
    CONF_ICON: "mdi:cake-variant",
}


async def test_user_flow_creates_the_entry(hass: HomeAssistant) -> None:
    """The user flow creates the single config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Birthdays"


async def test_only_one_entry_allowed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A second config entry is refused."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_add_birthday_subentry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A person can be added through the user interface."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, SUBENTRY_TYPE_BIRTHDAY),
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], PERSON
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lieke Heinsbroek"

    subentry = next(
        subentry
        for subentry in mock_config_entry.subentries.values()
        if subentry.unique_id == "lieke_heinsbroek"
    )
    assert subentry.data[CONF_DATE_OF_BIRTH] == "1985-04-21"

    # The entities of the new person exist without a restart.
    assert hass.states.get("sensor.lieke_heinsbroek_days_until_birthday") is not None


async def test_add_duplicate_birthday(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Adding a name that already exists shows an error instead of failing."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, SUBENTRY_TYPE_BIRTHDAY),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {**PERSON, CONF_NAME: "Fynn Hoogenbosch"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "already_configured"}


async def test_reconfigure_birthday(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An existing person can be edited."""
    await setup_integration(hass, mock_config_entry)

    subentry_id, subentry = next(
        (subentry_id, subentry)
        for subentry_id, subentry in mock_config_entry.subentries.items()
        if subentry.unique_id == "fynn_hoogenbosch"
    )

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, SUBENTRY_TYPE_BIRTHDAY),
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "subentry_id": subentry_id,
        },
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Fynn Hoogenbosch",
            CONF_DATE_OF_BIRTH: "2020-08-05",
            CONF_ICON: "mdi:party-popper",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    subentry = mock_config_entry.subentries[subentry_id]
    assert subentry.data[CONF_DATE_OF_BIRTH] == "2020-08-05"


async def test_remove_birthday(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Removing a person removes their entities."""
    await setup_integration(hass, mock_config_entry)
    assert hass.states.get("sensor.fynn_hoogenbosch_days_until_birthday") is not None

    subentry_id = next(
        subentry_id
        for subentry_id, subentry in mock_config_entry.subentries.items()
        if subentry.unique_id == "fynn_hoogenbosch"
    )
    hass.config_entries.async_remove_subentry(mock_config_entry, subentry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.fynn_hoogenbosch_days_until_birthday") is None
    assert hass.states.get("sensor.martijn_hoogenbosch_days_until_birthday") is not None
