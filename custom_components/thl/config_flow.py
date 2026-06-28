import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import DOMAIN, CONF_LANGUAGE, CONF_DISEASE_ID, CONF_DISEASE_NAME, LANGUAGES
from .session import ThlSession, ThlException

_LOGGER = logging.getLogger(__name__)

LANGUAGE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LANGUAGE): vol.All(cv.string, vol.In(LANGUAGES)),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    _language: str = None
    _diseases: dict[str, str] = None

    async def async_step_user(self, user_input: dict[str, any] = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=LANGUAGE_SCHEMA)

        self._language = user_input[CONF_LANGUAGE]
        self._diseases = None
        return await self.async_step_disease()

    async def async_step_disease(self, user_input: dict[str, any] = None) -> FlowResult:
        if user_input is not None:
            disease_id = user_input[CONF_DISEASE_ID]
            disease_name = self._diseases.get(disease_id, disease_id)

            await self.async_set_unique_id(f"thl_{disease_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"THL {disease_name}",
                data={
                    CONF_LANGUAGE: self._language,
                    CONF_DISEASE_ID: disease_id,
                    CONF_DISEASE_NAME: disease_name,
                },
            )

        if self._diseases is None:
            try:
                session = ThlSession(self._language)
                self._diseases = await self.hass.async_add_executor_job(session.get_diseases)
            except ThlException:
                return self.async_abort(reason="cannot_connect")

        options = [{"value": sid, "label": name} for sid, name in self._diseases.items()]
        schema = vol.Schema({
            vol.Required(CONF_DISEASE_ID): SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            )
        })

        return self.async_show_form(step_id="disease", data_schema=schema, last_step=True)

    async def async_step_reconfigure(self, user_input: dict[str, any] = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="reconfigure", data_schema=LANGUAGE_SCHEMA)

        entry = self._get_reconfigure_entry()
        language = user_input[CONF_LANGUAGE]
        disease_id = entry.data[CONF_DISEASE_ID]
        disease_name = entry.data[CONF_DISEASE_NAME]

        try:
            session = ThlSession(language)
            diseases = await self.hass.async_add_executor_job(session.get_diseases)
            disease_name = diseases.get(disease_id, disease_name)
        except ThlException:
            return self.async_abort(reason="cannot_connect")

        return self.async_update_reload_and_abort(
            entry,
            data={
                **entry.data,
                CONF_LANGUAGE: language,
                CONF_DISEASE_NAME: disease_name,
            },
        )
