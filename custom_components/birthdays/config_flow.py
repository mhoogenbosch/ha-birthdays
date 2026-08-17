"""Config flow for the Birthdays integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
    CONF_ATTRIBUTES,
    CONF_DATE_OF_BIRTH,
    CONF_ICON,
    CONF_NAME,
    CONF_UNIQUE_ID,
    DEFAULT_ICON,
    DOMAIN,
    DOMAIN_FRIENDLY_NAME,
    SUBENTRY_TYPE_BIRTHDAY,
)

BIRTHDAY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): selector.TextSelector(),
        vol.Required(CONF_DATE_OF_BIRTH): selector.DateSelector(),
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): selector.IconSelector(),
    }
)


class BirthdaysConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the single config entry that owns all birthdays."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the config entry; people are added as subentries afterwards."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

        return self.async_create_entry(title=DOMAIN_FRIENDLY_NAME, data={})

    async def async_step_import(
        self, import_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Import the birthdays configured in YAML as subentries."""
        subentries: list[ConfigSubentryData] = []
        used_unique_ids: set[str] = set()

        for birthday in import_data.get("birthdays", []):
            name = birthday[CONF_NAME]
            unique_id = slugify(birthday.get(CONF_UNIQUE_ID) or name)
            if unique_id in used_unique_ids:
                # Two YAML entries resolving to the same id would be rejected by
                # the config entry store; keep the first and skip the rest.
                continue
            used_unique_ids.add(unique_id)

            data: dict[str, Any] = {
                CONF_NAME: name,
                CONF_DATE_OF_BIRTH: str(birthday[CONF_DATE_OF_BIRTH]),
                CONF_ICON: birthday.get(CONF_ICON) or DEFAULT_ICON,
            }
            if attributes := birthday.get(CONF_ATTRIBUTES):
                data[CONF_ATTRIBUTES] = dict(attributes)

            subentries.append(
                ConfigSubentryData(
                    data=data,
                    subentry_type=SUBENTRY_TYPE_BIRTHDAY,
                    title=name,
                    unique_id=unique_id,
                )
            )

        return self.async_create_entry(
            title=DOMAIN_FRIENDLY_NAME, data={}, subentries=subentries
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the subentry types this integration supports."""
        return {SUBENTRY_TYPE_BIRTHDAY: BirthdaySubentryFlowHandler}


class BirthdaySubentryFlowHandler(ConfigSubentryFlow):
    """Add or edit a single person."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a new birthday."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = slugify(user_input[CONF_NAME])
            if self._unique_id_in_use(unique_id):
                errors[CONF_NAME] = "already_configured"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                    unique_id=unique_id,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                BIRTHDAY_SCHEMA, user_input or {}
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing birthday."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = slugify(user_input[CONF_NAME])
            if self._unique_id_in_use(unique_id, ignore=subentry.subentry_id):
                errors[CONF_NAME] = "already_configured"
            else:
                # Attributes are YAML-only and not shown in the form, so merge
                # rather than replace to avoid dropping them on an edit.
                data = dict(subentry.data) | user_input
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=user_input[CONF_NAME],
                    data=data,
                    unique_id=unique_id,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                BIRTHDAY_SCHEMA, user_input or subentry.data
            ),
            errors=errors,
        )

    @callback
    def _unique_id_in_use(self, unique_id: str, ignore: str | None = None) -> bool:
        """Return True if another subentry already uses this unique id."""
        return any(
            subentry.unique_id == unique_id and subentry_id != ignore
            for subentry_id, subentry in self._get_entry().subentries.items()
        )
