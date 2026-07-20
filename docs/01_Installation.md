# Installation

## Voraussetzungen

Empfohlen werden:

- Raspberry Pi 4 oder Raspberry Pi 5
- Raspberry Pi OS Lite 64-Bit
- USB-Webcam, UVC-Kamera oder USB-Capture-Gerät
- unterstützte ALSA-Audioquelle
- stabile LAN- oder WLAN-Verbindung
- SSH-Zugang zum Raspberry Pi

Für Full-HD-Streaming wird ein Raspberry Pi 5 und eine kabelgebundene Netzwerkverbindung empfohlen.

## Raspberry Pi vorbereiten

Im Raspberry Pi Imager:

1. **Raspberry Pi OS Lite 64-Bit** auswählen.
2. Benutzername und Passwort festlegen.
3. SSH aktivieren.
4. WLAN konfigurieren oder LAN anschließen.
5. SD-Karte schreiben und den Raspberry Pi starten.

Anschließend per SSH verbinden:

```bash
ssh BENUTZER@pistreamer.local
```

## Standardinstallation

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/spliter90/PiStreamer.git
cd PiStreamer
sudo ./install.sh
```

Der Installer:

- installiert Systempakete und FFmpeg,
- richtet eine Python-Umgebung ein,
- kopiert PiStreamer nach `/opt/pistreamer`,
- erzeugt `/etc/pistreamer/config.yaml`,
- richtet den systemd-Dienst ein,
- aktiviert den Zugriff über `pistreamer.local`,
- startet die Anwendung.

## Weboberfläche öffnen

```text
http://pistreamer.local:8080
```

Alternativ kann die IP-Adresse verwendet werden:

```text
http://IP-DES-PI:8080
```

Standardzugang:

```text
Benutzer: admin
Passwort: change-me
```

Das Standardpasswort muss direkt nach der ersten Anmeldung geändert werden.

## Update ohne vorhandenen Git-Klon

```bash
cd /tmp
curl -fL https://raw.githubusercontent.com/spliter90/PiStreamer/main/install.sh -o pistreamer-install.sh
chmod +x pistreamer-install.sh
sudo ./pistreamer-install.sh --update
```

Die Konfiguration unter `/etc/pistreamer` und die Daten unter `/opt/pistreamer/data` bleiben erhalten.

## Installation prüfen

```bash
sudo systemctl status pistreamer
```

Bei Problemen:

```bash
sudo journalctl -u pistreamer -n 100 --no-pager
```

## Sicherheit

Port 8080 sollte nicht direkt aus dem Internet erreichbar sein. Für Fernzugriff empfiehlt sich ein VPN wie WireGuard oder Tailscale.
