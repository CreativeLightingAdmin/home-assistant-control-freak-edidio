"""Control Freak eDIDIO Home Assistant Options Flow."""

import copy
import logging
import uuid

import voluptuous as vol

from homeassistant import config_entries
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
    PROTOCOLS,
)

_LOGGER = logging.getLogger(__name__)


class ControlFreakOptionsFlowHandler(config_entries.OptionsFlow):
    """Control Freak eDIDIO Home Assistant Options Flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.lights = copy.deepcopy(config_entry.options.get(CONF_LIGHTS, []))
        self.current_light_index = None

    async def async_step_init(self, user_input=None):
        """Show main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["reconfigure_connection", "manage_lights"],
        )

    async def async_step_reconfigure_connection(self, user_input=None):
        """Reconfigure host, port, and TLS."""
        errors = {}

        current_host = self.config_entry.data.get(CONF_HOST)
        current_port = self.config_entry.data.get(CONF_PORT)
        current_tls = self.config_entry.data.get(CONF_TLS, False)

        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_TLS: user_input[CONF_TLS],
                },
            )
            _LOGGER.debug(
                "Reconfigured Host: %s, Port: %s, TLS: %s",
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_TLS],
            )
            return self.async_create_entry(title="", data=dict(self.config_entry.options))

        return self.async_show_form(
            step_id="reconfigure_connection",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_host): str,
                    vol.Required(CONF_TLS, default=current_tls): bool,
                    vol.Required(CONF_PORT, default=current_port): int,
                }
            ),
            errors=errors,
            description_placeholders={
                "tls_port": str(DEFAULT_TLS_PORT),
                "plain_port": str(DEFAULT_PORT),
            },
        )

    async def async_step_manage_lights(self, user_input=None):
        """Show lights management menu."""
        if self.lights:
            menu_options = ["add_light", "edit_light", "remove_light", "finish"]
        else:
            menu_options = ["add_light", "finish"]

        return self.async_show_menu(
            step_id="manage_lights",
            menu_options=menu_options,
        )

    async def async_step_add_light(self, user_input=None):
        """Add a new light."""
        errors = {}

        if user_input:
            for light in self.lights:
                if light.get(CONF_LIGHT_NAME) == user_input[CONF_LIGHT_NAME]:
                    errors["base"] = "duplicate_light_name"
                    _LOGGER.warning(
                        "Duplicate light name detected during add: %s",
                        user_input[CONF_LIGHT_NAME],
                    )
                    break

            if not errors:
                self.lights.append(
                    {
                        CONF_LIGHT_NAME: user_input[CONF_LIGHT_NAME],
                        CONF_LIGHT_ADDRESS: user_input[CONF_LIGHT_ADDRESS],
                        CONF_LIGHT_PROTOCOL: user_input[CONF_LIGHT_PROTOCOL],
                        CONF_LIGHT_LINE: user_input[CONF_LIGHT_LINE],
                        CONF_LIGHT_ID: str(uuid.uuid4()),
                    }
                )
                return await self.async_step_manage_lights()

        return self.async_show_form(
            step_id="add_light",
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
            errors=errors,
        )

    async def async_step_edit_light(self, user_input=None):
        """Pick which light to edit."""
        errors = {}

        if user_input is not None:
            self.current_light_index = int(user_input["light_index"])
            return await self.async_step_edit_light_details()

        light_options = [
            {"value": str(i), "label": light.get(CONF_LIGHT_NAME, f"Light {i + 1}")}
            for i, light in enumerate(self.lights)
        ]

        return self.async_show_form(
            step_id="edit_light",
            data_schema=vol.Schema(
                {
                    vol.Required("light_index", default="0"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=light_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_edit_light_details(self, user_input=None):
        """Edit the selected light's details."""
        errors = {}

        if self.current_light_index is None or not (
            0 <= int(self.current_light_index) < len(self.lights)
        ):
            _LOGGER.error("Invalid light index for edit: %s", self.current_light_index)
            return self.async_abort(reason="invalid_selection")

        light_index = int(self.current_light_index)
        light_to_edit = self.lights[light_index]

        if user_input:
            new_name = user_input[CONF_LIGHT_NAME]
            for i, light in enumerate(self.lights):
                if i != light_index and light.get(CONF_LIGHT_NAME) == new_name:
                    errors["base"] = "duplicate_light_name"
                    _LOGGER.warning("Duplicate light name detected: %s", new_name)
                    break

            if not errors:
                light_to_edit.update(
                    {
                        CONF_LIGHT_NAME: user_input[CONF_LIGHT_NAME],
                        CONF_LIGHT_ADDRESS: user_input[CONF_LIGHT_ADDRESS],
                        CONF_LIGHT_PROTOCOL: user_input[CONF_LIGHT_PROTOCOL],
                        CONF_LIGHT_LINE: user_input[CONF_LIGHT_LINE],
                    }
                )
                return await self.async_step_manage_lights()

        current_data = {
            CONF_LIGHT_NAME: light_to_edit.get(CONF_LIGHT_NAME, ""),
            CONF_LIGHT_ADDRESS: light_to_edit.get(CONF_LIGHT_ADDRESS, 0),
            CONF_LIGHT_PROTOCOL: light_to_edit.get(CONF_LIGHT_PROTOCOL, PROTOCOLS[0]),
            CONF_LIGHT_LINE: light_to_edit.get(CONF_LIGHT_LINE, 1),
        }

        return self.async_show_form(
            step_id="edit_light_details",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LIGHT_NAME, default=current_data[CONF_LIGHT_NAME]
                    ): str,
                    vol.Required(
                        CONF_LIGHT_ADDRESS, default=current_data[CONF_LIGHT_ADDRESS]
                    ): vol.All(vol.Coerce(int), vol.Range(min=0)),
                    vol.Required(
                        CONF_LIGHT_PROTOCOL, default=current_data[CONF_LIGHT_PROTOCOL]
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=PROTOCOLS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_LIGHT_LINE, default=current_data[CONF_LIGHT_LINE]
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                }
            ),
            errors=errors,
            description_placeholders={
                "light_name": light_to_edit.get(CONF_LIGHT_NAME, "this light"),
            },
        )

    async def async_step_remove_light(self, user_input=None):
        """Pick and confirm removal of a light."""
        if user_input is not None:
            light_index = int(user_input["light_index"])
            if user_input.get("confirm_remove"):
                light_name = self.lights[light_index].get(CONF_LIGHT_NAME, "Unknown Light")
                self.lights.pop(light_index)
                _LOGGER.debug(
                    "Removed light: %s. Remaining lights: %d",
                    light_name,
                    len(self.lights),
                )
            return await self.async_step_manage_lights()

        light_options = [
            {"value": str(i), "label": light.get(CONF_LIGHT_NAME, f"Light {i + 1}")}
            for i, light in enumerate(self.lights)
        ]

        return self.async_show_form(
            step_id="remove_light",
            data_schema=vol.Schema(
                {
                    vol.Required("light_index", default="0"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=light_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required("confirm_remove", default=False): bool,
                }
            ),
        )

    async def async_step_finish(self, user_input=None):
        """Save lights and close."""
        return self.async_create_entry(title="", data={CONF_LIGHTS: self.lights})
