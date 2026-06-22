"""Avocent PM3000 PDU – switch platform.

Exposes one switch per outlet for the configured PDU. The switch state is read
from the outlet status column (.5: 1=off, 2=on) via the shared coordinator, and
toggling writes the command column (.6: 2=on, 3=off) via an SNMP SET using the
configured community as the write community.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    OID_OUTLET_COMMAND,
    OUTLET_CMD_ON,
    OUTLET_CMD_OFF,
)
from .sensor import AvocentPDUCoordinator, _snmp_set_int, build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up an outlet switch per port from a config entry."""
    coordinator: AvocentPDUCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = coordinator.pdu_name
    host = coordinator.host
    pdu_id = coordinator.pdu_id

    device_info = build_device_info(coordinator, name, host, pdu_id)
    name_slug = slugify(name)

    switches: list[AvocentOutletSwitch] = []
    for outlet_num, outlet in sorted(coordinator.data["outlets"].items()):
        # Friendly name: "PortNN - {outlet_name}" (PDU name comes from the device)
        label = (
            f"Port{outlet_num:02d} - {outlet['name']}".rstrip(" -")
            if outlet["name"] else f"Port{outlet_num:02d}"
        )
        switches.append(
            AvocentOutletSwitch(
                coordinator=coordinator,
                device_info=device_info,
                unique_id=f"{host}_{pdu_id}_port{outlet_num:02d}_switch",
                name=label,
                suggested_object_id=f"{name_slug}_port{outlet_num:02d}",
                outlet_num=outlet_num,
            )
        )

    async_add_entities(switches)


class AvocentOutletSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for a single Avocent PM3000 outlet."""

    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(
        self,
        coordinator: AvocentPDUCoordinator,
        device_info: DeviceInfo,
        unique_id: str,
        name: str,
        suggested_object_id: str,
        outlet_num: int,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_device_info = device_info
        self._outlet_num = outlet_num
        # Command-column OID for this outlet: .6.1.{pdu}.{outlet}
        self._command_oid = (
            f"{OID_OUTLET_COMMAND}.1.{coordinator.pdu_id}.{outlet_num}"
        )
        # Stable, port-number-based entity_id (mirrors the sensor scheme).
        self.entity_id = f"switch.{suggested_object_id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if the outlet is on, per the coordinator's status."""
        try:
            status = self.coordinator.data["outlets"][self._outlet_num]["status"]
        except (KeyError, TypeError):
            return None
        if status == "on":
            return True
        if status == "off":
            return False
        return None  # reboot / unavailable / unknown

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send_command(OUTLET_CMD_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send_command(OUTLET_CMD_OFF)

    async def _send_command(self, value: int) -> None:
        await _snmp_set_int(
            self.coordinator.host,
            self.coordinator.port,
            self.coordinator.write_community,
            self._command_oid,
            value,
        )
        # Refresh so the status column reflects the new state promptly.
        await self.coordinator.async_request_refresh()
