"""Control Freak eDIDIO Home Assistant integration."""

import logging
import ssl

from edidio_control_py import EdidioClient
from edidio_control_py.exceptions import EDIDIOConnectionError, EDIDIOTimeoutError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_HOST, CONF_PORT, CONF_TLS, DOMAIN

PLATFORMS: list[Platform] = [Platform.LIGHT]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Control Freak from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    use_tls = entry.data.get(CONF_TLS, False)

    ssl_context = None
    if use_tls:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    client = EdidioClient(host, port, use_tls=use_tls, ssl_context=ssl_context)

    try:
        await client.connect()
        _LOGGER.info(
            "Successfully connected to eDIDIO device at %s:%s (TLS: %s)",
            host,
            port,
            use_tls,
        )
    except (EDIDIOConnectionError, EDIDIOTimeoutError) as e:
        raise ConfigEntryNotReady(
            f"Cannot connect to Control Freak device at {host}:{port}: {e}"
        ) from e

    entry.runtime_data = client

    async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
        await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        client: EdidioClient = entry.runtime_data
        try:
            await client.disconnect()
        except Exception:
            pass
        _LOGGER.info("Control Freak client disconnected for %s", entry.entry_id)

    return unload_ok
