import importlib
import subprocess
import sys


REQUIRED = {"numpy": "numpy", "pyopencl": "pyopencl", "rich": "rich", "InquirerPy": "inquirerpy"}


def _ensure_deps():
    missing = []
    for module in REQUIRED:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(REQUIRED[module].split("==")[0] if "==" in REQUIRED[module] else REQUIRED[module])

    if not missing:
        return

    print(f"Installing missing dependencies: {', '.join(missing)}")
    for pkg in missing:
        res = subprocess.run([sys.executable, "-m", "pip", "install", pkg], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Failed to install {pkg}: {res.stderr[-300:]}")
        else:
            print(f"Installed {pkg}.")


def main():
    _ensure_deps()

    import cli
    import device
    import git_sync
    import remote_client

    startup_msg = None
    if git_sync.git_available():
        res = git_sync.sync_from_remote()
        if res["status"] == "pulled":
            startup_msg = res["message"]

    try:
        ctx, queue, dev_name, dev_type = device.detect_device()
    except Exception as e:
        ctx, queue, dev_name, dev_type = device.numpy_device()
        startup_msg = (startup_msg + " | " if startup_msg else "") + f"OpenCL unavailable ({e}); using NumPy CPU solver."

    info = device.get_device_info(ctx) if ctx is not None else {"name": dev_name, "type": "NUMPY", "compute_units": 0, "global_mem_mb": 0}
    info["name"] = dev_name
    info["type"] = "GPU" if dev_type == "gpu" else ("CPU" if dev_type == "cpu" else "NUMPY")

    try:
        remote_ok, remote_name, remote_type = remote_client.is_remote_available()
    except Exception:
        remote_ok, remote_name, remote_type = False, "", ""

    if remote_ok:
        info["remote_available"] = True
        info["remote_name"] = remote_name
        info["remote_type"] = remote_type
        remote_str = f"Remote GPU online: {remote_name}"
        startup_msg = (startup_msg + " | " if startup_msg else "") + remote_str

    cli.run(ctx, queue, info, startup_msg)


if __name__ == "__main__":
    main()
