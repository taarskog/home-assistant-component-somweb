"""Cover platform for SOMweb integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from pysomweb import DoorStatusType

from .entity import SomwebEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SomwebDataUpdateCoordinator
    from .types import SomwebConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SomwebConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SOMweb cover entities."""
    coordinator: SomwebDataUpdateCoordinator = config_entry.runtime_data

    entities = [SomwebDoor(coordinator, door.id) for door in coordinator.doors]

    _LOGGER.debug("Added %d door(s)", len(entities))
    async_add_entities(entities)


class SomwebDoor(SomwebEntity, CoverEntity):
    """Representation of a SOMweb Garage Door (or barrier)."""

    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, coordinator: SomwebDataUpdateCoordinator, door_id: int) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        self._door_id = door_id

        door = coordinator.get_door_by_id(door_id)
        if door:
            self._attr_name = door.name
            self._attr_unique_id = f"{coordinator.client.udi}_{door.id}"
            self._attr_translation_key = None  # Use custom name from device

        self._is_opening = False
        self._is_closing = False

        _LOGGER.debug(
            "Initialized cover '%s' (%s)",
            self._attr_name,
            self._attr_unique_id,
        )

    @property
    def current_cover_position(self) -> int | None:
        """Return current cover position."""
        state = self.coordinator.data.doors.get(self._door_id, DoorStatusType.UNKNOWN)

        if state == DoorStatusType.CLOSED:
            return 0
        elif state == DoorStatusType.OPEN:
            return 100
        elif self._is_opening or self._is_closing:
            return 50
        return None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        state = self.coordinator.data.doors.get(self._door_id, DoorStatusType.UNKNOWN)
        if state == DoorStatusType.UNKNOWN:
            return None
        return state == DoorStatusType.CLOSED

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._is_closing

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.debug("Opening cover '%s' (%s)", self._attr_name, self._attr_unique_id)

        self._is_opening = True
        self._is_closing = False
        self.async_write_ha_state()

        try:
            success = await self.coordinator.async_execute_door_action(
                self._door_id, DoorStatusType.OPEN
            )
            if not success:
                _LOGGER.error(
                    "Failed to open cover '%s' (%s)",
                    self._attr_name,
                    self._attr_unique_id,
                )
        finally:
            self._is_opening = False

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        _LOGGER.debug("Closing cover '%s' (%s)", self._attr_name, self._attr_unique_id)

        self._is_opening = False
        self._is_closing = True
        self.async_write_ha_state()

        try:
            success = await self.coordinator.async_execute_door_action(
                self._door_id, DoorStatusType.CLOSED
            )
            if not success:
                _LOGGER.error(
                    "Failed to close cover '%s' (%s)",
                    self._attr_name,
                    self._attr_unique_id,
                )
        finally:
            self._is_closing = False
