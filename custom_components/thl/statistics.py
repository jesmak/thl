"""Reading THL's dimensions and case numbers.

The dimensions file names the diseases, the weeks and the welfare counties, and
gives each an id. The data file is JSON-stat: one flat list of values, read with
the indexes of the area and the week.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
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
class CaseCount:
    area: Area
    cases: int


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


def areas(dimensions: Sequence[Any], language: str) -> list[Area]:
    """The whole country first, then the welfare counties."""
    children = dimension(dimensions, "hva").get("children") or []
    whole_country = next(
        (entry for entry in children if entry.get("label") == ALL_AREAS.get(language)),
        children[0] if children else None,
    )
    if whole_country is None or whole_country.get("sid") is None:
        raise ThlError("THL's dimensions have no areas")
    found = [area(whole_country)]
    found.extend(area(entry) for entry in whole_country.get("children") or [] if entry.get("sid") is not None)
    return found


def area(entry: dict[str, Any]) -> Area:
    sid = int(entry["sid"])
    name = str(entry.get("label") or sid)
    return Area(sid, name, AREA_IDS.get(sid) or area_id_from_name(name) or str(sid))


def area_id_from_name(name: str) -> str:
    """An id for an area THL has added since, in the style of the known ones: "keski-suomen_hyvinvointialue"."""
    plain = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]+", "_", plain).strip("_")


def week_sid(dimensions: Sequence[Any], language: str, year: int, week: int) -> str | None:
    """The id of one week, or None when THL hasn't published that week."""
    children = dimension(dimensions, "yearweek").get("children") or []
    all_weeks = next(
        (entry for entry in children if entry.get("label") == ALL_WEEKS.get(language)),
        children[0] if children else None,
    )
    if all_weeks is None:
        return None
    label = WEEK_LABEL[language].format(year=year, week=str(week).zfill(2))
    for year_node in all_weeks.get("children") or []:
        for week_node in year_node.get("children") or []:
            if week_node.get("label") == label and week_node.get("sid") is not None:
                return str(week_node["sid"])
    return None


def case_counts(data: Any, week: str, of_areas: Sequence[Area]) -> list[CaseCount]:
    """The cases of each area in one week, from the data file."""
    dataset = data.get("dataset") if isinstance(data, dict) else None
    try:
        dimensions = dataset["dimension"]
        week_index = dimensions["yearweek"]["category"]["index"][str(week)]
        area_index = dimensions["hva"]["category"]["index"]
        columns = dimensions["size"][1]
        values = dataset["value"]
    except (KeyError, IndexError, TypeError) as err:
        raise ThlError("THL sent the case numbers in an unexpected format") from err

    counts = []
    for of_area in of_areas:
        index = area_index.get(str(of_area.sid))
        if index is not None:
            counts.append(CaseCount(of_area, cell(values, (int(index) * int(columns)) + int(week_index))))
    return counts


def cell(values: Any, position: int) -> int:
    """One value of the data file. THL leaves out the cells with no cases, and they count as zero."""
    if isinstance(values, dict):
        value = values.get(str(position))
    elif isinstance(values, list) and 0 <= position < len(values):
        value = values[position]
    else:
        value = None
    try:
        return 0 if value is None else int(value)
    except (TypeError, ValueError):
        return 0


def build_values(current: Sequence[CaseCount], previous: Sequence[CaseCount]) -> list[dict[str, Any]]:
    """The sensor's `values` attribute: each area with last week's cases and the change from the week before."""
    before_by_name = {count.area.name: count.cases for count in previous}
    result = []
    for count in current:
        entry: dict[str, Any] = {
            "name": count.area.name,
            "amount_last_week": count.cases,
            "area_id": count.area.area_id,
        }
        before = before_by_name.get(count.area.name)
        if before is not None:
            entry["amount_two_weeks_ago"] = before
            entry["change_in_numbers"] = count.cases - before
            # As earlier versions wrote it: a rounded string, or the number 0 when there was nothing to compare with.
            entry["change_percentage"] = 0 if before == 0 else f"{(count.cases - before) / before * 100:.0f}"
        result.append(entry)
    return result


def previous_iso_week(year: int, week: int) -> tuple[int, int]:
    """The week before the given one."""
    if week > 1:
        return year, week - 1
    # The 28th of December is always in the last week of its year, 52 or 53.
    return year - 1, date(year - 1, 12, 28).isocalendar().week
