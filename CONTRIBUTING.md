# Mitwirken an PiStreamer

Beiträge, Fehlermeldungen und Verbesserungsvorschläge sind willkommen.

## Fehler melden

Bitte vor dem Erstellen eines Issues prüfen, ob das Problem bereits gemeldet wurde. Eine gute Fehlermeldung enthält:

- Raspberry-Pi-Modell und Betriebssystem
- verwendete Kamera und Audioquelle
- genaue Schritte zum Reproduzieren
- erwartetes und tatsächliches Verhalten
- relevante Ausgaben aus `journalctl -u pistreamer`

Stream-Keys, Passwörter, private IP-Adressen und andere Zugangsdaten müssen aus Logs entfernt werden.

## Änderungen einreichen

1. Repository forken und einen eigenen Branch anlegen.
2. Änderungen klein und nachvollziehbar halten.
3. Installation oder betroffene Funktion lokal testen.
4. Dokumentation und `CHANGELOG.md` bei sichtbaren Änderungen aktualisieren.
5. Pull Request mit einer klaren Beschreibung eröffnen.

## Stil

- Python-Code soll lesbar und möglichst typisiert sein.
- Shell-Skripte verwenden `set -Eeuo pipefail`.
- Keine lokalen Konfigurationen, Medien oder Zugangsdaten committen.

Mit dem Einreichen eines Beitrags erklärst du dich damit einverstanden, dass dein Beitrag unter der MIT-Lizenz des Projekts veröffentlicht wird.
