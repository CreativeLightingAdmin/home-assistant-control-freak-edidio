"""Control Freak eDIDIO Home Assistant Options Flow."""

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
    PROTOCOLS,
)

_LOGGER = logging.getLogger(__name__)


class ControlFreakOptionsFlowHandler(config_entries.OptionsFlow):
    """Control Freak eDIDIO Home Assistant Options Flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.lights = list(config_entry.options.get(CONF_LIGHTS, []))
        self.current_light_index = None

    async def async_step_init(self, user_input=None):
        """Step to start editing lights or prompt to add."""
        if user_input is not None:
            choice = user_input["menu_choice"]
            if choice == "reconfigure_connection":
                _LOGGER.debug("Navigating to reconfigure_connection step")
                return await self.async_step_reconfigure_connection()
            if choice == "manage_lights":
                _LOGGER.debug("Navigating to manage_lights step")
                return await self.async_step_manage_lights()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("menu_choice"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": "reconfigure_connection",
                                    "label": "Reconfigure IP/Port",
                                },
                                {"value": "manage_lights", "label": "Manage Lights"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            description_placeholders={
                "step_title": "Control Freak Options",
            },
        )

    async def async_step_reconfigure_connection(self, user_input=None):
        """Step to reconfigure host and port."""
        errors = {}

        current_host = self.config_entry.data.get(CONF_HOST)
        current_port = self.config_entry.data.get(CONF_PORT)

        if user_input is not None:
            new_host = user_input[CONF_HOST]
            new_port = user_input[CONF_PORT]

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        CONF_HOST: new_host,
                        CONF_PORT: new_port,
                    },
                    options=self.config_entry.options,
                )
                _LOGGER.debug("Reconfigured Host: %s, Port: %s", new_host, new_port)
                # No entities related to host/port, so no explicit reload needed for entities.
                # Just return to initial options flow.
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="reconfigure_connection",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_host): str,
                    vol.Required(CONF_PORT, default=current_port): int,
                }
            ),
            errors=errors,
            description_placeholders={
                "step_title": "Reconfigure Control Freak Connection",
            },
        )

    async def async_step_manage_lights(self, user_input=None):
        """Step to manage lights (add, edit, remove)."""
        errors = {}

        # If no lights are configured, jump to the add_light step
        if not self.lights:
            _LOGGER.debug("No lights configured, going directly to add_light step")
            return await self.async_step_add_light()

        # Process user input for action
        if user_input is not None:
            action = user_input.get("action")
            if action == "edit":
                # Ensure light_index is present before trying to convert
                if "light_index" not in user_input:
                    errors["base"] = "no_light_selected"
                else:
                    self.current_light_index = int(user_input["light_index"])
                    _LOGGER.debug(
                        "Editing light at index: %s", self.current_light_index
                    )
                    return await self.async_step_edit_light()
            elif action == "add":
                _LOGGER.debug("Adding new light")
                return await self.async_step_add_light()
            elif action == "remove":
                # Ensure light_index is present before trying to convert
                if "light_index" not in user_input:
                    errors["base"] = "no_light_selected"
                else:
                    self.current_light_index = int(user_input["light_index"])
                    _LOGGER.debug(
                        "Removing light at index: %s", self.current_light_index
                    )
                    return await self.async_step_remove_light()

            # If errors occurred, or if nothing specific matched, re-show the form with errors
            if errors:
                _LOGGER.debug("Errors found in manage_lights: %s", errors)
                # Fall through to showing the form again with errors

        # Prepare options for the light selection dropdown
        light_names = [
            light.get(CONF_LIGHT_NAME, f"Light {i + 1}")
            for i, light in enumerate(self.lights)
        ]
        light_options_for_selector = [
            {"value": str(i), "label": name} for i, name in enumerate(light_names)
        ]

        # Define the schema for the actions
        schema_dict = {
            vol.Required("action"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "edit", "label": "Edit a Light"},
                        {"value": "add", "label": "Add a Light"},
                        {"value": "remove", "label": "Remove a Light"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        # Add the light_index selector only if there are lights to choose from
        if self.lights:
            schema_dict[
                vol.Required(
                    "light_index", default=str(0 if light_options_for_selector else "")
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=light_options_for_selector,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="manage_lights",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "step_title": "Manage Lights",
                "prompt_message": "Select an action to manage your lights.",
            },
        )

    async def async_step_edit_light(self, user_input=None):
        """Edit selected light's details."""
        errors = {}
        if self.current_light_index is None or not (
            0 <= int(self.current_light_index) < len(self.lights)
        ):
            _LOGGER.error("Invalid light index for edit: %s", self.current_light_index)
            return self.async_abort(reason="invalid_selection")

        light_index = int(self.current_light_index)
        light_to_edit = self.lights[light_index]

        _LOGGER.debug("Edit step: Current index: %s", light_index)
        _LOGGER.debug("Edit step: Light data BEFORE update: %s", light_to_edit)

        if user_input:
            new_name = user_input[CONF_LIGHT_NAME]
            for i, light in enumerate(self.lights):
                # Ensure we are not comparing the light to itself
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
                _LOGGER.debug(
                    "Edit step: Light data AFTER update: %s",
                    self.lights[light_index],
                )
                current_options = dict(self.config_entry.options)
                current_options[CONF_LIGHTS] = self.lights
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=current_options
                )
                # IMPORTANT: Reload the config entry to refresh entities
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return await self.async_step_manage_lights()

        current_data = {
            CONF_LIGHT_NAME: light_to_edit.get(CONF_LIGHT_NAME, ""),
            CONF_LIGHT_ADDRESS: light_to_edit.get(CONF_LIGHT_ADDRESS, 0),
            CONF_LIGHT_PROTOCOL: light_to_edit.get(CONF_LIGHT_PROTOCOL, PROTOCOLS[0]),
            CONF_LIGHT_LINE: light_to_edit.get(CONF_LIGHT_LINE, 1),
        }

        return self.async_show_form(
            step_id="edit_light",
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
                "light_name": light_to_edit.get(CONF_LIGHT_NAME, "this Light"),
                "step_title": "Edit Light",
            },
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
                new_light_id = str(uuid.uuid4())
                self.lights.append(
                    {
                        CONF_LIGHT_NAME: user_input[CONF_LIGHT_NAME],
                        CONF_LIGHT_ADDRESS: user_input[CONF_LIGHT_ADDRESS],
                        CONF_LIGHT_PROTOCOL: user_input[CONF_LIGHT_PROTOCOL],
                        CONF_LIGHT_LINE: user_input[CONF_LIGHT_LINE],
                        CONF_LIGHT_ID: new_light_id,
                    }
                )
                _LOGGER.debug(
                    "Added new light with ID %s: %s",
                    new_light_id,
                    self.lights[-1],
                )
                current_options = dict(self.config_entry.options)
                current_options[CONF_LIGHTS] = self.lights
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=current_options
                )
                # IMPORTANT: Reload the config entry to refresh entities
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
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
            description_placeholders={"step_title": "Add a New Light"},
        )

    async def async_step_remove_light(self, user_input=None):
        """Confirm and remove a light."""
        errors = {}

        # Validate current_light_index *before* attempting to use it
        if self.current_light_index is None or not (
            0 <= int(self.current_light_index) < len(self.lights)
        ):
            _LOGGER.error(
                "Invalid light index for removal: %s",
                self.current_light_index,
            )
            # If invalid, go back to manage_lights with an error
            errors["base"] = "invalid_light_selection_for_removal"
            return await self.async_step_manage_lights()

        light_index = int(self.current_light_index)
        light_name_to_remove = self.lights[light_index].get(
            CONF_LIGHT_NAME, "Unknown Light"
        )
        light_id_to_remove = self.lights[light_index].get(CONF_LIGHT_ID, "No ID")

        _LOGGER.debug(
            "Attempting to remove light at index: %d (Name: %s, ID: %s)",
            light_index,
            light_name_to_remove,
            light_id_to_remove,
        )

        # Check if user has submitted the confirmation form
        if user_input is not None and user_input.get("confirm_remove"):
            self.lights.pop(light_index)
            _LOGGER.debug(
                "Removed light: %s. Remaining lights: %d",
                light_name_to_remove,
                len(self.lights),
            )
            current_options = dict(self.config_entry.options)
            current_options[CONF_LIGHTS] = self.lights
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=current_options
            )

            # if removed_light_id:
            #     _LOGGER.debug(
            #         "Attempting to remove device with ID: %s", removed_light_id
            #     )  # Debug 1: Confirm removed_light_id
            #     device_registry = dr.async_get(self.hass)

            #     # Debug 2: Get all devices and log their identifiers (for comprehensive check)
            #     # This can be very verbose, use with caution in production, but great for debugging.
            #     all_devices = device_registry.devices
            #     _LOGGER.debug("Current devices in registry:")
            #     for dev_id, dev_entry in all_devices.items():
            #         _LOGGER.debug(
            #             "  Device ID: %s, Identifiers: %s",
            #             dev_id,
            #             dev_entry.identifiers,
            #         )

            #     # Debug 3: Log the specific identifiers you are searching for
            #     search_identifiers = {(DOMAIN, removed_light_id)}
            #     _LOGGER.debug(
            #         "Searching for device with identifiers: %s", search_identifiers
            #     )

            #     device = device_registry.async_get_device(
            #         identifiers=search_identifiers  # Use the logged variable here
            #     )

            #     # Debug 4: Check what 'device' is after the lookup
            #     if device:
            #         _LOGGER.debug(
            #             "Found device to remove: ID=%s, Name=%s, Identifiers=%s",
            #             device.id,
            #             device.name,
            #             device.identifiers,
            #         )  # Debug found device details
            #         device_registry.async_remove_device(device.id)
            #         _LOGGER.debug(
            #             "Successfully called async_remove_device for ID: %s", device.id
            #         )
            #     else:
            #         _LOGGER.warning(
            #             "Device not found in registry with identifiers: %s. Cannot remove.",
            #             search_identifiers,
            #         )  # Debug if not found

            # IMPORTANT: Reload the config entry to refresh entities
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            # Go back to light management menu after successful removal
            return await self.async_step_manage_lights()
        if user_input is not None and not user_input.get("confirm_remove"):
            # User clicked submit but did NOT confirm, or clicked cancel (if there was a cancel button)
            _LOGGER.debug(
                "Removal not confirmed by user for light: %s", light_name_to_remove
            )
            return await self.async_step_manage_lights()  # Go back without removing

        # If user_input is None, it means the form is being shown for the first time
        # Show the confirmation form
        return self.async_show_form(
            step_id="remove_light",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm_remove", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={
                "light_name": light_name_to_remove,
            },
        )
