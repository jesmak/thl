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
from .card import async_add_card_resource, async_remove_card_resource, async_serve_card
from .const import DOMAIN, SUBENTRY_DISEASE, SUBENTRY_ILI
from .coordinator import IliCoordinator, ThlConfigEntry, ThlCoordinator, ThlRuntimeData, WeeklyCoordinator
from .migration import VERSION, async_migrate_to_subentries

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    # Runs before any entry is set up, so the old one-entry-per-disease entries
    # are merged before Home Assistant would try to set them up one by one.
    await async_migrate_to_subentries(hass)
    await async_serve_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ThlConfigEntry) -> bool:
    # Every disease shares one copy of THL's dimensions file.
    await async_add_card_resource(hass)
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
    for coordinator in coordinators.values():
        coordinator.async_write_history()

    # Adding or removing a disease, or changing the language, reloads everything.
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    return True


async def async_update_listener(hass: HomeAssistant, entry: ThlConfigEntry) -> None:
    # Changing the language updates every subentry and then the entry, and each update calls this. One reload covers them
    # all, once the flow has made every update: the listener runs at once, and a reload could finish before the last one.
    if entry.runtime_data.reload_scheduled:
        return
    entry.runtime_data.reload_scheduled = True
    hass.loop.call_soon(hass.config_entries.async_schedule_reload, entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ThlConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Entries from before 2.0 are merged into one in async_setup, which runs first.
    # A newer version than this means Home Assistant was downgraded.
    return entry.version <= VERSION


async def async_remove_entry(hass: HomeAssistant, entry: ThlConfigEntry) -> None:
    await async_remove_card_resource(hass)
