"""Base entity for the HomeWizard Instant integration."""

from __future__ import annotations

from homeassistant.const import ATTR_CONNECTIONS, ATTR_IDENTIFIERS
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HWInstantCoordinator


class HomeWizardEntity(CoordinatorEntity[HWInstantCoordinator]):
    """Defines a HomeWizard Instant entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HWInstantCoordinator) -> None:
        """Initialise the entity with device info from coordinator data."""
        super().__init__(coordinator)
        device = coordinator.data.device
        self._attr_device_info = DeviceInfo(
            manufacturer="HomeWizard",
            sw_version=device.firmware_version,
            model_id=device.product_type,
            model=f"{device.model_name} (Instant)",
            serial_number=device.serial,
        )

        if (serial := device.serial) is not None:
            # Use a DOMAIN-prefixed identifier so this integration can coexist
            # with the official HomeWizard integration on the same device.
            self._attr_device_info[ATTR_IDENTIFIERS] = {
                (DOMAIN, f"{DOMAIN}_{serial}")
            }
            # Register a MAC-style connection so DHCP registered_devices
            # discovery can map this device.
            self._attr_device_info[ATTR_CONNECTIONS] = {
                (CONNECTION_NETWORK_MAC, serial)
            }
