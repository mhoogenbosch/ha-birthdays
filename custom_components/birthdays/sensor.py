"""Sensor platform for the Birthdays integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_AGE_AT_NEXT_BIRTHDAY,
    CONF_DATE_OF_BIRTH,
    SUBENTRY_TYPE_BIRTHDAY,
)
from .coordinator import BirthdayInfo, BirthdaysConfigEntry
from .entity import BirthdayEntity, async_get_entity_name_translations


@dataclass(frozen=True, kw_only=True)
class BirthdaySensorEntityDescription(SensorEntityDescription):
    """Describes a birthday sensor."""

    value_fn: Callable[[BirthdayInfo], int | date]


SENSORS: tuple[BirthdaySensorEntityDescription, ...] = (
    BirthdaySensorEntityDescription(
        key="days_until",
        translation_key="days_until",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        # Duration is a convertible device class, for which Home Assistant
        # defaults to 2 decimals — a whole number of days must not render as
        # "352.00 d".
        suggested_display_precision=0,
        value_fn=lambda info: info.days_until,
    ),
    BirthdaySensorEntityDescription(
        key="next_birthday",
        translation_key="next_birthday",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda info: info.next_birthday,
    ),
    BirthdaySensorEntityDescription(
        key="age",
        translation_key="age",
        icon="mdi:human-male-height",
        value_fn=lambda info: info.age_now,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BirthdaysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors for every person."""
    coordinator = config_entry.runtime_data
    names = await async_get_entity_name_translations(hass, "sensor")

    for subentry_id, subentry in config_entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_BIRTHDAY:
            continue
        if subentry_id not in coordinator.data:
            continue

        async_add_entities(
            [
                BirthdaySensor(coordinator, subentry_id, description, names)
                for description in SENSORS
            ],
            config_subentry_id=subentry_id,
        )


class BirthdaySensor(BirthdayEntity, SensorEntity):
    """A single calculated value for one person."""

    entity_description: BirthdaySensorEntityDescription

    def __init__(
        self,
        coordinator,
        subentry_id: str,
        description: BirthdaySensorEntityDescription,
        names: dict[str, str],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            subentry_id,
            description.key,
            entity_id_format=ENTITY_ID_FORMAT,
            suggested_name=names.get(description.key),
        )
        self.entity_description = description

        if description.key == "days_until":
            # The days_until sensor is the successor of the old `birthdays.*`
            # entity, so it carries the user configured icon and attributes.
            self._attr_icon = self.person.icon

    @property
    def native_value(self) -> int | date:
        """Return the value of the sensor."""
        return self.entity_description.value_fn(self.person)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the extra attributes, kept compatible with version 1."""
        if self.entity_description.key != "days_until":
            return None

        person = self.person
        return {
            CONF_DATE_OF_BIRTH: person.date_of_birth.isoformat(),
            CONF_AGE_AT_NEXT_BIRTHDAY: person.age_at_next_birthday,
            **person.attributes,
        }
