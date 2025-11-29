"""DataUpdateCoordinator for SOMweb integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pysomweb import (
    DeviceInfo,
    Door,
    DoorActionType,
    DoorStatusType,
    SomwebClient,
)

from .const import DOMAIN, FIRMWARE_CHECK_HOURS, SCAN_INTERVAL_SECONDS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class SomwebData:
    """Class to hold SOMweb device data."""

    device_info: DeviceInfo | None
    doors: dict[int, DoorStatusType]
    firmware_update_available: bool


class SomwebDataUpdateCoordinator(DataUpdateCoordinator[SomwebData]):
    """Class to manage fetching SOMweb data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SomwebClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self._doors: list[Door] = []
        self._device_info: DeviceInfo | None = None
        self._firmware_update_available: bool = False
        self._last_firmware_check: datetime | None = None

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Get door list (this is static)
        self._doors = self.client.get_doors()
        _LOGGER.debug("Found %d door(s)", len(self._doors))

        # Fetch initial device info and firmware status (if admin)
        if self.client.is_admin:
            await self._async_update_firmware_info()

        # Perform initial data fetch
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self) -> SomwebData:
        """Fetch data from SOMweb device."""
        try:
            # Check if device is alive
            if not await self.client.async_is_alive():
                _LOGGER.debug("Device not alive, attempting to reconnect")
                if not await self._async_reconnect():
                    raise UpdateFailed("Device is not reachable")

            # Fetch door statuses
            door_statuses: dict[int, DoorStatusType] = {}
            for door in self._doors:
                try:
                    status = await self.client.async_get_door_status(door.id)
                    door_statuses[door.id] = status
                    _LOGGER.debug(
                        "Current state of door '%s' (ID %d) is '%s'",
                        door.name,
                        door.id,
                        status.name,
                    )
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to get status for door %s: %s", door.name, err
                    )
                    door_statuses[door.id] = DoorStatusType.UNKNOWN

            # Check firmware update periodically (not on every poll)
            if self.client.is_admin and self._should_check_firmware():
                await self._async_update_firmware_info()

            return SomwebData(
                device_info=self._device_info,
                doors=door_statuses,
                firmware_update_available=self._firmware_update_available,
            )

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    def _should_check_firmware(self) -> bool:
        """Check if it's time to update firmware information."""
        if self._last_firmware_check is None:
            return True

        time_since_check = dt_util.utcnow() - self._last_firmware_check
        return time_since_check >= timedelta(hours=FIRMWARE_CHECK_HOURS)

    async def _async_update_firmware_info(self) -> None:
        """Update device info and firmware availability (called infrequently)."""
        try:
            self._device_info = await self.client.async_get_device_info()
            self._firmware_update_available = await self.client.async_update_available()
            self._last_firmware_check = dt_util.utcnow()
            _LOGGER.debug(
                "Updated firmware info - update available: %s",
                self._firmware_update_available,
            )
        except Exception as err:
            _LOGGER.debug("Failed to update firmware info: %s", err)

    async def _async_reconnect(self) -> bool:
        """Attempt to reconnect to the SOMweb device."""
        try:
            if not await self.client.async_is_alive():
                _LOGGER.debug("Device with UDI %s is not alive", self.client.udi)
                return False

            _LOGGER.debug(
                "Attempting to re-authenticate device with UDI %s", self.client.udi
            )
            auth_result = await self.client.async_authenticate()
            if auth_result.success:
                _LOGGER.debug(
                    "Successfully re-authenticated device with UDI %s", self.client.udi
                )
                return True

            _LOGGER.warning(
                "Failed to re-authenticate device with UDI %s", self.client.udi
            )
            return False

        except Exception as err:
            _LOGGER.exception("Exception during reconnection: %s", err)
            return False

    async def async_execute_door_action(
        self, door_id: int, target_state: DoorStatusType
    ) -> bool:
        """Execute a door action and wait for completion."""
        action = (
            DoorActionType.OPEN
            if target_state == DoorStatusType.OPEN
            else DoorActionType.CLOSE
        )

        door = self.get_door_by_id(door_id)
        door_name = door.name if door else f"ID {door_id}"
        _LOGGER.debug("%s door '%s'", action.name, door_name)

        try:
            # Execute action
            if not await self.client.async_door_action(door_id, action):
                # First try failed - re-connect and try again
                if not await self._async_reconnect():
                    return False
                if not await self.client.async_door_action(door_id, action):
                    return False

            # Wait for door to reach target state
            await self.client.async_wait_for_door_state(door_id, target_state)
            _LOGGER.debug(
                "Door '%s' successfully reached %s state", door_name, target_state.name
            )

            # Force immediate state refresh to update UI
            await self.async_refresh()
            return True

        except Exception as err:
            _LOGGER.exception(
                "Failed to execute action %s for door %s: %s",
                action.name,
                door_id,
                err,
            )
            return False

    def get_door_by_id(self, door_id: int) -> Door | None:
        """Get door object by ID."""
        for door in self._doors:
            if door.id == door_id:
                return door
        return None

    @property
    def doors(self) -> list[Door]:
        """Return list of doors."""
        return self._doors
