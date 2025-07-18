# custom_components/control_freak_edidio/tests/test_init.py
from unittest.mock import AsyncMock, patch

from custom_components.control_freak_edidio import (
    DOMAIN,
    PLATFORMS,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
    options_update_listener,
)
from custom_components.control_freak_edidio.const import CONF_HOST, CONF_PORT
from edidio_control_py.exceptions import EDIDIOConnectionError, EDIDIOTimeoutError
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

MOCK_HOST = "192.168.1.200"
MOCK_PORT = 1234


@pytest.fixture
def mock_edidio_client(mocker):
    mock_client_instance = AsyncMock()
    mock_client_instance.connect = AsyncMock(return_value=None)
    mock_client_instance.disconnect = AsyncMock(return_value=None)

    mock_client_class = mocker.patch(
        "custom_components.control_freak_edidio.EdidioClient",
        return_value=mock_client_instance,
    )
    return mock_client_class, mock_client_instance


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Control Freak",
        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
        options={},
        source="user",
        unique_id=f"{MOCK_HOST}-{MOCK_PORT}",
        discovery_keys=[],
        subentries_data={},
    )
    return entry


async def test_async_setup_entry_success(
    hass: HomeAssistant, mock_edidio_client, mock_config_entry
):
    mock_client_class, mock_client_instance = mock_edidio_client

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=True,
    ) as mock_forward_setups:
        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        mock_client_class.assert_called_once_with(MOCK_HOST, MOCK_PORT)
        mock_client_instance.connect.assert_called_once()
        mock_forward_setups.assert_called_once_with(mock_config_entry, PLATFORMS)

        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        assert hass.data[DOMAIN][mock_config_entry.entry_id]["client"] is mock_client_instance
        assert hass.data[DOMAIN][mock_config_entry.entry_id]["config_entry"] is mock_config_entry


@pytest.mark.parametrize("exception_type", [EDIDIOConnectionError, EDIDIOTimeoutError])
async def test_async_setup_entry_connection_failure(
    hass: HomeAssistant, mock_edidio_client, mock_config_entry, exception_type
):
    mock_client_class, mock_client_instance = mock_edidio_client
    mock_client_instance.connect.side_effect = exception_type("Mock connection error")

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=True,
    ) as mock_forward_setups:
        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        mock_client_class.assert_called_once_with(MOCK_HOST, MOCK_PORT)
        mock_client_instance.connect.assert_called_once()
        mock_forward_setups.assert_called_once_with(mock_config_entry, PLATFORMS)

        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        assert hass.data[DOMAIN][mock_config_entry.entry_id]["client"] is mock_client_instance


async def test_async_unload_entry_success(
    hass: HomeAssistant, mock_edidio_client, mock_config_entry
):
    _, mock_client_instance = mock_edidio_client

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=True,
    ):
        await async_setup_entry(hass, mock_config_entry)
        await hass.async_block_till_done()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ) as mock_unload_platforms:
        result = await async_unload_entry(hass, mock_config_entry)

        assert result is True
        mock_unload_platforms.assert_called_once_with(mock_config_entry, PLATFORMS)
        mock_client_instance.disconnect.assert_called_once()
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]


async def test_async_unload_entry_platform_unload_failure(
    hass: HomeAssistant, mock_edidio_client, mock_config_entry
):
    _, mock_client_instance = mock_edidio_client

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=True,
    ):
        await async_setup_entry(hass, mock_config_entry)
        await hass.async_block_till_done()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ) as mock_unload_platforms:
        result = await async_unload_entry(hass, mock_config_entry)

        assert result is False
        mock_unload_platforms.assert_called_once_with(mock_config_entry, PLATFORMS)
        mock_client_instance.disconnect.assert_not_called()
        assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_async_reload_entry(
    hass: HomeAssistant, mock_edidio_client, mock_config_entry
):
    _mock_client_class, _mock_client_instance = mock_edidio_client

    with patch(
        "custom_components.control_freak_edidio.async_unload_entry",
        AsyncMock(return_value=True),
    ) as mock_unload:
        with patch(
            "custom_components.control_freak_edidio.async_setup_entry",
            AsyncMock(return_value=True),
        ) as mock_setup:
            await async_reload_entry(hass, mock_config_entry)
            mock_unload.assert_called_once_with(hass, mock_config_entry)
            mock_setup.assert_called_once_with(hass, mock_config_entry)


async def test_options_update_listener(hass: HomeAssistant, mock_config_entry):
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload", AsyncMock()
    ) as mock_reload:
        await options_update_listener(hass, mock_config_entry)
        mock_reload.assert_called_once_with(mock_config_entry.entry_id)
