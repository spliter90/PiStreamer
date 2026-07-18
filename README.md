# PiStreamer

PiStreamer macht aus einem Raspberry Pi 5 mit USB-Webcam eine über das Handy bedienbare YouTube-Live-Streaming-Box.

## Funktionen der ersten Version

- YouTube-Streaming per FFmpeg, 1280×720 bei 25/30 FPS
- Video über V4L2 und Ton über ALSA
- Mobilfreundliches Webinterface
- Start, Stop und Neustart
- CPU-, RAM- und Temperaturanzeige
- FFmpeg-Log
- Login-Schutz
- Optionaler Stream-Autostart
- systemd-Neustart des Webdienstes bei Fehlern

## Voraussetzungen

- Raspberry Pi 5
- Raspberry Pi OS Lite 64 Bit oder Desktop, Debian Bookworm/Trixie-basiert
- USB-Webcam mit Mikrofon
- LAN oder WLAN
- YouTube-Kanal mit aktiviertem Livestreaming und Stream-Key

## Ein-Klick-Installation

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/DEIN-BENUTZER/PiStreamer.git
cd PiStreamer
sudo ./install.sh
```

Danach öffnen:

- `http://pistreamer.local:8080`
- alternativ `http://IP-DES-PI:8080`

Erstanmeldung: `admin` / `change-me`

**Direkt nach der Anmeldung Passwort und Stream-Key ändern.**

## Geräte ermitteln

```bash
v4l2-ctl --list-devices
v4l2-ctl --list-formats-ext -d /dev/video0
arecord -L
arecord -l
```

Typische ALSA-Eingabe für eine USB-Webcam ist beispielsweise `plughw:CARD=Webcam,DEV=0`. Die genaue Bezeichnung hängt vom Gerät ab.

## Service verwalten

```bash
sudo systemctl status pistreamer
sudo systemctl restart pistreamer
journalctl -u pistreamer -f
```

## Sicherheit

Das Webinterface ist für das lokale Netzwerk gedacht. Port 8080 nicht direkt ins Internet freigeben. Für Fernzugriff empfiehlt sich ein VPN wie Tailscale oder WireGuard.

Der YouTube-Stream-Key wird mit Dateirechten `0600` in `/etc/pistreamer/config.yaml` gespeichert. In dieser MVP-Version erfolgt keine zusätzliche Verschlüsselung auf dem Gerät.

## Deinstallation

```bash
sudo ./uninstall.sh
```
