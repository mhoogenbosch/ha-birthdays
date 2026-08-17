# Birthdays

A Home Assistant integration that tracks birthdays: how many days are left, the
date of the next one, everyone's age, and a calendar you can put on a dashboard.
Everything is recalculated at local midnight.

This is a fork of [Miicroo/ha-birthdays](https://github.com/Miicroo/ha-birthdays)
with a user interface: birthdays are added and edited through **Settings →
Devices & services**, so no YAML is needed. Existing YAML configuration is
imported automatically.

## Installation

### HACS
1. Go to HACS → Integrations
2. Press the dotted menu in the top right corner
3. Choose custom repositories
4. Add `https://github.com/mhoogenbosch/ha-birthdays`, category `Integration`
5. Install and restart Home Assistant

### Manual
Copy `custom_components/birthdays` into your `config/custom_components`
directory and restart Home Assistant.

## Set up

Add the integration through **Settings → Devices & services → Add integration →
Birthdays**. Then use **Add birthday** on the integration page for each person:
their name, date of birth, and optionally an icon.

Every person can be edited or removed afterwards without restarting Home
Assistant.

## Entities

Each person becomes a device with four entities. Entity ids follow the language
of your Home Assistant installation, so a Dutch installation gets
`sensor.frodo_baggins_dagen_tot_verjaardag`.

| Entity | Example | Description |
| --- | --- | --- |
| `sensor.<name>_days_until_birthday` | `14` | Days left until the next birthday |
| `sensor.<name>_birthday` | `2027-09-22` | Date of the next birthday |
| `sensor.<name>_age` | `44` | Current age |
| `binary_sensor.<name>_birthday_today` | `on` | Whether they are celebrating today |

The days-until sensor carries the attributes `date_of_birth` and
`age_at_next_birthday`, as version 1 did.

On top of that there is a single `calendar.birthdays` entity holding an all-day
event for every person, for every year. This works with the standard calendar
card and with cards such as
[calendar-card-pro](https://github.com/alexpfau/calendar-card-pro).

People born on 29 February celebrate on 1 March in non-leap years.

## Automations

Use the binary sensor:

```yaml
automation:
  alias: Happy birthday
  triggers:
    - trigger: state
      entity_id: binary_sensor.frodo_baggins_birthday_today
      to: "on"
  actions:
    - action: notify.mobile_app
      data:
        title: Birthday!
        message: >-
          {{ state_attr('sensor.frodo_baggins_days_until_birthday',
             'age_at_next_birthday') }} years today!
```

Or trigger on the calendar, which fires for everybody and lets you pick the
time of day with an offset:

```yaml
automation:
  alias: Birthdays today
  triggers:
    - trigger: calendar
      entity_id: calendar.birthdays
      event: start
      offset: "09:00:00"
  actions:
    - action: notify.mobile_app
      data:
        title: Birthday!
        message: "{{ trigger.calendar_event.summary }}"
```

The `birthday` event from version 1 still fires at midnight, with the data
`name` and `age`:

```yaml
automation:
  triggers:
    - trigger: event
      event_type: birthday
  actions:
    - action: notify.mobile_app
      data:
        message: "{{ trigger.event.data.name }} turns {{ trigger.event.data.age }} today!"
```

## Dashboard

An auto-entities card listing everyone by days left:

```yaml
type: custom:auto-entities
show_empty: false
card:
  type: entities
  title: Birthdays
filter:
  include:
    - entity_id: sensor.*_days_until_birthday
sort:
  method: state
  numeric: true
```

## Upgrading from version 1

On the first start after upgrading, every birthday in `configuration.yaml` is
imported into the user interface and a repair notification tells you the YAML
can go. Remove the `birthdays:` block and restart.

Two things change:

* The old `birthdays.<name>` entities are replaced by the `sensor.` and
  `binary_sensor.` entities listed above. An integration with a user interface
  cannot own a domain of its own. Dashboards and automations referring to
  `birthdays.*` need to be updated.
* `calendar.birthdays` keeps its entity id and needs no changes.

The `unique_id` and `attributes` options from YAML are imported and keep
working, including templated attributes. They are not editable in the user
interface.

Version 2 also fixes three bugs from version 1: a 29 February date of birth
raised an error in non-leap years, the calendar only produced events for the
current calendar year, and the next upcoming birthday was sorted as text so
`10` came before `9`.
