"""Binary sensor platform for SOMweb integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityCategory

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

    entities = []
    # Only add device info binary sensors if user is admin
    if coordinator.client.is_admin:
        entities.append(FirmwareUpdateSensor(coordinator))
        if coordinator.data.device_info:
            entities.append(RemoteAccessSensor(coordinator))
        _LOGGER.debug("Added %d binary sensor(s)", len(entities))
    else:
        _LOGGER.debug("Binary sensors not added; user is not admin")

    if entities:
        async_add_entities(entities)


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


class RemoteAccessSensor(SomwebEntity, BinarySensorEntity):
    """Binary sensor for remote access status."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "remote_access"

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.udi}_remote_access"

    @property
    def is_on(self) -> bool | None:
        """Return true if remote access is enabled."""
        if self.coordinator.data.device_info:
            return self.coordinator.data.device_info.remote_access_enabled
        return None
