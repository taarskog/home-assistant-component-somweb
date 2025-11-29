"""Base entity for SOMweb integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SomwebDataUpdateCoordinator


class SomwebEntity(CoordinatorEntity[SomwebDataUpdateCoordinator]):
    """Base entity for SOMweb integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SomwebDataUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"UDI {coordinator.client.udi}")},
            name=f"SOMweb UDI {coordinator.client.udi}",
            manufacturer="Sommer",
            model="SOMweb",
            sw_version=(
                coordinator.data.device_info.firmware_version
                if coordinator.data.device_info
                else None
            ),
            configuration_url=(
                (
                    f"https://{coordinator.client.udi}.somweb.world/index.php?op=config"
                    if coordinator.data.device_info.remote_access_enabled
                    else f"http://{coordinator.data.device_info.ip_address}/index.php?op=config"
                )
                if coordinator.data.device_info
                and coordinator.data.device_info.ip_address
                else None
            ),
        )
