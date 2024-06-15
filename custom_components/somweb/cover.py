"""SOMweb (for Sommer garage doors) integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from somweb import Door, DoorStatusType, SomwebClient, DeviceInfo as SomwebDeviceInfo
import voluptuous as vol

from homeassistant.components.cover import (
    PLATFORM_SCHEMA,
    CoverEntityFeature,
    CoverDeviceClass,
    CoverEntity
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SECONDS)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add SOMweb platform for passed config_entry in Home Assistant."""

    somweb_client: SomwebClient = hass.data[DOMAIN][config_entry.entry_id]
    somweb_device_info = None if somweb_client.is_admin is None else await somweb_client.async_get_device_info()
    door_list = somweb_client.get_doors()

    entities = [SomwebDoor(somweb_client, somweb_device_info, door)
                for door in door_list]

    door_count = len(entities)
    _LOGGER.debug("Found %d door%s", door_count, "s" if door_count > 1 else "")
    async_add_entities(entities)
    return


class SomwebDoor(CoverEntity):
    """Representation of a SOMweb Garage Door (or barrier)."""

    def __init__(self, client: SomwebClient, somweb_device_info: SomwebDeviceInfo, door: Door) -> None:
        """Initialize SOMweb Door Entity.

        :param client: Client to access the SOMweb device
        :type client: SomwebClient
        :param door: The door managed by the client that this entity should represent
        :type door: Door
        """
        self._client: SomwebClient = client
        self._id: int = door.id
        self._name: str = door.name
        self._state: DoorStatusType = DoorStatusType.UNKNOWN
        self._is_opening: bool = False
        self._is_closing: bool = False
        self._device_id: str = f"UDI {client.udi}"
        self._unique_id: str = f"{client.udi}_{door.id}"
        self._available: bool = True
        self._id_in_log = f"'{self._name} ({client.udi}_{door.id})'"
        self._device_info: SomwebDeviceInfo = somweb_device_info

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._device_id)
            },
            name=f"SOMweb UDI {self._device_id}",
            manufacturer="Sommer",
            model="SOMweb",
            # configuration_url=,
            sw_version=self._device_info.firmware_version if self._device_info else None,
        )

    @property
    def unique_id(self) -> str:
        """Return unique id of the cover."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Name of the cover."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def current_cover_position(self) -> int | None:
        """Return current cover position where 0 means closed, 100 is fully open, 50 in transition to open/closed and none if unknown."""
        return (
            0
            if self._state == DoorStatusType.CLOSED
            else 100
            if self._state == DoorStatusType.OPEN
            else 50
            if self._is_opening or self._is_closing
            else None
        )

    @property
    def is_closed(self) -> bool:
        """Return the state of the cover."""
        return True if self._state == DoorStatusType.CLOSED else False

    @property
    def is_opening(self) -> bool:
        """Return the state of the cover."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return the state of the cover."""
        return self._is_closing

    @property
    def device_class(self) -> str:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return CoverDeviceClass.GARAGE

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        return CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    async def async_open_cover(self, **kwargs) -> None:  # type: ignore
        """Open the cover."""
        await self.__async_set_door_position(DoorStatusType.OPEN)

    async def async_close_cover(self, **kwargs) -> None:  # type: ignore
        """Close cover."""
        await self.__async_set_door_position(DoorStatusType.CLOSED)

    async def _force_update(self) -> None:
        """Force update of cover state in ha."""
        _LOGGER.debug("Force update state of cover %s", self._id_in_log)
        await self.async_update(no_throttle=True)
        self.async_write_ha_state()

    async def __async_refresh_state(self) -> bool:
        """Refresh cover state."""
        try:
            self._state = await self._client.async_get_door_status(self._id)
            _LOGGER.debug(
                "Current state of cover %s is '%s'", self._id_in_log, self._state.name
            )

            return True if self._state != DoorStatusType.UNKNOWN else False
        except Exception:  # pylint: disable=broad-except
            self._state = DoorStatusType.UNKNOWN
            _LOGGER.exception(
                "Exception when getting state of cover %s", self._id_in_log
            )
            return False

    async def __async_set_door_position(self, position: DoorStatusType) -> None:
        """Set cover position."""
        _LOGGER.debug("%s cover %s", position.name, self._id_in_log)

        try:
            self._is_opening = position == DoorStatusType.OPEN
            self._is_closing = position == DoorStatusType.CLOSED
            self.async_write_ha_state()

            if await self._client.async_door_action(self._id, position) or (
                # First try failed - re-connect and try again
                await self.__async_re_connect()
                and await self._client.async_door_action(self._id, position)
            ):
                await self._client.async_wait_for_door_state(self._id, position)
            else:
                _LOGGER.error("Unable to %s cover %s",
                              position.name, self._id_in_log)

        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Exception when setting cover %s position to %s",
                self._id_in_log,
                position.name,
            )
        finally:
            self._is_opening = False
            self._is_closing = False
            await self._force_update()

    async def __async_re_connect(self) -> bool:
        """Re-connect to SOMweb device."""
        try:
            if not await self._client.async_is_alive():
                _LOGGER.debug("Somweb with id %s is not alive",
                              self._client.udi)
                return False

            _LOGGER.debug(
                "Attempting to re-authenticate somweb for cover %s", self._id_in_log
            )
            auth_result = await self._client.async_authenticate()
            if auth_result.success:
                _LOGGER.debug(
                    "Successfully re-authenticated somweb for cover %s",
                    self._id_in_log,
                )
                return True

            _LOGGER.warning(
                "Failed re-authenticating somweb for cover %s", self._id_in_log
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Exception when re-authenticating somweb for cover %s",
                self._id_in_log,
            )

        return False

    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self, **kwargs) -> None:  # type: ignore
        """Get the latest status from SOMweb."""
        if self.is_opening or self._is_closing:
            _LOGGER.debug(
                "Skipping update of state while an operation is ongoing")
        elif not (
            await self.__async_refresh_state()
            or (await self.__async_re_connect() and await self.__async_refresh_state())
        ):
            _LOGGER.warning(
                "SOMweb seems to be off the grid. Will continue attempts")

        self._available = self._state != DoorStatusType.UNKNOWN
