"""Sensor platform for SOMweb integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
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
    """Set up SOMweb sensors."""
    coordinator: SomwebDataUpdateCoordinator = config_entry.runtime_data

    # Only add device info sensors if user is admin and device info is available
    entities = []
    if coordinator.client.is_admin and coordinator.data.device_info:
        entities.extend(
            [
                IdentifierSensor(coordinator),
                WifiSignalQualitySensor(coordinator),
                WifiSignalLevelSensor(coordinator),
                IpAddressSensor(coordinator),
                TimezoneSensor(coordinator),
            ]
        )
        _LOGGER.debug("Added %d device info sensor(s)", len(entities))
    else:
        _LOGGER.debug("Device info sensors not added; user not admin or no device info")

    if entities:
        async_add_entities(entities)


class IdentifierSensor(SomwebEntity, SensorEntity):
    """Sensor for device identifier (user-chosen name)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "identifier"
    _attr_icon = "mdi:label-outline"

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.udi}_identifier"

    @property
    def native_value(self) -> str | None:
        """Return the device identifier."""
        if self.coordinator.data.device_info:
            return self.coordinator.data.device_info.identifier
        return None


class WifiSignalQualitySensor(SomwebEntity, SensorEntity):
    """Sensor for WiFi signal quality (0-5 grade)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "wifi_signal_quality"
    _attr_icon = "mdi:signal"

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.udi}_wifi_signal_quality"

    @property
    def native_value(self) -> int | None:
        """Return the WiFi signal quality (0-5 grade)."""
        if self.coordinator.data.device_info:
            return self.coordinator.data.device_info.wifi_signal_quality
        return None


class WifiSignalLevelSensor(SomwebEntity, SensorEntity):
    """Sensor for WiFi signal level in dBm."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "wifi_signal_level"

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.udi}_wifi_signal_level"

    @property
    def native_value(self) -> int | None:
        """Return the WiFi signal level in dBm."""
        if self.coordinator.data.device_info:
            return self.coordinator.data.device_info.wifi_signal_level
        return None


class IpAddressSensor(SomwebEntity, SensorEntity):
    """Sensor for device IP address."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "ip_address"
    _attr_icon = "mdi:ip-network-outline"

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.udi}_ip_address"

    @property
    def native_value(self) -> str | None:
        """Return the device IP address."""
        if self.coordinator.data.device_info:
            return self.coordinator.data.device_info.ip_address
        return None


class TimezoneSensor(SomwebEntity, SensorEntity):
    """Sensor for device timezone setting."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "timezone"
    _attr_icon = "mdi:earth"

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.udi}_timezone"

    @property
    def native_value(self) -> str | None:
        """Return the device timezone."""
        if self.coordinator.data.device_info:
            return self.coordinator.data.device_info.time_zone
        return None
