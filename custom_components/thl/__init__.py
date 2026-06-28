from datetime import datetime, timedelta, date
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.thl.const import DOMAIN, CONF_LANGUAGE, CONF_DISEASE_ID
from custom_components.thl.session import ThlSession, ThlNoDataException

_LOGGER = logging.getLogger(__name__)

# How many weeks back to look for published data before giving up. THL publishes
# weekly data with a lag, so the most recently completed week is often not
# available yet right after a week change.
MAX_WEEK_FALLBACK = 4


def previous_iso_week(year: int, week: int) -> tuple[int, int]:
    """Return the (year, week) immediately preceding the given ISO week."""
    if week > 1:
        return year, week - 1
    # Dec 28 always falls in the last ISO week of its year (52 or 53).
    last_week = date(year - 1, 12, 28).isocalendar().week
    return year - 1, last_week


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def async_update_data():
        api = ThlSession(entry.data[CONF_LANGUAGE])
        disease_id = entry.data[CONF_DISEASE_ID]

        today = datetime.now().date().isocalendar()
        # Start from the most recently completed week and step back until THL has
        # published data, so a week change doesn't break the integration before
        # the new week's data is available.
        year, week = previous_iso_week(today.year, today.week)

        data_this_week = None
        for _ in range(MAX_WEEK_FALLBACK):
            try:
                data_this_week = await hass.async_add_executor_job(api.get_data, year, week, disease_id)
                break
            except ThlNoDataException:
                _LOGGER.warning(f"No THL data for year {year} week {week} yet, trying the previous week")
                year, week = previous_iso_week(year, week)

        if data_this_week is None:
            raise UpdateFailed(f"No THL data available within the last {MAX_WEEK_FALLBACK} weeks")

        previous_year, previous_week = previous_iso_week(year, week)
        try:
            data_previous_week = await hass.async_add_executor_job(api.get_data, previous_year, previous_week, disease_id)
        except ThlNoDataException:
            _LOGGER.warning(f"No THL data for year {previous_year} week {previous_week}, change figures unavailable")
            data_previous_week = []

        return {"year": year, "week": week, "current": data_this_week, "previous": data_previous_week}

    coord = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=entry.unique_id or DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=30),
    )

    await coord.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coord

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_forward_entry_unload(entry, "sensor"):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
