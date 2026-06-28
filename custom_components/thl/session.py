import json
import logging
from typing import Any

import requests
from requests import ConnectTimeout, RequestException
from .const import USER_AGENT, API_DIMENSIONS_URL, API_DATA_URL, STR_ALL_AREAS, STR_ALL_TIMES, STR_TIME

_LOGGER = logging.getLogger(__name__)


class ThlException(Exception):
    """Base exception for FMI Waterlevel"""


class ThlSession:
    _timeout: int
    _language: str

    def __init__(self, lang: str, timeout=20):
        self._timeout = timeout
        self._lang = lang

    def get_diseases(self) -> dict[str, str]:
        try:
            response = requests.get(
                url=API_DIMENSIONS_URL.replace("{lang}", self._lang),
                headers={"User-Agent": USER_AGENT},
                timeout=self._timeout,
            )

            if response.status_code != 200:
                raise ThlException(f"{response.status_code} is not valid")

            data = json.loads(
                response.text.lstrip().rstrip().removeprefix("thl.pivot.loadDimensions(").removesuffix(");"))

            disease_dim = next((entry for entry in data if entry["id"] == "nidrreportgroup"), None)
            if disease_dim is None:
                raise ThlException("Could not find nidrreportgroup dimension in data")

            result = {}
            for entry in disease_dim.get("children", []):
                if "children" in entry:
                    for child in entry["children"]:
                        result[str(child["sid"])] = child["label"]
                else:
                    result[str(entry["sid"])] = entry["label"]

            return dict(sorted(result.items(), key=lambda x: x[1]))

        except ConnectTimeout as exception:
            raise ThlException("Timeout error") from exception
        except RequestException as exception:
            raise ThlException(f"Communication error {exception}") from exception

    def get_data(self, year: int, week: int, disease_id: str) -> list:
        try:
            response = requests.get(
                url=API_DIMENSIONS_URL.replace("{lang}", self._lang),
                headers={
                    "User-Agent": USER_AGENT
                },
                timeout=self._timeout,
            )

            if response.status_code != 200:
                raise ThlException(f"{response.status_code} is not valid")
            else:
                data = json.loads(
                    response.text.lstrip().rstrip().removeprefix("thl.pivot.loadDimensions(").removesuffix(");"))
                week_sid = self.get_week_id(data, year, week)
                if week_sid is None:
                    raise ThlException(f"No data available for year {year} week {week}")
                area_sids = self.get_area_ids(data)

                area_sid = next((key for key in area_sids.keys() if area_sids[key] == STR_ALL_AREAS[self._lang]), None)
                url = (API_DATA_URL
                       .replace("{week_sid}", week_sid)
                       .replace("{area_sid}", str(area_sid))
                       .replace("{lang}", self._lang)
                       .replace("{disease_id}", disease_id))

                response = requests.get(
                    url=url,
                    headers={
                        "User-Agent": USER_AGENT
                    },
                    timeout=self._timeout,
                )

                return self.get_values(response.json(), week_sid, area_sids)

        except ConnectTimeout as exception:
            raise ThlException("Timeout error") from exception

        except RequestException as exception:
            raise ThlException(f"Communication error {exception}") from exception

    def get_week_id(self, data: Any, year: int, week: int) -> str | None:
        time_data = next((entry["children"] for entry in data if entry["id"] == "yearweek"), None)
        if time_data is None:
            return None
        all_weeks_node = next((entry for entry in time_data if entry["label"] == STR_ALL_TIMES[self._lang]), None)
        if all_weeks_node is None:
            return None
        time = STR_TIME[self._lang].replace("{week}", str(week).zfill(2)).replace("{year}", str(year))
        for year_node in all_weeks_node["children"]:
            result = next((entry for entry in year_node.get("children", []) if entry["label"] == time), None)
            if result is not None:
                return str(result["sid"])
        return None

    def get_area_ids(self, data: Any) -> dict[str, str]:
        area_data = next((entry["children"] for entry in data if entry["id"] == "hva"), None)
        if area_data is None:
            raise ThlException("Could not find hva dimension in data")
        all_areas = next((entry for entry in area_data if entry["label"] == STR_ALL_AREAS[self._lang]), None)
        if all_areas is None:
            raise ThlException("Could not find all-areas entry in dimension data")
        result = {all_areas["sid"]: all_areas["label"]}
        for area in all_areas["children"]:
            result[area["sid"]] = area["label"]
        return result

    @staticmethod
    def get_values(data: Any, week_sid: str, area_sids: dict[str, str]) -> list:
        result = []
        week_index = data["dataset"]["dimension"]["yearweek"]["category"]["index"][str(week_sid)]
        columns = data["dataset"]["dimension"]["size"][1]
        for area_key in area_sids.keys():
            name = data["dataset"]["dimension"]["hva"]["category"]["label"][str(area_key)]
            index = data["dataset"]["dimension"]["hva"]["category"]["index"][str(area_key)]
            value = data["dataset"]["value"][str((index * columns) + week_index)]
            result.append({"name": name, "value": value, "sid": area_key})
        return result
