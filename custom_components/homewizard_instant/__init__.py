"""The HomeWizard Instant integration."""

from __future__ import annotations

from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HomeWizardEnergyV2
from .const import CONF_TOKEN, PLATFORMS
from .coordinator import HomeWizardConfigEntry, HWInstantCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: HomeWizardConfigEntry) -> bool:
    """Set up HomeWizard Instant from a config entry."""
    api = HomeWizardEnergyV2(
        host=entry.data[CONF_IP_ADDRESS],
        token=entry.data[CONF_TOKEN],
        session=async_get_clientsession(hass),
    )

    coordinator = HWInstantCoordinator(hass, entry, api)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        raise

    entry.runtime_data = coordinator

    # Cancel the WebSocket background task when the entry is unloaded.
    entry.async_on_unload(coordinator._cancel_ws_task)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomeWizardConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
