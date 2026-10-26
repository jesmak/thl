"""Fetching THL's weekly numbers every half hour: a disease's cases, or the flu-like illness visits.

Each refresh reads the newest week with figures and the weeks before it in one
request. The newest two give the sensors' states and the change figures; all of
them are kept in the sensors' statistics as THL has them, so their graphs have a past.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DimensionsCache, ThlClient
from .const import (
    CONF_DISEASE_ID,
    CONF_DISEASE_NAME,
    CONF_LANGUAGE,
    DATA_URL,
    DIMENSIONS_URL,
    DOMAIN,
    HISTORY_WEEKS,
    ILI_ALL_AREAS,
    ILI_AREA_IDS,
    ILI_DATA_URL,
    ILI_DIMENSIONS_URL,
    MAX_WEEK_FALLBACK,
    MEASURE_ALL_VISITS,
    MEASURE_CASES,
    MEASURE_ILI_VISITS,
    MEASURE_INCIDENCE,
    UPDATE_INTERVAL,
)
from .exceptions import ThlError
from .history import WRITE_AGAIN_AFTER, async_write_history, recording
from .statistics import (
    Area,
    Cube,
    Week,
    areas,
    case_weeks,
    first_child_sid,
    ili_weeks,
    is_week_before,
    last_finished_week,
)

_LOGGER = logging.getLogger(__name__)

WEEK = timedelta(weeks=1)

# The figures of each kind of sensor. Cases and incidence are a disease's; the share is the flu-like illness visits'.
CASES = "cases"
INCIDENCE = "incidence"
SHARE = "share"
VISITS = "visits"
ALL_VISITS = "all_visits"


@dataclass
class ThlRuntimeData:
    # One copy of each dimensions file, shared by every coordinator.
    cache: DimensionsCache
    # By subentry id.
    coordinators: dict[str, WeeklyCoordinator]
    reload_scheduled: bool = False


type ThlConfigEntry = ConfigEntry[ThlRuntimeData]


@dataclass(frozen=True)
class WeekFigures:
    week: Week
    # By area id: that area's figures in the week, such as {"cases": 17, "incidence": 0.3}.
    areas: dict[str, dict[str, float | None]]


@dataclass(frozen=True)
class Weekly:
    # The whole country first, then the welfare counties.
    areas: list[Area]
    # Oldest first. The last one is the newest week with figures.
    weeks: list[WeekFigures]

    @property
    def latest(self) -> WeekFigures:
        return self.weeks[-1]

    @property
    def previous(self) -> WeekFigures | None:
        """The week before the newest, when THL has it."""
        if len(self.weeks) < 2 or not is_week_before(self.weeks[-2].week, self.latest.week):
            return None
        return self.weeks[-2]

    @property
    def whole_country(self) -> Area:
        return self.areas[0]

    def figure(self, area_id: str, key: str, figures: WeekFigures | None = None) -> float | None:
        return (figures or self.latest).areas.get(area_id, {}).get(key)


class WeeklyCoordinator(DataUpdateCoordinator[Weekly]):
    """The newest weeks of one cube, for every area."""

    config_entry: ThlConfigEntry
    # The figures that get a sensor for each area.
    keys: tuple[str, ...] = ()
    dimensions_url: str = ""
    data_url: str = ""

    def __init__(self, hass: HomeAssistant, entry: ThlConfigEntry, subentry: ConfigSubentry, cache: DimensionsCache) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {subentry.title}",
            update_interval=UPDATE_INTERVAL,
        )
        self.subentry = subentry
        self.language: str = entry.data[CONF_LANGUAGE]
        # The sensors added, whose past is written: entity id → unit, area id and figure.
        self.history_targets: dict[str, tuple[str | None, str, str]] = {}
        # The figures last written into the statistics.
        self._history_of: Weekly | None = None
        self._write_again: CALLBACK_TYPE | None = None
        self._client = ThlClient(hass, self.language)
        self._cache = cache

    async def _async_update_data(self) -> Weekly:
        newest = last_finished_week(dt_util.now().date())
        try:
            dimensions = await self._cache.get(self._client, self.dimensions_url)
            of_areas, weeks = self._categories(dimensions, newest)
            # THL publishes with a lag, so the newest finished week is often missing; a few weeks back is fine.
            oldest_allowed = date.fromisocalendar(*newest, 1) - (MAX_WEEK_FALLBACK - 1) * WEEK
            recent = [week for week in weeks if week.monday >= oldest_allowed]
            if not recent:
                raise UpdateFailed(f"THL has published no data for the last {MAX_WEEK_FALLBACK} weeks")
            cube = Cube(await self._client.data(self.data_url, self._params(dimensions, of_areas[0], weeks)))
        except ThlError as err:
            raise UpdateFailed(str(err)) from err
        latest = next((week for week in recent if self._has_figures(cube, of_areas[0], week)), None)
        if latest is None:
            raise UpdateFailed(f"THL has published no data for the last {MAX_WEEK_FALLBACK} weeks")
        # The history kept is counted back from the newest week with figures.
        kept = [week for week in weeks if week.monday <= latest.monday and latest.monday - week.monday < HISTORY_WEEKS * WEEK]

        # Oldest first.
        return Weekly(
            of_areas,
            [WeekFigures(week, {area.area_id: self._figures(cube, area, week) for area in of_areas}) for week in reversed(kept)],
        )

    @callback
    def async_update_listeners(self) -> None:
        super().async_update_listeners()
        # THL couldn't be read when the sensors were added, or has changed a figure since.
        if self.history_targets:
            self.async_write_history()

    @callback
    def async_write_history(self) -> None:
        """Gives each week in the statistics of every sensor added THL's figure for it, once a setup and whenever THL changes one."""
        if self.data is None or self.data == self._history_of or not recording(self.hass):
            return
        self._history_of = self.data
        self._start_writing(self.data)
        if self._write_again is not None:
            self._write_again()
        self._write_again = async_call_later(self.hass, WRITE_AGAIN_AFTER, self._async_write_again)

    @callback
    def _async_write_again(self, _now: datetime) -> None:
        """Writes the same figures once more, for the hour the recorder was keeping when they changed."""
        self._write_again = None
        if self._history_of is not None and recording(self.hass):
            self._start_writing(self._history_of)

    @callback
    def _start_writing(self, data: Weekly) -> None:
        self.config_entry.async_create_background_task(self.hass, self._write_history(data), f"{self.name} history")

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
        if self._write_again is not None:
            self._write_again()
            self._write_again = None

    async def _write_history(self, data: Weekly) -> None:
        sensors = [
            (entity_id, unit, [(figures.week, figures.areas.get(area_id, {}).get(key)) for figures in data.weeks])
            for entity_id, (unit, area_id, key) in self.history_targets.items()
        ]
        try:
            await async_write_history(self.hass, sensors)
        except Exception:
            # The sensors work without their past, so a recorder that fails is only logged.
            _LOGGER.exception("Writing the past weeks of %s into the statistics failed", self.subentry.title)

    def _categories(self, dimensions: list[Any], newest: tuple[int, int]) -> tuple[list[Area], list[Week]]:
        """The areas, and the listed weeks newest first."""
        raise NotImplementedError

    def _params(self, dimensions: list[Any], whole_country: Area, weeks: list[Week]) -> list[tuple[str, str]]:
        raise NotImplementedError

    def _has_figures(self, cube: Cube, whole_country: Area, week: Week) -> bool:
        """Whether THL has filled in the week, rather than only listed it."""
        return True

    def _figures(self, cube: Cube, area: Area, week: Week) -> dict[str, float | None]:
        raise NotImplementedError


class ThlCoordinator(WeeklyCoordinator):
    """One disease: its cases and incidence per 100 000 people."""

    keys = (CASES, INCIDENCE)
    dimensions_url = DIMENSIONS_URL
    data_url = DATA_URL

    def __init__(self, hass: HomeAssistant, entry: ThlConfigEntry, subentry: ConfigSubentry, cache: DimensionsCache) -> None:
        super().__init__(hass, entry, subentry, cache)
        self.disease_id = str(subentry.data[CONF_DISEASE_ID])
        self.disease_name: str = subentry.data[CONF_DISEASE_NAME]

    def _categories(self, dimensions: list[Any], newest: tuple[int, int]) -> tuple[list[Area], list[Week]]:
        return areas(dimensions, self.language), case_weeks(dimensions, self.language, newest, HISTORY_WEEKS + MAX_WEEK_FALLBACK)

    def _params(self, dimensions: list[Any], whole_country: Area, weeks: list[Week]) -> list[tuple[str, str]]:
        return [
            ("row", f"hva-{whole_country.sid}"),
            ("column", "yearweek-" + "".join(f"{week.sid}." for week in weeks)),
            ("column", f"measure-{MEASURE_CASES}.{MEASURE_INCIDENCE}."),
            ("filter", f"nidrreportgroup-{self.disease_id}"),
        ]

    def _figures(self, cube: Cube, area: Area, week: Week) -> dict[str, float | None]:
        # THL leaves out the cells of the areas with no cases, and they count as zero.
        cases = cube.value(hva=area.sid, yearweek=week.sid, measure=MEASURE_CASES)
        incidence = cube.value(hva=area.sid, yearweek=week.sid, measure=MEASURE_INCIDENCE)
        return {CASES: int(cases or 0), INCIDENCE: incidence or 0.0}


class IliCoordinator(WeeklyCoordinator):
    """Flu-like illness visits in primary care, as a share of all visits."""

    keys = (SHARE,)
    dimensions_url = ILI_DIMENSIONS_URL
    data_url = ILI_DATA_URL

    def _categories(self, dimensions: list[Any], newest: tuple[int, int]) -> tuple[list[Area], list[Week]]:
        return areas(dimensions, self.language, ILI_ALL_AREAS, ILI_AREA_IDS), ili_weeks(
            dimensions, newest, HISTORY_WEEKS + MAX_WEEK_FALLBACK
        )

    def _params(self, dimensions: list[Any], whole_country: Area, weeks: list[Week]) -> list[tuple[str, str]]:
        return [
            ("row", f"hva-{whole_country.sid}"),
            ("column", "weeks40-" + "".join(f"{week.sid}." for week in weeks)),
            ("column", f"measure-{MEASURE_ILI_VISITS}.{MEASURE_ALL_VISITS}."),
            # Every age group together.
            ("filter", f"inf_age-{first_child_sid(dimensions, 'inf_age')}"),
        ]

    def _has_figures(self, cube: Cube, whole_country: Area, week: Week) -> bool:
        # THL lists the weeks ahead of the data with zero visits of any kind in the whole country.
        return bool(cube.value(hva=whole_country.sid, weeks40=week.sid, measure=MEASURE_ALL_VISITS))

    def _figures(self, cube: Cube, area: Area, week: Week) -> dict[str, float | None]:
        visits = int(cube.value(hva=area.sid, weeks40=week.sid, measure=MEASURE_ILI_VISITS) or 0)
        all_visits = int(cube.value(hva=area.sid, weeks40=week.sid, measure=MEASURE_ALL_VISITS) or 0)
        # Without any visits there is no share to speak of.
        share = round(visits / all_visits * 100, 4) if all_visits else None
        return {SHARE: share, VISITS: visits, ALL_VISITS: all_visits}
