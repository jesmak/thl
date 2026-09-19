"""Shared fixtures: THL's dimensions and numbers, shaped like the real ones but small."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker, AiohttpClientMockResponse

from custom_components.thl.const import (
    CONF_DISEASE_ID,
    CONF_DISEASE_NAME,
    CONF_LANGUAGE,
    DATA_URL,
    DIMENSIONS_URL,
    DOMAIN,
    ILI_DATA_URL,
    ILI_DIMENSIONS_URL,
    ILI_TITLE,
    ILI_UNIQUE_ID,
    MEASURE_ALL_VISITS,
    MEASURE_CASES,
    MEASURE_ILI_VISITS,
    MEASURE_INCIDENCE,
    SUBENTRY_DISEASE,
    SUBENTRY_ILI,
)

DIMENSIONS_FI_URL = DIMENSIONS_URL.format(language="fi")
DIMENSIONS_EN_URL = DIMENSIONS_URL.format(language="en")
DATA_FI_URL = DATA_URL.format(language="fi")
DATA_EN_URL = DATA_URL.format(language="en")
ILI_DIMENSIONS_FI_URL = ILI_DIMENSIONS_URL.format(language="fi")
ILI_DIMENSIONS_EN_URL = ILI_DIMENSIONS_URL.format(language="en")
ILI_DATA_FI_URL = ILI_DATA_URL.format(language="fi")
ILI_DATA_EN_URL = ILI_DATA_URL.format(language="en")

INFLUENZA = "877719"
ADENOVIRUS = "878000"

# Two weeks of 2026, with the ids THL gives them.
WEEK_37 = "1236829"
WEEK_36 = "1236739"

# The whole country and three wellbeing services counties, with the sids THL uses.
FINLAND = 841988
AREA_SIDS = [837181, 837147, 839479]

# THL publishes everything in both languages; the names differ, the ids do not.
LABELS: dict[str, dict[str, Any]] = {
    "fi": {
        "all_areas": "Kaikki hyvinvointialueet",
        "all_weeks": "Kaikki viikot",
        "year": "Vuosi 2026",
        "week": "Vuosi 2026 Viikko {week}",
        "diseases": {INFLUENZA: "Influenssa", ADENOVIRUS: "Adenovirus"},
        "areas": {
            837181: "Itä-Uudenmaan hyvinvointialue",
            837147: "Keski-Uudenmaan hyvinvointialue",
            839479: "Länsi-Uudenmaan hyvinvointialue",
        },
    },
    "en": {
        "all_areas": "All areas",
        "all_weeks": "All times",
        "year": "Year 2026",
        "week": "Year 2026 Week {week}",
        "diseases": {INFLUENZA: "Influenza", ADENOVIRUS: "Adenovirus"},
        "areas": {
            837181: "East Uusimaa wellbeing services county",
            837147: "Central Uusimaa wellbeing services county",
            839479: "West Uusimaa wellbeing services county",
        },
    },
}


def dimensions(language: str = "fi") -> list[dict[str, Any]]:
    labels = LABELS[language]
    return [
        {
            "id": "nidrreportgroup",
            "children": [
                {
                    "sid": 878152,
                    "label": "Kaikki raportointiryhmät",
                    "children": [{"sid": int(sid), "label": name} for sid, name in labels["diseases"].items()],
                }
            ],
        },
        {
            "id": "yearweek",
            "children": [
                {
                    "sid": 1,
                    "label": labels["all_weeks"],
                    "children": [
                        {
                            "sid": 2,
                            "label": labels["year"],
                            "children": [
                                {"sid": int(WEEK_36), "label": labels["week"].format(week=36)},
                                {"sid": int(WEEK_37), "label": labels["week"].format(week=37)},
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "id": "hva",
            "children": [
                {
                    "sid": FINLAND,
                    "label": labels["all_areas"],
                    "children": [{"sid": sid, "label": labels["areas"][sid]} for sid in AREA_SIDS],
                }
            ],
        },
        {"id": "measure", "children": []},
    ]


def jsonp(language: str = "fi") -> str:
    """The dimensions file, which comes wrapped in a JavaScript call."""
    return f"thl.pivot.loadDimensions({json.dumps(dimensions(language), ensure_ascii=False)});"


DIMENSIONS = dimensions("fi")
DIMENSIONS_JSONP = jsonp("fi")


def cube(
    row: str, column: str, weeks: dict[str, dict[str, dict[int, float | None]]], labels: dict[str, str], sids: list[int]
) -> dict[str, Any]:
    """A data file: a row per area, and a column per week and measure. THL leaves out the empty cells.

    `weeks` holds, by week id, the values of each measure by the position of the area in `sids`.
    """
    measures = list(next(iter(weeks.values())).keys()) if weeks else []
    values: dict[str, str] = {}
    for area_index in range(len(sids)):
        for week_index, week in enumerate(weeks.values()):
            for measure_index, measure in enumerate(measures):
                value = week[measure].get(area_index)
                if value is not None:
                    position = (area_index * len(weeks) + week_index) * len(measures) + measure_index
                    values[str(position)] = str(value)
    return {
        "dataset": {
            "dimension": {
                "id": [row, column, "measure"],
                "size": [len(sids), len(weeks), len(measures)],
                row: {"category": {"index": {str(sid): index for index, sid in enumerate(sids)}, "label": labels}},
                column: {"category": {"index": {week: index for index, week in enumerate(weeks)}}},
                "measure": {"category": {"index": {measure: index for index, measure in enumerate(measures)}}},
            },
            "value": values,
        }
    }


# Week 37: 17 cases in the country, and one area whose cells THL left out.
WEEK_37_CASES = {0: 17, 1: 5, 2: None, 3: 12}
WEEK_37_INCIDENCE = {0: 0.3, 1: 4.7, 2: None, 3: 5.1}
# Week 36: more cases, so the change figures are negative.
WEEK_36_CASES = {0: 20, 1: 4, 2: 0, 3: 16}
WEEK_36_INCIDENCE = {0: 0.4, 1: 3.8, 2: 0.0, 3: 6.8}

CASE_WEEKS: dict[str, dict[str, dict[int, float | None]]] = {
    WEEK_36: {MEASURE_CASES: WEEK_36_CASES, MEASURE_INCIDENCE: WEEK_36_INCIDENCE},
    WEEK_37: {MEASURE_CASES: WEEK_37_CASES, MEASURE_INCIDENCE: WEEK_37_INCIDENCE},
}


def cases(weeks: list[str], language: str = "fi") -> dict[str, Any]:
    """The case numbers of the weeks asked for, oldest first as THL sends them."""
    labels = LABELS[language]
    names = {str(FINLAND): labels["all_areas"], **{str(sid): labels["areas"][sid] for sid in AREA_SIDS}}
    asked = {week: CASE_WEEKS[week] for week in CASE_WEEKS if week in weeks}
    return cube("hva", "yearweek", asked, names, [FINLAND, *AREA_SIDS])


def categories(url: Any, name: str) -> list[str]:
    """The categories a request asks for in one dimension: "yearweek-1236829.1236739." gives both weeks."""
    for value in url.query.getall("column"):
        if value.startswith(f"{name}-"):
            return [part for part in value.removeprefix(f"{name}-").split(".") if part]
    return []


# The flu-like illness cube numbers the areas differently, and names its weeks by their Monday.
ILI_FINLAND = 1200922
ILI_AREA_SIDS = [1200944, 1200918, 1200935]
ILI_WEEK_37 = "1236828"
ILI_WEEK_36 = "1236679"
ALL_AGES = 1200921

# Week 37: 250 visits for flu-like illness out of 2 000 000 in the country, and one area with none.
ILI_WEEKS: dict[str, dict[str, dict[int, float | None]]] = {
    ILI_WEEK_36: {
        MEASURE_ILI_VISITS: {0: 200, 1: 10, 2: 0, 3: 4},
        MEASURE_ALL_VISITS: {0: 1_600_000, 1: 50_000, 2: 40_000, 3: 80_000},
    },
    ILI_WEEK_37: {
        MEASURE_ILI_VISITS: {0: 250, 1: 12, 2: None, 3: 8},
        MEASURE_ALL_VISITS: {0: 2_000_000, 1: 60_000, 2: 45_000, 3: 80_000},
    },
}


def ili_dimensions(language: str = "fi") -> list[dict[str, Any]]:
    labels = LABELS[language]
    return [
        {
            "id": "weeks40",
            "children": [
                {
                    "sid": 294512,
                    "label": labels["all_weeks"],
                    "children": [
                        {
                            "sid": 1131195,
                            "label": "2025-2026",
                            "children": [
                                {"sid": int(ILI_WEEK_36), "label": "2026-08-31"},
                                {"sid": int(ILI_WEEK_37), "label": "2026-09-07"},
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "id": "hva",
            "children": [
                {
                    "sid": ILI_FINLAND,
                    "label": "Kaikki alueet" if language == "fi" else "All areas",
                    "children": [
                        {"sid": sid, "label": labels["areas"][area_sid]}
                        for sid, area_sid in zip(ILI_AREA_SIDS, AREA_SIDS, strict=True)
                    ],
                }
            ],
        },
        {"id": "inf_age", "children": [{"sid": ALL_AGES, "label": "Kaikki iät", "children": []}]},
        {"id": "measure", "children": []},
    ]


def ili_numbers(weeks: list[str]) -> dict[str, Any]:
    asked = {week: ILI_WEEKS[week] for week in ILI_WEEKS if week in weeks}
    return cube("hva", "weeks40", asked, {}, [ILI_FINLAND, *ILI_AREA_SIDS])


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Lets Home Assistant load integrations from custom_components/."""


def by_week(language: str = "fi") -> Callable[..., Awaitable[AiohttpClientMockResponse]]:
    """Answers the data requests with the weeks they ask for, whichever disease is asked about."""

    async def answer(method: str, url: Any, data: Any) -> AiohttpClientMockResponse:
        return AiohttpClientMockResponse(method, url, text=json.dumps(cases(categories(url, "yearweek"), language)))

    return answer


async def ili_answer(method: str, url: Any, data: Any) -> AiohttpClientMockResponse:
    return AiohttpClientMockResponse(method, url, text=json.dumps(ili_numbers(categories(url, "weeks40"))))


@pytest.fixture
def thl(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """THL with both weeks published, in both languages."""
    aioclient_mock.get(DIMENSIONS_FI_URL, text=jsonp("fi"))
    aioclient_mock.get(DIMENSIONS_EN_URL, text=jsonp("en"))
    aioclient_mock.get(DATA_FI_URL, side_effect=by_week("fi"))
    aioclient_mock.get(DATA_EN_URL, side_effect=by_week("en"))
    for language, url in (("fi", ILI_DIMENSIONS_FI_URL), ("en", ILI_DIMENSIONS_EN_URL)):
        aioclient_mock.get(url, text=f"thl.pivot.loadDimensions({json.dumps(ili_dimensions(language))});")
    aioclient_mock.get(ILI_DATA_FI_URL, side_effect=ili_answer)
    aioclient_mock.get(ILI_DATA_EN_URL, side_effect=ili_answer)
    return aioclient_mock


def thl_entry(
    hass: HomeAssistant, *diseases: tuple[str, str], language: str = "fi", ili: bool = False
) -> MockConfigEntry:
    """The THL entry, with a subentry per disease, and one for the flu-like illness visits if asked."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="THL",
        version=2,
        data={CONF_LANGUAGE: language},
        subentries_data=[
            ConfigSubentryData(
                data={CONF_DISEASE_ID: disease_id, CONF_DISEASE_NAME: name},
                subentry_type=SUBENTRY_DISEASE,
                title=f"THL {name}",
                unique_id=f"thl_{disease_id}",
            )
            for disease_id, name in diseases
        ]
        + (
            [
                ConfigSubentryData(
                    data={}, subentry_type=SUBENTRY_ILI, title=ILI_TITLE[language], unique_id=ILI_UNIQUE_ID
                )
            ]
            if ili
            else []
        ),
    )
    entry.add_to_hass(hass)
    return entry
