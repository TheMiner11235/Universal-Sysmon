"""
GPU Server - run this on your desktop to share GPU compute over Tailscale.

Usage:
    python gpu_server.py                  # start on default port 9753
    python gpu_server.py --port 8080      # custom port
    python gpu_server.py --install        # register as Windows auto-start task

Requires: flask, numpy, pyopencl (same deps as the main solver).
"""

import argparse
import importlib
import os
import subprocess
import sys
import time

REQUIRED_SERVER = {"flask": "flask"}


def _ensure_server_deps():
    missing = []
    for module, pkg in REQUIRED_SERVER.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing server dependencies: {', '.join(missing)}")
        for pkg in missing:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg],
                           capture_output=True, text=True)


_ensure_server_deps()

from flask import Flask, request, jsonify  # noqa: E402

import solver  # noqa: E402
from device import detect_device  # noqa: E402

app = Flask(__name__)

GPU_CTX = None
GPU_QUEUE = None
DEVICE_NAME = ""
DEVICE_TYPE = ""


def _init_gpu():
    global GPU_CTX, GPU_QUEUE, DEVICE_NAME, DEVICE_TYPE
    try:
        GPU_CTX, GPU_QUEUE, DEVICE_NAME, DEVICE_TYPE = detect_device()
        print(f"GPU ready: {DEVICE_NAME} ({DEVICE_TYPE})")
    except Exception as e:
        print(f"WARNING: OpenCL not available ({e}). Running in NumPy-only mode.")


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status": "ok",
        "device": DEVICE_NAME,
        "device_type": DEVICE_TYPE,
        "uptime": time.time() - _start_time,
    })


@app.route("/equations", methods=["GET"])
def equations():
    eqs = solver.load_equations()
    return jsonify([{"id": e["id"], "name": e["name"],
                     "description": e.get("description", ""),
                     "params": e.get("params", {})} for e in eqs])


@app.route("/compute", methods=["POST"])
def compute():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    eq_id = data.get("equation_id")
    params = data.get("params", {})

    eq = solver.get_equation(eq_id)
    if eq is None:
        return jsonify({"error": f"Unknown equation: {eq_id}"}), 404

    try:
        results, elapsed, n_combos, error = solver.run_equation(
            eq, params, GPU_CTX, GPU_QUEUE
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "results": results,
        "elapsed": round(elapsed, 4),
        "total_combinations": n_combos,
        "solutions_found": len(results),
        "device": DEVICE_NAME,
        "device_type": DEVICE_TYPE,
        "error": error,
    })


@app.route("/compute_bulk", methods=["POST"])
def compute_bulk():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    jobs = data.get("jobs", [])
    out = []
    for job in jobs:
        eq_id = job.get("equation_id")
        params = job.get("params", {})
        eq = solver.get_equation(eq_id)
        if eq is None:
            out.append({"error": f"Unknown equation: {eq_id}"})
            continue
        try:
            results, elapsed, n_combos, error = solver.run_equation(
                eq, params, GPU_CTX, GPU_QUEUE
            )
            out.append({
                "results": results,
                "elapsed": round(elapsed, 4),
                "total_combinations": n_combos,
                "solutions_found": len(results),
                "error": error,
            })
        except Exception as e:
            out.append({"error": str(e)})

    return jsonify({"results": out})


def _get_tailscale_ip():
    try:
        out = subprocess.run(["tailscale", "ip", "-4"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None


_start_time = time.time()


def main():
    parser = argparse.ArgumentParser(description="Math-GPU remote server")
    parser.add_argument("--port", type=int, default=9753)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--install", action="store_true",
                        help="Register as Windows auto-start scheduled task")
    args = parser.parse_args()

    if args.install:
        _install_autostart()
        return

    _init_gpu()
    ts_ip = _get_tailscale_ip()

    print(f"Math-GPU server listening on {args.host}:{args.port}")
    if ts_ip:
        print(f"  Tailscale IP: {ts_ip}")
        print(f"  Connect from laptop: http://{ts_ip}:{args.port}")
    print(f"  Local: http://127.0.0.1:{args.port}")
    print("  Press Ctrl+C to stop.")

    app.run(host=args.host, port=args.port, debug=False)


def _install_autostart():
    python_exe = sys.executable
    server_script = os.path.abspath(__file__)
    task_name = "MathGpuServer"

    ps_cmd = (
        f'$action = New-ScheduledTaskAction -Execute "{python_exe}" '
        f'-Argument "{server_script}" -WorkingDirectory "{os.path.dirname(server_script)}"\n'
        f'$trigger = New-ScheduledTaskTrigger -AtLogon\n'
        f'$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries '
        f'-DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 '
        f'-RestartInterval (New-TimeSpan -Minutes 1)\n'
        f'Register-ScheduledTask -TaskName "{task_name}" -Action $action '
        f'-Trigger $trigger -Settings $settings -Force\n'
        f'Write-Host "Task {task_name} registered. It will start on next login."'
    )

    result = subprocess.run(
        ["powershell", "-Command", ps_cmd],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.stderr.strip():
        print("Note:", result.stderr.strip())


if __name__ == "__main__":
    main()
