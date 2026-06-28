import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_LANGUAGE, LANGUAGES

_LOGGER = logging.getLogger(__name__)

CONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LANGUAGE): vol.All(cv.string, vol.In(LANGUAGES)),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, any] = None) -> FlowResult:

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=CONFIGURE_SCHEMA, last_step=True)

        await self.async_set_unique_id("thl_covid")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title="THL Covid stats", data=user_input)
