"""Config flow for SOMweb (for Sommer garage doors) integration."""
from __future__ import annotations

import logging
from typing import Any

from somweb import SomwebClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_BASE, CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    udi: str = data[CONF_ID]
    username: str = data[CONF_USERNAME]
    password: str = data[CONF_PASSWORD]

    if udi is None or len(udi) == 0:
        raise InvalidSomwebUdi

    if username is None or len(username) == 0 or password is None or len(password) == 0:
        raise InvalidAuth

    somweb_client = SomwebClient(
        udi, username, password, aiohttp_client.async_get_clientsession(hass)
    )

    try:
        if not await somweb_client.is_alive():
            raise CannotConnect

        if not (await somweb_client.authenticate()).success:
            raise InvalidAuth

        # Return info to store in the config entry.
        return {"title": f"SOMweb {udi}"}
    finally:
        await somweb_client.close()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SOMweb."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial and only step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidSomwebUdi:
            errors[CONF_ID] = "invalid_udi"
        except CannotConnect:
            errors[CONF_BASE] = "cannot_connect"
        except InvalidAuth:
            errors[CONF_BASE] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors[CONF_BASE] = "unknown"
        else:
            await self.async_set_unique_id(user_input[CONF_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidSomwebUdi(HomeAssistantError):
    """Error to indicate there is an invalid somweb udi."""
