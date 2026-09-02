import pyopencl as cl

# Map common AMD/Intel OpenCL device ID strings to friendly names.
AMD_NAMES = {
    "gfx1102": "AMD Radeon RX 7600 / 7600 XT",
    "gfx1100": "AMD Radeon RX 7900 XTX / XT",
    "gfx1030": "AMD Radeon RX 6800 / 6600 series",
    "gfx902": "AMD Ryzen iGPU (Radeon Vega)",
    "gfx906": "AMD Ryzen iGPU (Radeon Vega 8/11)",
    "gfx1010": "AMD RX 5700 series",
    "gfx1031": "AMD RX 6700 XT",
}


def friendly_name(raw):
    raw = raw.strip()
    lk = raw.lower()
    return AMD_NAMES.get(lk, raw)


# Substrings that identify an integrated GPU (matches _device_key's heuristic).
_INTEGRATED = ("gfx902", "gfx906", "gfx1001", "gfx1003", "iray", "vega",
               "renoir", "cézanne", "raphael", "phoenix", "strix", "gfx10", "gfx11")


def _device_key(device):
    if device.type & cl.device_type.GPU:
        name = device.name.strip().lower()
        integrated = any(k in name for k in _INTEGRATED)
        return (0 if not integrated else 1, 0, 0)
    if device.type & cl.device_type.CPU:
        return (2, 0, 0)
    return (3, 0, 0)


def detect_device():
    platforms = cl.get_platforms()
    if not platforms:
        raise RuntimeError("No OpenCL platforms found. Is OpenCL installed?")

    devices = []
    for platform in platforms:
        try:
            for device in platform.get_devices():
                devices.append(device)
        except Exception:
            continue

    if not devices:
        raise RuntimeError("No OpenCL devices found.")

    devices.sort(key=_device_key)
    device = devices[0]
    device_type = "gpu" if device.type & cl.device_type.GPU else "cpu"

    ctx = cl.Context([device])
    queue = cl.CommandQueue(ctx)
    return ctx, queue, friendly_name(device.name), device_type


def numpy_device():
    """Fallback: no OpenCL hardware, run everything via NumPy on the CPU."""
    import multiprocessing

    return (
        None,
        None,
        f"NumPy CPU ({multiprocessing.cpu_count()} cores)",
        "numpy",
    )


def get_device_info(ctx):
    device = ctx.devices[0]
    try:
        mem = device.get_info(cl.device_info.GLOBAL_MEM_SIZE) / (1024 * 1024)
    except Exception:
        mem = 0
    return {
        "name": friendly_name(device.name),
        "type": "GPU" if device.type & cl.device_type.GPU else "CPU",
        "compute_units": device.max_compute_units,
        "global_mem_mb": round(mem),
    }
