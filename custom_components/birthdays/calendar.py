"""Calendar platform for the Birthdays integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, DOMAIN_FRIENDLY_NAME
from .coordinator import (
    BirthdayInfo,
    BirthdaysConfigEntry,
    BirthdaysCoordinator,
    occurrence_in_year,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BirthdaysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the single calendar holding every birthday."""
    async_add_entities([BirthdaysCalendar(config_entry.runtime_data)])


class BirthdaysCalendar(CoordinatorEntity[BirthdaysCoordinator], CalendarEntity):
    """A calendar with a recurring all-day event for every person."""

    _attr_has_entity_name = False
    _attr_name = DOMAIN_FRIENDLY_NAME
    _attr_icon = "mdi:cake-variant"

    def __init__(self, coordinator: BirthdaysCoordinator) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        # Keep the unique id used by version 1 so existing installations keep
        # their `calendar.birthdays` entity id and stay wired into dashboards.
        self._attr_unique_id = f"calendar.{DOMAIN}"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming birthday."""
        upcoming = sorted(self.coordinator.data.values(), key=lambda i: i.days_until)
        if not upcoming:
            return None
        return _to_calendar_event(upcoming[0], upcoming[0].next_birthday.year)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return every birthday that falls within the requested range.

        Version 1 only ever generated events for the current calendar year, so
        a dashboard looking ahead across new year's eve showed nothing.
        """
        start = dt_util.as_local(start_date).date()
        end = dt_util.as_local(end_date).date()

        events: list[CalendarEvent] = []
        for info in self.coordinator.data.values():
            for year in range(start.year, end.year + 1):
                if year < info.date_of_birth.year:
                    continue

                occurrence = occurrence_in_year(info.date_of_birth, year)
                # All-day event: [occurrence, occurrence + 1 day)
                if occurrence < end and start < occurrence + timedelta(days=1):
                    events.append(_to_calendar_event(info, year))

        events.sort(key=lambda event: event.start)
        return events


def _to_calendar_event(info: BirthdayInfo, year: int) -> CalendarEvent:
    """Build the all-day event for one person in one year."""
    occurrence: date = occurrence_in_year(info.date_of_birth, year)
    age = year - info.date_of_birth.year
    summary = f"{info.name}, {age}"

    return CalendarEvent(
        start=occurrence,
        end=occurrence + timedelta(days=1),
        summary=summary,
        description=summary,
        uid=f"{info.subentry_id}-{year}",
    )
