# SysMonitor

Terminal-based system resource monitor with colored progress bars.

## Features

- CPU usage and clock speed
- GPU usage, VRAM (NVIDIA, AMD, Intel)
- RAM usage
- Disk usage and I/O speeds
- Network download/upload speeds
- Colored progress bars (`|` characters)
- Dark (OLED) and Light themes
- Cross-platform (Windows, Linux, macOS)
- Configurable refresh rate

## Installation

```bash
pip install sysmonitor
```

## Usage

```bash
sysmonitor                    # Dark theme (OLED)
sysmonitor --theme light       # Light theme
sysmonitor --refresh 0.5      # Slower refresh
sysmonitor --width 40         # Smaller bars
```

## Optional Dependencies

For full GPU support:

```bash
# NVIDIA GPUs
pip install sysmonitor[nvidia]

# AMD GPUs (Windows)
pip install sysmonitor[amd]

# AMD GPUs (Linux)
pip install sysmonitor[amd-linux]
```

## Development

```bash
cd system_monitor
pip install -e .
pip install -e ".[nvidia,amd,amd-linux]"
python -m sysmonitor
```

## Sample Output

```
+==============================================================================+
|                           SYSTEM RESOURCE MONITOR                            |
|                                    Linux                                     |
+------------------------------------------------------------------------------+

  CPU: AMD Ryzen 5 4500
  [|||||||||||--------------------------]  22.5% | 3.60 GHz

  GPU: NVIDIA GeForce RTX 3080
  [||||-------------------------------]   8.0% | VRAM: 2.5 GB/10.0 GB

  RAM:
  [|||||||||||||||||||-----------------]  39.2% | 12.4 GB/31.9 GB

  Disk: /
  [||||||||||||||||||||||||||||---------]  65.3% | 450.2 GB/953.0 GB

  Net: eth0
  DL: 1.2 MB/s | UL: 0.5 MB/s

+==============================================================================+
|                      Refresh: 0.1s | Ctrl+C to exit                         |
+==============================================================================+
```

## License

MIT