# AGENTS.md

## Project
GPU/CPU brute-force math equation solver with an interactive neon-on-OLED-black CLI.

## Run
```bash
python main.py
```
On first run it auto-installs deps (numpy, pyopencl, rich, inquirerpy), git-syncs from remote, detects hardware, and opens the menu.

## Layout
- `main.py` - entry point: auto-install deps, git sync, device detection, launch CLI
- `cli.py` - interactive menu (Rich tables + InquirerPy prompts), neon OLED theme
- `device.py` - picks backend: discrete GPU -> iGPU -> OpenCL CPU -> NumPy CPU fallback
- `solver.py` - runs equation kernels (OpenCL or NumPy fallback), dispatch logic
- `kernel_gen.py` - parses pasted formulas (e.g. `x**2 + y**2 == 25`) into OpenCL kernels
- `results.py` - writes JSON reports to `results/`
- `git_sync.py` - pulls on startup, commits/pushes only under the `maths/` tree
- `equations/` - JSON equation definitions (built-ins at top, added ones in `equations/custom/`)

## Equation file format
Each equation is a JSON file:
```json
{
  "id": "linear_diophantine",
  "name": "Linear Diophantine",
  "formula": "a*x + b*y == target",
  "solver_type": "gpu",
  "builtin": true,
  "params": {"target": {"default": 100, "min": 1, "max": 1000000, "label": "Target value"}},
  "param_values": {"target": 100}
}
```

## Hardware/backends
- `detect_device()` returns `(ctx, queue, device_name, device_type)` for OpenCL.
- If OpenCL unavailable, `device.numpy_device()` returns `(None, None, "NumPy CPU (...)")`.
- When `ctx`/`queue` are `None`, `solver.run_equation` uses the NumPy fallback (`_numpy_solve`).
- `friendly_name()` maps raw OpenCL device ID strings to readable names.

## Custom formulas
"Add a new equation" parses a formula into a kernel. Supported: variables `x`/`y`, operators `+ - * / **`, parens, `==`.
Security: formulas containing `import`, `exec`, `eval`, `open(`, `__`, `lambda` are rejected.

## Git
- Repo root is the user home directory; the project lives at `projects/maths`.
- Git operations are scoped to the `maths/` tree only (`git_sync.py`).
- Current approach: adding equations offers to commit + push just that file.

## Testing
No formal test suite; verification is done by running all equations end-to-end:
- GPU path and NumPy fallback (`ctx=None`) must both produce identical results.
- All result dicts must be JSON-serializable (cast numpy ints to Python ints).