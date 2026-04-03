# Universal-Sysmon

Terminal-based system resource monitor with colored progress bars.

## Downloads

| Platform | File | Install |
|----------|------|---------|
| Windows | [sysmonitor.exe](https://github.com/TheMiner11235/Universal-Sysmon/releases) | Run directly |
| macOS | sysmonitor.dmg | Drag to Applications |
| Linux | sysmonitor.AppImage | `chmod +x && ./sysmonitor` |

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

## Quick Start

### Pre-built Executables

Download the executable for your OS from [Releases](https://github.com/TheMiner11235/Universal-Sysmon/releases) and run it.

### From Source

```bash
# Clone
git clone https://github.com/TheMiner11235/Universal-Sysmon.git
cd Universal-Sysmon

# Install dependencies
pip install -r requirements.txt

# Run
python -m sysmonitor
```

## Usage

```bash
sysmonitor                    # Dark theme (OLED)
sysmonitor --theme light       # Light theme
sysmonitor --refresh 0.5      # Slower refresh
sysmonitor --width 40         # Smaller bars
```

## Options

- `-r, --refresh` - Refresh rate in seconds (default: 0.1)
- `-w, --width` - Progress bar width (default: 50)
- `--theme` - Color theme: dark (default) or light

## Building from Source

```bash
# Install build dependencies
pip install pyinstaller

# Build for current platform
pyinstaller --onefile --console sysmonitor/__init__.py --name sysmonitor

# Output in dist/ folder
```

## Python Package Installation

```bash
pip install sysmonitor                    # Basic
pip install sysmonitor[nvidia]            # NVIDIA GPU support
pip install sysmonitor[amd]               # AMD GPU support (Windows)
pip install sysmonitor[amd-linux]         # AMD GPU support (Linux)
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

MIT - Feel free to use, modify, and distribute!