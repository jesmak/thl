"""THL's Sampo service: the dimensions file and the weekly case numbers."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DATA_URL, DIMENSIONS_TTL, DIMENSIONS_URL, USER_AGENT
from .exceptions import ThlError
from .statistics import parse_dimensions

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)


class ThlClient:
    def __init__(self, hass: HomeAssistant, language: str) -> None:
        self._session = async_get_clientsession(hass)
        self._language = language

    async def dimensions(self) -> list[Any]:
        """The diseases, weeks and areas THL has data for."""
        return parse_dimensions(await self._get(DIMENSIONS_URL.format(language=self._language)))

    async def cases(self, disease_id: str, week: str, area_sid: int | str) -> Any:
        """The cases of one disease in one week, by area."""
        text = await self._get(
            DATA_URL.format(language=self._language),
            {"row": f"hva-{area_sid}", "column": f"yearweek-{week}", "filter": f"nidrreportgroup-{disease_id}"},
        )
        try:
            return json.loads(text)
        except ValueError as err:
            raise ThlError("THL sent the case numbers in an unexpected format") from err

    async def _get(self, url: str, params: dict[str, str] | None = None) -> str:
        try:
            async with self._session.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
            ) as response:
                if response.status != 200:
                    raise ThlError(f"THL answered with status {response.status}")
                return await response.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ThlError(f"THL couldn't be reached: {err}") from err


@dataclass
class _Cached:
    dimensions: list[Any]
    fetched: float


class DimensionsCache:
    """One copy of the dimensions file per language, shared by every disease.

    The file is over 100 kB and changes once a week, so fetching it for each
    sensor on every update would be needless traffic.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_language: dict[str, _Cached] = {}

    async def get(self, client: ThlClient, language: str, now: float | None = None) -> list[Any]:
        now = time.monotonic() if now is None else now
        async with self._lock:
            cached = self._by_language.get(language)
            if cached is not None and now - cached.fetched < DIMENSIONS_TTL.total_seconds():
                return cached.dimensions
            _LOGGER.debug("Fetching THL's dimensions in %s", language)
            dimensions = await client.dimensions()
            self._by_language[language] = _Cached(dimensions, now)
            return dimensions
