"""Fetching a disease's weekly case numbers every half hour."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DimensionsCache, ThlClient
from .const import CONF_DISEASE_ID, CONF_DISEASE_NAME, CONF_LANGUAGE, DOMAIN, MAX_WEEK_FALLBACK, UPDATE_INTERVAL
from .exceptions import ThlError
from .statistics import Area, CaseCount, areas, build_values, case_counts, previous_iso_week, week_sid

_LOGGER = logging.getLogger(__name__)


@dataclass
class ThlRuntimeData:
    # One copy of THL's dimensions file, shared by every disease.
    cache: DimensionsCache
    # By subentry id.
    coordinators: dict[str, ThlCoordinator]


type ThlConfigEntry = ConfigEntry[ThlRuntimeData]


@dataclass(frozen=True)
class WeekCases:
    year: int
    week: int
    # The cases of the whole country, which is the sensor's state.
    cases: int | None
    # Each area with its cases and the change from the week before, as the sensor's `values` attribute.
    values: list[dict[str, Any]]


class ThlCoordinator(DataUpdateCoordinator[WeekCases]):
    config_entry: ThlConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ThlConfigEntry, subentry: ConfigSubentry, cache: DimensionsCache
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {subentry.title}",
            update_interval=UPDATE_INTERVAL,
        )
        self.subentry = subentry
        self.language = entry.data[CONF_LANGUAGE]
        self.disease_id = str(subentry.data[CONF_DISEASE_ID])
        self.disease_name = subentry.data[CONF_DISEASE_NAME]
        self._client = ThlClient(hass, self.language)
        self._cache = cache

    async def _async_update_data(self) -> WeekCases:
        try:
            dimensions = await self._cache.get(self._client, self.language)
            of_areas = areas(dimensions, self.language)
            latest = await self._latest_published_week(dimensions, of_areas)
            if latest is None:
                raise UpdateFailed(f"THL has published no data for the last {MAX_WEEK_FALLBACK} weeks")
            year, week, current = latest
            previous = await self._week_before(dimensions, of_areas, year, week)
        except ThlError as err:
            raise UpdateFailed(str(err)) from err

        whole_country = next((count.cases for count in current if count.area.sid == of_areas[0].sid), None)
        return WeekCases(year, week, whole_country, build_values(current, previous))

    async def _latest_published_week(
        self, dimensions: list[Any], of_areas: list[Area]
    ) -> tuple[int, int, list[CaseCount]] | None:
        """The newest week THL has published, starting from the last finished one."""
        today = dt_util.now().date().isocalendar()
        year, week = previous_iso_week(today.year, today.week)
        for _ in range(MAX_WEEK_FALLBACK):
            counts = await self._cases(dimensions, of_areas, year, week)
            if counts is not None:
                return year, week, counts
            _LOGGER.debug("THL has no data for %s week %s yet; looking at the week before", year, week)
            year, week = previous_iso_week(year, week)
        return None

    async def _week_before(self, dimensions: list[Any], of_areas: list[Area], year: int, week: int) -> list[CaseCount]:
        """The week before the latest one, for the change figures. Empty when THL doesn't have it."""
        counts = await self._cases(dimensions, of_areas, *previous_iso_week(year, week))
        return counts or []

    async def _cases(self, dimensions: list[Any], of_areas: list[Area], year: int, week: int) -> list[CaseCount] | None:
        sid = week_sid(dimensions, self.language, year, week)
        if sid is None:
            return None
        data = await self._client.cases(self.disease_id, sid, of_areas[0].sid)
        return case_counts(data, sid, of_areas)
