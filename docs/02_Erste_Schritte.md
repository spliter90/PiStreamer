# Erste Schritte

Nach der Installation ist PiStreamer unter `http://pistreamer.local:8080` erreichbar.

## 1. Anmelden

Verwende bei der ersten Anmeldung:

```text
Benutzer: admin
Passwort: change-me
```

Ändere anschließend sofort das Web-Passwort.

## 2. Kamera prüfen

Verfügbare Videogeräte:

```bash
v4l2-ctl --list-devices
v4l2-ctl --list-formats-ext -d /dev/video0
```

Wähle in den Einstellungen das passende Gerät, beispielsweise `/dev/video0`.

## 3. Audioquelle prüfen

```bash
arecord -l
arecord -L
```

Typische Eingaben sind:

```text
default
plughw:CARD=Webcam,DEV=0
```

Die genaue Bezeichnung hängt von Kamera, Capture-Karte oder USB-Audiogerät ab.

## 4. Stream-Ziel eintragen

Trage den RTMP-Server und den Stream-Key in der Weboberfläche ein. Zugangsdaten werden lokal in `/etc/pistreamer/config.yaml` gespeichert.

Stream-Keys dürfen nicht in Screenshots, Logs oder öffentlichen Issues veröffentlicht werden.

## 5. Qualitätsprofil wählen

Für den ersten Test empfiehlt sich:

- **Mobilfunk Standard** bei LTE oder schwankendem WLAN
- **WLAN Standard** bei einer stabilen WLAN-Verbindung
- **LAN Full HD** nur bei Raspberry Pi 5, passender Kamera und stabiler LAN-Verbindung

Weitere Details stehen unter [Streaming und Qualitätsprofile](03_Streaming.md).

## 6. Teststream starten

1. Zielplattform öffnen und einen privaten oder nicht gelisteten Teststream vorbereiten.
2. PiStreamer starten.
3. Bild, Ton und Synchronität kontrollieren.
4. CPU-Temperatur und Streamstatus mindestens 15 Minuten beobachten.
5. Stream stoppen und FFmpeg-Log auf Fehler prüfen.

## 7. Pausenbild einrichten

Das Bild sollte dieselbe Auflösung wie das gewählte Profil haben.

```bash
sudo cp pause.png /opt/pistreamer/data/pause.png
```

Pfad in der Weboberfläche:

```text
/opt/pistreamer/data/pause.png
```

## Checkliste für den ersten produktiven Einsatz

- Standardpasswort geändert
- Stream-Key geprüft
- Kamera und Audio korrekt ausgewählt
- privater Teststream erfolgreich
- Temperatur stabil
- Uploadrate ausreichend
- Pausenbild getestet
- Neustart des Raspberry Pi getestet
- Weboberfläche nach Neustart erreichbar
