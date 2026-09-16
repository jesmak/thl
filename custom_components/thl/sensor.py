"""The sensor of a disease: last week's cases in the whole country, with the areas in its attributes."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DISEASE_ID,
    ATTR_DISEASE_NAME,
    ATTR_LAST_WEEK,
    ATTR_VALUES,
    ATTRIBUTION,
    DOMAIN,
)
from .coordinator import ThlConfigEntry, ThlCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThlConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, coordinator in entry.runtime_data.coordinators.items():
        async_add_entities([ThlSensor(coordinator)], config_subentry_id=subentry_id)


class ThlSensor(CoordinatorEntity[ThlCoordinator], SensorEntity):
    """Last week's cases of one disease in the whole country."""

    # The areas change once a week and would fill the database; the state is history enough.
    _unrecorded_attributes = frozenset({ATTR_VALUES})
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:virus"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ThlCoordinator) -> None:
        super().__init__(coordinator)
        # The same unique id as in earlier versions, so the entity keeps its id and history.
        self._attr_unique_id = f"thl_{coordinator.disease_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.subentry.subentry_id)},
            name=coordinator.subentry.title,
            manufacturer="THL",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.cases if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            ATTR_LAST_WEEK: data.week if data else None,
            ATTR_VALUES: data.values if data else [],
            ATTR_DISEASE_ID: self.coordinator.disease_id,
            ATTR_DISEASE_NAME: self.coordinator.disease_name,
        }
