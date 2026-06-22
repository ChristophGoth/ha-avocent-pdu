"""Avocent PM3000 PDU – sensor platform.

Registers one HA *device* per configured PDU instance.
Under each device, the following entities are created:

  PDU-level (strip/inlet totals):
    • power           (W)  – current active power
    • power_min/max   (W)
    • current         (A)
    • current_min/max (A)
    • voltage         (V)
    • power_factor    (–)
    • energy          (kWh) – total_increasing, used in Energy Dashboard

  Per-outlet (one device entity per port):
    • power           (W)
    • power_min/max   (W)
    • current         (A)
    • voltage         (V)
    • power_factor    (–)
    • energy          (kWh) – total_increasing, used in Energy Dashboard
    • status          (on/off/…)

Configuration example (configuration.yaml):
  sensor:
    - platform: avocent_pdu
      name: PDU01
      host: 192.168.1.10
      community: public
      pdu_id: 1
      scan_interval: 60

    - platform: avocent_pdu
      name: PDU02
      host: 192.168.1.11
      community: public
      pdu_id: 1
      scan_interval: 60
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_COMMUNITY,
    CONF_PDU_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_COMMUNITY,
    DEFAULT_PDU_ID,
    DEFAULT_SCAN_INTERVAL,
    OID_PDU_MODEL,
    OID_PDU_CURRENT, OID_PDU_CURRENT_MIN, OID_PDU_CURRENT_MAX,
    OID_PDU_VOLTAGE,
    OID_PDU_POWER, OID_PDU_POWER_MIN, OID_PDU_POWER_MAX, OID_PDU_POWER_AVG,
    OID_PDU_POWER_FACTOR,
    OID_PDU_ENERGY,
    OID_OUTLET_NAME, OID_OUTLET_STATUS, OID_OUTLET_PORT, OID_OUTLET_PDU_ID,
    OID_OUTLET_CURRENT, OID_OUTLET_CURRENT_MIN, OID_OUTLET_CURRENT_MAX,
    OID_OUTLET_VOLTAGE,
    OID_OUTLET_POWER, OID_OUTLET_POWER_MIN, OID_OUTLET_POWER_MAX,
    OID_OUTLET_POWER_FACTOR,
    OID_OUTLET_ENERGY,
    OUTLET_STATUS_MAP,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default="PDU"): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_COMMUNITY, default=DEFAULT_COMMUNITY): cv.string,
        vol.Optional(CONF_PDU_ID, default=DEFAULT_PDU_ID): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=5)
        ),
    }
)


# ── SNMP helper ───────────────────────────────────────────────────────────────

async def _snmp_get(host: str, port: int, community: str, oids: list[str]) -> dict[str, Any]:
    """Async SNMPv2c GET for a list of OIDs (pysnmp 7.x API).

    Returns {oid_string: raw_value} or raises RuntimeError on failure.
    """
    from pysnmp.hlapi.asyncio import (
        get_cmd, SnmpEngine, CommunityData, UdpTransportTarget,
        ContextData, ObjectType, ObjectIdentity,
    )

    results: dict[str, Any] = {}
    engine = SnmpEngine()
    transport = await UdpTransportTarget.create((host, port), timeout=5, retries=2)
    auth = CommunityData(community, mpModel=1)  # mpModel=1 → SNMPv2c

    for oid in oids:
        error_indication, error_status, error_index, var_binds = await get_cmd(
            engine, auth, transport, ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
        if error_indication:
            raise RuntimeError(f"SNMP GET error for {oid}: {error_indication}")
        if error_status:
            raise RuntimeError(
                f"SNMP error status {error_status.prettyPrint()} "
                f"at index {error_index} for {oid}"
            )
        for var_bind in var_binds:
            results[oid] = var_bind[1]

    return results


async def _snmp_walk(host: str, port: int, community: str, base_oid: str) -> dict[str, Any]:
    """Async SNMPv2c GETNEXT walk on base_oid subtree (pysnmp 7.x API).

    Returns {full_oid_string: value} for every node in the subtree.
    """
    from pysnmp.hlapi.asyncio import (
        walk_cmd, SnmpEngine, CommunityData, UdpTransportTarget,
        ContextData, ObjectType, ObjectIdentity,
    )

    results: dict[str, Any] = {}
    engine = SnmpEngine()
    transport = await UdpTransportTarget.create((host, port), timeout=5, retries=2)
    auth = CommunityData(community, mpModel=1)

    async for error_indication, error_status, _, var_binds in walk_cmd(
        engine, auth, transport, ContextData(),
        ObjectType(ObjectIdentity(base_oid)),
        lexicographicMode=False,
    ):
        if error_indication:
            raise RuntimeError(f"SNMP walk error for {base_oid}: {error_indication}")
        if error_status:
            raise RuntimeError(f"SNMP walk error status: {error_status.prettyPrint()}")
        for var_bind in var_binds:
            results[str(var_bind[0])] = var_bind[1]

    return results


def _get_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _scale(value: Any, factor: float) -> float | None:
    raw = _get_int(value)
    if raw is None:
        return None
    return round(raw * factor, 3)


def _wh_to_kwh(value: Any) -> float | None:
    raw = _get_int(value)
    if raw is None:
        return None
    return round(raw / 1000.0, 4)


def _str_value(value: Any) -> str:
    try:
        return str(value).strip()
    except Exception:
        return ""


# ── Coordinator ───────────────────────────────────────────────────────────────

class AvocentPDUCoordinator(DataUpdateCoordinator):
    """Polls one Avocent PM3000 PDU (primary or chained) via SNMPv2c.

    Data structure returned by _async_update_data():
    {
        "pdu": {
            "model": str,
            "power": float,  "power_min": float, "power_max": float,
            "current": float, "current_min": float, "current_max": float,
            "voltage": float,
            "power_factor": float,
            "energy_kwh": float,
        },
        "outlets": {
            1: {                          # key = outlet port number (1-based)
                "name": str,
                "status": str,
                "power": float, "power_min": float, "power_max": float,
                "current": float, "current_min": float, "current_max": float,
                "voltage": float,
                "power_factor": float,
                "energy_kwh": float,
            },
            …
        }
    }
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        community: str,
        pdu_id: int,
        name: str,
        scan_interval: int,
    ) -> None:
        self.host      = host
        self.port      = port
        self.community = community
        self.pdu_id    = pdu_id
        self.pdu_name  = name

        super().__init__(
            hass,
            _LOGGER,
            name=f"avocent_pdu_{name}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from the PDU. Runs SNMP I/O in executor thread."""
        try:
            return await self._fetch_all()
        except Exception as exc:
            raise UpdateFailed(f"SNMP poll failed for {self.pdu_name}: {exc}") from exc

    async def _fetch_all(self) -> dict:
        pdu_id = self.pdu_id

        # ── PDU-level GET ─────────────────────────────────────────────────────
        pdu_oids = {
            "model":        f"{OID_PDU_MODEL}.{pdu_id}",
            "current":      f"{OID_PDU_CURRENT}.{pdu_id}",
            "current_min":  f"{OID_PDU_CURRENT_MIN}.{pdu_id}",
            "current_max":  f"{OID_PDU_CURRENT_MAX}.{pdu_id}",
            "voltage":      f"{OID_PDU_VOLTAGE}.{pdu_id}",
            "power":        f"{OID_PDU_POWER}.{pdu_id}",
            "power_min":    f"{OID_PDU_POWER_MIN}.{pdu_id}",
            "power_max":    f"{OID_PDU_POWER_MAX}.{pdu_id}",
            "power_avg":    f"{OID_PDU_POWER_AVG}.{pdu_id}",
            "power_factor": f"{OID_PDU_POWER_FACTOR}.{pdu_id}",
            "energy":       f"{OID_PDU_ENERGY}.{pdu_id}",
        }
        raw = await _snmp_get(
            self.host, self.port, self.community, list(pdu_oids.values())
        )
        # re-key by friendly name
        pdu_raw = {k: raw[v] for k, v in pdu_oids.items()}

        pdu_data: dict[str, Any] = {
            "model":        _str_value(pdu_raw["model"]),
            "power":        _scale(pdu_raw["power"],        0.1),
            "power_min":    _scale(pdu_raw["power_min"],    0.1),
            "power_max":    _scale(pdu_raw["power_max"],    0.1),
            "power_avg":    _scale(pdu_raw["power_avg"],    0.1),
            "current":      _scale(pdu_raw["current"],      0.1),
            "current_min":  _scale(pdu_raw["current_min"],  0.1),
            "current_max":  _scale(pdu_raw["current_max"],  0.1),
            "voltage":      _scale(pdu_raw["voltage"],      1.0),
            "power_factor": _scale(pdu_raw["power_factor"], 0.01),
            "energy_kwh":   _wh_to_kwh(pdu_raw["energy"]),
        }

        # ── Outlet discovery via SNMP walk ────────────────────────────────────
        # Walk the outlet-name, outlet-port and outlet-pdu-id subtrees once each
        # to discover which SNMP indices belong to our pdu_id.
        names_raw    = await _snmp_walk(self.host, self.port, self.community, OID_OUTLET_NAME)
        ports_raw    = await _snmp_walk(self.host, self.port, self.community, OID_OUTLET_PORT)
        pdu_ids_raw  = await _snmp_walk(self.host, self.port, self.community, OID_OUTLET_PDU_ID)

        # Build index→(name, port, pdu_id) map; filter to our pdu_id
        outlets_meta: dict[str, dict] = {}  # snmp_index → metadata
        for oid_str, name_val in names_raw.items():
            # SNMP index is the last OID component
            idx = oid_str.split(".")[-1]
            this_pdu = _get_int(pdu_ids_raw.get(f"{OID_OUTLET_PDU_ID}.{idx}"))
            if this_pdu != pdu_id:
                continue
            port_num = _get_int(ports_raw.get(f"{OID_OUTLET_PORT}.{idx}"))
            if port_num is None:
                continue
            outlets_meta[idx] = {
                "port":  port_num,
                "name":  _str_value(name_val),
            }

        # ── Per-outlet GET ────────────────────────────────────────────────────
        outlets_data: dict[int, dict[str, Any]] = {}

        for idx, meta in outlets_meta.items():
            outlet_oids = {
                "status":       f"{OID_OUTLET_STATUS}.{idx}",
                "current":      f"{OID_OUTLET_CURRENT}.{idx}",
                "current_min":  f"{OID_OUTLET_CURRENT_MIN}.{idx}",
                "current_max":  f"{OID_OUTLET_CURRENT_MAX}.{idx}",
                "voltage":      f"{OID_OUTLET_VOLTAGE}.{idx}",
                "power":        f"{OID_OUTLET_POWER}.{idx}",
                "power_min":    f"{OID_OUTLET_POWER_MIN}.{idx}",
                "power_max":    f"{OID_OUTLET_POWER_MAX}.{idx}",
                "power_factor": f"{OID_OUTLET_POWER_FACTOR}.{idx}",
                "energy":       f"{OID_OUTLET_ENERGY}.{idx}",
            }
            raw_o = await _snmp_get(
                self.host, self.port, self.community, list(outlet_oids.values())
            )
            raw_o = {k: raw_o[v] for k, v in outlet_oids.items()}

            port = meta["port"]
            outlets_data[port] = {
                "name":         meta["name"],
                "status":       OUTLET_STATUS_MAP.get(_get_int(raw_o["status"]), "unknown"),
                "power":        _scale(raw_o["power"],        0.1),
                "power_min":    _scale(raw_o["power_min"],    0.1),
                "power_max":    _scale(raw_o["power_max"],    0.1),
                "current":      _scale(raw_o["current"],      0.1),
                "current_min":  _scale(raw_o["current_min"],  0.1),
                "current_max":  _scale(raw_o["current_max"],  0.1),
                "voltage":      _scale(raw_o["voltage"],      1.0),
                "power_factor": _scale(raw_o["power_factor"], 0.01),
                "energy_kwh":   _wh_to_kwh(raw_o["energy"]),
            }

        return {"pdu": pdu_data, "outlets": outlets_data}


# ── Platform setup ────────────────────────────────────────────────────────────

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Avocent PDU sensor platform from configuration.yaml."""

    host      = config[CONF_HOST]
    port      = config.get(CONF_PORT, DEFAULT_PORT)
    community = config.get(CONF_COMMUNITY, DEFAULT_COMMUNITY)
    pdu_id    = config.get(CONF_PDU_ID, DEFAULT_PDU_ID)
    name      = config.get(CONF_NAME, "PDU")
    # CONF_SCAN_INTERVAL is handled natively by HA's PLATFORM_SCHEMA and
    # arrives as a timedelta. Fall back to DEFAULT_SCAN_INTERVAL (int seconds).
    _scan = config.get(CONF_SCAN_INTERVAL)
    scan_interval = int(_scan.total_seconds()) if hasattr(_scan, 'total_seconds') else DEFAULT_SCAN_INTERVAL

    coordinator = AvocentPDUCoordinator(
        hass, host, port, community, pdu_id, name, scan_interval
    )

    # Fetch initial data. We use async_refresh() here because this is a
    # YAML-based platform (async_setup_platform), not a config entry.
    # async_config_entry_first_refresh() is only valid in async_setup_entry().
    try:
        await coordinator.async_refresh()
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("avocent_pdu: initial SNMP poll failed, will retry: %s", err)

    # If the initial refresh failed coordinator.data is None – bail out early.
    # The coordinator will keep retrying on its own schedule.
    if coordinator.data is None:
        _LOGGER.error(
            "avocent_pdu: could not reach PDU %s during setup – "
            "check host/community and ensure SNMP is reachable. "
            "The integration will retry automatically.",
            host,
        )
        return

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{host}_{pdu_id}")},
        name=name,
        manufacturer="Avocent (Vertiv)",
        model="PM3000",
        sw_version=coordinator.data["pdu"].get("model", "PM3000"),
        configuration_url=f"http://{host}/",
    )

    entities: list[SensorEntity] = []

    # ── PDU-level sensors ─────────────────────────────────────────────────────
    pdu_sensors: list[tuple[str, str, str | None, str | None, str]] = [
        # (key, friendly_suffix, device_class, state_class, unit)
        ("power",        "Power",              SensorDeviceClass.POWER,         SensorStateClass.MEASUREMENT,    UnitOfPower.WATT),
        ("power_min",    "Power Min",          SensorDeviceClass.POWER,         SensorStateClass.MEASUREMENT,    UnitOfPower.WATT),
        ("power_max",    "Power Max",          SensorDeviceClass.POWER,         SensorStateClass.MEASUREMENT,    UnitOfPower.WATT),
        ("power_avg",    "Power Avg",          SensorDeviceClass.POWER,         SensorStateClass.MEASUREMENT,    UnitOfPower.WATT),
        ("current",      "Current",            SensorDeviceClass.CURRENT,       SensorStateClass.MEASUREMENT,    UnitOfElectricCurrent.AMPERE),
        ("current_min",  "Current Min",        SensorDeviceClass.CURRENT,       SensorStateClass.MEASUREMENT,    UnitOfElectricCurrent.AMPERE),
        ("current_max",  "Current Max",        SensorDeviceClass.CURRENT,       SensorStateClass.MEASUREMENT,    UnitOfElectricCurrent.AMPERE),
        ("voltage",      "Voltage",            SensorDeviceClass.VOLTAGE,       SensorStateClass.MEASUREMENT,    UnitOfElectricPotential.VOLT),
        ("power_factor", "Power Factor",       SensorDeviceClass.POWER_FACTOR,  SensorStateClass.MEASUREMENT,    None),
        ("energy_kwh",   "Energy",             SensorDeviceClass.ENERGY,        SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR),
    ]

    # Slugify the PDU name once for use in entity_id construction.
    # e.g. "PDU01" → "pdu01",  "My PDU #2" → "my_pdu_2"
    from homeassistant.util import slugify as _slugify
    name_slug = _slugify(name)

    for key, suffix, dev_class, state_class, unit in pdu_sensors:
        # Entity ID: sensor.pdu01_pdu_power  (stable, name-independent after first registration)
        obj_id = f"{name_slug}_pdu_{key}"
        entities.append(
            AvocentPDUSensor(
                coordinator=coordinator,
                device_info=device_info,
                unique_id=f"{host}_{pdu_id}_pdu_{key}",
                name=f"{name} {suffix}",
                suggested_object_id=obj_id,
                data_path=("pdu", key),
                device_class=dev_class,
                state_class=state_class,
                unit=unit,
            )
        )

    # ── Outlet sensors (added after first coordinator refresh) ────────────────
    for port_num, outlet in sorted(coordinator.data["outlets"].items()):
        # Friendly name uses the live PDU outlet name (updates on next HA restart
        # when the outlet is renamed on the PDU), but entity_id and unique_id are
        # always port-number-based and never change.
        outlet_label = outlet["name"] or f"Port {port_num:02d}"

        outlet_sensors: list[tuple[str, str, str | None, str | None, str | None]] = [
            ("power",        "Power",         SensorDeviceClass.POWER,         SensorStateClass.MEASUREMENT,      UnitOfPower.WATT),
            ("power_min",    "Power Min",     SensorDeviceClass.POWER,         SensorStateClass.MEASUREMENT,      UnitOfPower.WATT),
            ("power_max",    "Power Max",     SensorDeviceClass.POWER,         SensorStateClass.MEASUREMENT,      UnitOfPower.WATT),
            ("current",      "Current",       SensorDeviceClass.CURRENT,       SensorStateClass.MEASUREMENT,      UnitOfElectricCurrent.AMPERE),
            ("current_min",  "Current Min",   SensorDeviceClass.CURRENT,       SensorStateClass.MEASUREMENT,      UnitOfElectricCurrent.AMPERE),
            ("current_max",  "Current Max",   SensorDeviceClass.CURRENT,       SensorStateClass.MEASUREMENT,      UnitOfElectricCurrent.AMPERE),
            ("voltage",      "Voltage",       SensorDeviceClass.VOLTAGE,       SensorStateClass.MEASUREMENT,      UnitOfElectricPotential.VOLT),
            ("power_factor", "Power Factor",  SensorDeviceClass.POWER_FACTOR,  SensorStateClass.MEASUREMENT,      None),
            ("energy_kwh",   "Energy",        SensorDeviceClass.ENERGY,        SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR),
            ("status",       "Status",        None,                            None,                              None),
        ]

        for key, suffix, dev_class, state_class, unit in outlet_sensors:
            # Entity ID: sensor.pdu01_port03_energy  ← always port-number-based
            # Friendly name: "PDU01 PVE01 Energy"    ← reflects current PDU label
            obj_id = f"{name_slug}_port{port_num:02d}_{key}"
            entities.append(
                AvocentPDUSensor(
                    coordinator=coordinator,
                    device_info=device_info,
                    unique_id=f"{host}_{pdu_id}_port{port_num:02d}_{key}",
                    name=f"{name} {outlet_label} {suffix}",
                    suggested_object_id=obj_id,
                    data_path=("outlets", port_num, key),
                    device_class=dev_class,
                    state_class=state_class,
                    unit=unit,
                )
            )

    async_add_entities(entities)


# ── Entity class ──────────────────────────────────────────────────────────────

class AvocentPDUSensor(CoordinatorEntity, SensorEntity):
    """Single sensor entity for an Avocent PM3000 PDU data point.

    The entity_id slug is derived from `suggested_object_id` (port-number-based)
    so that renaming an outlet on the PDU only changes the friendly name in HA,
    never the entity_id or unique_id.

    Entity ID pattern:
      PDU-level : sensor.{slug(name)}_pdu_{key}
                  e.g.  sensor.pdu01_pdu_energy
      Outlet    : sensor.{slug(name)}_port{NN}_{key}
                  e.g.  sensor.pdu01_port03_energy
    """

    def __init__(
        self,
        coordinator: AvocentPDUCoordinator,
        device_info: DeviceInfo,
        unique_id: str,
        name: str,
        suggested_object_id: str,
        data_path: tuple,          # e.g. ("pdu", "power") or ("outlets", 3, "energy_kwh")
        device_class: str | None,
        state_class: str | None,
        unit: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id        = unique_id
        self._attr_name             = name
        self._attr_device_info      = device_info
        self._attr_device_class     = device_class
        self._attr_state_class      = state_class
        self._attr_native_unit_of_measurement = unit
        self._data_path             = data_path
        # Pin the entity_id slug so outlet renames never change the entity_id.
        # HA only uses this as a *suggestion* on first registration; once
        # the entity is in the registry the stored entity_id takes precedence.
        self.entity_id = (
            f"sensor.{suggested_object_id}"
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value by traversing the coordinator data dict."""
        data = self.coordinator.data
        try:
            for key in self._data_path:
                data = data[key]
            return data
        except (KeyError, TypeError):
            return None
