"""Control Freak eDIDIO Home Assistant integration."""

import logging

from edidio_control_py import EdidioClient
from edidio_control_py.exceptions import EDIDIOConnectionError, EDIDIOTimeoutError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, DOMAIN

PLATFORMS: list[Platform] = [Platform.LIGHT]  # Define platforms

_LOGGER = logging.getLogger(__name__)


async def options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.info("Control Freak options updated, reloading integration")
    # This will call async_unload_entry and then async_setup_entry again
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Control Freak from a config entry."""
    host = entry.data.get(CONF_HOST)
    port = entry.data.get(CONF_PORT)

    if not host or not port:
        _LOGGER.error(
            "Host or port not found in configuration data. This should not happen with proper config flow validation"
        )
        return False

    # Instantiate EdidioClient
    client = EdidioClient(host, port)

    # Attempt to connect to the device.
    try:
        await client.connect()
        _LOGGER.info("Successfully connected to eDIDIO device at %s:%s", host, port)
    except (EDIDIOConnectionError, EDIDIOTimeoutError) as e:
        _LOGGER.warning(
            "Initial connection to Control Freak device failed (%s:%s): %s. "
            "The integration will attempt to reconnect when needed",
            host,
            port,
            e,
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "config_entry": entry,
    }
    _LOGGER.debug(
        "Control Freak integration data stored for %s: %s",
        entry.entry_id,
        hass.data[DOMAIN][entry.entry_id],
    )

    # Register the options update listener
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # Forward the setup to platforms (e.g., "light")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(
        "Unloading Control Freak integration for entry_id: %s", entry.entry_id
    )
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        domain_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if domain_data and (client := domain_data.get("client")):
            await client.disconnect()
            _LOGGER.info(
                "Control Freak client disconnected and data removed for %s",
                entry.entry_id,
            )

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    _LOGGER.debug("Reloading Control Freak config entry: %s", entry.entry_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
