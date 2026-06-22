"""Constants and OID definitions for the Avocent PM3000 PDU integration.

OID base: 1.3.6.1.4.1.10418.17.2.5   (Avocent PM PDU MIB)
  .3.1.{field}.1.{pdu}          = PDU-level table  (pmPowerMgmtPDUTable)
  .5.1.{field}.1.{pdu}.{outlet} = Outlet-level table (pmPowerMgmtOutletsTable)

Both tables are indexed by the PDU chain position ({pdu}: 1 = primary,
2 = first chained …). The outlet table adds a second index component, the
1-based outlet number within that PDU. Verified live against a PM3000/10/16A:

  .5.1.4.1.{pdu}.{outlet}  = outlet name  (e.g. 'PVE01')
  .5.1.5.1.{pdu}.{outlet}  = outlet status (1=on, 2=off)
  .5.1.8.1.{pdu}.{outlet}  = owning PDU name string (e.g. 'PDU01')

Scaling notes (as documented in the Avocent MIB / Zabbix template):
  Current:     raw value × 0.1  → Ampere
  Power:       raw value × 0.1  → Watt
  Power factor:raw value × 0.01 → dimensionless (0–1)
  Voltage:     raw value × 1    → Volt  (integer, no scaling)
  Energy:      raw value × 1    → Wh    (integer, no scaling)
"""

DOMAIN = "avocent_pdu"

# ── Configuration keys (configuration.yaml) ──────────────────────────────────
CONF_HOST       = "host"
CONF_PORT       = "port"          # SNMP UDP port, default 161
CONF_COMMUNITY  = "community"     # SNMPv2c read community string
CONF_WRITE_COMMUNITY = "write_community"  # SNMPv2c write community (for switching)
CONF_PDU_ID     = "pdu_id"        # PDU chain index (1 = primary, 2 = first chained …)
CONF_NAME       = "name"          # Friendly name for this PDU device, e.g. "PDU01"
CONF_SCAN_INTERVAL = "scan_interval"  # seconds between polls

DEFAULT_PORT           = 161
DEFAULT_COMMUNITY      = "public"
DEFAULT_PDU_ID         = 1
DEFAULT_SCAN_INTERVAL  = 60   # seconds

# ── OID root ─────────────────────────────────────────────────────────────────
_BASE = "1.3.6.1.4.1.10418.17.2.5"

# ── PDU-level OIDs  (.3.1.{field}.1.{pdu_id}) ────────────────────────────────
# These return strip/inlet totals for the whole PDU.
OID_PDU_MODEL          = f"{_BASE}.3.1.5.1"      # string – model name
OID_PDU_CURRENT        = f"{_BASE}.3.1.50.1"     # ×0.1  A
OID_PDU_CURRENT_MIN    = f"{_BASE}.3.1.52.1"     # ×0.1  A
OID_PDU_CURRENT_MAX    = f"{_BASE}.3.1.51.1"     # ×0.1  A
OID_PDU_CURRENT_AVG    = f"{_BASE}.3.1.53.1"     # ×0.1  A
OID_PDU_VOLTAGE        = f"{_BASE}.3.1.70.1"     # V
OID_PDU_VOLTAGE_MIN    = f"{_BASE}.3.1.72.1"     # V
OID_PDU_VOLTAGE_MAX    = f"{_BASE}.3.1.71.1"     # V
OID_PDU_POWER          = f"{_BASE}.3.1.60.1"     # ×0.1  W
OID_PDU_POWER_MIN      = f"{_BASE}.3.1.62.1"     # ×0.1  W
OID_PDU_POWER_MAX      = f"{_BASE}.3.1.61.1"     # ×0.1  W
OID_PDU_POWER_AVG      = f"{_BASE}.3.1.63.1"     # ×0.1  W
OID_PDU_POWER_FACTOR   = f"{_BASE}.3.1.80.1"     # ×0.01
OID_PDU_ENERGY         = f"{_BASE}.3.1.105.1"    # Wh

# ── Outlet-level OIDs  (.5.1.{field}.1.{pdu}.{outlet}) ───────────────────────
# Column prefixes only; callers append ".1.{pdu}.{outlet}" to address a cell.
OID_OUTLET_NAME        = f"{_BASE}.5.1.4"        # string  (outlet label)
OID_OUTLET_STATUS      = f"{_BASE}.5.1.5"        # read state: 1=off, 2=on
OID_OUTLET_COMMAND     = f"{_BASE}.5.1.6"        # write cmd: 2=switch on, 3=switch off
OID_OUTLET_PDU_NAME    = f"{_BASE}.5.1.8"        # owning PDU name string ('PDU01')
OID_OUTLET_CURRENT     = f"{_BASE}.5.1.50"       # ×0.1  A
OID_OUTLET_CURRENT_MIN = f"{_BASE}.5.1.52"       # ×0.1  A
OID_OUTLET_CURRENT_MAX = f"{_BASE}.5.1.51"       # ×0.1  A
OID_OUTLET_VOLTAGE     = f"{_BASE}.5.1.70"       # V
OID_OUTLET_POWER       = f"{_BASE}.5.1.60"       # ×0.1  W
OID_OUTLET_POWER_MIN   = f"{_BASE}.5.1.62"       # ×0.1  W
OID_OUTLET_POWER_MAX   = f"{_BASE}.5.1.61"       # ×0.1  W
OID_OUTLET_POWER_FACTOR= f"{_BASE}.5.1.80"       # ×0.01
OID_OUTLET_ENERGY      = f"{_BASE}.5.1.105"      # Wh  (cumulative, monotonically increasing)

# ── Outlet status value map (read column .5) ──────────────────────────────────
OUTLET_STATUS_MAP = {
    1: "off",
    2: "on",
    3: "reboot",
    4: "unavailable",
}

# ── Outlet switch command values (write column .6) ────────────────────────────
OUTLET_CMD_ON  = 2
OUTLET_CMD_OFF = 3
