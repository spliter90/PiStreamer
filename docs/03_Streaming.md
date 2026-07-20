# Streaming und Qualitätsprofile

PiStreamer verwendet vordefinierte Qualitätsprofile. Ein Profil setzt Auflösung, Bildrate, Zielbitrate, Maximalbitrate und FFmpeg-Puffer gemeinsam.

## Profile

| Profil | Auflösung | FPS | Bitrate | Maxrate | Einsatz |
|---|---:|---:|---:|---:|---|
| Mobilfunk Sparsam | 854×480 | 25 | 800 kbit/s | 1000 kbit/s | schwache oder begrenzte Mobilfunkverbindung |
| Mobilfunk Standard | 1280×720 | 25 | 1800 kbit/s | 2200 kbit/s | LTE und wechselnde Netzqualität |
| WLAN Standard | 1280×720 | 30 | 2500 kbit/s | 3000 kbit/s | stabiles WLAN |
| WLAN Qualität | 1280×720 | 30 | 4000 kbit/s | 4500 kbit/s | sehr stabiles WLAN oder LAN |
| LAN Full HD | 1920×1080 | 30 | 6000 kbit/s | 7000 kbit/s | Raspberry Pi 5 und kabelgebundenes Netzwerk |

## Profil auswählen

Die verfügbare Uploadrate sollte dauerhaft deutlich über der Maximalbitrate des Profils liegen. Neben dem Videostream benötigen Audio, Protokoll-Overhead und kurzfristige Schwankungen zusätzliche Reserve.

Als praktische Untergrenze wird mindestens das 1,5-Fache der Maximalbitrate empfohlen. Mehr Reserve erhöht die Stabilität.

## Automatische Qualitätsreduzierung

Wenn die automatische Qualitätsreduzierung aktiviert ist, kann PiStreamer nach wiederholten FFmpeg-Fehlern auf das nächstkleinere Profil wechseln:

```text
LAN Full HD
→ WLAN Qualität
→ WLAN Standard
→ Mobilfunk Standard
→ Mobilfunk Sparsam
```

Die Funktion reduziert die Qualität nur. Eine automatische Hochstufung ist derzeit nicht vorgesehen.

## Hardwaregrenzen

Das aktuelle Software-Encoding mit `libx264` belastet die CPU. Typische Ausgangspunkte:

- Raspberry Pi 3: 480p mit 25 FPS
- Raspberry Pi 4: 720p mit 25 oder 30 FPS
- Raspberry Pi 5: 720p oder 1080p, abhängig von Kamera, Kühlung und Overlays

Die tatsächliche Stabilität muss auf der eingesetzten Hardware getestet werden.

## Netzwerkempfehlungen

- LAN ist für dauerhafte Streams vorzuziehen.
- WLAN sollte eine gute Signalstärke und geringe Paketverluste haben.
- Mobilfunkrouter sollten möglichst per Ethernet mit dem Raspberry Pi verbunden werden.
- Andere große Uploads im selben Netzwerk vermeiden.
- Vor Veranstaltungen einen längeren privaten Teststream durchführen.

## Symptome eines zu hohen Profils

- wiederholte FFmpeg-Neustarts
- sinkende FFmpeg-Geschwindigkeit
- ausgelassene Frames
- schwankender oder abbrechender Stream
- hohe CPU-Temperatur
- stark verzögertes Bild

In diesem Fall zuerst ein Profil herunterstufen und anschließend Kameraformat, Netzwerk und Temperatur prüfen.
