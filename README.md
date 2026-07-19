# PiStreamer

PiStreamer macht aus einem Raspberry Pi mit USB-Webcam eine über das Handy oder den Browser bedienbare YouTube-Live-Streaming-Box.

> **Projektstatus:** Frühe Entwicklungsversion. Vor dem produktiven Einsatz sollten Kamera, Audio, Stream-Stabilität und thermische Belastung auf der eigenen Hardware getestet werden.

## Funktionen

- YouTube-Streaming per FFmpeg
- Video über V4L2 und Ton über ALSA
- Mobilfreundliches Webinterface
- Start, Pause, Fortsetzen, Stop und Neustart
- Konfigurierbares Pausenbild
- Optionales Logo und Text-Overlay
- CPU-, RAM- und Temperaturanzeige
- FFmpeg-Log im Browser
- Login-Schutz
- Optionaler Stream-Autostart
- Automatischer Neustart des Webdienstes über systemd

## Unterstützte Hardware

Empfohlen:

- Raspberry Pi 5 für 720p oder 1080p
- Raspberry Pi 4 für 720p
- Raspberry Pi 3 oder 3B+ für einfache Streams mit reduzierter Auflösung
- USB-Webcam mit Mikrofon oder separates USB-Audiogerät
- LAN wird für stabile Livestreams empfohlen

Für einen Raspberry Pi 3 sind diese Startwerte sinnvoll:

- 854×480 oder 640×480
- 25 FPS
- 1000k bis 1500k Video-Bitrate

Das aktuelle Software-Encoding mit `libx264` kann einen Pi 3 bei 720p stark auslasten.

## Betriebssystem

Empfohlen wird Raspberry Pi OS Lite 64-Bit ohne Desktop. PiStreamer ist für Raspberry Pi OS und Debian ausgelegt.

Im Raspberry Pi Imager:

1. Raspberry Pi OS Lite 64-Bit auswählen.
2. Benutzername und Passwort festlegen.
3. SSH aktivieren.
4. WLAN konfigurieren oder später LAN anschließen.
5. SD-Karte schreiben und den Raspberry Pi starten.

## Installation

Per SSH mit dem Raspberry Pi verbinden:

```bash
ssh BENUTZER@pistreamer.local
```

Danach PiStreamer installieren:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/spliter90/PiStreamer.git
cd PiStreamer
sudo ./install.sh
```

Der Installer:

- installiert FFmpeg, Python, ALSA-, V4L2- und Netzwerkpakete
- kopiert PiStreamer nach `/opt/pistreamer`
- legt die Python-Umgebung an
- installiert alle Python-Abhängigkeiten
- legt `/etc/pistreamer/config.yaml` an
- fügt den Benutzer den Gruppen `video` und `audio` hinzu
- richtet `pistreamer.service` und Avahi ein
- startet PiStreamer automatisch

Vorhandene Konfigurationen und Dateien unter `/opt/pistreamer/data` bleiben bei einer erneuten Installation erhalten.

## Webinterface öffnen

Nach erfolgreicher Installation:

```text
http://pistreamer.local:8080
```

Alternativ die IP-Adresse verwenden:

```text
http://IP-DES-PI:8080
```

Erstanmeldung:

```text
Benutzer: admin
Passwort: change-me
```

Direkt nach der ersten Anmeldung das Web-Passwort und den YouTube-Stream-Key ändern.

## Pausenbild einrichten

Ein Bild mit derselben Auflösung wie der Stream verwenden, zum Beispiel 1280×720 Pixel.

```bash
sudo cp pause.png /opt/pistreamer/data/pause.png
sudo chown "$(id -un):$(id -gn)" /opt/pistreamer/data/pause.png
```

Danach in den Einstellungen diesen Pfad eintragen:

```text
/opt/pistreamer/data/pause.png
```

Beim Pausieren wird FFmpeg aktuell neu gestartet und mit dem Standbild verbunden. YouTube kann beim Umschalten deshalb kurzzeitig kein Signal anzeigen.

## Update

Im ursprünglichen Git-Klon:

```bash
cd ~/PiStreamer
sudo ./install.sh --update
```

Der Installer lädt die neueste Version, aktualisiert die Python-Abhängigkeiten und startet den Dienst neu. Die Konfiguration und der Ordner `/opt/pistreamer/data` bleiben erhalten.

Liegt der ursprüngliche Klon nicht mehr vor, kann ein neuer Klon verwendet werden:

```bash
cd ~
git clone https://github.com/spliter90/PiStreamer.git PiStreamer-update
cd PiStreamer-update
sudo ./install.sh
```

## Kamera und Mikrofon prüfen

Kamerageräte anzeigen:

```bash
v4l2-ctl --list-devices
v4l2-ctl --list-formats-ext -d /dev/video0
```

Audiogeräte anzeigen:

```bash
arecord -L
arecord -l
```

Typische ALSA-Eingaben sind beispielsweise:

```text
default
plughw:CARD=Webcam,DEV=0
```

Die genaue Bezeichnung hängt vom verwendeten Gerät ab.

## Dienst verwalten

Status anzeigen:

```bash
sudo systemctl status pistreamer
```

Dienst neu starten:

```bash
sudo systemctl restart pistreamer
```

Live-Log anzeigen:

```bash
sudo journalctl -u pistreamer -f
```

Letzte 100 Logzeilen anzeigen:

```bash
sudo journalctl -u pistreamer -n 100 --no-pager
```

## Häufige Probleme

### Webinterface ist nicht erreichbar

```bash
sudo systemctl status pistreamer
hostname -I
```

Danach `http://IP-ADRESSE:8080` öffnen.

### Kamera wird nicht gefunden

```bash
ls -l /dev/video*
groups
```

Der PiStreamer-Benutzer muss Mitglied der Gruppe `video` sein. Nach der ersten Installation kann ein Neustart sinnvoll sein:

```bash
sudo reboot
```

### Mikrofon funktioniert nicht

```bash
arecord -l
arecord -L
```

Anschließend das passende ALSA-Gerät im Webinterface auswählen.

### FFmpeg startet nicht

```bash
sudo journalctl -u pistreamer -n 100 --no-pager
ffmpeg -version
```

Außerdem prüfen, ob Stream-Key, Kamera, Mikrofon und Pausenbild-Pfad korrekt sind.

## Sicherheit

Das Webinterface ist für das lokale Netzwerk gedacht. Port 8080 sollte nicht direkt ins Internet freigegeben werden. Für Fernzugriff empfiehlt sich ein VPN wie Tailscale oder WireGuard.

Der YouTube-Stream-Key wird lokal in `/etc/pistreamer/config.yaml` gespeichert. Die Datei ist nur für `root` und die PiStreamer-Benutzergruppe lesbar.

Sicherheitsprobleme bitte nach den Hinweisen in [SECURITY.md](SECURITY.md) melden. Stream-Keys, Passwörter und vollständige Konfigurationsdateien dürfen nicht in öffentlichen Issues veröffentlicht werden.

## Mitwirken

Fehlerberichte und Beiträge sind willkommen. Hinweise zu Issues, Pull Requests und dem Umgang mit Logs stehen in [CONTRIBUTING.md](CONTRIBUTING.md). Änderungen werden in [CHANGELOG.md](CHANGELOG.md) dokumentiert.

## Deinstallation

Im ursprünglichen Repository:

```bash
sudo ./uninstall.sh
```

## Lizenz

PiStreamer ist unter der [MIT-Lizenz](LICENSE) veröffentlicht.

Copyright © 2026 Chris X.
