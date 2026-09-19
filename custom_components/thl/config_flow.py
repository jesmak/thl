"""Config flow: one THL entry holds the language, and each disease is a subentry of it.

The disease list comes from THL's dimensions file. The flu-like illness visits
are a subentry of their own, added once. Changing the language later renames
every subentry.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import ThlClient
from .const import (
    CONF_DISEASE_ID,
    CONF_DISEASE_NAME,
    CONF_LANGUAGE,
    DOMAIN,
    ILI_TITLE,
    ILI_UNIQUE_ID,
    LANGUAGES,
    SUBENTRY_DISEASE,
    SUBENTRY_ILI,
)
from .exceptions import ThlError
from .migration import TITLE, VERSION
from .statistics import diseases

LANGUAGE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LANGUAGE): SelectSelector(
            SelectSelectorConfig(options=LANGUAGES, translation_key=CONF_LANGUAGE, mode=SelectSelectorMode.DROPDOWN)
        )
    }
)


async def async_diseases(hass: HomeAssistant, language: str) -> dict[str, str]:
    """The diseases THL reports, by id and sorted by name."""
    return diseases(await ThlClient(hass, language).dimensions())


def disease_schema(options: dict[str, str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_DISEASE_ID): SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=sid, label=name) for sid, name in options.items()],
                    mode=SelectSelectorMode.DROPDOWN,
                    sort=False,
                )
            )
        }
    )


def subentry_data(disease_id: str, disease_name: str) -> ConfigSubentryData:
    return ConfigSubentryData(
        data={CONF_DISEASE_ID: disease_id, CONF_DISEASE_NAME: disease_name},
        subentry_type=SUBENTRY_DISEASE,
        title=f"THL {disease_name}",
        unique_id=f"thl_{disease_id}",
    )


def already_followed(entry: ConfigEntry) -> set[str]:
    return {
        str(subentry.data[CONF_DISEASE_ID])
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_DISEASE
    }


class ThlConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = VERSION

    _language: str = LANGUAGES[0]
    _diseases: dict[str, str] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None:
            language = self.hass.config.language[:2]
            values = {CONF_LANGUAGE: language if language in LANGUAGES else "en"}
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(LANGUAGE_SCHEMA, values),
                last_step=False,
            )

        self._language = user_input[CONF_LANGUAGE]
        return await self.async_step_disease()

    async def async_step_disease(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The first disease, added together with the integration itself."""
        if user_input is not None and self._diseases:
            disease_id = str(user_input[CONF_DISEASE_ID])
            return self.async_create_entry(
                title=TITLE,
                data={CONF_LANGUAGE: self._language},
                subentries=[subentry_data(disease_id, self._diseases.get(disease_id, disease_id))],
            )

        try:
            self._diseases = await async_diseases(self.hass, self._language)
        except ThlError:
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(step_id="disease", data_schema=disease_schema(self._diseases), last_step=True)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Changing the language, which renames every disease being followed."""
        entry = self._get_reconfigure_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(LANGUAGE_SCHEMA, dict(entry.data)),
            )

        language = user_input[CONF_LANGUAGE]
        try:
            names = await async_diseases(self.hass, language)
        except ThlError:
            return self.async_abort(reason="cannot_connect")

        for subentry in list(entry.subentries.values()):
            if subentry.subentry_type == SUBENTRY_ILI:
                self.hass.config_entries.async_update_subentry(entry, subentry, title=ILI_TITLE[language])
                continue
            disease_id = str(subentry.data[CONF_DISEASE_ID])
            name = names.get(disease_id, subentry.data[CONF_DISEASE_NAME])
            self.hass.config_entries.async_update_subentry(
                entry,
                subentry,
                title=f"THL {name}",
                data={**subentry.data, CONF_DISEASE_NAME: name},
            )

        return self.async_update_reload_and_abort(entry, data={**entry.data, CONF_LANGUAGE: language})

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_DISEASE: DiseaseSubentryFlow, SUBENTRY_ILI: IliSubentryFlow}


class DiseaseSubentryFlow(ConfigSubentryFlow):
    """Following one more disease."""

    _diseases: dict[str, str] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        if user_input is not None and self._diseases:
            disease_id = str(user_input[CONF_DISEASE_ID])
            disease_name = self._diseases.get(disease_id, disease_id)
            data = subentry_data(disease_id, disease_name)
            return self.async_create_entry(title=data["title"], data=data["data"], unique_id=data["unique_id"])

        try:
            found = await async_diseases(self.hass, entry.data[CONF_LANGUAGE])
        except ThlError:
            return self.async_abort(reason="cannot_connect")

        followed = already_followed(entry)
        self._diseases = {sid: name for sid, name in found.items() if sid not in followed}
        if not self._diseases:
            return self.async_abort(reason="all_configured")

        return self.async_show_form(step_id="user", data_schema=disease_schema(self._diseases))


class IliSubentryFlow(ConfigSubentryFlow):
    """Following the flu-like illness visits in primary care. There is nothing to choose."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        if any(subentry.subentry_type == SUBENTRY_ILI for subentry in entry.subentries.values()):
            return self.async_abort(reason="already_configured")
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
        return self.async_create_entry(title=ILI_TITLE[entry.data[CONF_LANGUAGE]], data={}, unique_id=ILI_UNIQUE_ID)
