"""THL disease statistics: the weekly case numbers of a disease, by wellbeing services county.

One config entry holds the language. Every disease being followed is a config
subentry with its own coordinator and sensors, and so are the flu-like illness
visits when they are followed.
"""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import DimensionsCache
from .const import CONF_HISTORY_IMPORTED, DOMAIN, SUBENTRY_DISEASE, SUBENTRY_ILI
from .coordinator import IliCoordinator, ThlConfigEntry, ThlCoordinator, ThlRuntimeData, WeeklyCoordinator
from .history import recording
from .migration import VERSION, async_migrate_to_subentries

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    # Runs before any entry is set up, so the old one-entry-per-disease entries
    # are merged before Home Assistant would try to set them up one by one.
    await async_migrate_to_subentries(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ThlConfigEntry) -> bool:
    # Every disease shares one copy of THL's dimensions file.
    cache = DimensionsCache()
    kinds: dict[str, type[WeeklyCoordinator]] = {SUBENTRY_DISEASE: ThlCoordinator, SUBENTRY_ILI: IliCoordinator}
    coordinators = {
        subentry.subentry_id: kinds[subentry.subentry_type](hass, entry, subentry, cache)
        for subentry in entry.subentries.values()
        if subentry.subentry_type in kinds
    }
    entry.runtime_data = ThlRuntimeData(cache, coordinators)

    # A disease that cannot be read becomes unavailable and keeps retrying; it
    # does not stop the others from being set up.
    await asyncio.gather(*(coordinator.async_refresh() for coordinator in coordinators.values()))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _remember_history_was_imported(hass, entry)

    # Adding or removing a disease, or changing the language, reloads everything. Added last, so noting
    # the flag above does not reload the entry that is still being set up.
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    return True


async def async_update_listener(hass: HomeAssistant, entry: ThlConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ThlConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Entries from before 2.0 are merged into one in async_setup, which runs first.
    # A newer version than this means Home Assistant was downgraded.
    return entry.version <= VERSION


def _remember_history_was_imported(hass: HomeAssistant, entry: ThlConfigEntry) -> None:
    """Note on each subentry that its sensors have been given their past.

    The sensors write it as they are added, when THL could be read. Without the note every
    start would ask the recorder about every sensor again. Without a recorder nothing was written.
    """
    if not recording(hass):
        return
    for coordinator in entry.runtime_data.coordinators.values():
        if coordinator.history_imported or coordinator.data is None:
            continue
        coordinator.history_imported = True
        hass.config_entries.async_update_subentry(
            entry, coordinator.subentry, data={**coordinator.subentry.data, CONF_HISTORY_IMPORTED: True}
        )
