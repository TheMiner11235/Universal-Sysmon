# Math-GPU Solver

GPU/CPU brute-force equation solver with an interactive neon-on-OLED-black CLI.

## Run

```bash
python main.py
```

On first run it auto-installs missing dependencies (`numpy`, `pyopencl`, `rich`, `inquirerpy`), syncs with git, detects your hardware, and opens the menu.

## Hardware handling

- **Discrete GPU** (e.g. RX 7600 XT) -> runs OpenCL kernels on the GPU.
- **Laptop iGPU** (AMD integrated graphics) -> detected as a GPU device and used via OpenCL.
- **CPU-only / no OpenCL driver** -> falls back to a NumPy multi-core solver automatically.

On startup it prefers a discrete GPU over an integrated one when both exist.

## Menu options

- **Run an equation** - pick from the equations in `equations/`, set your parameters (steps limit, target number, search range, coefficients), runs the solver, shows a compact summary (device, problem, search space, solutions found, elapsed time) and saves a full JSON report.
- **Add a new equation** - paste a formula like `x**2 + y**2 == 25` (or `x**3 + y**3 == 100`). The tool generates the OpenCL kernel, saves it as a JSON file under `equations/custom/`, and optionally commits + pushes it to git.
- **View saved results** - browse and print past JSON result files.
- **Sync with git** - fetch remote, pull new equations if behind, push if ahead.

## Equation files

Each equation is a JSON file in `equations/` (bulit-ins at the top level, added ones in `equations/custom/`):

```json
{
  "id": "linear_diophantine",
  "name": "Linear Diophantine",
  "formula": "a*x + b*y == target",
  "solver_type": "gpu",
  "builtin": true,
  "params": {
    "target": {"default": 100, "min": 1, "max": 1000000, "label": "Target value"},
    "grid_size": {"default": 10000, "min": 100, "max": 100000, "label": "Search range (0 to N)"}
  },
  "param_values": {"target": 100, "grid_size": 10000}
}
```

### Built-in equations

| Equation | Description |
|----------|-------------|
| Linear Diophantine | `a*x + b*y == target` |
| Fibonacci Sequence | seeds x, y produce target in N steps |
| Pythagorean Triples | `x^2 + y^2 == target` |
| Quadratic Equation | `a*x^2 + b*x + c == 0` |
| Factorial Finder | `n! == target` (CPU loop) |

### Custom formulas

The "Add a new equation" flow parses a formula into an OpenCL kernel. Supported syntax:
- Variables: `x`, `y`
- Operators: `+ - * / **` and parentheses
- Comparison: `==`
- Numbers and powers: `x**2`, `x**3`, `y**2`, etc.

Examples: `x*x + y*y == 100`, `x**3 + y**3 == 1729`, `2*x + 3*y == 100`.

## Results

Each run writes a JSON report to `results/` (created automatically):

```json
{
  "name": "Linear Diophantine",
  "formula": "2x + 3y == 100",
  "device": "AMD Radeon RX 7600 / 7600 XT",
  "device_type": "gpu",
  "parameters": {"a": 2, "b": 3, "target": 100, "grid_size": 10000},
  "total_combinations": 40000,
  "solutions_found": 17,
  "elapsed_seconds": 0.0883,
  "results": [
    {"x": 2, "y": 32, "lhs": 100, "sequence": [2, 32, 34, 66, 100]},
    ...
  ]
}
```

## Git sync

The project auto-commits/pushes only files under the `maths/` tree (the git repo may live at your home directory). On startup it pulls remote changes; after adding an equation it offers to commit and push.