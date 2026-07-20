# Fehlerbehebung

## Weboberfläche nicht erreichbar

```bash
sudo systemctl status pistreamer
hostname -I
```

Öffne anschließend:

```text
http://IP-ADRESSE:8080
```

Dienst neu starten:

```bash
sudo systemctl restart pistreamer
```

## Kamera wird nicht erkannt

```bash
ls -l /dev/video*
v4l2-ctl --list-devices
groups
```

Der Benutzer des PiStreamer-Dienstes muss Mitglied der Gruppe `video` sein. Nach einer Gruppenänderung ist ein Neustart sinnvoll:

```bash
sudo reboot
```

Prüfe außerdem, ob ein anderes Programm bereits auf die Kamera zugreift.

## Kein Bild oder falsches Bildformat

```bash
v4l2-ctl --list-formats-ext -d /dev/video0
```

Nicht jede Kamera unterstützt jede Kombination aus Auflösung und Bildrate. Wähle zunächst ein kleineres Profil und teste erneut.

## Mikrofon funktioniert nicht

```bash
arecord -l
arecord -L
```

Kurze Testaufnahme:

```bash
arecord -D default -d 5 -f cd /tmp/test.wav
aplay /tmp/test.wav
```

Ersetze `default` bei Bedarf durch das passende ALSA-Gerät.

## FFmpeg startet nicht

```bash
ffmpeg -version
sudo journalctl -u pistreamer -n 100 --no-pager
```

Prüfe:

- Stream-Key und RTMP-Ziel
- Kamera-Gerätepfad
- Audioquelle
- unterstützte Auflösung und FPS
- Pausenbild-Pfad
- Dateiberechtigungen

## Stream bricht regelmäßig ab

1. Ein kleineres Qualitätsprofil auswählen.
2. Raspberry Pi möglichst per LAN verbinden.
3. CPU-Temperatur prüfen.
4. Uploadrate und Paketverlust prüfen.
5. FFmpeg-Log auf Reconnects und ausgelassene Frames untersuchen.

## Hohe Temperatur

Temperatur auslesen:

```bash
vcgencmd measure_temp
```

Bei hoher Temperatur:

- aktiven Kühler verwenden,
- Gehäusebelüftung verbessern,
- niedrigeres Profil wählen,
- Overlays reduzieren,
- direkte Sonneneinstrahlung vermeiden.

## Dienstprotokoll

Live-Ausgabe:

```bash
sudo journalctl -u pistreamer -f
```

Letzte 200 Zeilen:

```bash
sudo journalctl -u pistreamer -n 200 --no-pager
```

Vor dem Veröffentlichen von Logs müssen Stream-Keys, Passwörter, öffentliche IP-Adressen und andere Zugangsdaten entfernt werden.

## Update schlägt fehl

Update erneut aus einer frischen Installer-Datei starten:

```bash
cd /tmp
curl -fL https://raw.githubusercontent.com/spliter90/PiStreamer/main/install.sh -o pistreamer-install.sh
chmod +x pistreamer-install.sh
sudo ./pistreamer-install.sh --update
```

Danach den Dienststatus prüfen:

```bash
sudo systemctl status pistreamer
```
