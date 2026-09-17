# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier festgehalten.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionierung an [Semantic Versioning](https://semver.org/lang/de/).

## [1.1.2]

* SNMP-Abfragen laufen nicht mehr im Event-Loop. Das Laden der MIB-Dateien
  greift blockierend auf das Dateisystem zu und bremste damit Home Assistant
  insgesamt aus.

## [1.1.1]

* Die Min-/Max-Sensoren entfallen; die Werte lassen sich bei Bedarf über
  Statistik-Helfer nachbilden.
* Entitätsnamen sind einheitlich mit `Port NN - ` bzw. dem PDU-Namen
  vorangestellt, damit sie in Listen eindeutig bleiben.

## [1.1.0]

* Schaltbare Ausgänge: jeder Outlet erscheint als `switch`-Entität und wird
  per SNMP SET geschaltet.
* Die Zuordnung der Statuswerte war invertiert und ist korrigiert.

## [1.0.6]

* README vollständig auf Englisch, inklusive Dokumentation der
  Daisy-Chain-Konfiguration und einer korrigierten OID-Tabelle.
* Die Indizierung der Outlet-Tabelle war falsch, wodurch die Sensoren je
  Ausgang nicht angelegt wurden.

## [1.0.5]

* Konfiguration über einen Config Flow statt YAML, damit alle Entitäten unter
  einem gemeinsamen Gerät zusammengefasst werden.

## [1.0.4]

* Portierung auf die asynchrone API von pysnmp 7.x; pysnmp ist entsprechend
  auf 7.x festgelegt.
* Eine `None`-Prüfung griff erst nach dem Zugriff und lief dadurch ins Leere.

## [1.0.3]

* Der Coordinator nutzt `async_refresh()`; `async_config_entry_first_refresh()`
  passte zum damaligen YAML-Setup nicht.

## [1.0.2]

* `scan_interval` entfällt aus dem `PLATFORM_SCHEMA`; das Abfrageintervall
  verwaltet Home Assistant selbst.

## [1.0.1]

* Das Verzeichnis `brands/` heißt jetzt `brand/`, wie HACS es erwartet.

## [1.0.0]

* Erste Veröffentlichung: Avocent-PM3000-PDUs über SNMP, vollständig lokal.
* Sensoren je PDU und je Ausgang, gruppiert unter einem Gerät.
