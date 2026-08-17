"""Coordinator that recalculates all birthdays once per day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.template import Template, is_template_string, render_complex
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ATTRIBUTES,
    CONF_DATE_OF_BIRTH,
    CONF_ICON,
    CONF_NAME,
    DEFAULT_ICON,
    DOMAIN,
    EVENT_BIRTHDAY,
    SUBENTRY_TYPE_BIRTHDAY,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

type BirthdaysConfigEntry = ConfigEntry[BirthdaysCoordinator]


def occurrence_in_year(date_of_birth: date, year: int) -> date:
    """Return the date the birthday is celebrated in the given year.

    People born on 29 February celebrate on 1 March in non-leap years, which is
    also how Dutch law treats the date for coming of age.
    """
    try:
        return date(year, date_of_birth.month, date_of_birth.day)
    except ValueError:
        return date(year, 3, 1)


@dataclass(slots=True)
class BirthdayInfo:
    """Calculated state for a single person."""

    subentry_id: str
    name: str
    date_of_birth: date
    icon: str
    next_birthday: date
    days_until: int
    age_now: int
    age_at_next_birthday: int
    attributes: dict[str, Any]

    @property
    def is_birthday_today(self) -> bool:
        """Return True if this person has their birthday today."""
        return self.days_until == 0


class BirthdaysCoordinator(DataUpdateCoordinator[dict[str, BirthdayInfo]]):
    """Recalculate every birthday at local midnight.

    There is nothing to poll: the only thing that changes the state is the
    local date rolling over, so we listen for that instead of using an
    update_interval.
    """

    config_entry: BirthdaysConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: BirthdaysConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=None,
        )
        # Guards against firing the birthday event twice on the same day, for
        # example when the config entry is reloaded after adding a person.
        self._events_fired: dict[str, date] = {}
        self._templates: dict[str, dict[str, Template]] = {}

    @callback
    def async_setup_midnight_listener(self) -> None:
        """Schedule a refresh at every local midnight."""
        self.config_entry.async_on_unload(
            async_track_time_change(
                self.hass, self._handle_midnight, hour=0, minute=0, second=0
            )
        )

    async def _handle_midnight(self, _now: datetime) -> None:
        """Recalculate and fire events for anyone with a birthday today."""
        await self.async_refresh()
        self.async_fire_birthday_events()

    @callback
    def async_fire_birthday_events(self) -> None:
        """Fire the `birthday` event for everyone celebrating today."""
        today = dt_util.start_of_local_day().date()
        for info in self.data.values():
            if not info.is_birthday_today:
                continue
            if self._events_fired.get(info.subentry_id) == today:
                continue
            self._events_fired[info.subentry_id] = today
            self.hass.bus.async_fire(
                event_type=EVENT_BIRTHDAY,
                event_data={"name": info.name, "age": info.age_at_next_birthday},
            )

    async def _async_update_data(self) -> dict[str, BirthdayInfo]:
        """Recalculate the state of every person in the config entry."""
        today = dt_util.start_of_local_day().date()
        result: dict[str, BirthdayInfo] = {}

        for subentry_id, subentry in self.config_entry.subentries.items():
            if subentry.subentry_type != SUBENTRY_TYPE_BIRTHDAY:
                continue

            data = subentry.data
            date_of_birth = _as_date(data[CONF_DATE_OF_BIRTH])

            next_birthday = occurrence_in_year(date_of_birth, today.year)
            if next_birthday < today:
                next_birthday = occurrence_in_year(date_of_birth, today.year + 1)

            age_at_next_birthday = next_birthday.year - date_of_birth.year

            result[subentry_id] = BirthdayInfo(
                subentry_id=subentry_id,
                name=data[CONF_NAME],
                date_of_birth=date_of_birth,
                icon=data.get(CONF_ICON) or DEFAULT_ICON,
                next_birthday=next_birthday,
                days_until=(next_birthday - today).days,
                age_now=age_at_next_birthday - 1
                if next_birthday > today
                else age_at_next_birthday,
                age_at_next_birthday=age_at_next_birthday,
                attributes=self._render_attributes(subentry_id, data),
            )

        return result

    def _render_attributes(self, subentry_id: str, data: Any) -> dict[str, Any]:
        """Render the optional extra attributes carried over from YAML."""
        configured: dict[str, Any] = dict(data.get(CONF_ATTRIBUTES) or {})
        if not configured:
            self._templates.pop(subentry_id, None)
            return {}

        templates = self._templates.setdefault(subentry_id, {})
        rendered: dict[str, Any] = {}

        for key, value in configured.items():
            if not isinstance(value, str) or not is_template_string(value):
                rendered[key] = value
                continue
            if key not in templates:
                templates[key] = Template(template=value, hass=self.hass)
            try:
                rendered[key] = render_complex(templates[key])
            except Exception:
                _LOGGER.exception(
                    "Error rendering attribute '%s' for %s", key, data.get(CONF_NAME)
                )
                rendered[key] = None

        return rendered


def _as_date(value: Any) -> date:
    """Coerce a stored value into a date.

    Config entry data round-trips through JSON, so a date becomes a string.
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))
