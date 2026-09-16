"""Reading THL's dimensions and case numbers."""

from __future__ import annotations

import pytest

from custom_components.thl.exceptions import ThlError
from custom_components.thl.statistics import (
    Area,
    CaseCount,
    areas,
    build_values,
    case_counts,
    cell,
    diseases,
    parse_dimensions,
    previous_iso_week,
    week_sid,
)

from .conftest import (
    ADENOVIRUS,
    CASES_WEEK_36,
    CASES_WEEK_37,
    DIMENSIONS,
    DIMENSIONS_JSONP,
    INFLUENZA,
    WEEK_36,
    WEEK_37,
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


def test_weeks_are_found_by_year_and_number() -> None:
    assert week_sid(DIMENSIONS, "fi", 2026, 37) == WEEK_37
    assert week_sid(DIMENSIONS, "fi", 2026, 36) == WEEK_36
    assert week_sid(DIMENSIONS, "fi", 2026, 38) is None, "THL hasn't published it yet"


def test_case_numbers_of_each_area() -> None:
    counts = case_counts(CASES_WEEK_37, WEEK_37, areas(DIMENSIONS, "fi"))
    assert [(count.area.area_id, count.cases) for count in counts] == [
        ("finland", 17),
        ("ita-uudenmaan_hyvinvointialue", 5),
        ("keski-uudenmaan_hyvinvointialue", 0),
        ("lansi-uudenmaan_hyvinvointialue", 12),
    ], "a cell THL left out counts as no cases"


def test_unreadable_case_numbers() -> None:
    with pytest.raises(ThlError):
        case_counts({"dataset": {}}, WEEK_37, areas(DIMENSIONS, "fi"))


def test_missing_cells_count_as_zero() -> None:
    assert cell({"3": "7"}, 3) == 7
    assert cell({"3": None}, 3) == 0
    assert cell({}, 3) == 0
    assert cell([1, 2, 3], 1) == 2
    assert cell([1], 5) == 0


def test_values_carry_the_change_from_the_week_before() -> None:
    of_areas = areas(DIMENSIONS, "fi")
    current = case_counts(CASES_WEEK_37, WEEK_37, of_areas)
    previous = case_counts(CASES_WEEK_36, WEEK_36, of_areas)

    values = build_values(current, previous)
    assert values[0] == {
        "name": "Kaikki hyvinvointialueet",
        "amount_last_week": 17,
        "area_id": "finland",
        "amount_two_weeks_ago": 20,
        "change_in_numbers": -3,
        "change_percentage": "-15",
    }
    assert values[1]["change_percentage"] == "25", "a rounded string, as earlier versions wrote it"
    assert values[2]["change_percentage"] == 0, "the number zero when there was nothing to compare with"


def test_values_without_the_week_before() -> None:
    [value] = build_values([CaseCount(Area(1, "Kaikki", "finland"), 3)], [])
    assert value == {"name": "Kaikki", "amount_last_week": 3, "area_id": "finland"}


@pytest.mark.parametrize(
    ("year", "week", "before"), [(2026, 37, (2026, 36)), (2026, 1, (2025, 52)), (2021, 1, (2020, 53))]
)
def test_the_week_before(year: int, week: int, before: tuple[int, int]) -> None:
    assert previous_iso_week(year, week) == before
