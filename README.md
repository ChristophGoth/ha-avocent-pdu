# avocent_pdu – Home Assistant Custom Component

Custom Component für die **Avocent PM3000 PDU** (und PM2000) via SNMPv2c.

Erzeugt pro konfigurierter PDU **ein einzelnes HA-Gerät** mit allen Sensor-Entitäten
darunter gruppiert – statt loser SNMP-Sensoren ohne Gerätezugehörigkeit.

> **KI-generiert** – Dieser Code wurde mit Unterstützung von [Claude](https://claude.ai)
> (Anthropic) erstellt. Claude ist als Co-Autor in der Git-Historie eingetragen.
> Der Code wurde vom Repository-Inhaber geprüft und veröffentlicht.

---

## Installation

### Via HACS (empfohlen)

1. HACS → ⋮ → **Custom repositories**
2. URL: `https://github.com/ChristophGoth/ha-avocent-pdu`
3. Kategorie: **Integration**
4. **Herunterladen** → Home Assistant neu starten

### Manuell

```
config/
└── custom_components/
    └── avocent_pdu/
        ├── __init__.py
        ├── manifest.json
        ├── const.py
        └── sensor.py
```

HA lädt `pysnmp` automatisch beim ersten Start (via `requirements` in manifest.json).

---

## Konfiguration (configuration.yaml)

```yaml
sensor:
  # ── PDU01 ────────────────────────────────────────────────────────────────
  - platform: avocent_pdu
    name: PDU01                   # Anzeigename in HA (auch Geräte-Name)
    host: 192.168.1.10            # IP-Adresse der PDU
    community: public             # SNMPv2c Community String
    pdu_id: 1                     # 1 = primäre PDU, 2–5 = verkettete PDUs
    scan_interval: 60             # Abfrageintervall in Sekunden (min 10)

  # ── PDU02 (zweite eigenständige PDU) ─────────────────────────────────────
  - platform: avocent_pdu
    name: PDU02
    host: 192.168.1.11
    community: public
    pdu_id: 1
    scan_interval: 60
```

### Parameter

| Parameter       | Pflicht | Standard | Beschreibung                                              |
|----------------|---------|----------|-----------------------------------------------------------|
| `host`          | ✓       | –        | IP/Hostname der PDU                                       |
| `name`          |         | `PDU`    | Anzeigename (Gerät + Entitäts-Präfix)                    |
| `community`     |         | `public` | SNMPv2c Read Community                                    |
| `port`          |         | `161`    | SNMP UDP Port                                             |
| `pdu_id`        |         | `1`      | PDU-Index in einer Chain (1–5)                           |
| `scan_interval` |         | `60`     | Abfrageintervall Sekunden                                 |

---

## Erzeugte Entitäten

### PDU-Gesamt (Inlet / Strip)

| Entität                    | Klasse         | State Class        | Einheit |
|---------------------------|----------------|--------------------|---------|
| `{name} Power`            | power          | measurement        | W       |
| `{name} Power Min`        | power          | measurement        | W       |
| `{name} Power Max`        | power          | measurement        | W       |
| `{name} Power Avg`        | power          | measurement        | W       |
| `{name} Current`          | current        | measurement        | A       |
| `{name} Current Min`      | current        | measurement        | A       |
| `{name} Current Max`      | current        | measurement        | A       |
| `{name} Voltage`          | voltage        | measurement        | V       |
| `{name} Power Factor`     | power_factor   | measurement        | –       |
| `{name} Energy`           | energy         | total_increasing   | kWh     |

### Pro Outlet (Port)

Der Outlet-Name wird direkt aus dem PDU-SNMP-Namen gelesen (OID `.5.1.4`) und als
**Friendly Name** in HA angezeigt. Die **Entity-ID** basiert ausschließlich auf der
Port-Nummer und ändert sich nie — auch nicht wenn der Outlet auf der PDU umbenannt wird.

| Entität (Friendly Name)             | Klasse         | State Class        | Einheit |
|------------------------------------|----------------|--------------------|---------|
| `{name} {outlet_name} Power`       | power          | measurement        | W       |
| `{name} {outlet_name} Power Min`   | power          | measurement        | W       |
| `{name} {outlet_name} Power Max`   | power          | measurement        | W       |
| `{name} {outlet_name} Current`     | current        | measurement        | A       |
| `{name} {outlet_name} Current Min` | current        | measurement        | A       |
| `{name} {outlet_name} Current Max` | current        | measurement        | A       |
| `{name} {outlet_name} Voltage`     | voltage        | measurement        | V       |
| `{name} {outlet_name} Power Factor`| power_factor   | measurement        | –       |
| `{name} {outlet_name} Energy`      | energy         | total_increasing   | kWh     |
| `{name} {outlet_name} Status`      | –              | –                  | on/off  |

---

## Entity-ID-Schema

Entity-IDs sind stabil und ändern sich nicht bei Outlet-Umbenennungen auf der PDU.

```
PDU-Gesamt : sensor.{slug(name)}_pdu_{key}
             z.B.  sensor.pdu01_pdu_energy
                   sensor.pdu01_pdu_power

Pro Outlet : sensor.{slug(name)}_port{NN}_{key}
             z.B.  sensor.pdu01_port03_energy
                   sensor.pdu01_port03_power
                   sensor.pdu02_port10_energy
```

Der Friendly Name (`{name} {outlet_name} Energy`) spiegelt dagegen immer den
aktuellen Outlet-Namen der PDU wider und wird beim nächsten HA-Neustart aktualisiert.

---

## Energie-Dashboard

Die `Energy`-Entitäten (`device_class: energy`, `state_class: total_increasing`)
sind direkt im **Energie-Dashboard** unter „Individuelle Geräte" verwendbar.

**Empfohlene Verkettung:**

```
Netz (stromzaehler_sml)
└── Keller (stromzahler_keller)
    ├── sensor.pdu01_pdu_energy      ← included_in_stat: sensor.stromzahler_keller_import_energy
    │   ├── sensor.pdu01_port01_energy  ← included_in_stat: sensor.pdu01_pdu_energy
    │   ├── sensor.pdu01_port02_energy
    │   └── …
    └── sensor.pdu02_pdu_energy
        ├── sensor.pdu02_port01_energy
        └── …
```

---

## Bekannte OID-Tabelle (Avocent PM3000 MIB)

OID-Basis: `1.3.6.1.4.1.10418.17.2.5`

| Feld              | PDU-Level OID (`.3.1.X.1.{id}`) | Outlet-Level OID (`.5.1.X.{idx}`) | Skalierung |
|-------------------|----------------------------------|-----------------------------------|------------|
| Name / Model      | `.3.1.5.1.{id}`                  | `.5.1.4.{idx}`                    | String     |
| Current           | `.3.1.50.1.{id}`                 | `.5.1.50.{idx}`                   | ×0.1 A     |
| Current Min       | `.3.1.52.1.{id}`                 | `.5.1.52.{idx}`                   | ×0.1 A     |
| Current Max       | `.3.1.51.1.{id}`                 | `.5.1.51.{idx}`                   | ×0.1 A     |
| Voltage           | `.3.1.70.1.{id}`                 | `.5.1.70.{idx}`                   | ×1 V       |
| Power             | `.3.1.60.1.{id}`                 | `.5.1.60.{idx}`                   | ×0.1 W     |
| Power Min         | `.3.1.62.1.{id}`                 | `.5.1.62.{idx}`                   | ×0.1 W     |
| Power Max         | `.3.1.61.1.{id}`                 | `.5.1.61.{idx}`                   | ×0.1 W     |
| Power Avg         | `.3.1.63.1.{id}`                 | `.5.1.63.{idx}`                   | ×0.1 W     |
| Power Factor      | `.3.1.80.1.{id}`                 | `.5.1.80.{idx}`                   | ×0.01      |
| Energy            | `.3.1.105.1.{id}`                | `.5.1.105.{idx}`                  | Wh → kWh   |
| Outlet Status     | –                                | `.5.1.5.{idx}`                    | 1/2/3/4    |
| Outlet Port#      | –                                | `.5.1.7.{idx}`                    | Integer    |
| Outlet PDU-ID     | –                                | `.5.1.8.{idx}`                    | Integer    |

---

## Troubleshooting

**Keine Entitäten nach Neustart:**
- SNMP-Erreichbarkeit prüfen: `snmpwalk -v2c -c public <IP> 1.3.6.1.4.1.10418.17.2.5.5.1.4`
- HA-Log prüfen: `grep avocent_pdu home-assistant.log`

**Entitäten vorhanden aber `unavailable`:**
- Community-String prüfen
- `pdu_id` prüfen (bei Standalone immer `1`)

**Outlet-Name leer / `Port NN` statt Name als Friendly Name:**
- Im PDU-Webinterface unter Power Management → Outlets die Outlet-Namen setzen.
  Die Entity-ID bleibt davon unberührt; nur der Friendly Name in HA wird aktualisiert.

**pysnmp fehlt:**
- HA installiert Requirements aus `manifest.json` automatisch. Falls nicht:
  `pip install pysnmp==6.2.6` im HA-venv oder HACS-Python-Umgebung.

---

## Mitwirkende

Entwickelt von **ChristophGoth** mit KI-Unterstützung durch
**Claude Sonnet** ([Anthropic](https://anthropic.com)).

Claude ist in der Git-Historie als Co-Autor eingetragen gemäß den
[GitHub-Richtlinien für Co-Autoren](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors):

```
Co-authored-by: Claude <claude@anthropic.com>
```
