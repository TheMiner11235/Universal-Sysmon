# Laptop Setup Guide

Run the math solver on your laptop, offloading GPU work to your desktop at home over Tailscale.

## Prerequisites

Both machines must be on the same Tailscale network:
- Desktop Tailnet IP: `100.76.11.85`
- Laptop Tailnet IP: `100.121.175.35`

## On the desktop (one-time setup)

1. Leave your desktop on and connected to Tailscale.
2. Register the GPU server to auto-start on login:
   ```powershell
   cd C:\Users\coope\projects\maths
   python gpu_server.py --install
   ```
   Or run the setup script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File setup_autostart.ps1
   ```
3. Start it now:
   ```powershell
   python gpu_server.py
   ```
   You should see:
   ```
   GPU ready: AMD Radeon RX 7600 / 7600 XT (gpu)
   Math-GPU server listening on 0.0.0.0:9753
     Tailscale IP: 100.76.11.85
     Connect from laptop: http://100.76.11.85:9753
   ```

## On the laptop

1. Clone or pull the maths repo:
   ```bash
   git pull origin main
   ```

2. Run the solver:
   ```bash
   python main.py
   ```

3. On first run it will:
   - Auto-install dependencies (numpy, rich, inquirerpy)
   - Detect your local hardware (laptop iGPU or NumPy CPU)
   - Try to reach the desktop GPU server over Tailscale
   - Show status in the startup banner

4. From the menu, select **"Run on remote GPU"** to send work to the desktop.
   The solver sends the equation + parameters over Tailscale, the desktop computes
   on its RX 7600 XT, and results come back as JSON.

## How it works

```
Laptop (CLI)              Tailscale              Desktop (GPU Server)
  |                           |                         |
  |-- POST /compute --------->|----> gpu_server.py ---->|
  |   {equation_id, params}   |        solver.py        |
  |                           |        GPU kernel       |
  |<--- {results, elapsed} ---|<---- results JSON ------|
```

- The laptop client uses only stdlib (urllib) — no extra deps needed.
- The server uses Flask (auto-installed on first run on desktop).
- Results are saved locally on the laptop in `results/` as usual.

## Configuration

Edit `config.json` in the maths folder:
```json
{
  "remote_host": "100.76.11.85",
  "remote_port": 9753,
  "prefer_remote": true
}
```

- `remote_host` / `remote_port` — desktop's Tailscale IP and server port.
- `prefer_remote` — if true, the CLI tries remote GPU first before falling back to local.

## If the desktop is offline

The CLI will automatically fall back to:
1. Local GPU (if laptop has one via OpenCL)
2. NumPy CPU (multi-core, slower but works anywhere)

You'll see a warning in the banner if the desktop isn't reachable.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Connection refused" | Desktop is off or gpu_server.py isn't running. |
| "Timed out" | Tailscale may be disconnected. Check `tailscale status`. |
| Slow results | Large grid sizes (100k+) take time even on GPU. Try 5000 first. |
| Equation not found | Run `git pull` on laptop to sync new equations from desktop. |

## Tailscale IPs

| Machine | Tailnet IP |
|---------|------------|
| Desktop | 100.76.11.85 |
| Laptop  | 100.121.175.35 |
