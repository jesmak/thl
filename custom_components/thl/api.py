"""THL's Sampo service: the dimensions and data files of its cubes."""

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

from .const import DIMENSIONS_TTL, DIMENSIONS_URL, USER_AGENT
from .exceptions import ThlError
from .statistics import parse_dimensions

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)


class ThlClient:
    def __init__(self, hass: HomeAssistant, language: str) -> None:
        self._session = async_get_clientsession(hass)
        self._language = language

    @property
    def language(self) -> str:
        return self._language

    async def dimensions(self, url: str = DIMENSIONS_URL) -> list[Any]:
        """The categories of a cube: for the case numbers, the diseases, weeks and areas THL has data for."""
        return parse_dimensions(await self._get(url.format(language=self._language)))

    async def data(self, url: str, params: list[tuple[str, str]]) -> Any:
        """Numbers from a cube. A parameter can list several categories: "yearweek-1236829.1236739."."""
        text = await self._get(url.format(language=self._language), params)
        try:
            return json.loads(text)
        except ValueError as err:
            raise ThlError("THL sent the numbers in an unexpected format") from err

    async def _get(self, url: str, params: list[tuple[str, str]] | None = None) -> str:
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
    """One copy of each dimensions file per language, shared by every disease.

    The file is over 100 kB and changes once a week, so fetching it for each
    sensor on every update would be needless traffic.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_url: dict[str, _Cached] = {}

    async def get(self, client: ThlClient, url: str = DIMENSIONS_URL, now: float | None = None) -> list[Any]:
        now = time.monotonic() if now is None else now
        key = url.format(language=client.language)
        async with self._lock:
            cached = self._by_url.get(key)
            if cached is not None and now - cached.fetched < DIMENSIONS_TTL.total_seconds():
                return cached.dimensions
            _LOGGER.debug("Fetching %s", key)
            dimensions = await client.dimensions(url)
            self._by_url[key] = _Cached(dimensions, now)
            return dimensions
