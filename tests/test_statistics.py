"""Reading THL's dimensions and data files."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.thl.const import ILI_ALL_AREAS, ILI_AREA_IDS, MEASURE_CASES, MEASURE_INCIDENCE
from custom_components.thl.exceptions import ThlError
from custom_components.thl.statistics import (
    Cube,
    Week,
    areas,
    case_weeks,
    diseases,
    first_child_sid,
    ili_weeks,
    is_week_before,
    last_finished_week,
    parse_dimensions,
    previous_iso_week,
)

from .conftest import (
    ADENOVIRUS,
    DIMENSIONS,
    DIMENSIONS_JSONP,
    FINLAND,
    ILI_WEEK_36,
    ILI_WEEK_37,
    INFLUENZA,
    WEEK_36,
    WEEK_37,
    cases,
    ili_dimensions,
)


def test_the_dimensions_come_wrapped_in_a_javascript_call() -> None:
    assert parse_dimensions(DIMENSIONS_JSONP) == DIMENSIONS
    with pytest.raises(ThlError):
        parse_dimensions("<html>Service unavailable</html>")


def test_diseases_are_sorted_by_name() -> None:
    assert diseases(DIMENSIONS) == {ADENOVIRUS: "Adenovirus", INFLUENZA: "Influenssa"}


def test_areas_start_with_the_whole_country() -> None:
    found = areas(DIMENSIONS, "fi")
    assert [area.area_id for area in found] == [
        "finland",
        "ita-uudenmaan_hyvinvointialue",
        "keski-uudenmaan_hyvinvointialue",
        "lansi-uudenmaan_hyvinvointialue",
    ]
    assert found[1].name == "Itä-Uudenmaan hyvinvointialue"


def test_an_area_thl_adds_later_gets_an_id_from_its_name() -> None:
    dimensions = [
        {
            "id": "hva",
            "children": [
                {
                    "sid": 841988,
                    "label": "Kaikki hyvinvointialueet",
                    "children": [{"sid": 999999, "label": "Uuden Ahvenanmaan hyvinvointialue"}],
                }
            ],
        }
    ]
    assert areas(dimensions, "fi")[1].area_id == "uuden_ahvenanmaan_hyvinvointialue"


def test_published_weeks_newest_first() -> None:
    assert case_weeks(DIMENSIONS, "fi", (2026, 38), 4) == [Week(2026, 37, WEEK_37), Week(2026, 36, WEEK_36)], (
        "week 38 isn't published yet and is skipped; nor are weeks 35 and before"
    )
    assert case_weeks(DIMENSIONS, "fi", (2026, 37), 1) == [Week(2026, 37, WEEK_37)]


def test_flu_like_illness_weeks_are_named_by_their_monday() -> None:
    assert ili_weeks(ili_dimensions(), (2026, 37), 3) == [Week(2026, 37, ILI_WEEK_37), Week(2026, 36, ILI_WEEK_36)]


def test_flu_like_illness_areas_have_the_same_ids() -> None:
    found = areas(ili_dimensions(), "fi", ILI_ALL_AREAS, ILI_AREA_IDS)
    assert [area.area_id for area in found] == [area.area_id for area in areas(DIMENSIONS, "fi")]
    assert first_child_sid(ili_dimensions(), "inf_age") == "1200921", "every age group together"


def test_cells_are_read_by_their_categories() -> None:
    cube = Cube(cases([WEEK_36, WEEK_37]))
    assert cube.value(hva=FINLAND, yearweek=WEEK_37, measure=MEASURE_CASES) == 17
    assert cube.value(hva=FINLAND, yearweek=WEEK_36, measure=MEASURE_INCIDENCE) == 0.4
    assert cube.value(hva=837147, yearweek=WEEK_37, measure=MEASURE_CASES) is None, "a cell THL left out"
    assert cube.value(hva=FINLAND, yearweek="1", measure=MEASURE_CASES) is None, "a week not in the file"


def test_cells_can_come_as_a_list() -> None:
    data = cases([WEEK_37])
    data["dataset"]["value"] = [17, 0.3]
    cube = Cube(data)
    assert cube.value(hva=FINLAND, yearweek=WEEK_37, measure=MEASURE_INCIDENCE) == 0.3
    assert cube.value(hva=837181, yearweek=WEEK_37, measure=MEASURE_CASES) is None, "past the end of the list"


def test_unreadable_numbers() -> None:
    with pytest.raises(ThlError):
        Cube({"dataset": {}})


def test_the_last_finished_week() -> None:
    assert last_finished_week(date(2026, 9, 16)) == (2026, 37)
    assert last_finished_week(date(2026, 1, 1)) == (2025, 52)


def test_a_week_follows_another() -> None:
    assert is_week_before(Week(2025, 52, ""), Week(2026, 1, ""))
    assert not is_week_before(Week(2026, 35, ""), Week(2026, 37, ""))


@pytest.mark.parametrize(
    ("year", "week", "before"), [(2026, 37, (2026, 36)), (2026, 1, (2025, 52)), (2021, 1, (2020, 53))]
)
def test_the_week_before(year: int, week: int, before: tuple[int, int]) -> None:
    assert previous_iso_week(year, week) == before
