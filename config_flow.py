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
    DOMAIN,
    PROTOCOLS,
)
from .options_flow import ControlFreakOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)  # Add logger for debug messages


class ControlFreakConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Control Freak eDIDIO Config Flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.lights = []  # List to store light configurations during initial setup
        self._host = None
        self._port = None
        self._num_lights = 0
        self._current_light_index = 0

    async def async_step_user(self, user_input=None):
        """Step 1: Gather general information like host, port, and number of lights."""
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]
            self._num_lights = user_input["num_lights"]
            self._current_light_index = 0  # Start at the first light

            # If no lights to configure, create entry directly
            if self._num_lights == 0:
                await self.async_set_unique_id(f"{self._host}-{self._port}")
                self._abort_if_unique_id_configured()  # Check for existing entry

                return self.async_create_entry(
                    title=f"Control Freak ({self._host}:{self._port})",
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                    },
                    options={
                        CONF_LIGHTS: [],  # Empty list of lights
                    },
                )
            # Proceed to configure the first light
            return await self.async_step_light_details()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=23): int,
                    vol.Required("num_lights", default=1): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    ),
                }
            ),
        )

    async def async_step_light_details(self, user_input=None):
        """Step 2: Gather details for each light (name, address, protocol, line)."""
        # If user input is provided, save the current light details
        if user_input is not None:
            # Generate a stable ID for the light before adding it to the list
            light_id = str(uuid.uuid4())  # Generate a new UUID
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
            self._current_light_index += 1

        # Check if we've added all lights
        if self._current_light_index < self._num_lights:
            # If more lights to configure, show form for the next light
            return self.async_show_form(
                step_id="light_details",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_LIGHT_NAME): str,
                        vol.Required(CONF_LIGHT_ADDRESS): vol.All(
                            vol.Coerce(int), vol.Range(min=0)
                        ),  # Validate address
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
                # Use description_placeholders to guide the user
                description_placeholders={
                    "light_number": self._current_light_index + 1,
                    "total_lights": self._num_lights,
                    "step_title": "Add a Light",
                },
            )
        # All lights configured, finish and create the configuration entry
        # Ensure we also call async_set_unique_id for the config entry itself
        await self.async_set_unique_id(f"{self._host}-{self._port}")
        self._abort_if_unique_id_configured()  # Check for existing entry

        return self.async_create_entry(
            title=f"Control Freak ({self._host}:{self._port})",
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
            },
            options={
                CONF_LIGHTS: self.lights,  # Store collected lights with IDs in options
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ControlFreakOptionsFlowHandler:
        """Get the options flow for this handler."""
        return ControlFreakOptionsFlowHandler(config_entry)
