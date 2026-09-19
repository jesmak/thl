"""The sensors of a disease or of the flu-like illness visits.

A disease has its cases in the whole country, which carries every area in its
attributes as it always has, its incidence in the whole country, and the cases
and incidence of each welfare county. The flu-like illness visits have their
share of all visits in the whole country and in each county.

A new sensor gets the past weeks written into its statistics, so its graphs and
the card's trend have a past from the start.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    AREA_IDS,
    AREA_SHORT_NAMES,
    ATTR_DISEASE_ID,
    ATTR_DISEASE_NAME,
    ATTR_LAST_WEEK,
    ATTR_VALUES,
    ATTRIBUTION,
    DOMAIN,
    ILI_AREA_IDS,
    ILI_UNIQUE_ID,
)
from .coordinator import (
    ALL_VISITS,
    CASES,
    INCIDENCE,
    SHARE,
    VISITS,
    IliCoordinator,
    ThlConfigEntry,
    ThlCoordinator,
    WeeklyCoordinator,
)
from .history import async_import_history
from .statistics import Area

WHOLE_COUNTRY = "finland"
INCIDENCE_UNIT = "per 100 000"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThlConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, coordinator in entry.runtime_data.coordinators.items():
        async_add_entities(entities_of(coordinator), config_subentry_id=subentry_id)


def entities_of(coordinator: WeeklyCoordinator) -> list[SensorEntity]:
    """The sensors of one subentry. The whole country's comes last: its attributes name the others' entity ids."""
    if isinstance(coordinator, ThlCoordinator):
        of_areas = counties(coordinator, AREA_IDS)
        prefix = f"thl_{coordinator.disease_id}"
        entities: list[SensorEntity] = [
            AreaSensor(coordinator, WHOLE_COUNTRY, INCIDENCE, f"{prefix}_incidence", "incidence"),
        ]
        for area in of_areas:
            entities.append(
                AreaSensor(coordinator, area.area_id, CASES, f"{prefix}_{area.area_id}", "area_cases", area)
            )
            entities.append(
                AreaSensor(
                    coordinator, area.area_id, INCIDENCE, f"{prefix}_{area.area_id}_incidence", "area_incidence", area
                )
            )
        return [*entities, ThlSensor(coordinator)]
    if isinstance(coordinator, IliCoordinator):
        of_areas = counties(coordinator, ILI_AREA_IDS)
        return [
            *(
                AreaSensor(coordinator, area.area_id, SHARE, f"{ILI_UNIQUE_ID}_{area.area_id}", "area_share", area)
                for area in of_areas
            ),
            IliSensor(coordinator),
        ]
    return []


def counties(coordinator: WeeklyCoordinator, known: dict[int, str]) -> list[Area]:
    """The welfare counties, known in advance so their sensors exist even while THL can't be reached.

    An area THL has added since is taken from the data as well.
    """
    found = [
        Area(sid, AREA_SHORT_NAMES.get(area_id, {}).get(coordinator.language) or area_id, area_id)
        for sid, area_id in known.items()
        if area_id != WHOLE_COUNTRY
    ]
    ids = {area.area_id for area in found}
    if coordinator.data:
        found.extend(area for area in coordinator.data.areas[1:] if area.area_id not in ids)
    return found


def short_name(area: Area, language: str) -> str:
    return AREA_SHORT_NAMES.get(area.area_id, {}).get(language) or area.name


class WeeklySensor(CoordinatorEntity[WeeklyCoordinator], SensorEntity):
    """One figure of one area in the newest published week."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: WeeklyCoordinator, area_id: str, key: str, unique_id: str) -> None:
        super().__init__(coordinator)
        self._area_id = area_id
        self._key = key
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.subentry.subentry_id)},
            name=coordinator.subentry.title,
            manufacturer="THL",
            entry_type=DeviceEntryType.SERVICE,
        )
        if key == INCIDENCE:
            self._attr_native_unit_of_measurement = INCIDENCE_UNIT
            self._attr_suggested_display_precision = 1
        elif key == SHARE:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_suggested_display_precision = 3
        self._history_pending = not coordinator.history_imported

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.figure(self._area_id, self._key) if data else None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._import_history()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        # THL couldn't be reached when the sensor was added; its past is written once it can.
        if self._history_pending and self.coordinator.data:
            self.hass.async_create_task(self._import_history())

    async def _import_history(self) -> None:
        data = self.coordinator.data
        if not self._history_pending or data is None:
            return
        self._history_pending = False
        points = [(figures.week, figures.areas.get(self._area_id, {}).get(self._key)) for figures in data.weeks]
        await async_import_history(self.hass, self.entity_id, self.native_unit_of_measurement, points)


class AreaSensor(WeeklySensor):
    """The cases or incidence of a disease, or the share of flu-like illness visits, in one area."""

    def __init__(
        self,
        coordinator: WeeklyCoordinator,
        area_id: str,
        key: str,
        unique_id: str,
        translation_key: str,
        area: Area | None = None,
    ) -> None:
        super().__init__(coordinator, area_id, key, unique_id)
        self._attr_translation_key = translation_key
        if area is not None:
            self._attr_translation_placeholders = {"area": short_name(area, coordinator.language)}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {ATTR_LAST_WEEK: data.latest.week.week if data else None}


class SummarySensor(WeeklySensor):
    """The whole country, with every area in its attributes."""

    # The areas change once a week and would fill the database; each area has sensors of its own for history.
    _unrecorded_attributes = frozenset({ATTR_VALUES})
    _attr_name = None

    def entity_id_of(self, unique_id: str) -> str | None:
        return er.async_get(self.hass).async_get_entity_id("sensor", DOMAIN, unique_id)


class ThlSensor(SummarySensor):
    """Last week's cases of one disease in the whole country."""

    coordinator: ThlCoordinator
    _attr_icon = "mdi:virus"

    def __init__(self, coordinator: ThlCoordinator) -> None:
        # The same unique id as in earlier versions, so the entity keeps its id and history.
        super().__init__(coordinator, WHOLE_COUNTRY, CASES, f"thl_{coordinator.disease_id}")

    @property
    def native_value(self) -> int | None:
        value = super().native_value
        return None if value is None else int(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            ATTR_LAST_WEEK: data.latest.week.week if data else None,
            ATTR_VALUES: self._values() if data else [],
            ATTR_DISEASE_ID: self.coordinator.disease_id,
            ATTR_DISEASE_NAME: self.coordinator.disease_name,
        }

    def _values(self) -> list[dict[str, Any]]:
        """Each area with last week's cases and incidence, the change from the week before, and its sensors."""
        data = self.coordinator.data
        previous = data.previous
        prefix = f"thl_{self.coordinator.disease_id}"
        result = []
        for area in data.areas:
            cases = int(data.figure(area.area_id, CASES) or 0)
            entry: dict[str, Any] = {
                "name": area.name,
                "amount_last_week": cases,
                "area_id": area.area_id,
                "incidence_last_week": data.figure(area.area_id, INCIDENCE),
            }
            if previous is not None:
                before = int(data.figure(area.area_id, CASES, previous) or 0)
                entry["amount_two_weeks_ago"] = before
                entry["change_in_numbers"] = cases - before
                # As earlier versions wrote it: a rounded string, or 0 when there was nothing to compare with.
                entry["change_percentage"] = 0 if before == 0 else f"{(cases - before) / before * 100:.0f}"
                entry["incidence_two_weeks_ago"] = data.figure(area.area_id, INCIDENCE, previous)
            if area.area_id == WHOLE_COUNTRY:
                entry["entity_id"] = self.entity_id
                entry["incidence_entity_id"] = self.entity_id_of(f"{prefix}_incidence")
            else:
                entry["entity_id"] = self.entity_id_of(f"{prefix}_{area.area_id}")
                entry["incidence_entity_id"] = self.entity_id_of(f"{prefix}_{area.area_id}_incidence")
            result.append(entry)
        return result


class IliSensor(SummarySensor):
    """Flu-like illness visits as a share of all primary care visits in the whole country."""

    _attr_icon = "mdi:stethoscope"

    def __init__(self, coordinator: IliCoordinator) -> None:
        super().__init__(coordinator, WHOLE_COUNTRY, SHARE, ILI_UNIQUE_ID)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            ATTR_LAST_WEEK: data.latest.week.week if data else None,
            ATTR_VALUES: self._values() if data else [],
        }

    def _values(self) -> list[dict[str, Any]]:
        """Each area with last week's share and visits, the share the week before, and its sensor."""
        data = self.coordinator.data
        previous = data.previous
        result = []
        for area in data.areas:
            entry: dict[str, Any] = {
                "name": area.name,
                "area_id": area.area_id,
                "share_last_week": data.figure(area.area_id, SHARE),
                "visits_last_week": data.figure(area.area_id, VISITS),
                "all_visits_last_week": data.figure(area.area_id, ALL_VISITS),
            }
            if previous is not None:
                entry["share_two_weeks_ago"] = data.figure(area.area_id, SHARE, previous)
            entry["entity_id"] = (
                self.entity_id
                if area.area_id == WHOLE_COUNTRY
                else self.entity_id_of(f"{ILI_UNIQUE_ID}_{area.area_id}")
            )
            result.append(entry)
        return result
