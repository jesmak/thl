"""Setting up the THL entry and the sensors of its diseases."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thl.sensor import ThlSensor

from .conftest import (
    ADENOVIRUS,
    DATA_FI_URL,
    DIMENSIONS_FI_URL,
    INFLUENZA,
    WEEK_36,
    WEEK_37,
    by_week,
    dimensions,
    thl_entry,
)

INFLUENZA_SENSOR = "sensor.thl_influenssa"
ADENOVIRUS_SENSOR = "sensor.thl_adenovirus"
# A Wednesday of week 38, so the last finished week is 37.
NOW = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)

TWO_DISEASES = ((INFLUENZA, "Influenssa"), (ADENOVIRUS, "Adenovirus"))


async def test_every_disease_gets_a_sensor_of_last_weeks_cases(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, *TWO_DISEASES)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(INFLUENZA_SENSOR)
    assert state.state == "17", "the cases of the whole country"
    assert state.attributes["last_week"] == 37
    assert state.attributes["disease_id"] == INFLUENZA
    assert state.attributes["disease_name"] == "Influenssa"
    assert state.attributes["state_class"] == "measurement"
    assert state.attributes["values"][0] == {
        "name": "Kaikki hyvinvointialueet",
        "amount_last_week": 17,
        "area_id": "finland",
        "amount_two_weeks_ago": 20,
        "change_in_numbers": -3,
        "change_percentage": "-15",
        "incidence_last_week": 0.3,
        "incidence_two_weeks_ago": 0.4,
        "entity_id": INFLUENZA_SENSOR,
        "incidence_entity_id": "sensor.thl_influenssa_incidence",
    }
    assert state.attributes["values"][1]["change_percentage"] == "25", "a rounded string, as earlier versions wrote it"
    assert state.attributes["values"][2]["change_percentage"] == 0, "zero when there was nothing to compare with"
    assert state.attributes["values"][2]["incidence_last_week"] == 0.0, "a cell THL left out means no cases"
    assert state.attributes["values"][1]["entity_id"] == "sensor.thl_influenssa_ita_uusimaa"
    assert state.attributes["values"][1]["incidence_entity_id"] == "sensor.thl_influenssa_ita_uusimaa_incidence"
    assert hass.states.get(ADENOVIRUS_SENSOR).attributes["disease_name"] == "Adenovirus"

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_each_sensor_belongs_to_its_own_disease(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, *TWO_DISEASES)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    for entity_id, disease_id in ((INFLUENZA_SENSOR, INFLUENZA), (ADENOVIRUS_SENSOR, ADENOVIRUS)):
        registered = registry.async_get(entity_id)
        assert registered.unique_id == f"thl_{disease_id}", "as in earlier versions"
        assert entry.subentries[registered.config_subentry_id].data["disease_id"] == disease_id


async def test_the_dimensions_are_fetched_once_for_every_disease(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, *TWO_DISEASES)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    fetches = [call for call in thl.mock_calls if str(call[1]).startswith(DIMENSIONS_FI_URL)]
    assert len(fetches) == 1, "the file is over 100 kB; every disease shares one copy"


async def test_the_areas_are_kept_out_of_the_recorder() -> None:
    assert "values" in ThlSensor._unrecorded_attributes


async def test_the_week_before_is_used_until_thl_publishes_the_newest(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    # THL has published week 36 but not yet week 37.
    published = dimensions("fi")
    weeks = next(entry for entry in published if entry["id"] == "yearweek")
    year = weeks["children"][0]["children"][0]
    year["children"] = [week for week in year["children"] if str(week["sid"]) == WEEK_36]
    aioclient_mock.get(DIMENSIONS_FI_URL, text=f"thl.pivot.loadDimensions({json.dumps(published)});")
    aioclient_mock.get(DATA_FI_URL, side_effect=by_week("fi"))

    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(INFLUENZA_SENSOR)
    assert state.state == "20"
    assert state.attributes["last_week"] == 36
    assert "change_percentage" not in state.attributes["values"][0], "no week before it to compare with"


async def test_the_sensor_is_unavailable_while_thl_is_down(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(INFLUENZA_SENSOR).state == "17"

    thl.clear_requests()
    thl.get(DIMENSIONS_FI_URL, status=503)
    thl.get(DATA_FI_URL, status=503)
    freezer.tick(timedelta(minutes=40))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(INFLUENZA_SENSOR).state == STATE_UNAVAILABLE


async def test_thl_being_down_at_startup_does_not_stop_the_entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    aioclient_mock.get(DIMENSIONS_FI_URL, status=503)
    entry = thl_entry(hass, *TWO_DISEASES)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED, "one disease failing must not stop the others"
    assert hass.states.get(INFLUENZA_SENSOR).state == STATE_UNAVAILABLE
    assert WEEK_37 not in json.dumps(dict(hass.states.get(INFLUENZA_SENSOR).attributes))
