"""Light Object for Control Freak eDIDIO integration with Home Assistant."""

import logging
import uuid

# Import client library
from edidio_control_py import (
    DALI_ARC_LEVEL_MAX,
    EdidioClient,
    eDS10_ProtocolBuffer_pb2 as pb,
)
from edidio_control_py.exceptions import (
    EDIDIOCommunicationError,
    EDIDIOConnectionError,
    EDIDIOTimeoutError,
)

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired,
    color_temperature_mired_to_kelvin,
)

from .const import (
    CONF_LIGHT_ADDRESS,
    CONF_LIGHT_ID,
    CONF_LIGHT_LINE,
    CONF_LIGHT_NAME,
    CONF_LIGHT_PROTOCOL,
    CONF_LIGHTS,
    DOMAIN,
    PROTOCOL_DALI_DT8_CCT,
    PROTOCOL_DALI_DT8_XY,
    PROTOCOL_DALI_RGB,
    PROTOCOL_DALI_RGBW,
    PROTOCOL_DALI_WHITE,
    PROTOCOL_DMX_RGB,
    PROTOCOL_DMX_RGBW,
    PROTOCOL_DMX_WHITE,
)

_LOGGER = logging.getLogger(__name__)


# --- Message ID Generator Function ---
def get_message_id_generator():
    """Return a function that generates incrementing message IDs.

    Each call to the returned function will increment the ID.
    """

    current_id = 0

    def increment_and_get_id():
        nonlocal current_id
        current_id += 1
        return current_id

    return increment_and_get_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,  # This 'entry' is already the config_entry object passed by HA
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Control Freak lights from config entry."""
    client_data = hass.data[DOMAIN][entry.entry_id]
    client: EdidioClient = client_data["client"]  # Type hint for clarity

    get_next_message_id = get_message_id_generator()

    # Get the lights configuration directly from the entry.options
    lights_config = entry.options.get(CONF_LIGHTS, [])
    _LOGGER.debug(
        "Light platform async_setup_entry: retrieved lights_config: %s", lights_config
    )

    entities_to_add = []
    for light_data in lights_config:
        if CONF_LIGHT_ID not in light_data:
            _LOGGER.error(
                "Light data missing unique ID (%s). Skipping entity creation for: %s",
                CONF_LIGHT_ID,
                light_data,
            )
            continue
        if CONF_LIGHT_ADDRESS not in light_data:
            _LOGGER.error(
                "Light data missing address (%s). Skipping entity creation for: %s",
                CONF_LIGHT_ADDRESS,
                light_data,
            )
            continue
        if CONF_LIGHT_NAME not in light_data:
            _LOGGER.error(
                "Light data missing name (%s). Skipping entity creation for: %s",
                CONF_LIGHT_NAME,
                light_data,
            )
            continue
        if CONF_LIGHT_PROTOCOL not in light_data:
            _LOGGER.error(
                "Light data missing protocol (%s). Skipping entity creation for: %s",
                CONF_LIGHT_PROTOCOL,
                light_data,
            )
            continue

        entities_to_add.append(
            ControlFreakLight(
                client,
                light_data[CONF_LIGHT_ADDRESS],
                light_data[CONF_LIGHT_NAME],
                light_data[CONF_LIGHT_PROTOCOL],
                get_next_message_id,
                line=light_data.get(CONF_LIGHT_LINE, 1),  # Default to 1 if not present
                stable_id=light_data.get(CONF_LIGHT_ID),  # Pass the stable ID
            )
        )

    if entities_to_add:
        async_add_entities(entities_to_add)
        _LOGGER.debug("Added %d Control Freak light entities", len(entities_to_add))
    else:
        _LOGGER.debug("No Control Freak light entities to add")


class ControlFreakLight(LightEntity):
    """Light Object for the Contrl Freak Controller."""

    def __init__(
        self,
        client: EdidioClient,
        address: int,
        name: str,
        protocol: str,
        get_message_id_func,
        line: int = 1,
        stable_id: str | None = None,
    ) -> None:
        """Initialize the light."""
        self._client = client
        self._address = address
        self._name = name
        self._protocol = protocol
        self._line = line
        self._get_message_id = get_message_id_func

        # Store and use the stable ID for unique_id
        if stable_id:
            self._attr_unique_id = f"{DOMAIN}_{stable_id}"
            self._stable_id_value = stable_id
            _LOGGER.debug(
                "Light '%s' initialized with stable ID: %s", name, self._attr_unique_id
            )
        else:
            new_uuid = str(uuid.uuid4())
            self._attr_unique_id = f"{DOMAIN}_{new_uuid}"
            self._stable_id_value = new_uuid
            _LOGGER.warning(
                "Light '%s' initialized without a stable ID. Generating a new one: %s "
                "Please update configuration via options flow to persist this ID to avoid entity re-creation on restart",
                name,
                self._attr_unique_id,
            )

        # Initial state
        self._is_on = False
        self._brightness = 255  # Home Assistant brightness (0-255)
        self._rgb_color = (255, 255, 255)  # Internal state for RGB
        self._rgbw_color = (255, 255, 255, 255)  # Internal state for RGBW (R, G, B, W)
        self._color_temp = 3000

        # Set min/max color temp based on protocol
        if self._protocol == PROTOCOL_DALI_DT8_CCT:
            self._attr_min_color_temp_kelvin = 2000
            self._attr_max_color_temp_kelvin = 6500
        else:
            self._attr_min_color_temp_kelvin = None
            self._attr_max_color_temp_kelvin = None

        # Default availability until update confirms connection
        self._attr_available = True

    @property
    def unique_id(self):
        """Return the unique ID for this light."""
        return self._attr_unique_id

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return the supported color modes based on protocol."""
        if self._protocol in [PROTOCOL_DALI_RGB, PROTOCOL_DMX_RGB]:
            return {ColorMode.RGB}
        if self._protocol in [
            PROTOCOL_DALI_RGBW,
            PROTOCOL_DMX_RGBW,
            PROTOCOL_DALI_DT8_XY,
        ]:
            return {ColorMode.RGBW}
        if self._protocol == PROTOCOL_DALI_DT8_CCT:
            return {ColorMode.COLOR_TEMP}
        return {ColorMode.BRIGHTNESS}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode of the light."""
        if self._protocol in [PROTOCOL_DALI_RGB, PROTOCOL_DMX_RGB]:
            return ColorMode.RGB
        if self._protocol in [
            PROTOCOL_DALI_RGBW,
            PROTOCOL_DMX_RGBW,
            PROTOCOL_DALI_DT8_XY,
        ]:
            return ColorMode.RGBW
        if self._protocol == PROTOCOL_DALI_DT8_CCT:
            return ColorMode.COLOR_TEMP
        return ColorMode.BRIGHTNESS

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def is_on(self):
        """Return true if the light is on."""
        return self._is_on

    @property
    def brightness(self):
        """Return the brightness of the light (0-255)."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the RGB color of the light."""
        return self._rgb_color

    @property
    def rgbw_color(self):
        """Return the RGBW color of the light."""
        if self._protocol in [
            PROTOCOL_DALI_RGBW,
            PROTOCOL_DMX_RGBW,
            PROTOCOL_DALI_DT8_XY,
        ]:
            return self._rgbw_color
        return None

    @property
    def color_temp_kelvin(self):
        """Return the color temperature of the light in Kelvin."""
        if self._protocol == PROTOCOL_DALI_DT8_CCT and self._color_temp is not None:
            return color_temperature_mired_to_kelvin(self._color_temp)
        return None

    @property
    def min_mireds(self):
        """Return the minimum color temperature that this light supports."""
        if self._protocol == PROTOCOL_DALI_DT8_CCT:
            # These values should match _attr_min/max_color_temp_kelvin conversion
            # 6500K -> approx 153 mireds
            # 2000K -> approx 500 mireds
            return color_temperature_kelvin_to_mired(self._attr_max_color_temp_kelvin)
        return None

    @property
    def max_mireds(self):
        """Return the maximum color temperature that this light supports."""
        if self._protocol == PROTOCOL_DALI_DT8_CCT:
            return color_temperature_kelvin_to_mired(self._attr_min_color_temp_kelvin)
        return None

    @property
    def available(self):
        """Return True if the device is connected and available."""
        return self._attr_available

    async def async_turn_on(self, **kwargs):
        """Turn the light on with brightness and color control."""
        # 1. Update internal state based on kwargs
        if "brightness" in kwargs:
            self._brightness = kwargs["brightness"]
        elif not self._is_on and self._brightness == 0:
            self._brightness = 255

        if "rgb_color" in kwargs:
            self._rgb_color = kwargs["rgb_color"]
        if "rgbw_color" in kwargs:
            self._rgbw_color = kwargs["rgbw_color"]
            self._rgb_color = self._rgbw_color[:3]  # Keep RGB part updated

        if "color_temp_kelvin" in kwargs:
            self._color_temp = color_temperature_kelvin_to_mired(
                kwargs["color_temp_kelvin"]
            )

        commands_to_send = []  # This list will hold raw protobuf messages

        # 2. Generate commands based on protocol and updated internal state
        try:
            if self._protocol == PROTOCOL_DMX_RGB:
                r, g, b = self._rgb_color[:3]
                scaling_factor = self._brightness / 255.0
                scaled_r = int(r * scaling_factor)
                scaled_g = int(g * scaling_factor)
                scaled_b = int(b * scaling_factor)

                commands_to_send.append(
                    self._client.create_dmx_message(
                        message_id=self._get_message_id(),
                        zone=0,
                        universe_mask=0b0010,
                        channel=self._address,
                        repeat=1,
                        level=[scaled_r, scaled_g, scaled_b],
                        fade_time_by_10ms=25,
                    )
                )
                _LOGGER.debug(
                    "Generated DMX_RGB color command(s) for %s (RGB: %s, Brightness: %s). Total commands: %s",
                    self._name,
                    self._rgb_color,
                    self._brightness,
                    len(commands_to_send),
                )

            elif self._protocol == PROTOCOL_DMX_RGBW:
                r, g, b, w = self._rgbw_color[:4]
                scaling_factor = self._brightness / 255.0
                scaled_r = int(r * scaling_factor)
                scaled_g = int(g * scaling_factor)
                scaled_b = int(b * scaling_factor)
                scaled_w = int(w * scaling_factor)

                commands_to_send.append(
                    self._client.create_dmx_message(
                        message_id=self._get_message_id(),
                        zone=0,
                        universe_mask=0b0010,
                        channel=self._address,
                        repeat=1,
                        level=[scaled_r, scaled_g, scaled_b, scaled_w],
                        fade_time_by_10ms=25,
                    )
                )
                _LOGGER.debug(
                    "Generated DMX_RGBW color command(s) for %s (RGBW: %s, Brightness: %s). Total commands: %s",
                    self._name,
                    self._rgbw_color,
                    self._brightness,
                    len(commands_to_send),
                )

            elif self._protocol == PROTOCOL_DALI_RGB:
                dali_max_val = DALI_ARC_LEVEL_MAX
                ha_max = 255.0

                effective_r = int(self._rgb_color[0] * (self._brightness / ha_max))
                effective_g = int(self._rgb_color[1] * (self._brightness / ha_max))
                effective_b = int(self._rgb_color[2] * (self._brightness / ha_max))

                dali_r = min(int(effective_r * (dali_max_val / ha_max)), dali_max_val)
                dali_g = min(int(effective_g * (dali_max_val / ha_max)), dali_max_val)
                dali_b = min(int(effective_b * (dali_max_val / ha_max)), dali_max_val)

                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_r],
                    )
                )
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address + 1,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_g],
                    )
                )
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address + 2,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_b],
                    )
                )
                _LOGGER.debug(
                    "Generated DALI_RGB commands for %s (RGB: %s, Brightness: %s). Total commands: %s",
                    self._name,
                    self._rgb_color,
                    self._brightness,
                    len(commands_to_send),
                )

            elif self._protocol == PROTOCOL_DALI_RGBW:
                # Ensure self._rgbw_color is (R, G, B, W)
                r, g, b, w = (
                    self._rgbw_color
                    if len(self._rgbw_color) == 4
                    else (
                        self._rgb_color[0],
                        self._rgb_color[1],
                        self._rgb_color[2],
                        255,  # Default white to full if only RGB is provided
                    )
                )

                dali_max_val = DALI_ARC_LEVEL_MAX
                ha_max = 255.0

                effective_r = int(r * (self._brightness / ha_max))
                effective_g = int(g * (self._brightness / ha_max))
                effective_b = int(b * (self._brightness / ha_max))
                effective_w = int(
                    w * (self._brightness / ha_max)
                )  # Apply brightness to white channel

                dali_r = min(int(effective_r * (dali_max_val / ha_max)), dali_max_val)
                dali_g = min(int(effective_g * (dali_max_val / ha_max)), dali_max_val)
                dali_b = min(int(effective_b * (dali_max_val / ha_max)), dali_max_val)
                dali_w = min(int(effective_w * (dali_max_val / ha_max)), dali_max_val)

                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_r],
                    )
                )
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address + 1,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_g],
                    )
                )
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address + 2,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_b],
                    )
                )
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address + 3,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_w],
                    )
                )
                _LOGGER.debug(
                    "Generated DALI_RGBW commands for %s (RGBW: %s, Brightness: %s). Total commands: %s",
                    self._name,
                    self._rgbw_color,
                    self._brightness,
                    len(commands_to_send),
                )

            elif self._protocol == PROTOCOL_DALI_DT8_XY:
                # Ensure self._rgbw_color is (R, G, B, W)
                r, g, b, w = (
                    self._rgbw_color
                    if len(self._rgbw_color) == 4
                    else (
                        *self._rgb_color,
                        255,
                    )  # Default white to full if only RGB is provided
                )

                x16, y16 = rgb_to_xy_16bit(r, g, b)

                # Break 16-bit values into LSB/MSB
                x_lsb, x_msb = x16 & 0xFF, (x16 >> 8) & 0xFF
                y_lsb, y_msb = y16 & 0xFF, (y16 >> 8) & 0xFF

                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        type8=pb.Type8CommandType.SET_TEMP_X_COORD,
                        dtr=[x_lsb, x_msb],
                    )
                )

                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        type8=pb.Type8CommandType.SET_TEMP_Y_COORD,
                        dtr=[y_lsb, y_msb],
                    )
                )

                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[int(self._brightness / 255.0 * DALI_ARC_LEVEL_MAX)],
                    )
                )

                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        type8=pb.Type8CommandType.ACTIVATE,
                    )
                )

                _LOGGER.debug(
                    "Generated DALI DT8 XY commands for %s (RGB: %s, Brightness: %s). XY: (%s, %s)",
                    self._name,
                    (r, g, b),
                    self._brightness,
                    x16,
                    y16,
                )
            elif self._protocol == PROTOCOL_DALI_DT8_CCT:
                if self._color_temp is not None:
                    # Convert HA mireds to DALI DT8 Color Temperature (0-65535)
                    # Note: DALI DT8 Color Temperature is not directly Mireds or Kelvin.
                    # It's a scaled value from Min to Max Colour Temperature.
                    # DALI DT8 range is 0 (warmest, max mireds) to 65535 (coolest, min mireds).

                    # HA mireds: min_mireds (coolest) to max_mireds (warmest)
                    # DALI DT8: 0 (warmest) to 65535 (coolest)

                    # Map HA mireds (e.g., 153-500) to DALI DT8 range (0-65535)
                    # min_mireds -> 65535 (coolest)
                    # max_mireds -> 0 (warmest)

                    # Normalize HA mireds to 0-1 (0 is warmest, 1 is coolest)
                    normalized_mired = (self._color_temp - self.max_mireds) / (
                        self.min_mireds - self.max_mireds
                    )

                    # Invert and scale to DALI DT8 range (0 warmest, 65535 coolest)
                    dali_dt8_cct_value = int((1 - normalized_mired) * 65535)

                    # This acts as a safety clamp
                    dali_dt8_cct_value = max(0, min(65535, dali_dt8_cct_value))

                    # Split the 16-bit value into Least Significant Byte (LSB) and Most Significant Byte (MSB).
                    dali_cct_lsb = dali_dt8_cct_value & 0xFF
                    dali_cct_msb = (dali_dt8_cct_value >> 8) & 0xFF

                    commands_to_send.append(
                        self._client.create_dali_message(
                            message_id=self._get_message_id(),
                            line_mask=self._line,
                            address=self._address,
                            type8=pb.Type8CommandType.SET_TEMP_COLOUR_TEMPERATURE,
                            dtr=[dali_cct_lsb, dali_cct_msb],
                        )
                    )

                    # Also send brightness for CCT
                    commands_to_send.append(
                        self._client.create_dali_message(
                            message_id=self._get_message_id(),
                            line_mask=self._line,
                            address=self._address,
                            custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                            arg=[int(self._brightness / 255.0 * DALI_ARC_LEVEL_MAX)],
                        )
                    )

                    # Send DT8 Activate
                    commands_to_send.append(
                        self._client.create_dali_message(
                            message_id=self._get_message_id(),
                            line_mask=self._line,
                            address=self._address,
                            type8=pb.Type8CommandType.ACTIVATE,
                        )
                    )

                    _LOGGER.debug(
                        "Generated DALI DT8 CCT commands for %s (HA Mireds: %s, DALI DT8 CCT: %s, Brightness: %s). Total commands: %s",
                        self._name,
                        self._color_temp,
                        dali_dt8_cct_value,
                        self._brightness,
                        len(commands_to_send),
                    )

            elif self._protocol == PROTOCOL_DALI_WHITE:
                dali_arc_level = int(self._brightness / 255.0 * DALI_ARC_LEVEL_MAX)
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_arc_level],
                    )
                )
                _LOGGER.debug(
                    "Generated DALI_WHITE brightness command for %s (Brightness: %s). Total commands: %s",
                    self._name,
                    self._brightness,
                    len(commands_to_send),
                )

            elif self._protocol == PROTOCOL_DMX_WHITE:
                commands_to_send.append(
                    self._client.create_dmx_message(
                        message_id=self._get_message_id(),
                        zone=0,
                        universe_mask=0b0010,
                        channel=self._address,
                        repeat=1,
                        level=[self._brightness],
                        fade_time_by_10ms=25,  # Set Nice Fade Time
                    )
                )
                _LOGGER.debug(
                    "Generated DMX_WHITE brightness command for %s (Brightness: %s). Total commands: %s",
                    self._name,
                    self._brightness,
                    len(commands_to_send),
                )

            else:
                _LOGGER.warning(
                    "Unsupported protocol '%s' for light %s. Sending brightness command as fallback",
                    self._protocol,
                    self._name,
                )
                # Default to DALI white if it's the most common fallback, otherwise handle DMX/etc.
                # For now, replicate the DALI_WHITE logic for fallback:
                dali_arc_level = int(self._brightness / 255.0 * DALI_ARC_LEVEL_MAX)
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),  # Use the incrementing function
                        line_mask=self._line,
                        address=self._address,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_arc_level],
                    )
                )

            # 3. Send all generated commands sequentially using the client
            if not commands_to_send:
                _LOGGER.warning(
                    "No commands generated for light %s with protocol %s",
                    self._name,
                    self._protocol,
                )
                return

            await self._client.send_dali_commands_sequence(commands_to_send)

        except (
            EDIDIOConnectionError,
            EDIDIOCommunicationError,
            EDIDIOTimeoutError,
        ) as e:
            _LOGGER.error("Communication error turning on light %s: %s", self._name, e)
            self._attr_available = False
            return
        except Exception:
            _LOGGER.exception(
                "An unexpected error occurred while turning on light %s", self._name
            )
            self._attr_available = False
            return

        # 4. Update internal entity state and notify Home Assistant
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        commands_to_send = []

        try:
            # For DMX, sending brightness 0 or all channels to 0
            if self._protocol in [
                PROTOCOL_DMX_RGB,
                PROTOCOL_DMX_RGBW,
                PROTOCOL_DMX_WHITE,
            ]:
                # Send 0 brightness to all channels for DMX
                if self._protocol == PROTOCOL_DMX_RGB:
                    commands_to_send.append(
                        self._client.create_dmx_message(
                            message_id=self._get_message_id(),
                            zone=0,
                            universe_mask=0b0010,
                            channel=self._address,
                            repeat=1,
                            level=[0, 0, 0],
                            fade_time_by_10ms=25,
                        )
                    )
                elif self._protocol == PROTOCOL_DMX_RGBW:
                    commands_to_send.append(
                        self._client.create_dmx_message(
                            message_id=self._get_message_id(),
                            zone=0,
                            universe_mask=0b0010,
                            channel=self._address,
                            repeat=1,
                            level=[0, 0, 0, 0],
                            fade_time_by_10ms=25,
                        )
                    )
                elif self._protocol == PROTOCOL_DMX_WHITE:
                    commands_to_send.append(
                        self._client.create_dmx_message(
                            message_id=self._get_message_id(),
                            zone=0,
                            universe_mask=0b0010,
                            channel=self._address,
                            repeat=1,
                            level=[0],
                            fade_time_by_10ms=25,
                        )
                    )
                _LOGGER.debug(
                    "Turning off %s (%s) by sending zero DMX levels",
                    self._name,
                    self._protocol,
                )
            # For DALI, sending ARC_LEVEL to 0 is common
            elif self._protocol in [
                PROTOCOL_DALI_DT8_XY,
                PROTOCOL_DALI_DT8_CCT,
                PROTOCOL_DALI_WHITE,
            ]:
                dali_arc_level = 0  # Zero brightness
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[dali_arc_level],
                    )
                )
                _LOGGER.debug(
                    "Turning off %s (%s) by sending DALI ARC_LEVEL 0",
                    self._name,
                    self._protocol,
                )

            elif self._protocol == PROTOCOL_DALI_RGB:
                channel_count = 3  # RGB has 3 channels
                commands_to_send.extend(
                    [
                        self._client.create_dali_message(
                            message_id=self._get_message_id(),
                            line_mask=self._line,
                            address=self._address + i,
                            custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                            arg=[0],
                        )
                        for i in range(channel_count)
                    ]
                )
            elif self._protocol == PROTOCOL_DALI_RGBW:
                channel_count = 4  # RGBW has 4 channels
                commands_to_send.extend(
                    [
                        self._client.create_dali_message(
                            message_id=self._get_message_id(),
                            line_mask=self._line,
                            address=self._address + i,
                            custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                            arg=[0],
                        )
                        for i in range(channel_count)
                    ]
                )
            else:
                _LOGGER.warning(
                    "Unsupported protocol '%s' for light %s. Defaulting to DALI ARC_LEVEL 0 for turn off",
                    self._protocol,
                    self._name,
                )
                commands_to_send.append(
                    self._client.create_dali_message(
                        message_id=self._get_message_id(),
                        line_mask=self._line,
                        address=self._address,
                        custom_command=pb.CustomDALICommandType.DALI_ARC_LEVEL,
                        arg=[0],
                    )
                )

            if not commands_to_send:
                _LOGGER.warning(
                    "No commands generated for turning off light %s with protocol %s",
                    self._name,
                    self._protocol,
                )
                return

            await self._client.send_dali_commands_sequence(commands_to_send)

        except (
            EDIDIOConnectionError,
            EDIDIOCommunicationError,
            EDIDIOTimeoutError,
        ) as e:
            _LOGGER.error("Communication error turning off light %s: %s", self._name, e)
            self._attr_available = False
            return
        except Exception:
            _LOGGER.exception(
                "An unexpected error occurred while turning off light %s", self._name
            )
            self._attr_available = False
            return

        self._is_on = False
        self._brightness = 0
        self.async_write_ha_state()

    async def async_update(self):
        """Fetch new state data for the light."""
        try:
            self._attr_available = self._client.connected

            if self._attr_available:
                pass

        except (
            EDIDIOConnectionError,
            EDIDIOCommunicationError,
            EDIDIOTimeoutError,
        ) as e:
            _LOGGER.debug(
                "Client connection error during update for %s: %s", self._name, e
            )
            self._attr_available = False
        except Exception:
            _LOGGER.exception(
                "An unexpected error occurred during update for %s", self._name
            )
            self._attr_available = False

    def set_protocol(self, protocol):
        """Dynamically set the protocol (DALI/DMX)."""
        self._protocol = protocol

    def set_address(self, address):
        """Dynamically set the address."""
        self._address = address


def rgb_to_xy_16bit(r, g, b):
    """Convert RGB to 16-bit XY using Wide RGB D65 (Philips Hue style)."""

    # Step 1: Normalize to 0–1 range if needed
    if r > 1:
        r /= 255.0
    if g > 1:
        g /= 255.0
    if b > 1:
        b /= 255.0

    # Step 2: Apply gamma correction
    def gamma(c):
        if c > 0.045045:
            return ((c + 0.055) / (1.0 + 0.055)) ** 2.4
        return c / 12.92

    r = gamma(r)
    g = gamma(g)
    b = gamma(b)

    # Step 3: Convert to XYZ using Wide RGB D65
    X = r * 0.649926 + g * 0.103455 + b * 0.197109
    Y = r * 0.234327 + g * 0.743075 + b * 0.022598
    Z = r * 0.0 + g * 0.053077 + b * 1.035763

    # Step 4: Convert to xy coordinates
    total = X + Y + Z
    x = X / total if total != 0 else 0
    y = Y / total if total != 0 else 0

    # Step 5: Scale to 16-bit DALI range
    x_int = int(max(0, min(1, x)) * 65535)
    y_int = int(max(0, min(1, y)) * 65535)

    return x_int, y_int
