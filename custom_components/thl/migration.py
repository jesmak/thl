"""From one config entry per disease (version 1) to one entry with a subentry per disease (version 2).

Every old entry becomes a subentry of a single THL entry, and its entities move
with it. Entity IDs and unique IDs do not change, so history, dashboards,
automations and thl-card keep working. Modelled on the same migration in fmi.
"""

from __future__ import annotations

import logging
from collections import Counter
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_DISEASE_ID, CONF_DISEASE_NAME, CONF_LANGUAGE, DOMAIN, LANGUAGES, SUBENTRY_DISEASE

_LOGGER = logging.getLogger(__name__)

VERSION = 2
TITLE = "THL"


async def async_migrate_to_subentries(hass: HomeAssistant) -> None:
    # The enabled entries come first, so the entry that is kept is an enabled one.
    entries = sorted(hass.config_entries.async_entries(DOMAIN), key=lambda entry: entry.disabled_by is not None)
    old_entries = [entry for entry in entries if entry.version < VERSION]

    if not old_entries:
        return

    parent = next((entry for entry in entries if entry.version >= VERSION), old_entries[0])
    all_disabled = all(entry.disabled_by is not None for entry in entries)
    _LOGGER.info("Moving %s THL config entries into subentries of %s", len(old_entries), parent.title)

    registry = er.async_get(hass)
    devices = dr.async_get(hass)

    for entry in old_entries:
        subentry = subentry_for(entry)
        existing = next((item for item in parent.subentries.values() if item.unique_id == subentry.unique_id), None)

        if existing is not None:
            # A migration cut short left this entry behind after its subentry was
            # made, or the same disease was added twice. Either way its entities
            # belong with the subentry that is already there.
            subentry = existing
        else:
            hass.config_entries.async_add_subentry(parent, subentry)

        for registered in er.async_entries_for_config_entry(registry, entry.entry_id):
            disabled_by = registered.disabled_by
            if disabled_by is er.RegistryEntryDisabler.CONFIG_ENTRY and not all_disabled:
                # Moving to an enabled entry would clear this flag; the user had
                # the old entry disabled, so keep the entity disabled.
                disabled_by = er.RegistryEntryDisabler.USER
            # The unique id stays as it was, so the entity keeps its id and history.
            registry.async_update_entity(
                registered.entity_id,
                config_entry_id=parent.entry_id,
                config_subentry_id=subentry.subentry_id,
                device_id=None,
                disabled_by=disabled_by,
            )

        # The entry's own device; the subentry is given one of its own when its sensor is added again.
        device = devices.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
        if device is not None:
            devices.async_remove_device(device.id)

        if entry.entry_id != parent.entry_id:
            await hass.config_entries.async_remove(entry.entry_id)

    if parent.version < VERSION:
        # Last, because until now the parent's data was still that of its own disease.
        hass.config_entries.async_update_entry(
            parent,
            title=TITLE,
            data={CONF_LANGUAGE: most_common_language(old_entries)},
            unique_id=None,
            version=VERSION,
        )


def subentry_for(entry: ConfigEntry) -> ConfigSubentry:
    disease_id = str(entry.data[CONF_DISEASE_ID])
    return ConfigSubentry(
        data=MappingProxyType({CONF_DISEASE_ID: disease_id, CONF_DISEASE_NAME: entry.data[CONF_DISEASE_NAME]}),
        subentry_type=SUBENTRY_DISEASE,
        title=entry.title,
        unique_id=f"thl_{disease_id}",
    )


def most_common_language(entries: list[ConfigEntry]) -> str:
    """The language of the new entry. Each disease had its own; from now on they share one."""
    languages = Counter(entry.data[CONF_LANGUAGE] for entry in entries if entry.data.get(CONF_LANGUAGE) in LANGUAGES)
    return languages.most_common(1)[0][0] if languages else LANGUAGES[0]
