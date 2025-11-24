"""Config flow for SOMweb (for Sommer garage doors) integration."""
from __future__ import annotations

from collections.abc import Mapping
from copy import copy
import logging
from typing import Any

from somweb import SomwebClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_BASE, CONF_ID, CONF_PASSWORD, CONF_USERNAME, CONF_URL, CONF_MODE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client, selector

from .const import DOMAIN, MODE_CLOUD, MODE_LOCAL, MODE_TRANSLATION_KEY

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[MODE_CLOUD, MODE_LOCAL],
                translation_key= MODE_TRANSLATION_KEY
            )
        ),
        vol.Optional(CONF_ID): str,
        vol.Optional(CONF_URL): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def generate_data_schema(data_schema: vol.Schema, suggested_values: Mapping[str, Any]):
    # Code Inspired by: https://www.hacf.fr/dev_tuto_4_config_flow/
    """Make a copy of the schema, populated with suggested values.

    For each schema marker matching items in `suggested_values`,
    the `suggested_value` will be set. The existing `suggested_value` will
    be left untouched if there is no matching item.
    """
    schema = {}
    for key, val in data_schema.schema.items():
        new_key = key
        if key in suggested_values and isinstance(key, vol.Marker):
            # Copy the marker to not modify the flow schema
            new_key = copy(key)
            new_key.description = {"suggested_value": suggested_values[key]}
        schema[new_key] = val
    _LOGGER.debug("add_suggested_values_to_schema: schema=%s", schema)
    return vol.Schema(schema)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    mode: str = data[CONF_MODE]
    udi: str|None = data.get(CONF_ID, None)
    url: str|None = data.get(CONF_URL, None)
    username: str|None = data[CONF_USERNAME]
    password: str|None = data[CONF_PASSWORD]

    if (mode == MODE_LOCAL):
        if url is None or len(url) == 0:
            raise InvalidSomwebUrl
    else:
        if udi is None or len(udi) == 0:
            raise InvalidSomwebUdi

    if username is None or len(username) == 0 or password is None or len(password) == 0:
        raise InvalidAuth

    if (mode == MODE_LOCAL):
        _LOGGER.debug("Local login with URL '%s'", url)
        somweb_client = SomwebClient(url, username, password, aiohttp_client.async_get_clientsession(hass))
    else:
        _LOGGER.debug("Cloud login with UDI '%s'", udi)
        somweb_client = SomwebClient.create_using_udi(udi, username, password, aiohttp_client.async_get_clientsession(hass))

    try:
        if not await somweb_client.async_is_alive():
            raise CannotConnect

        if not (await somweb_client.async_authenticate()).success:
            raise InvalidAuth

        _LOGGER.debug("Connected to SOMweb device with UDI '%s'", somweb_client.udi)

        # Return info to store in the config entry.
        return {"title": f"SOMweb {somweb_client.udi}", "udi": somweb_client.udi}
    finally:
        await somweb_client.close()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SOMweb."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial and only step."""
        if user_input is None:
            return self.async_show_form(step_id="user",data_schema=STEP_USER_DATA_SCHEMA)

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidSomwebUdi:
            errors[CONF_ID] = "invalid_udi"
        except InvalidSomwebUrl:
            errors[CONF_URL] = "invalid_url"
        except CannotConnect:
            errors[CONF_BASE] = "cannot_connect"
        except InvalidAuth:
            errors[CONF_BASE] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors[CONF_BASE] = "unknown"
        else:
            await self.async_set_unique_id(info["udi"])
            self._abort_if_unique_id_configured()

            # Set/override UDI with value retrieved from device
            user_input[CONF_ID] = info["udi"]
            _LOGGER.debug("Got UDI '%s' and set '%s'", info["udi"], user_input[CONF_ID])

            if (user_input[CONF_MODE] == MODE_CLOUD):
                # Reset url when doing cloud - we'll use UDI value for connecting
                user_input[CONF_URL] = None

            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=generate_data_schema(STEP_USER_DATA_SCHEMA, user_input), errors=errors
        )

    # async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
    #     if user_input is not None:
    #         pass  # TODO: process user input

    #     return self.async_show_form(
    #         step_id="user",
    #         data_schema=STEP_USER_DATA_SCHEMA,
    #     )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidSomwebUdi(HomeAssistantError):
    """Error to indicate there is an invalid somweb udi."""

class InvalidSomwebUrl(HomeAssistantError):
    """Error to indicate there is an invalid somweb url."""
