"""Shared fixtures: THL's dimensions and case numbers, shaped like the real ones but small."""

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
    SUBENTRY_DISEASE,
)

DIMENSIONS_FI_URL = DIMENSIONS_URL.format(language="fi")
DIMENSIONS_EN_URL = DIMENSIONS_URL.format(language="en")
DATA_FI_URL = DATA_URL.format(language="fi")
DATA_EN_URL = DATA_URL.format(language="en")

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


def cases(week: str, values: dict[int, int | None], language: str = "fi") -> dict[str, Any]:
    """A data file: one column for the week, one row per area. THL leaves out the cells with no cases."""
    labels = LABELS[language]
    sids = [FINLAND, *AREA_SIDS]
    names = {str(FINLAND): labels["all_areas"], **{str(sid): labels["areas"][sid] for sid in AREA_SIDS}}
    return {
        "dataset": {
            "dimension": {
                "id": ["hva", "yearweek"],
                "size": [len(sids), 1],
                "hva": {"category": {"index": {str(sid): index for index, sid in enumerate(sids)}, "label": names}},
                "yearweek": {"category": {"index": {week: 0}, "label": {week: labels["week"].format(week=week[-2:])}}},
            },
            "value": {str(index): str(value) for index, value in values.items() if value is not None},
        }
    }


# Week 37: 17 cases in the country, and one area whose cell THL left out.
WEEK_37_CASES = {0: 17, 1: 5, 2: None, 3: 12}
# Week 36: more cases, so the change figures are negative.
WEEK_36_CASES = {0: 20, 1: 4, 2: 0, 3: 16}

CASES_WEEK_37 = cases(WEEK_37, WEEK_37_CASES)
CASES_WEEK_36 = cases(WEEK_36, WEEK_36_CASES)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Lets Home Assistant load integrations from custom_components/."""


def by_week(language: str = "fi") -> Callable[..., Awaitable[AiohttpClientMockResponse]]:
    """Answers the data requests by the week they ask for, whichever disease is asked about."""
    weeks = {WEEK_37: cases(WEEK_37, WEEK_37_CASES, language), WEEK_36: cases(WEEK_36, WEEK_36_CASES, language)}

    async def answer(method: str, url: Any, data: Any) -> AiohttpClientMockResponse:
        body = weeks.get(url.query["column"].removeprefix("yearweek-"))
        if body is None:
            return AiohttpClientMockResponse(method, url, status=404)
        return AiohttpClientMockResponse(method, url, text=json.dumps(body))

    return answer


@pytest.fixture
def thl(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """THL with both weeks published, in both languages."""
    aioclient_mock.get(DIMENSIONS_FI_URL, text=jsonp("fi"))
    aioclient_mock.get(DIMENSIONS_EN_URL, text=jsonp("en"))
    aioclient_mock.get(DATA_FI_URL, side_effect=by_week("fi"))
    aioclient_mock.get(DATA_EN_URL, side_effect=by_week("en"))
    return aioclient_mock


def thl_entry(hass: HomeAssistant, *diseases: tuple[str, str], language: str = "fi") -> MockConfigEntry:
    """The THL entry, with a subentry per disease."""
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
        ],
    )
    entry.add_to_hass(hass)
    return entry
