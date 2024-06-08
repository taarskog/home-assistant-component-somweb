"""The SOMweb (for Sommer garage doors) integration.

For more details about this integration, please refer to
https://github.com/taarskog/home-assistant-component-somweb
"""
from __future__ import annotations

import asyncio
import logging

from somweb import SomwebClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import ALIVE_RETRY_INTERVAL_SECONDS, DOMAIN

PLATFORMS: list[str] = ["cover"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SOMweb (for Sommer garage doors) from a config entry."""

    config = entry.data
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    somweb_udi = config[CONF_ID]
    somweb_url = config[CONF_URL]

    if (somweb_url is None):
        _LOGGER.debug("Cloud login with UDI '%s'", somweb_udi)
        somweb_client = SomwebClient.createUsingUdi(somweb_udi, username, password, aiohttp_client.async_get_clientsession(hass))
    else:
        _LOGGER.debug("Local or Cloud login with URL '%s'", somweb_url)
        somweb_client = SomwebClient(somweb_url, username, password, aiohttp_client.async_get_clientsession(hass)
        )

    while not await somweb_client.is_alive():
        _LOGGER.error(
            "Device with UDI '%s' and URL '%s' not found on this network. Make sure that at least one of these values are set (if bot are set URL will override UDI)",
            somweb_udi,
            somweb_url
        )
        await asyncio.sleep(ALIVE_RETRY_INTERVAL_SECONDS)

    auth_result = await somweb_client.authenticate()
    if not auth_result.success:
        _LOGGER.error("Failed to authenticate (udi=%s)", somweb_udi)
        return False

    # Store client for platforms to access
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = somweb_client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("Reloading somweb...")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating configuration from version %s.%s", config_entry.version, config_entry.minor_version)

    if config_entry.version == 1:

        new_data = {**config_entry.data}
        if config_entry.minor_version < 2:
            new_data[CONF_URL] = None
            pass

        # Set new config version
        hass.config_entries.async_update_entry(config_entry, data=new_data, minor_version=2, version=1)

    _LOGGER.debug("Migration to configuration version %s.%s successful", config_entry.version, config_entry.minor_version)

    return True

