"""THL's service: fetching the dimensions and the case numbers, and sharing one copy of the dimensions."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thl.api import DimensionsCache, ThlClient
from custom_components.thl.const import DATA_URL, DIMENSIONS_TTL, ILI_DIMENSIONS_URL
from custom_components.thl.exceptions import ThlError

from .conftest import (
    DATA_FI_URL,
    DIMENSIONS,
    DIMENSIONS_FI_URL,
    DIMENSIONS_JSONP,
    ILI_DIMENSIONS_FI_URL,
    INFLUENZA,
    WEEK_36,
    WEEK_37,
    cases,
)


async def test_fetching_the_dimensions_and_numbers(hass: HomeAssistant, thl: AiohttpClientMocker) -> None:
    client = ThlClient(hass, "fi")

    assert await client.dimensions() == DIMENSIONS
    params = [
        ("row", "hva-841988"),
        ("column", f"yearweek-{WEEK_37}.{WEEK_36}."),
        ("column", "measure-877837.931297."),
        ("filter", f"nidrreportgroup-{INFLUENZA}"),
    ]
    assert await client.data(DATA_URL, params) == cases([WEEK_36, WEEK_37])

    _method, url, _data, headers = thl.mock_calls[-1]
    assert str(url).startswith(DATA_FI_URL)
    assert list(url.query.items()) == params, "several weeks and measures in one request"
    assert headers["User-Agent"].startswith("Mozilla/5.0")


async def test_errors(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(DIMENSIONS_FI_URL, status=503)
    with pytest.raises(ThlError):
        await ThlClient(hass, "fi").dimensions()


async def test_every_disease_shares_one_copy_of_the_dimensions(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(DIMENSIONS_FI_URL, text=DIMENSIONS_JSONP)
    cache = DimensionsCache()
    client = ThlClient(hass, "fi")

    assert await cache.get(client, now=1000.0) == DIMENSIONS
    assert await cache.get(client, now=1000.0 + DIMENSIONS_TTL.total_seconds() - 1) == DIMENSIONS
    assert len(aioclient_mock.mock_calls) == 1, "fetched once for every disease"

    await cache.get(client, now=1000.0 + DIMENSIONS_TTL.total_seconds())
    assert len(aioclient_mock.mock_calls) == 2, "fetched again when the copy is old"


async def test_each_cube_has_its_own_copy(hass: HomeAssistant, thl: AiohttpClientMocker) -> None:
    cache = DimensionsCache()
    client = ThlClient(hass, "fi")

    assert await cache.get(client, now=1.0) == DIMENSIONS
    assert await cache.get(client, ILI_DIMENSIONS_URL, now=1.0) != DIMENSIONS
    assert [str(call[1]) for call in thl.mock_calls] == [DIMENSIONS_FI_URL, ILI_DIMENSIONS_FI_URL]
