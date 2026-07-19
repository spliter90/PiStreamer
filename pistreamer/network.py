from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from flask import redirect, render_template, request, url_for

from .app import app, auth_required


@dataclass
class WifiNetwork:
    active: bool
    ssid: str
    signal: int
    security: str


def _nmcli(*args: str, timeout: int = 20) -> str:
    nmcli = shutil.which("nmcli")
    if not nmcli:
        raise RuntimeError("NetworkManager/nmcli ist nicht installiert.")
    result = subprocess.run([nmcli, *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "nmcli ist fehlgeschlagen").strip()
        if "Not authorized" in message or "nicht berechtigt" in message.lower():
            message += " Der PiStreamer-Dienst benötigt eine NetworkManager-Berechtigung."
        raise RuntimeError(message)
    return result.stdout.strip()


def _split_escaped(line: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def wifi_status() -> dict:
    status = {"device": "", "state": "nicht verbunden", "ssid": "", "ip": ""}
    try:
        rows = _nmcli("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status").splitlines()
        for row in rows:
            parts = _split_escaped(row)
            if len(parts) >= 4 and parts[1] == "wifi":
                status.update(device=parts[0], state=parts[2], ssid=parts[3] if parts[3] != "--" else "")
                if parts[2] == "connected":
                    ip_rows = _nmcli("-t", "-f", "IP4.ADDRESS", "device", "show", parts[0]).splitlines()
                    for ip_row in ip_rows:
                        if ":" in ip_row:
                            status["ip"] = ip_row.split(":", 1)[1]
                            break
                break
    except RuntimeError as exc:
        status["error"] = str(exc)
    return status


def scan_wifi() -> list[WifiNetwork]:
    output = _nmcli("-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes")
    networks: dict[str, WifiNetwork] = {}
    for line in output.splitlines():
        parts = _split_escaped(line)
        if len(parts) < 4 or not parts[1].strip():
            continue
        ssid = parts[1].strip()
        try:
            signal = max(0, min(100, int(parts[2] or 0)))
        except ValueError:
            signal = 0
        candidate = WifiNetwork(parts[0].strip() == "*", ssid, signal, parts[3].strip() or "Offen")
        previous = networks.get(ssid)
        if previous is None or candidate.signal > previous.signal or candidate.active:
            networks[ssid] = candidate
    return sorted(networks.values(), key=lambda item: (not item.active, -item.signal, item.ssid.lower()))


def saved_wifi() -> list[str]:
    output = _nmcli("-t", "-f", "NAME,TYPE", "connection", "show")
    names: list[str] = []
    for line in output.splitlines():
        parts = _split_escaped(line)
        if len(parts) >= 2 and parts[-1] in {"802-11-wireless", "wifi"}:
            names.append(":".join(parts[:-1]))
    return sorted(set(names), key=str.lower)


def _valid_ssid(value: str) -> str:
    value = value.strip()
    if not value or len(value.encode("utf-8")) > 32 or "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("Ungültige SSID.")
    return value


@app.route("/settings/network", methods=["GET", "POST"])
@auth_required
def network_settings():
    message = request.args.get("message")
    error = request.args.get("error")

    if request.method == "POST":
        action = request.form.get("action", "")
        try:
            if action == "connect":
                ssid = _valid_ssid(request.form.get("ssid", ""))
                password = request.form.get("password", "")
                command = ["device", "wifi", "connect", ssid]
                if password:
                    if len(password) < 8 or len(password) > 63:
                        raise ValueError("Das WLAN-Passwort muss 8 bis 63 Zeichen enthalten.")
                    command += ["password", password]
                _nmcli(*command, timeout=45)
                message = f"Verbindung mit {ssid} wurde gestartet. Die IP-Adresse kann sich ändern."
            elif action == "activate":
                name = _valid_ssid(request.form.get("name", ""))
                _nmcli("connection", "up", "id", name, timeout=45)
                message = f"Gespeichertes Netzwerk {name} wurde aktiviert."
            elif action == "disconnect":
                device = request.form.get("device", "").strip()
                if not device or not device.replace("-", "").replace("_", "").isalnum():
                    raise ValueError("Ungültiges WLAN-Gerät.")
                _nmcli("device", "disconnect", device)
                message = "WLAN wurde getrennt. Das Webinterface kann dadurch nicht mehr erreichbar sein."
            elif action == "forget":
                name = _valid_ssid(request.form.get("name", ""))
                _nmcli("connection", "delete", "id", name)
                message = f"Gespeichertes Netzwerk {name} wurde entfernt."
            elif action == "wifi_on":
                _nmcli("radio", "wifi", "on")
                message = "WLAN wurde eingeschaltet."
            elif action == "wifi_off":
                _nmcli("radio", "wifi", "off")
                message = "WLAN wurde ausgeschaltet."
            else:
                raise ValueError("Unbekannte Netzwerkaktion.")
            return redirect(url_for("network_settings", message=message))
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            error = str(exc)

    status = wifi_status()
    networks: list[WifiNetwork] = []
    saved: list[str] = []
    try:
        networks = scan_wifi()
        saved = saved_wifi()
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        error = error or str(exc)

    return render_template(
        "network.html",
        status=status,
        networks=networks,
        saved=saved,
        message=message,
        error=error,
    )
