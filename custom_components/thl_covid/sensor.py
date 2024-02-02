import logging
from datetime import datetime, date

from homeassistant.components.sensor import SensorStateClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

from .const import DOMAIN, STR_ALL_AREAS, CONF_LANGUAGE, AREA_IDS

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Data provided by Finnish Institute for Health and Welfare (THL)"

ATTR_VALUES = "values"
ATTR_NAME = "name"
ATTR_AMOUNT_LAST_WEEK = "amount_last_week"
ATTR_AMOUNT_TWO_WEEKS_AGO = "amount_two_weeks_ago"
ATTR_CHANGE_IN_NUMBERS = "change_in_numbers"
ATTR_CHANGE_PERCENTAGE = "change_percentage"
ATTR_LAST_WEEK = "last_week"
ATTR_AREA_ID = "area_id"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    lang = entry.data.get(CONF_LANGUAGE)
    sensor = CovidSensor(coord, lang)
    async_add_entities([sensor], update_before_add=True)


class CovidSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, lang: str):
        super().__init__(coordinator)
        self._attr_attribution = ATTRIBUTION
        self._attr_icon = "mdi:virus"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_name = "THL Covid stats"
        self._attr_unique_id = "thl_covid"
        self.lang = lang

        if len(coordinator.data) > 0:
            _LOGGER.debug(f"Coordinator data sizes: current={len(coordinator.data[0])}, previous={len(coordinator.data[1])}")
        else:
            _LOGGER.debug("Coordinator data is empty")

        self._attr_extra_state_attributes = {}
        self.update_attributes()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.update_attributes()
        self.async_write_ha_state()

    def update_attributes(self):
        data = []

        for current_value in self.coordinator.data[0]:
            entry = {ATTR_NAME: current_value["name"], ATTR_AMOUNT_LAST_WEEK: int(current_value["value"]), ATTR_AREA_ID: AREA_IDS[current_value["sid"]]}
            previous_value = next(
                (entry for entry in self.coordinator.data[1] if entry["name"] == current_value["name"]), None)
            if previous_value is not None:
                entry[ATTR_AMOUNT_TWO_WEEKS_AGO] = int(previous_value["value"])
                entry[ATTR_CHANGE_IN_NUMBERS] = int(current_value["value"]) - int(previous_value["value"])
                entry[ATTR_CHANGE_PERCENTAGE] = 0 if int(previous_value["value"]) == 0 else "{:.0f}".format((int(current_value["value"]) - int(previous_value["value"])) / int(previous_value[
                    "value"]) * 100)
            data.append(entry)

        current_week = datetime.now().date().isocalendar().week
        current_year = datetime.now().date().isocalendar().year
        week = current_week - 1 if current_week > 1 else date(current_year - 1, 12, 28).isocalendar().week

        self._attr_extra_state_attributes[ATTR_LAST_WEEK] = week
        self._attr_extra_state_attributes[ATTR_VALUES] = data

    @property
    def native_value(self):
        value = next((entry for entry in self.coordinator.data[0] if entry["name"] == STR_ALL_AREAS[self.lang]), None)
        return int(value["value"]) if value is not None else None
