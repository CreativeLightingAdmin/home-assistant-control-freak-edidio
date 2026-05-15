"""Config Flow for Control Freak eDIDIO integration with Home Assistant."""

import logging
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_HOST,
    CONF_LIGHT_ADDRESS,
    CONF_LIGHT_ID,
    CONF_LIGHT_LINE,
    CONF_LIGHT_NAME,
    CONF_LIGHT_PROTOCOL,
    CONF_LIGHTS,
    CONF_PORT,
    CONF_TLS,
    DEFAULT_PORT,
    DEFAULT_TLS_PORT,
    DOMAIN,
    PROTOCOLS,
)
from .options_flow import ControlFreakOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)


class ControlFreakConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Control Freak eDIDIO Config Flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.lights = []
        self._host = None
        self._port = None
        self._tls = False

    async def async_step_user(self, user_input=None):
        """Gather connection details."""
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._tls = user_input[CONF_TLS]
            self._port = user_input[CONF_PORT]
            return await self.async_step_add_another()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_TLS, default=False): bool,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            description_placeholders={
                "tls_port": str(DEFAULT_TLS_PORT),
                "plain_port": str(DEFAULT_PORT),
            },
        )

    async def async_step_add_another(self, user_input=None):
        """Menu: add another light or finish setup."""
        return self.async_show_menu(
            step_id="add_another",
            menu_options=["configure_light", "finish_setup"],
        )

    async def async_step_configure_light(self, user_input=None):
        """Add a light during initial setup."""
        if user_input is not None:
            light_id = str(uuid.uuid4())
            _LOGGER.debug(
                "Generated stable ID for light '%s': %s",
                user_input[CONF_LIGHT_NAME],
                light_id,
            )
            self.lights.append(
                {
                    CONF_LIGHT_NAME: user_input[CONF_LIGHT_NAME],
                    CONF_LIGHT_ADDRESS: user_input[CONF_LIGHT_ADDRESS],
                    CONF_LIGHT_PROTOCOL: user_input[CONF_LIGHT_PROTOCOL],
                    CONF_LIGHT_LINE: user_input[CONF_LIGHT_LINE],
                    CONF_LIGHT_ID: light_id,
                }
            )
            return await self.async_step_add_another()

        return self.async_show_form(
            step_id="configure_light",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LIGHT_NAME): str,
                    vol.Required(CONF_LIGHT_ADDRESS): vol.All(
                        vol.Coerce(int), vol.Range(min=0)
                    ),
                    vol.Required(CONF_LIGHT_PROTOCOL): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=PROTOCOLS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_LIGHT_LINE, default=1): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    ),
                }
            ),
            description_placeholders={
                "light_number": str(len(self.lights) + 1),
            },
        )

    async def async_step_finish_setup(self, user_input=None):
        """Create the config entry."""
        await self.async_set_unique_id(f"{self._host}-{self._port}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Control Freak ({self._host}:{self._port})",
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_TLS: self._tls,
            },
            options={
                CONF_LIGHTS: self.lights,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ControlFreakOptionsFlowHandler:
        """Get the options flow for this handler."""
        return ControlFreakOptionsFlowHandler(config_entry)
