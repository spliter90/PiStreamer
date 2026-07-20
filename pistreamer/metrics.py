from __future__ import annotations

from flask import jsonify

from .app import api_auth_required, app, manager
from .network_monitor import NetworkMonitor

monitor = NetworkMonitor(manager)


@app.get("/api/network/status")
@api_auth_required
def network_status():
    return jsonify(monitor.snapshot())
