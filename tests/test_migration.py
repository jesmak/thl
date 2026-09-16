"""From one config entry per disease (1.x) to one entry with a subentry per disease (2.0).

What matters is that nothing the user has built on the sensors breaks: the
entity IDs, and so history, dashboards, automations and thl-card, stay as they were.
"""

from __future__ import annotations

from datetime import UTC, datetime

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thl.const import CONF_DISEASE_ID, CONF_DISEASE_NAME, CONF_LANGUAGE, DOMAIN
from custom_components.thl.migration import async_migrate_to_subentries

from .conftest import ADENOVIRUS, INFLUENZA

NOW = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)

INFLUENZA_SENSOR = "sensor.thl_influenssa"
ADENOVIRUS_SENSOR = "sensor.thl_adenovirus"


def old_entry(
    hass: HomeAssistant,
    disease_id: str,
    name: str,
    *,
    language: str = "fi",
    disabled: bool = False,
) -> MockConfigEntry:
    """A 1.x entry: one disease, with its sensor registered as 1.x left it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        title=f"THL {name}",
        data={CONF_LANGUAGE: language, CONF_DISEASE_ID: disease_id, CONF_DISEASE_NAME: name},
        unique_id=f"thl_{disease_id}",
        disabled_by=ConfigEntryDisabler.USER if disabled else None,
    )
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"thl_{disease_id}",
        config_entry=entry,
        suggested_object_id=f"thl_{name.lower()}",
        disabled_by=er.RegistryEntryDisabler.CONFIG_ENTRY if disabled else None,
    )
    return entry


async def start(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


async def test_every_entry_becomes_a_subentry_and_keeps_its_sensor(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    old_entry(hass, INFLUENZA, "Influenssa")
    old_entry(hass, ADENOVIRUS, "Adenovirus")

    await start(hass)

    [entry] = hass.config_entries.async_entries(DOMAIN)
    assert entry.version == 2
    assert entry.title == "THL"
    assert entry.data == {CONF_LANGUAGE: "fi"}
    assert entry.unique_id is None, "the entry is no longer one disease"
    assert {subentry.unique_id for subentry in entry.subentries.values()} == {
        f"thl_{INFLUENZA}",
        f"thl_{ADENOVIRUS}",
    }

    registry = er.async_get(hass)
    for entity_id, disease_id in ((INFLUENZA_SENSOR, INFLUENZA), (ADENOVIRUS_SENSOR, ADENOVIRUS)):
        registered = registry.async_get(entity_id)
        assert registered is not None, "the entity id is what dashboards and thl-card use"
        assert registered.unique_id == f"thl_{disease_id}"
        assert registered.config_entry_id == entry.entry_id
        assert entry.subentries[registered.config_subentry_id].data[CONF_DISEASE_ID] == disease_id
        assert hass.states.get(entity_id).state == "17"


async def test_the_sensor_moves_to_the_device_of_its_disease(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = old_entry(hass, INFLUENZA, "Influenssa")
    # The device of the 2.0.0 entry, which the disease's own device replaces.
    devices = dr.async_get(hass)
    devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}, name="THL")

    await start(hass)

    [migrated] = hass.config_entries.async_entries(DOMAIN)
    [subentry] = migrated.subentries.values()
    old = devices.async_get_device_by_identifier((DOMAIN, entry.entry_id), migrated.entry_id)
    assert old is None, "the device of the old entry is gone"
    assert devices.async_get_device_by_identifier((DOMAIN, subentry.subentry_id), migrated.entry_id) is not None


async def test_a_disease_the_user_had_disabled_stays_disabled(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    old_entry(hass, INFLUENZA, "Influenssa")
    old_entry(hass, ADENOVIRUS, "Adenovirus", disabled=True)

    await start(hass)

    registered = er.async_get(hass).async_get(ADENOVIRUS_SENSOR)
    assert registered.disabled_by is er.RegistryEntryDisabler.USER
    assert hass.states.get(ADENOVIRUS_SENSOR) is None
    assert hass.states.get(INFLUENZA_SENSOR).state == "17"


async def test_the_language_of_the_new_entry_is_the_one_most_diseases_had(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    old_entry(hass, INFLUENZA, "Influenssa", language="en")
    old_entry(hass, ADENOVIRUS, "Adenovirus", language="fi")
    old_entry(hass, "878001", "Rotavirus", language="fi")

    await start(hass)

    [entry] = hass.config_entries.async_entries(DOMAIN)
    assert entry.data == {CONF_LANGUAGE: "fi"}


async def test_migrating_a_second_time_changes_nothing(
    hass: HomeAssistant, thl: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    old_entry(hass, INFLUENZA, "Influenssa")
    old_entry(hass, ADENOVIRUS, "Adenovirus")
    await start(hass)
    [entry] = hass.config_entries.async_entries(DOMAIN)
    before = {subentry.subentry_id for subentry in entry.subentries.values()}

    await async_migrate_to_subentries(hass)
    await hass.async_block_till_done()

    [entry] = hass.config_entries.async_entries(DOMAIN)
    assert {subentry.subentry_id for subentry in entry.subentries.values()} == before
    assert er.async_get(hass).async_get(INFLUENZA_SENSOR).config_entry_id == entry.entry_id
