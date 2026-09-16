"""THL's service: fetching the dimensions and the case numbers, and sharing one copy of the dimensions."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thl.api import DimensionsCache, ThlClient
from custom_components.thl.const import DIMENSIONS_TTL
from custom_components.thl.exceptions import ThlError

from .conftest import CASES_WEEK_37, DIMENSIONS, DIMENSIONS_FI_URL, DIMENSIONS_JSONP, INFLUENZA, WEEK_37


async def test_fetching_the_dimensions_and_cases(hass: HomeAssistant, thl: AiohttpClientMocker) -> None:
    client = ThlClient(hass, "fi")

    assert await client.dimensions() == DIMENSIONS
    assert await client.cases(INFLUENZA, WEEK_37, 841988) == CASES_WEEK_37

    _method, url, _data, headers = thl.mock_calls[-1]
    assert dict(url.query) == {
        "row": "hva-841988",
        "column": f"yearweek-{WEEK_37}",
        "filter": f"nidrreportgroup-{INFLUENZA}",
    }
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

    assert await cache.get(client, "fi", 1000.0) == DIMENSIONS
    assert await cache.get(client, "fi", 1000.0 + DIMENSIONS_TTL.total_seconds() - 1) == DIMENSIONS
    assert len(aioclient_mock.mock_calls) == 1, "fetched once for every disease"

    await cache.get(client, "fi", 1000.0 + DIMENSIONS_TTL.total_seconds())
    assert len(aioclient_mock.mock_calls) == 2, "fetched again when the copy is old"
