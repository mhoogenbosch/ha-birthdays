"""Constants for the Birthdays integration."""

from typing import Final

DOMAIN: Final = "birthdays"
DOMAIN_FRIENDLY_NAME: Final = "Birthdays"

# Subentry type: one subentry per person.
SUBENTRY_TYPE_BIRTHDAY: Final = "birthday"

CONF_NAME: Final = "name"
CONF_DATE_OF_BIRTH: Final = "date_of_birth"
CONF_ICON: Final = "icon"
CONF_ATTRIBUTES: Final = "attributes"
CONF_BIRTHDAYS: Final = "birthdays"
CONF_GLOBAL_CONFIG: Final = "config"
CONF_AGE_AT_NEXT_BIRTHDAY: Final = "age_at_next_birthday"
CONF_UNIQUE_ID: Final = "unique_id"

DEFAULT_ICON: Final = "mdi:cake-variant"

# Fired on the day itself, kept for backwards compatibility with YAML users.
EVENT_BIRTHDAY: Final = "birthday"

ISSUE_DEPRECATED_YAML: Final = "deprecated_yaml"
