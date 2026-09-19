"""Adding the integration, following more diseases and the flu-like illness visits, and changing the language."""

from __future__ import annotations

from datetime import UTC, datetime

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thl.const import (
    CONF_DISEASE_ID,
    CONF_DISEASE_NAME,
    CONF_LANGUAGE,
    DOMAIN,
    SUBENTRY_DISEASE,
    SUBENTRY_ILI,
)

from .conftest import ADENOVIRUS, DIMENSIONS_FI_URL, INFLUENZA, thl_entry

NOW = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)


async def test_adding_the_integration_follows_the_first_disease(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_LANGUAGE: "fi"})
    assert result["step_id"] == "disease"
    assert [option["label"] for option in result["data_schema"].schema[CONF_DISEASE_ID].config["options"]] == [
        "Adenovirus",
        "Influenssa",
    ]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DISEASE_ID: INFLUENZA})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "THL"
    assert result["data"] == {CONF_LANGUAGE: "fi"}
    entry = result["result"]
    [subentry] = entry.subentries.values()
    assert subentry.subentry_type == SUBENTRY_DISEASE
    assert subentry.title == "THL Influenssa"
    assert subentry.unique_id == f"thl_{INFLUENZA}"
    assert subentry.data == {CONF_DISEASE_ID: INFLUENZA, CONF_DISEASE_NAME: "Influenssa"}
    assert hass.states.get("sensor.thl_influenssa").state == "17"


async def test_the_integration_is_added_only_once(hass: HomeAssistant, thl: AiohttpClientMocker) -> None:
    thl_entry(hass, (INFLUENZA, "Influenssa"))

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed", "further diseases are added to the entry that exists"


async def test_following_one_more_disease(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_DISEASE), context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert [option["label"] for option in result["data_schema"].schema[CONF_DISEASE_ID].config["options"]] == [
        "Adenovirus"
    ], "the disease already being followed is left out"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {CONF_DISEASE_ID: ADENOVIRUS})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(entry.subentries) == 2
    assert hass.states.get("sensor.thl_adenovirus").state == "17"


async def test_following_the_flu_like_illness_visits(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_ILI), context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user", "nothing to choose; the form explains what is added"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "THL Influenssankaltaiset käynnit"
    assert hass.states.get("sensor.thl_influenssankaltaiset_kaynnit").state == "0.0125"

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_ILI), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured", "there is one set of flu-like illness visits"


async def test_when_every_disease_is_already_followed(hass: HomeAssistant, thl: AiohttpClientMocker) -> None:
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"), (ADENOVIRUS, "Adenovirus"))

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_DISEASE), context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "all_configured"


async def test_thl_cannot_be_reached(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(DIMENSIONS_FI_URL, status=503)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_LANGUAGE: "fi"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_changing_the_language_renames_every_disease(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"), (ADENOVIRUS, "Adenovirus"), ili=True)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_LANGUAGE: "en"})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_LANGUAGE] == "en"
    titles = {subentry.title for subentry in entry.subentries.values()}
    assert titles == {"THL Influenza", "THL Adenovirus", "THL Flu-like illness visits"}

    state = hass.states.get("sensor.thl_influenssa")
    assert state.attributes["disease_name"] == "Influenza", "the entity keeps its id, the names change"
    assert state.attributes["values"][1]["name"] == "East Uusimaa wellbeing services county"
    assert state.attributes["values"][1]["area_id"] == "ita-uudenmaan_hyvinvointialue", "ids never change"
