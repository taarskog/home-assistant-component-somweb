"""Binary sensor platform for SOMweb integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .entity import SomwebEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SomwebDataUpdateCoordinator
    from .types import SomwebConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: SomwebConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SOMweb binary sensors."""
    coordinator: SomwebDataUpdateCoordinator = config_entry.runtime_data

    # Only add firmware update sensor if user is admin
    if coordinator.client.is_admin:
        async_add_entities([FirmwareUpdateSensor(coordinator)])
        _LOGGER.debug("Added firmware update sensor")
    else:
        _LOGGER.debug("Firmware update sensor not added; user is not admin")


class FirmwareUpdateSensor(SomwebEntity, BinarySensorEntity):
    """Binary sensor for monitoring firmware update availability."""

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_translation_key = "firmware_update"

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.udi}_firmware_update"

    @property
    def is_on(self) -> bool:
        """Return true if a firmware update is available."""
        return self.coordinator.data.firmware_update_available
