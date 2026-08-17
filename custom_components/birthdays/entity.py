"""Base entity for the Birthdays integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BirthdayInfo, BirthdaysCoordinator


async def async_get_entity_name_translations(
    hass: HomeAssistant, platform: str
) -> dict[str, str]:
    """Return the translated entity names for a platform, keyed by translation key.

    Home Assistant derives entity ids from the *English* entity names, so an
    installation running in another language would still get English entity
    ids. We look the names up in the user's own language and suggest the entity
    id ourselves, so a Dutch installation gets Dutch entity ids.
    """
    translations = await async_get_translations(
        hass, hass.config.language, "entity", [DOMAIN]
    )
    prefix = f"component.{DOMAIN}.entity.{platform}."
    suffix = ".name"

    return {
        key[len(prefix) : -len(suffix)]: value
        for key, value in translations.items()
        if key.startswith(prefix) and key.endswith(suffix)
    }


class BirthdayEntity(CoordinatorEntity[BirthdaysCoordinator]):
    """Base class for entities belonging to one person."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BirthdaysCoordinator,
        subentry_id: str,
        key: str,
        entity_id_format: str | None = None,
        suggested_name: str | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._subentry_id = subentry_id
        # The subentry id is stable across renames, the name and slug are not.
        self._attr_unique_id = f"{subentry_id}-{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry_id)},
            name=self.person.name,
            entry_type=DeviceEntryType.SERVICE,
        )

        if entity_id_format and suggested_name:
            self.entity_id = async_generate_entity_id(
                entity_id_format,
                f"{self.person.name} {suggested_name}",
                hass=coordinator.hass,
            )

    @property
    def person(self) -> BirthdayInfo:
        """Return the calculated data for this person."""
        return self.coordinator.data[self._subentry_id]

    @property
    def available(self) -> bool:
        """Return True if the person still exists in the config entry."""
        return super().available and self._subentry_id in self.coordinator.data
