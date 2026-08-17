# Changelog

All notable changes to this fork are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [2.0.0-mh.2] - 2026-08-17

### Fixed
- The days-until sensor rendered as `352.00 d`. Duration is a convertible
  device class, for which Home Assistant assigns a default display precision of
  2; the sensor now suggests 0 decimals.

## [2.0.0-mh.1] - 2026-08-17

First release of the fork. The integration is now configured through the user
interface instead of YAML.

### Added
- Config flow with one config entry and a **config subentry per person**, so
  birthdays are added, edited and removed through Settings → Devices & services
  without restarting Home Assistant.
- Every person is a device with four entities: `sensor.<name>_days_until_birthday`,
  `sensor.<name>_birthday` (`device_class: date`), `sensor.<name>_age` and
  `binary_sensor.<name>_birthday_today`.
- Entity ids are suggested in the language of the installation, so a Dutch
  installation gets `sensor.<name>_dagen_tot_verjaardag` rather than the English
  name Home Assistant would derive by default.
- Automatic import of the existing YAML configuration (both the list and the
  dict format, including `unique_id`, `attributes` and global attributes), plus
  a repair issue telling the user the YAML block can be removed.
- Test suite covering the flows, the calculations, the daily rollover and the
  calendar (27 tests, 94% coverage), pinned to `homeassistant==2026.8.2`.

### Fixed
- A date of birth of 29 February raised `ValueError` in non-leap years and took
  the whole integration down. Those birthdays are now celebrated on 1 March.
- The calendar only generated events for the current calendar year, so a
  dashboard looking ahead across new year's eve showed nothing. Events are now
  generated for every year in the requested range.
- The next upcoming birthday was picked by sorting the state as text, so a
  birthday in 10 days sorted before one in 9 days.
- Birthdays were recalculated by counting seconds to midnight, which drifts
  around daylight saving time. The integration now listens for local midnight.

### Changed
- The daily recalculation runs through a `DataUpdateCoordinator`.
- `manifest.json` declares `single_config_entry`, `integration_type: service`
  and `iot_class: calculated`.
- Linting moved from flake8/black to ruff.

### Removed
- **Breaking:** the `birthdays.<name>` entities. An integration configured
  through the user interface cannot register entities in a domain of its own.
  Their replacements are listed under Added; `calendar.birthdays` keeps its
  entity id.
- The translated `day`/`days` unit of measurement. The days-until sensor is a
  duration sensor in days, which Home Assistant formats itself.

[Unreleased]: https://github.com/mhoogenbosch/ha-birthdays/compare/v2.0.0-mh.2...HEAD
[2.0.0-mh.2]: https://github.com/mhoogenbosch/ha-birthdays/compare/v2.0.0-mh.1...v2.0.0-mh.2
[2.0.0-mh.1]: https://github.com/mhoogenbosch/ha-birthdays/compare/v1.3.0...v2.0.0-mh.1
