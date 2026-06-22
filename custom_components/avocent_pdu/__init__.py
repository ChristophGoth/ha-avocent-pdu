"""Avocent PM3000 PDU integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_COMMUNITY,
    CONF_WRITE_COMMUNITY,
    CONF_PDU_ID,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_COMMUNITY,
    DEFAULT_PDU_ID,
    DEFAULT_SCAN_INTERVAL,
)
from .sensor import AvocentPDUCoordinator

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Avocent PDU from a config entry."""
    data = entry.data
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    coordinator = AvocentPDUCoordinator(
        hass,
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        community=data.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
        write_community=data.get(CONF_WRITE_COMMUNITY) or None,
        pdu_id=data.get(CONF_PDU_ID, DEFAULT_PDU_ID),
        name=data.get(CONF_NAME, "PDU"),
        scan_interval=scan_interval,
    )

    # First poll must succeed for the device/entities to be created. If the PDU
    # is unreachable, async_config_entry_first_refresh raises ConfigEntryNotReady
    # so HA retries setup automatically.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (e.g. scan_interval)."""
    await hass.config_entries.async_reload(entry.entry_id)
