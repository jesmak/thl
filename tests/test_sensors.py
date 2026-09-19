"""The sensors of each welfare county, the whole country's incidence, and the flu-like illness visits."""

from __future__ import annotations

from datetime import UTC, datetime

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import DIMENSIONS_FI_URL, ILI_DIMENSIONS_FI_URL, INFLUENZA, thl_entry

# A Wednesday of week 38, so the last finished week is 37.
NOW = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)


async def set_up(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **kwargs: bool) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"), **kwargs)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_every_county_has_its_cases_and_incidence(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    await set_up(hass, freezer)

    cases = hass.states.get("sensor.thl_influenssa_ita_uusimaa")
    assert cases.state == "5"
    assert cases.attributes["friendly_name"] == "THL Influenssa Itä-Uusimaa"
    assert cases.attributes["state_class"] == "measurement"
    assert cases.attributes["last_week"] == 37
    assert "unit_of_measurement" not in cases.attributes, "cases are a count, as the whole country's always were"

    incidence = hass.states.get("sensor.thl_influenssa_ita_uusimaa_incidence")
    assert incidence.state == "4.7"
    assert incidence.attributes["unit_of_measurement"] == "per 100 000"
    assert incidence.attributes["state_class"] == "measurement"

    assert hass.states.get("sensor.thl_influenssa_keski_uusimaa").state == "0", "a cell THL left out means no cases"
    assert hass.states.get("sensor.thl_influenssa_incidence").state == "0.3", "the whole country's incidence"


async def test_county_sensors_exist_for_every_county_thl_reports(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    await set_up(hass, freezer)

    registry = er.async_get(hass)
    ids = {entity.unique_id for entity in registry.entities.values() if entity.platform == "thl"}
    assert f"thl_{INFLUENZA}_etela-karjalan_hyvinvointialue" in ids
    assert f"thl_{INFLUENZA}_etela-karjalan_hyvinvointialue_incidence" in ids
    # 23 counties with two sensors each, and the whole country's cases and incidence.
    assert len(ids) == 48
    assert hass.states.get("sensor.thl_influenssa_etela_karjala").state == STATE_UNKNOWN, (
        "a county missing from the data has no number"
    )


async def test_county_sensors_are_made_while_thl_is_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    aioclient_mock.get(DIMENSIONS_FI_URL, status=503)
    await set_up(hass, freezer)

    assert hass.states.get("sensor.thl_influenssa_ita_uusimaa").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.thl_influenssa_ita_uusimaa_incidence").state == STATE_UNAVAILABLE


async def test_flu_like_illness_visits_as_a_share_of_all_visits(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    await set_up(hass, freezer, ili=True)

    whole_country = hass.states.get("sensor.thl_influenssankaltaiset_kaynnit")
    assert whole_country.state == "0.0125", "250 visits out of 2 000 000"
    assert whole_country.attributes["unit_of_measurement"] == "%"
    assert whole_country.attributes["last_week"] == 37
    assert whole_country.attributes["values"][1] == {
        "name": "Itä-Uudenmaan hyvinvointialue",
        "area_id": "ita-uudenmaan_hyvinvointialue",
        "share_last_week": 0.02,
        "visits_last_week": 12,
        "all_visits_last_week": 60000,
        "share_two_weeks_ago": 0.02,
        "entity_id": "sensor.thl_influenssankaltaiset_kaynnit_ita_uusimaa",
    }

    assert hass.states.get("sensor.thl_influenssankaltaiset_kaynnit_ita_uusimaa").state == "0.02"
    assert hass.states.get("sensor.thl_influenssankaltaiset_kaynnit_keski_uusimaa").state == "0.0", (
        "no flu-like illness visits among the county's visits"
    )
    assert hass.states.get("sensor.thl_influenssa").state == "17", "the diseases carry on as before"


async def test_flu_like_illness_visits_use_their_own_dimensions(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    await set_up(hass, freezer, ili=True)

    fetched = [str(call[1]) for call in thl.mock_calls]
    assert fetched.count(ILI_DIMENSIONS_FI_URL) == 1
    assert fetched.count(DIMENSIONS_FI_URL) == 1, "the diseases' dimensions are still fetched once"
