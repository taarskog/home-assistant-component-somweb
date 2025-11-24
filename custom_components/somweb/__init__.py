"""The SOMweb (for Sommer garage doors) integration.

For more details about this integration, please refer to
https://github.com/taarskog/home-assistant-component-somweb
"""
from __future__ import annotations

import logging

from somweb import SomwebClient

from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .types import SomwebConfigEntry

PLATFORMS = ["cover"]

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: SomwebConfigEntry) -> bool:
    """Set up SOMweb (for Sommer garage doors) from a config entry."""

    config = entry.data
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    somweb_udi = config[CONF_ID]
    somweb_url = config[CONF_URL]

    if somweb_url is None:
        LOGGER.debug("Cloud login as '%s' with UDI '%s'", username, somweb_udi)
        somweb_client = SomwebClient.create_using_udi(
            somweb_udi, username, password, aiohttp_client.async_get_clientsession(hass))
    else:
        LOGGER.debug("Local login as '%s' with URL '%s'", username, somweb_url)
        somweb_client = SomwebClient(somweb_url, username, password, aiohttp_client.async_get_clientsession(hass)
                                     )

    if await somweb_client.async_is_alive():
        LOGGER.debug("Device %s is alive", somweb_url or somweb_udi)
    else:
        raise ConfigEntryNotReady(
            f"Device {somweb_url or somweb_udi} is not reachable")

    auth_result = await somweb_client.async_authenticate()
    if not auth_result.success:
        LOGGER.error("Authentication failed for %s", somweb_udi or somweb_url)
        return False

    # Forward client for platforms to access
    entry.runtime_data = somweb_client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SomwebConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: SomwebConfigEntry) -> None:
    """Reload config entry."""
    LOGGER.info("Reloading somweb...")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_migrate_entry(hass: HomeAssistant, config_entry: SomwebConfigEntry) -> bool:
    """Migrate old entry."""
    LOGGER.debug("Migrating configuration from version %s.%s",
                 config_entry.version, config_entry.minor_version)

    if config_entry.version == 1:

        new_data = {**config_entry.data}
        if config_entry.minor_version < 2:
            new_data[CONF_URL] = None

        # Set new config version
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, minor_version=2, version=1)

    LOGGER.debug("Migration to configuration version %s.%s successful",
                 config_entry.version, config_entry.minor_version)

    return True
