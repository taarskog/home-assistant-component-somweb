"""Config flow for SOMweb (for Sommer garage doors) integration."""

from __future__ import annotations

import logging
from copy import copy
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_BASE,
    CONF_ID,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client, selector
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from pysomweb import SomwebClient

from .const import DOMAIN, MODE_CLOUD, MODE_LOCAL, MODE_TRANSLATION_KEY

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[MODE_CLOUD, MODE_LOCAL], translation_key=MODE_TRANSLATION_KEY
            )
        ),
        vol.Optional(CONF_ID): TextSelector(),
        vol.Optional(CONF_URL): TextSelector(),
        vol.Required(CONF_USERNAME): TextSelector(),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


def generate_data_schema(data_schema: vol.Schema, suggested_values: Mapping[str, Any]):
    # Code Inspired by: https://www.hacf.fr/dev_tuto_4_config_flow/
    """
    Make a copy of the schema, populated with suggested values.

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
            new_key.description = {"suggested_value": suggested_values[key]}  # type: ignore
        schema[new_key] = val
    _LOGGER.debug("add_suggested_values_to_schema: schema=%s", schema)
    return vol.Schema(schema)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.

    Returns dict with 'title' and 'udi' keys.
    """
    mode: str = data[CONF_MODE]
    udi: str | None = data.get(CONF_ID)
    url: str | None = data.get(CONF_URL)
    username: str | None = data[CONF_USERNAME]
    password: str | None = data[CONF_PASSWORD]

    if mode == MODE_LOCAL:
        if url is None or len(url) == 0:
            raise InvalidSomwebUrl
    elif udi is None or len(udi) == 0:
        raise InvalidSomwebUdi

    if username is None or len(username) == 0 or password is None or len(password) == 0:
        raise InvalidAuth

    if mode == MODE_LOCAL and url is not None:
        _LOGGER.debug("Local login with URL '%s'", url)
        somweb_client = SomwebClient(
            url,
            username,
            password,
            aiohttp_client.async_get_clientsession(hass),  # pyright: ignore[reportArgumentType]
        )
    elif mode == MODE_CLOUD and udi is not None:
        _LOGGER.debug("Cloud login with UDI '%s'", udi)
        somweb_client = SomwebClient.create_using_udi(
            udi, username, password, aiohttp_client.async_get_clientsession(hass)
        )
    else:
        raise InvalidSomwebUrl

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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.discovery_info: dict[str, Any] = {}

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult | ConfigFlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        hostname = discovery_info.hostname or ""

        _LOGGER.debug(
            "Zeroconf discovery - hostname: %s, host: %s, type: %s, name: %s, properties: %s",
            hostname,
            host,
            discovery_info.type,
            discovery_info.name,
            discovery_info.properties,
        )

        # SOMweb devices broadcast as somweb.local (with or without trailing dot)
        hostname_lower = hostname.lower().rstrip(".")
        if not hostname_lower.startswith("somweb"):
            _LOGGER.debug("Ignoring non-SOMweb device: %s", hostname)
            return self.async_abort(reason="not_somweb_device")

        # Build URL from discovery info
        url = f"http://{host}"

        _LOGGER.debug("Discovered SOMweb device at %s", url)

        # Store discovery info for later steps
        self.discovery_info = {
            CONF_URL: url,
            CONF_MODE: MODE_LOCAL,
        }

        # Try to connect and get UDI without authentication
        somweb_client = SomwebClient(
            url, "", "", aiohttp_client.async_get_clientsession(self.hass)
        )
        try:
            if not await somweb_client.async_is_alive():
                _LOGGER.debug(
                    "Discovered device at '%s' not alive or is not a supported SOMweb device",
                    url,
                )
                return self.async_abort(reason="cannot_connect")

            udi = await somweb_client.async_get_udi()
            if udi:
                await self.async_set_unique_id(udi)
                self._abort_if_unique_id_configured(updates={CONF_URL: url})
                self.discovery_info[CONF_ID] = udi
                _LOGGER.debug("Discovered SOMweb with UDI '%s' at '%s'", udi, url)
        except AbortFlow:
            # Let abort flow exceptions propagate (e.g., already_configured)
            raise
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug("Failed to probe discovered device: %s", err)
            return self.async_abort(reason="cannot_connect")
        finally:
            await somweb_client.close()

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult | ConfigFlowResult:
        """Confirm discovery and ask for credentials."""
        if user_input is not None:
            # Merge discovery info with user credentials
            combined_data = {**self.discovery_info, **user_input}

            errors = {}
            try:
                info = await validate_input(self.hass, combined_data)
            except InvalidAuth:
                errors[CONF_BASE] = "invalid_auth"
            except CannotConnect:
                errors[CONF_BASE] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during discovery confirm")
                errors[CONF_BASE] = "unknown"
            else:
                # Update with discovered UDI
                combined_data[CONF_ID] = info["udi"]
                await self.async_set_unique_id(info["udi"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=combined_data,
                )

            # Show form again with errors
            return self.async_show_form(
                step_id="discovery_confirm",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_USERNAME): TextSelector(),
                        vol.Required(CONF_PASSWORD): TextSelector(
                            TextSelectorConfig(type=TextSelectorType.PASSWORD)
                        ),
                    }
                ),
                errors=errors,
                description_placeholders={
                    "url": self.discovery_info.get(CONF_URL, ""),
                    "udi": self.discovery_info.get(CONF_ID, "Unknown"),
                },
            )

        # Initial form - ask for credentials
        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): TextSelector(),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            description_placeholders={
                "url": self.discovery_info.get(CONF_URL, ""),
                "udi": self.discovery_info.get(CONF_ID, "Unknown"),
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult | ConfigFlowResult:
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

            if user_input[CONF_MODE] == MODE_CLOUD:
                # Reset url when doing cloud - we'll use UDI value for connecting
                user_input[CONF_URL] = None

            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=generate_data_schema(STEP_USER_DATA_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult | ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        entryid = self.context.get("entry_id", None)
        if entryid is None:
            return self.async_abort(reason="missing_entry_id")
        config_entry = self.hass.config_entries.async_get_entry(entryid)

        if config_entry is None:
            return self.async_abort(reason="invalid_entry_id")

        if user_input is None:
            # Show form with current values, but exclude password for security
            suggested_values = {
                key: value
                for key, value in config_entry.data.items()
                if key != CONF_PASSWORD
            }
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=generate_data_schema(
                    STEP_USER_DATA_SCHEMA, suggested_values
                ),
            )

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
            _LOGGER.exception("Unexpected exception during reconfiguration")
            errors[CONF_BASE] = "unknown"
        else:
            # Set/override UDI with value retrieved from device
            user_input[CONF_ID] = info["udi"]

            if user_input[CONF_MODE] == MODE_CLOUD:
                # Reset url when doing cloud - we'll use UDI value for connecting
                user_input[CONF_URL] = None

            # TODO: Reconfigure and reload does not work properly yet as entities are
            #       not updated when going to/from admin user

            # Update the config entry
            return self.async_update_reload_and_abort(
                config_entry,
                title=info["title"],
                data=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=generate_data_schema(STEP_USER_DATA_SCHEMA, user_input),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidSomwebUdi(HomeAssistantError):
    """Error to indicate there is an invalid somweb udi."""


class InvalidSomwebUrl(HomeAssistantError):
    """Error to indicate there is an invalid somweb url."""
