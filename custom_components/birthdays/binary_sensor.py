"""Binary sensor platform for the Birthdays integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SUBENTRY_TYPE_BIRTHDAY
from .coordinator import BirthdaysConfigEntry, BirthdaysCoordinator
from .entity import BirthdayEntity, async_get_entity_name_translations

KEY_IS_BIRTHDAY = "is_birthday"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BirthdaysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a 'birthday today' binary sensor for every person."""
    coordinator = config_entry.runtime_data
    names = await async_get_entity_name_translations(hass, "binary_sensor")

    for subentry_id, subentry in config_entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_BIRTHDAY:
            continue
        if subentry_id not in coordinator.data:
            continue

        async_add_entities(
            [BirthdayTodayBinarySensor(coordinator, subentry_id, names)],
            config_subentry_id=subentry_id,
        )


class BirthdayTodayBinarySensor(BirthdayEntity, BinarySensorEntity):
    """True on the day itself."""

    _attr_icon = "mdi:party-popper"

    def __init__(
        self,
        coordinator: BirthdaysCoordinator,
        subentry_id: str,
        names: dict[str, str],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            coordinator,
            subentry_id,
            KEY_IS_BIRTHDAY,
            entity_id_format=ENTITY_ID_FORMAT,
            suggested_name=names.get(KEY_IS_BIRTHDAY),
        )

    @property
    def is_on(self) -> bool:
        """Return True if this person has their birthday today."""
        return self.person.is_birthday_today
