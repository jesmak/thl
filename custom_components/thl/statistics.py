"""Reading THL's dimensions and data files.

The dimensions file names the diseases, the weeks and the welfare counties, and
gives each an id. A data file is JSON-stat: one flat list of values, read with
the position of each cell in every dimension the file has.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .const import ALL_AREAS, ALL_WEEKS, AREA_IDS, WEEK_LABEL
from .exceptions import ThlError

# The dimensions file comes wrapped in a JavaScript call.
JSONP_PREFIX = "thl.pivot.loadDimensions("
JSONP_SUFFIX = ");"


@dataclass(frozen=True)
class Area:
    sid: int
    name: str
    # The area's id in the sensor's attributes, such as "finland".
    area_id: str


@dataclass(frozen=True)
class Week:
    """An ISO week, and the id THL's dimensions give it."""

    year: int
    week: int
    sid: str

    @property
    def monday(self) -> date:
        return date.fromisocalendar(self.year, self.week, 1)


def parse_dimensions(text: str) -> list[Any]:
    body = text.strip().removeprefix(JSONP_PREFIX).removesuffix(JSONP_SUFFIX)
    try:
        data = json.loads(body)
    except ValueError as err:
        raise ThlError("THL sent the dimensions in an unexpected format") from err
    if not isinstance(data, list):
        raise ThlError("THL sent the dimensions in an unexpected format")
    return data


def dimension(dimensions: Sequence[Any], name: str) -> dict[str, Any]:
    found = next((entry for entry in dimensions if isinstance(entry, dict) and entry.get("id") == name), None)
    if found is None:
        raise ThlError(f"THL's dimensions have no {name}")
    return found


def diseases(dimensions: Sequence[Any]) -> dict[str, str]:
    """The diseases THL reports, by id and sorted by name. They are grouped, and a group can have one disease."""
    result: dict[str, str] = {}
    for entry in dimension(dimensions, "nidrreportgroup").get("children") or []:
        children = entry.get("children") or [entry]
        for child in children:
            if child.get("sid") is not None:
                result[str(child["sid"])] = str(child.get("label") or child["sid"])
    if not result:
        raise ThlError("THL's dimensions have no diseases")
    return dict(sorted(result.items(), key=lambda item: item[1]))


def areas(
    dimensions: Sequence[Any],
    language: str,
    all_areas: Mapping[str, str] = ALL_AREAS,
    ids: Mapping[int, str] = AREA_IDS,
) -> list[Area]:
    """The whole country first, then the welfare counties."""
    children = dimension(dimensions, "hva").get("children") or []
    whole_country = next(
        (entry for entry in children if entry.get("label") == all_areas.get(language)),
        children[0] if children else None,
    )
    if whole_country is None or whole_country.get("sid") is None:
        raise ThlError("THL's dimensions have no areas")
    found = [area(whole_country, ids)]
    found.extend(area(entry, ids) for entry in whole_country.get("children") or [] if entry.get("sid") is not None)
    return found


def area(entry: dict[str, Any], ids: Mapping[int, str] = AREA_IDS) -> Area:
    sid = int(entry["sid"])
    name = str(entry.get("label") or sid)
    return Area(sid, name, ids.get(sid) or area_id_from_name(name) or str(sid))


def area_id_from_name(name: str) -> str:
    """An id for an area THL has added since, in the style of the known ones: "keski-suomen_hyvinvointialue"."""
    plain = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]+", "_", plain).strip("_")


def first_child_sid(dimensions: Sequence[Any], name: str) -> str:
    """The id of a dimension's total, such as all ages."""
    children = dimension(dimensions, name).get("children") or []
    if not children or children[0].get("sid") is None:
        raise ThlError(f"THL's dimensions have nothing in {name}")
    return str(children[0]["sid"])


def leaves(entries: Sequence[Any]) -> list[dict[str, Any]]:
    """The innermost entries of a dimension, such as the weeks under their years."""
    found: list[dict[str, Any]] = []
    for entry in entries:
        children = entry.get("children") or []
        if children:
            found.extend(leaves(children))
        elif entry.get("sid") is not None:
            found.append(entry)
    return found


def case_weeks(dimensions: Sequence[Any], language: str, newest: tuple[int, int], count: int) -> list[Week]:
    """The weeks THL has published in the case numbers, newest first, from `newest` back over `count` weeks."""
    children = dimension(dimensions, "yearweek").get("children") or []
    all_weeks = next(
        (entry for entry in children if entry.get("label") == ALL_WEEKS.get(language)),
        children[0] if children else None,
    )
    by_label = {str(entry.get("label")): str(entry["sid"]) for entry in leaves([all_weeks] if all_weeks else [])}
    return published(
        newest, count, lambda year, week: by_label.get(WEEK_LABEL[language].format(year=year, week=str(week).zfill(2)))
    )


def ili_weeks(dimensions: Sequence[Any], newest: tuple[int, int], count: int) -> list[Week]:
    """The same for the flu-like illness visits, whose weeks are named by their Monday: "2026-09-07"."""
    by_label = {
        str(entry.get("label")): str(entry["sid"])
        for entry in leaves(dimension(dimensions, "weeks40").get("children") or [])
    }
    return published(newest, count, lambda year, week: by_label.get(date.fromisocalendar(year, week, 1).isoformat()))


def published(newest: tuple[int, int], count: int, sid_of: Callable[[int, int], str | None]) -> list[Week]:
    found = []
    year, week = newest
    for _ in range(count):
        sid = sid_of(year, week)
        if sid is not None:
            found.append(Week(year, week, sid))
        year, week = previous_iso_week(year, week)
    return found


class Cube:
    """The cells of a data file, looked up by the id of their category in each dimension."""

    def __init__(self, data: Any) -> None:
        try:
            dataset = data["dataset"]
            dimensions = dataset["dimension"]
            self._names: list[str] = list(dimensions["id"])
            self._sizes: list[int] = [int(size) for size in dimensions["size"]]
            self._index: dict[str, dict[str, int]] = {
                name: {str(key): int(value) for key, value in dimensions[name]["category"]["index"].items()}
                for name in self._names
            }
            self._values: Any = dataset["value"]
        except (KeyError, IndexError, TypeError, ValueError) as err:
            raise ThlError("THL sent the numbers in an unexpected format") from err
        if len(self._names) != len(self._sizes):
            raise ThlError("THL sent the numbers in an unexpected format")

    def has(self, name: str, category: str) -> bool:
        return str(category) in self._index.get(name, {})

    def value(self, **categories: str | int) -> float | None:
        """One cell. THL leaves out the cells with nothing in them, and those are None."""
        position = 0
        for name, size in zip(self._names, self._sizes, strict=True):
            index = self._index[name].get(str(categories[name]))
            if index is None:
                return None
            position = position * size + index
        if isinstance(self._values, dict):
            raw = self._values.get(str(position))
        elif isinstance(self._values, list) and 0 <= position < len(self._values):
            raw = self._values[position]
        else:
            raw = None
        try:
            return None if raw is None or raw == "" else float(raw)
        except (TypeError, ValueError):
            return None


def previous_iso_week(year: int, week: int) -> tuple[int, int]:
    """The week before the given one."""
    if week > 1:
        return year, week - 1
    # The 28th of December is always in the last week of its year, 52 or 53.
    return year - 1, date(year - 1, 12, 28).isocalendar().week


def last_finished_week(today: date) -> tuple[int, int]:
    iso = today.isocalendar()
    return previous_iso_week(iso.year, iso.week)


def is_week_before(earlier: Week, later: Week) -> bool:
    return later.monday - earlier.monday == timedelta(weeks=1)
