# Build scripts for Universal-Sysmon

## Windows

```bash
pip install pyinstaller
pyinstaller --onefile --console --name sysmonitor sysmonitor/__init__.py
# Output: dist/sysmonitor.exe
```

## macOS (on Mac)

```bash
pip install pyinstaller
pyinstaller --onefile --console --name sysmonitor sysmonitor/__init__.py
# Output: dist/sysmonitor (executable)
# To create DMG: use Disk Utility
```

## Linux (on Linux)

```bash
pip install pyinstaller
pyinstaller --onefile --console --name sysmonitor sysmonitor/__init__.py
# Output: dist/sysmonitor (executable)
# To create AppImage: use appimagetool
```

## Python Package

```bash
pip install build
python -m build
# Output: dist/sysmonitor-1.0.0-py3-none-any.whl
```

## Notes

- The executable must be built on the target platform
- PyInstaller creates a standalone binary
- No Python installation needed on target machine