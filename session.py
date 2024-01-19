import json
import logging
from typing import Any

import requests
from requests import ConnectTimeout, RequestException
from .const import USER_AGENT, API_DIMENSIONS_URL, API_DATA_URL, STR_ALL_AREAS, STR_ALL_TIMES, STR_TIME

_LOGGER = logging.getLogger(__name__)


class CovidException(Exception):
    """Base exception for FMI Waterlevel"""


class CovidSession:
    _timeout: int
    _language: str

    def __init__(self, lang: str, timeout=20):
        self._timeout = timeout
        self._lang = lang

    def get_data(self, year: int, week: int) -> list:
        try:
            print(API_DIMENSIONS_URL.replace("{lang}", self._lang))
            response = requests.get(
                url=API_DIMENSIONS_URL.replace("{lang}", self._lang),
                headers={
                    "User-Agent": USER_AGENT
                },
                timeout=self._timeout,
            )

            if response.status_code != 200:
                raise CovidException(f"{response.status_code} is not valid")
            else:
                data = json.loads(
                    response.text.lstrip().rstrip().removeprefix("thl.pivot.loadDimensions(").removesuffix(");"))
                week_sid = self.get_week_id(data, year, week)
                area_sids = self.get_area_ids(data)

                area_sid = next((key for key in area_sids.keys() if area_sids[key] == STR_ALL_AREAS[self._lang]), None)
                url = API_DATA_URL.replace("{week_sid}", week_sid).replace("{area_sid}", str(area_sid)).replace("{lang}", self._lang)

                response = requests.get(
                    url=url,
                    headers={
                        "User-Agent": USER_AGENT
                    },
                    timeout=self._timeout,
                )

                return self.get_values(response.json(), week_sid, area_sids)

        except ConnectTimeout as exception:
            raise CovidException("Timeout error") from exception

        except RequestException as exception:
            raise CovidException(f"Communication error {exception}") from exception

    def get_week_id(self, data: Any, year: int, week: int) -> str:
        time_data = next((entry["children"] for entry in data if entry["id"] == "dateweek20200101"), None)
        weeks = next((entry["children"] for entry in time_data if entry["label"] == STR_ALL_TIMES[self._lang]), None)
        time = STR_TIME[self._lang].replace("{week}", str(week).zfill(2)).replace("{year}", str(year))
        result = next((entry for entry in weeks if entry["label"] == time), None)
        return str(result["sid"]) if result is not None else None

    def get_area_ids(self, data: Any) -> dict[str, str]:
        area_data = next((entry["children"] for entry in data if entry["id"] == "hcdmunicipality2020"), None)
        all_areas = next((entry for entry in area_data if entry["label"] == STR_ALL_AREAS[self._lang]), None)
        result = {all_areas["sid"]: all_areas["label"]}
        for area in all_areas["children"]:
            result[area["sid"]] = area["label"]
        return result

    @staticmethod
    def get_values(data: Any, week_sid: str, area_sids: {str, str}) -> list:
        result = []
        week_index = data["dataset"]["dimension"]["dateweek20200101"]["category"]["index"][str(week_sid)]
        columns = data["dataset"]["dimension"]["size"][1]
        for area_key in area_sids.keys():
            name = data["dataset"]["dimension"]["hcdmunicipality2020"]["category"]["label"][str(area_key)]
            index = data["dataset"]["dimension"]["hcdmunicipality2020"]["category"]["index"][str(area_key)]
            value = data["dataset"]["value"][str((index * columns) + week_index)]
            result.append({"name": name, "value": value, "sid": area_key})
        return result
