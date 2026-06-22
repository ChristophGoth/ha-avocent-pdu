"""Constants and OID definitions for the Avocent PM3000 PDU integration.

OID base: 1.3.6.1.4.1.10418.17.2.5   (Avocent PM PDU MIB)
  .3.1.X.1.{pdu_id}   = PDU-level table (pmPowerMgmtPDUTable)
  .5.1.X.{outlet_idx} = Outlet-level table (pmPowerMgmtOutletsTable)

Outlet discovery OIDs:
  .5.5.1.4  = outlet name
  .5.5.1.7  = outlet port number (1-based)
  .5.5.1.8  = PDU id the outlet belongs to

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
CONF_COMMUNITY  = "community"     # SNMPv2c community string
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

# ── Outlet-level OIDs  (.5.1.{field}.{outlet_idx}) ───────────────────────────
OID_OUTLET_NAME        = f"{_BASE}.5.1.4"        # string
OID_OUTLET_STATUS      = f"{_BASE}.5.1.5"        # 1=on, 2=off, 3=reboot, 4=na
OID_OUTLET_PORT        = f"{_BASE}.5.1.7"        # outlet port number (1-based)
OID_OUTLET_PDU_ID      = f"{_BASE}.5.1.8"        # which PDU in chain
OID_OUTLET_CURRENT     = f"{_BASE}.5.1.50"       # ×0.1  A
OID_OUTLET_CURRENT_MIN = f"{_BASE}.5.1.52"       # ×0.1  A
OID_OUTLET_CURRENT_MAX = f"{_BASE}.5.1.51"       # ×0.1  A
OID_OUTLET_VOLTAGE     = f"{_BASE}.5.1.70"       # V
OID_OUTLET_POWER       = f"{_BASE}.5.1.60"       # ×0.1  W
OID_OUTLET_POWER_MIN   = f"{_BASE}.5.1.62"       # ×0.1  W
OID_OUTLET_POWER_MAX   = f"{_BASE}.5.1.61"       # ×0.1  W
OID_OUTLET_POWER_FACTOR= f"{_BASE}.5.1.80"       # ×0.01
OID_OUTLET_ENERGY      = f"{_BASE}.5.1.105"      # Wh  (cumulative, monotonically increasing)

# ── Outlet status value map ───────────────────────────────────────────────────
OUTLET_STATUS_MAP = {
    1: "on",
    2: "off",
    3: "reboot",
    4: "unavailable",
}
