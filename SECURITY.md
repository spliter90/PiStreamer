# Sicherheitsrichtlinie

## Unterstützte Versionen

PiStreamer befindet sich in aktiver Entwicklung. Sicherheitskorrekturen werden grundsätzlich für den aktuellen Stand des Standard-Branches bereitgestellt.

## Sicherheitsproblem melden

Bitte veröffentliche Sicherheitslücken, Zugangsdaten oder funktionierende Exploits nicht als öffentliches Issue. Nutze nach Möglichkeit GitHubs Funktion **Report a vulnerability** im Bereich Security des Repositorys.

Die Meldung sollte eine Beschreibung, betroffene Versionen, Reproduktionsschritte und eine Einschätzung der Auswirkungen enthalten. Entferne Stream-Keys, Passwörter und andere reale Zugangsdaten aus allen Beispielen.

## Einsatzhinweise

- Das Webinterface ist für vertrauenswürdige lokale Netzwerke vorgesehen.
- Port 8080 sollte nicht direkt aus dem Internet erreichbar sein.
- Das Standardpasswort muss unmittelbar nach der Installation geändert werden.
- Für Fernzugriff sollte ein VPN wie WireGuard oder Tailscale verwendet werden.
- Konfigurationsdateien und Logs dürfen nicht veröffentlicht werden, solange sie Zugangsdaten enthalten könnten.
