from datetime import datetime, timedelta, date
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.thl_covid.const import DOMAIN, CONF_LANGUAGE
from custom_components.thl_covid.session import CovidSession

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def async_update_data():
        api = CovidSession(entry.data[CONF_LANGUAGE])

        current_year = datetime.now().date().isocalendar().year
        current_week = datetime.now().date().isocalendar().week

        week = current_week - 1 if current_week > 1 else date(current_year - 1, 12, 28).isocalendar().week
        year = current_year if week > 1 else current_year - 1
        data_this_week = await hass.async_add_executor_job(api.get_data, year, week)

        previous_week = week - 1 if week > 1 else date(year - 1, 12, 28).isocalendar().week
        previous_week_year = year if week > 1 else year - 1
        data_previous_week = await hass.async_add_executor_job(api.get_data, previous_week_year, previous_week)

        return [data_this_week, data_previous_week]

    coord = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=entry.unique_id or DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=30),
    )

    await coord.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coord

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_forward_entry_unload(entry, "sensor"):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
