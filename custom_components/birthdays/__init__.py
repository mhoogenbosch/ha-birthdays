"""The Birthdays integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ATTRIBUTES,
    CONF_BIRTHDAYS,
    CONF_DATE_OF_BIRTH,
    CONF_GLOBAL_CONFIG,
    CONF_ICON,
    CONF_NAME,
    CONF_UNIQUE_ID,
    DEFAULT_ICON,
    DOMAIN,
    ISSUE_DEPRECATED_YAML,
)
from .coordinator import BirthdaysConfigEntry, BirthdaysCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.SENSOR,
]

BIRTHDAY_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DATE_OF_BIRTH): cv.date,
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
        vol.Optional(CONF_ATTRIBUTES, default={}): vol.Schema({cv.string: cv.string}),
    }
)

GLOBAL_CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(CONF_ATTRIBUTES, default={}): vol.Schema({cv.string: cv.string})}
)

# Version 1 supported a plain list of birthdays as well as a dict with a
# `birthdays` key and global attributes. Both are still accepted, and both are
# imported into the config entry.
OLD_CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [BIRTHDAY_CONFIG_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)

NEW_CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            CONF_BIRTHDAYS: vol.All(cv.ensure_list, [BIRTHDAY_CONFIG_SCHEMA]),
            vol.Optional(CONF_GLOBAL_CONFIG, default={}): GLOBAL_CONFIG_SCHEMA,
        }
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    vol.Any(OLD_CONFIG_SCHEMA, NEW_CONFIG_SCHEMA), extra=vol.ALLOW_EXTRA
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import any YAML configuration into the config entry."""
    if DOMAIN not in config:
        return True

    birthdays = _birthdays_from_yaml(config[DOMAIN])
    if not birthdays:
        return True

    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_DEPRECATED_YAML,
        breaks_in_ha_version=None,
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_DEPRECATED_YAML,
        translation_placeholders={"count": str(len(birthdays))},
    )

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_BIRTHDAYS: birthdays},
        )
    )

    return True


def _birthdays_from_yaml(yaml_config: Any) -> list[dict[str, Any]]:
    """Flatten either YAML format into a plain list of birthdays."""
    is_new_format = (
        isinstance(yaml_config, dict) and yaml_config.get(CONF_BIRTHDAYS) is not None
    )

    if not is_new_format:
        return list(yaml_config)

    global_attributes = (
        yaml_config.get(CONF_GLOBAL_CONFIG, {}).get(CONF_ATTRIBUTES) or {}
    )

    birthdays = []
    for birthday in yaml_config[CONF_BIRTHDAYS]:
        merged = dict(birthday)
        # Local attributes win over global ones.
        merged[CONF_ATTRIBUTES] = {
            **global_attributes,
            **(birthday.get(CONF_ATTRIBUTES) or {}),
        }
        birthdays.append(merged)

    return birthdays


async def async_setup_entry(hass: HomeAssistant, entry: BirthdaysConfigEntry) -> bool:
    """Set up Birthdays from a config entry."""
    coordinator = BirthdaysCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    coordinator.async_setup_midnight_listener()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Someone whose birthday is today should still get their event when Home
    # Assistant starts, as was the case in version 1.
    coordinator.async_fire_birthday_events()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BirthdaysConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: BirthdaysConfigEntry
) -> None:
    """Reload when a birthday is added, edited or removed."""
    await hass.config_entries.async_reload(entry.entry_id)
