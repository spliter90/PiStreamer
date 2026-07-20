# PiStreamer-Dokumentation

Diese Dokumentation beschreibt Installation, Einrichtung und Betrieb von PiStreamer. Sie richtet sich sowohl an Einsteiger ohne Linux-Erfahrung als auch an Betreiber, die das System dauerhaft einsetzen möchten.

## Einstieg

1. [Installation](01_Installation.md)
2. [Erste Schritte](02_Erste_Schritte.md)
3. [Streaming und Qualitätsprofile](03_Streaming.md)
4. [Fehlerbehebung](04_Fehlerbehebung.md)

## Weitere geplante Kapitel

- Dashboard und Bedienoberfläche
- Kamera-, Audio- und Capture-Hardware
- Mobilfunkbetrieb
- Overlays und Pausenbild
- Updates und Wiederherstellung
- Diagnose und Logdateien
- REST-API
- Entwicklerhandbuch

## Wichtige Pfade

| Zweck | Pfad |
|---|---|
| Installation | `/opt/pistreamer` |
| Konfiguration | `/etc/pistreamer/config.yaml` |
| Nutzerdaten | `/opt/pistreamer/data` |
| systemd-Dienst | `pistreamer.service` |
| Weboberfläche | `http://pistreamer.local:8080` |

## Projektstatus

PiStreamer befindet sich in aktiver Entwicklung. Vor einem produktiven Einsatz sollten Kamera, Audio, Netzwerkstabilität und thermische Belastung auf der konkreten Hardware getestet werden.
