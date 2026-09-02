"""
Remote GPU client - sends compute requests to a desktop GPU server over Tailscale.

Zero external dependencies: uses only stdlib urllib + json.
"""

import json
import os
import urllib.error
import urllib.request

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_HOST = "100.76.11.85"
DEFAULT_PORT = 9753
CONNECT_TIMEOUT = 3
COMPUTE_TIMEOUT = 120


def _load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"remote_host": DEFAULT_HOST, "remote_port": DEFAULT_PORT,
                "prefer_remote": False}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"remote_host": DEFAULT_HOST, "remote_port": DEFAULT_PORT,
                "prefer_remote": False}


def get_endpoint():
    cfg = _load_config()
    return cfg.get("remote_host", DEFAULT_HOST), cfg.get("remote_port", DEFAULT_PORT)


def _status_data():
    host, port = get_endpoint()
    url = f"http://{host}:{port}/status"
    req = urllib.request.Request(url, method="GET")
    resp = urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT)
    return json.loads(resp.read().decode())


def is_remote_available():
    try:
        data = _status_data()
        return True, data.get("device", "unknown"), data.get("device_type", "unknown")
    except Exception:
        return False, "", ""


def prefer_remote():
    return bool(_load_config().get("prefer_remote", False))


def remote_compute(eq_id, params):
    host, port = get_endpoint()
    url = f"http://{host}:{port}/compute"
    payload = json.dumps({"equation_id": eq_id, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=COMPUTE_TIMEOUT)
    return json.loads(resp.read().decode())
