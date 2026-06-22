# avocent_pdu – Home Assistant Custom Component

Custom component for the **Avocent PM3000 PDU** (and PM2000) via SNMPv2c.

Creates **one HA device per configured PDU**, with all sensor entities grouped
underneath it — instead of loose, ungrouped SNMP sensors.

Daisy-chained PDUs are fully supported: configure one platform entry per PDU in
the chain, each addressed by its `pdu_id` (see [Daisy-chained PDUs](#daisy-chained-pdus)).

> **AI-generated** – This code was created with the help of
> [Claude](https://claude.ai) (Anthropic). Claude is recorded as a co-author in
> the git history. The code was reviewed and published by the repository owner.

---

## Installation

### Via HACS (recommended)

1. HACS → ⋮ → **Custom repositories**
2. URL: `https://github.com/ChristophGoth/ha-avocent-pdu`
3. Category: **Integration**
4. **Download** → restart Home Assistant

### Manual

```
config/
└── custom_components/
    └── avocent_pdu/
        ├── __init__.py
        ├── manifest.json
        ├── const.py
        └── sensor.py
```

HA installs `pysnmp` automatically on first start (via `requirements` in
`manifest.json`). Restart HA after updating so the requirement is (re)installed.

---

## Configuration (configuration.yaml)

```yaml
sensor:
  - platform: avocent_pdu
    name: PDU01                   # Display name in HA (also the device name)
    host: 192.168.1.10            # IP address of the PDU
    community: public             # SNMPv2c community string
    pdu_id: 1                     # 1 = primary PDU, 2–5 = chained PDUs
    scan_interval: 60             # Poll interval in seconds (min 10)
```

### Parameters

| Parameter       | Required | Default  | Description                                   |
|-----------------|----------|----------|-----------------------------------------------|
| `host`          | ✓        | –        | IP / hostname of the PDU                      |
| `name`          |          | `PDU`    | Display name (device + entity prefix)         |
| `community`     |          | `public` | SNMPv2c read community                        |
| `port`          |          | `161`    | SNMP UDP port                                 |
| `pdu_id`        |          | `1`      | PDU position in a chain (1–5)                 |
| `scan_interval` |          | `60`     | Poll interval in seconds                      |

---

## Daisy-chained PDUs

When multiple PM3000 units are daisy-chained, they share a **single IP / SNMP
agent** (the primary). Each PDU in the chain is addressed by its position via
`pdu_id`: `1` = primary, `2` = first chained unit, and so on (1–5).

Configure **one platform entry per PDU**, all pointing at the **same `host`**,
differing only in `pdu_id` and `name`:

```yaml
sensor:
  # ── PDU01 (primary) ────────────────────────────────────────────────────────
  - platform: avocent_pdu
    name: PDU01
    host: 192.168.1.10
    community: public
    pdu_id: 1

  # ── PDU02 (chained — SAME host, pdu_id: 2) ─────────────────────────────────
  - platform: avocent_pdu
    name: PDU02
    host: 192.168.1.10            # same agent as PDU01
    community: public
    pdu_id: 2
```

Each entry produces its **own HA device** (`PDU01`, `PDU02`) with its own strip
totals and its own 10 outlets. The integration filters the outlet table by
`pdu_id`, so PDU01 only sees its outlets and PDU02 only sees its own — verified
live against a 2× PM3000/10/16A chain.

> Two independent PDUs (separate IPs, not chained) are configured the same way,
> but with **different `host`** values and `pdu_id: 1` on each.

---

## Created entities

### PDU totals (inlet / strip)

| Entity                | Class        | State class      | Unit |
|-----------------------|--------------|------------------|------|
| `{name} Power`        | power        | measurement      | W    |
| `{name} Power Min`    | power        | measurement      | W    |
| `{name} Power Max`    | power        | measurement      | W    |
| `{name} Power Avg`    | power        | measurement      | W    |
| `{name} Current`      | current      | measurement      | A    |
| `{name} Current Min`  | current      | measurement      | A    |
| `{name} Current Max`  | current      | measurement      | A    |
| `{name} Voltage`      | voltage      | measurement      | V    |
| `{name} Power Factor` | power_factor | measurement      | –    |
| `{name} Energy`       | energy       | total_increasing | kWh  |

### Per outlet (port)

The outlet name is read directly from the PDU's SNMP name (OID column `.5.1.4`)
and shown as the **friendly name** in HA. The **entity ID** is based purely on
the port number and never changes — even if the outlet is renamed on the PDU.

| Entity (friendly name)              | Class        | State class      | Unit   |
|-------------------------------------|--------------|------------------|--------|
| `{name} {outlet_name} Power`        | power        | measurement      | W      |
| `{name} {outlet_name} Power Min`    | power        | measurement      | W      |
| `{name} {outlet_name} Power Max`    | power        | measurement      | W      |
| `{name} {outlet_name} Current`      | current      | measurement      | A      |
| `{name} {outlet_name} Current Min`  | current      | measurement      | A      |
| `{name} {outlet_name} Current Max`  | current      | measurement      | A      |
| `{name} {outlet_name} Voltage`      | voltage      | measurement      | V      |
| `{name} {outlet_name} Power Factor` | power_factor | measurement      | –      |
| `{name} {outlet_name} Energy`       | energy       | total_increasing | kWh    |
| `{name} {outlet_name} Status`       | –            | –                | on/off |

---

## Entity ID scheme

Entity IDs are stable and do not change when outlets are renamed on the PDU.

```
PDU totals : sensor.{slug(name)}_pdu_{key}
             e.g.  sensor.pdu01_pdu_energy
                   sensor.pdu01_pdu_power

Per outlet : sensor.{slug(name)}_port{NN}_{key}
             e.g.  sensor.pdu01_port03_energy
                   sensor.pdu01_port03_power
                   sensor.pdu02_port10_energy
```

The friendly name (`{name} {outlet_name} Energy`) always reflects the current
outlet name on the PDU and is refreshed on the next HA restart.

---

## Energy dashboard

The `Energy` entities (`device_class: energy`, `state_class: total_increasing`)
can be used directly in the **Energy dashboard** under "Individual devices".

**Recommended hierarchy:**

```
Grid (stromzaehler_sml)
└── Basement (stromzahler_keller)
    ├── sensor.pdu01_pdu_energy      ← included_in_stat: sensor.stromzahler_keller_import_energy
    │   ├── sensor.pdu01_port01_energy  ← included_in_stat: sensor.pdu01_pdu_energy
    │   ├── sensor.pdu01_port02_energy
    │   └── …
    └── sensor.pdu02_pdu_energy
        ├── sensor.pdu02_port01_energy
        └── …
```

---

## Avocent PM3000 OID reference

OID base: `1.3.6.1.4.1.10418.17.2.5`

Both tables are indexed by the PDU chain position `{pdu}` (1 = primary,
2 = first chained …). The **outlet table adds a second index component**, the
1-based outlet number within that PDU:

- PDU-level cell:  `.3.1.{field}.1.{pdu}`
- Outlet cell:     `.5.1.{field}.1.{pdu}.{outlet}`

| Field         | PDU-level (`.3.1.{field}.1.{pdu}`) | Outlet (`.5.1.{field}.1.{pdu}.{outlet}`) | Scaling   |
|---------------|------------------------------------|------------------------------------------|-----------|
| Name / model  | `.3.1.5`                           | `.5.1.4`                                 | string    |
| Current       | `.3.1.50`                          | `.5.1.50`                                | ×0.1 A    |
| Current min   | `.3.1.52`                          | `.5.1.52`                                | ×0.1 A    |
| Current max   | `.3.1.51`                          | `.5.1.51`                                | ×0.1 A    |
| Voltage       | `.3.1.70`                          | `.5.1.70`                                | ×1 V      |
| Power         | `.3.1.60`                          | `.5.1.60`                                | ×0.1 W    |
| Power min     | `.3.1.62`                          | `.5.1.62`                                | ×0.1 W    |
| Power max     | `.3.1.61`                          | `.5.1.61`                                | ×0.1 W    |
| Power avg     | `.3.1.63`                          | `.5.1.63`                                | ×0.1 W    |
| Power factor  | `.3.1.80`                          | `.5.1.80`                                | ×0.01     |
| Energy        | `.3.1.105`                         | `.5.1.105`                               | Wh → kWh  |
| Outlet status | –                                  | `.5.1.5`                                 | 1/2/3/4   |
| Owning PDU    | –                                  | `.5.1.8`                                 | string (`'PDU01'`) |

Outlet status values: `1` = on, `2` = off, `3` = reboot, `4` = unavailable.

---

## Troubleshooting

**No entities after restart:**
- Check SNMP reachability:
  `snmpwalk -v2c -c public <IP> 1.3.6.1.4.1.10418.17.2.5.5.1.4`
  (this walks the outlet-name column; you should see your outlet labels)
- Check the HA log: `grep avocent_pdu home-assistant.log`

**Entities present but `unavailable`:**
- Verify the community string
- Verify `pdu_id` (standalone PDU = `1`; chained PDUs increment from there)

**Only the 10 PDU-total sensors appear, no outlets:**
- Make sure you are on ≥ v1.0.6 — earlier versions indexed the outlet table
  incorrectly and silently dropped every outlet.

**Outlet name empty / `Port NN` shown instead of a name:**
- Set the outlet names in the PDU web UI under Power Management → Outlets.
  The entity ID is unaffected; only the friendly name in HA updates (on restart).

**pysnmp missing:**
- HA installs requirements from `manifest.json` automatically. If not:
  `pip install "pysnmp>=7.1.0,<8"` in the HA venv / HACS Python environment.

---

## Contributors

Developed by **ChristophGoth** with AI assistance from
**Claude** ([Anthropic](https://anthropic.com)).

Claude is recorded as a co-author in the git history per the
[GitHub multiple-authors guidelines](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors):

```
Co-authored-by: Claude <claude@anthropic.com>
```
