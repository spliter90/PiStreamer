# Changelog

Alle wesentlichen Änderungen an PiStreamer werden in dieser Datei dokumentiert.
Das Format orientiert sich an Keep a Changelog und das Projekt verwendet Semantic Versioning.

## [Unreleased]

## [1.2.0] - 2026-07-26

### Added

- Atomare Release-Installation mit getrennten virtuellen Python-Umgebungen
- Automatischer Rollback, wenn eine neue Version nicht startet
- GitHub-Actions-Prüfungen für Python, Konfiguration und Shell-Skripte
- Vollständige Beispielkonfiguration als zentrale Referenz

### Changed

- Root-Updater liegt unveränderbar unter `/usr/local/libexec`
- Programmcode und Python-Umgebung gehören `root`; nur Daten und Konfiguration bleiben für den Dienst schreibbar
- Sicherheitsaufnahme beendet FFmpeg bei einem Ausfall des Netzwerkziels, damit Reconnect und Auto-Quality greifen
- Health-Fehler verfallen nach dem vorgesehenen Zeitfenster
- Alte Einstellungsroute leitet auf das neue Einstellungsmenü weiter
- Versionsinformationen werden ausschließlich aus `VERSION` gelesen

### Fixed

- Dauerhafte Warn- oder Kritisch-Anzeige nach längst vergangenen FFmpeg-Fehlern
- Unvollständige Deinstallation der Update-Dienste
- Umwandlung normaler HTTP-Fehler in Status 500
- Ungültige Formwerte, die Einstellungsseiten mit Status 500 beenden konnten
- Wirkungsloser Schalter für Mobilfunkoptimierung; Mobilfunk wird jetzt eindeutig über die Profile gewählt

## [0.1.0] - 2026-07-19

### Added

- Erste öffentliche Entwicklungsversion von PiStreamer
