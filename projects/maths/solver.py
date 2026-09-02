import json
import math
import os
import time

import numpy as np
import pyopencl as cl

from device import detect_device
from kernel_gen import FormulaError, generate_kernel, parse_formula

EQUATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "equations")


def load_equations():
    equations = []
    for root, _dirs, files in os.walk(EQUATIONS_DIR):
        for fname in sorted(files):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    eq = json.load(f)
                eq["_file"] = path
                equations.append(eq)
            except Exception:
                continue
    return equations


def get_equation(eq_id):
    for eq in load_equations():
        if eq["id"] == eq_id:
            return eq
    return None


def eq_kind(eq):
    """Classify an equation by its JSON formula. Single source of truth for
    the formula-string mapping used by the GPU dispatch, NumPy fallback, and
    CLI display text."""
    f = eq.get("formula", "")
    if eq.get("solver_type") == "python_loop":
        return "factorial"
    if eq.get("builtin"):
        if f == "custom_fib":
            return "fib"
        if f.startswith("a*x + b*y"):
            return "linear"
        if f == "x*x + y*y == target":
            return "pythag"
        if f.startswith("a*x*x + b*x + c"):
            return "quadratic"
    return "custom"


def fib_coeffs(steps):
    """Fib-style coefficients: cx*x + cy*y is the value at `steps` from seeds x,y."""
    coeffs = [0, 1]
    while len(coeffs) <= steps:
        coeffs.append(coeffs[-1] + coeffs[-2])
    cx = coeffs[-2] if len(coeffs) > 2 else 0
    return cx, coeffs[-1]


def _build_seed_arrays(grid_size, signed=False):
    if signed:
        stop = grid_size // 2
        rng = np.arange(-stop, stop, dtype=np.int32)
        n = rng.size
    else:
        rng = np.arange(0, grid_size, dtype=np.int32)
        n = grid_size
    x_seeds = np.repeat(rng, n)
    y_seeds = np.tile(rng, n)
    return x_seeds, y_seeds


def _run_gpu_kernel(ctx, queue, kernel_code, variables, x_seeds, y_seeds):
    n = x_seeds.size
    output_results = np.zeros(n, dtype=np.int32)
    mf = cl.mem_flags
    args = []
    if "x" in variables:
        x_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=x_seeds)
        args.append(x_buf)
    if "y" in variables:
        y_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=y_seeds)
        args.append(y_buf)
    out_buf = cl.Buffer(ctx, mf.WRITE_ONLY, output_results.nbytes)
    args.append(out_buf)

    prg = cl.Program(ctx, kernel_code).build()
    prg.check_eq(queue, (n,), None, *args)

    cl.enqueue_copy(queue, output_results, out_buf)
    match_indices = np.where(output_results == 1)[0]
    return match_indices, x_seeds, y_seeds


def _fibonacci_kernel(steps):
    steps = int(steps)
    cx, cy = fib_coeffs(steps)
    return f"""
__kernel void check_eq(__global const int* x, __global const int* y, __global int* out) {{
    int i = get_global_id(0);
    if (({cx} * x[i]) + ({cy} * y[i]) == TARGET_PLACEHOLDER) {{
        out[i] = 1;
    }} else {{
        out[i] = 0;
    }}
}}
"""


def _solve_fibonacci(eq, params, ctx, queue):
    target = int(params["target"])
    steps = int(params["steps"])
    grid_size = int(params["grid_size"])
    x_seeds, y_seeds = _build_seed_arrays(grid_size)

    code = _fibonacci_kernel(steps).replace("TARGET_PLACEHOLDER", str(target))
    match_idx, x, y = _run_gpu_kernel(ctx, queue, code, ["x", "y"], x_seeds, y_seeds)

    results = []
    for i in match_idx:
        xv = int(x[i])
        yv = int(y[i])
        seq = []
        a, b = xv, yv
        seq.append(a)
        for _ in range(steps - 1):
            a, b = b, a + b
            seq.append(b)
        results.append({"x": xv, "y": yv, "sequence": seq})
    return results


def _solve_linear(eq, params, ctx, queue):
    a = int(params["a"])
    b = int(params["b"])
    target = int(params["target"])
    grid_size = int(params["grid_size"])
    x_seeds, y_seeds = _build_seed_arrays(grid_size)
    code = f"""
__kernel void check_eq(__global const int* x, __global const int* y, __global int* out) {{
    int i = get_global_id(0);
    if (({a} * x[i]) + ({b} * y[i]) == {target}) {{
        out[i] = 1;
    }} else {{
        out[i] = 0;
    }}
}}
"""
    match_idx, x, y = _run_gpu_kernel(ctx, queue, code, ["x", "y"], x_seeds, y_seeds)
    results = []
    for i in match_idx:
        xv = int(x[i])
        yv = int(y[i])
        results.append({"x": xv, "y": yv, "lhs": a * xv + b * yv, "sequence": [xv, yv, xv + yv, xv + 2 * yv, a * xv + b * yv]})
    return results


def _solve_pythagorean(eq, params, ctx, queue):
    target = int(params["target"])
    grid_size = int(params["grid_size"])
    x_seeds, y_seeds = _build_seed_arrays(grid_size)
    code = f"""
__kernel void check_eq(__global const int* x, __global const int* y, __global int* out) {{
    int i = get_global_id(0);
    if ((x[i]*x[i]) + (y[i]*y[i]) == {target}) {{
        out[i] = 1;
    }} else {{
        out[i] = 0;
    }}
}}
"""
    match_idx, x, y = _run_gpu_kernel(ctx, queue, code, ["x", "y"], x_seeds, y_seeds)
    results = []
    for i in match_idx:
        xv = int(x[i])
        yv = int(y[i])
        c = int(math.isqrt(xv * xv + yv * yv))
        results.append({"x": xv, "y": yv, "c": c, "formula": f"{xv}^2 + {yv}^2 = {c}^2"})
    return results


def _solve_quadratic(eq, params, ctx, queue):
    a = int(params["a"])
    b = int(params["b"])
    c = int(params["c"])
    grid_size = int(params["grid_size"])
    x_seeds = np.arange(-grid_size, grid_size + 1, dtype=np.int32)
    code = f"""
__kernel void check_eq(__global const int* x, __global int* out) {{
    int i = get_global_id(0);
    if (({a} * x[i] * x[i]) + ({b} * x[i]) + {c} == 0) {{
        out[i] = 1;
    }} else {{
        out[i] = 0;
    }}
}}
"""
    match_idx, x_arr, _ = _run_gpu_kernel(ctx, queue, code, ["x"], x_seeds, None)
    results = []
    for i in match_idx:
        xv = int(x_arr[i])
        results.append({"x": xv, "value": int(a * xv * xv + b * xv + c)})
    return results


def _solve_factorial(eq, params):
    target = int(params["target"])
    max_n = int(params["max_n"])
    results = []
    fact = 1
    for n in range(0, max_n + 1):
        if n > 0:
            fact *= n
        if fact == target:
            results.append({"n": n, "factorial": fact})
        if fact > target:
            break
    return results


def _solve_custom(eq, params, ctx, queue):
    formula = eq["custom_formula"]
    grid_size = int(params["grid_size"])
    try:
        code, variables = generate_kernel(formula)
    except FormulaError as e:
        return [], str(e)
    x_seeds, y_seeds = _build_seed_arrays(grid_size)
    match_idx, x, y = _run_gpu_kernel(ctx, queue, code, variables, x_seeds, y_seeds)
    results = []
    for i in match_idx:
        row = {}
        if "x" in variables:
            row["x"] = int(x[i])
        if "y" in variables:
            row["y"] = int(y[i])
        results.append(row)
    return results, None


def _chunked_matches(fn, grid_size, chunk=8192):
    matches = []
    for x0 in range(0, grid_size, chunk):
        xa = np.arange(x0, min(x0 + chunk, grid_size), dtype=np.int64)
        y_row = np.arange(grid_size, dtype=np.int64)[None, :]
        hit = fn(xa[:, None], y_row)
        yx = np.nonzero(hit)
        for hx, hy in zip(yx[0], yx[1]):
            xx = x0 + int(hx)
            matches.append((xx, int(hy)))
    return matches


def _try_eval(formula_expr, x, y):
    ns = {"x": x, "y": y, "pow": pow, "abs": abs}
    return eval(formula_expr, {"__builtins__": {}}, ns)


def _numpy_solve(eq, params):
    grid_size = int(params["grid_size"])
    kind = eq_kind(eq)

    if kind == "fib":
        target = int(params["target"])
        steps = int(params["steps"])
        cx, cy = fib_coeffs(steps)
        rows = _chunked_matches(lambda X, Y: (cx * X + cy * Y) == target, grid_size)
        out = []
        for xv, yv in rows:
            seq = []
            a, b = xv, yv
            seq.append(a)
            for _ in range(steps - 1):
                a, b = b, a + b
                seq.append(b)
            out.append({"x": xv, "y": yv, "sequence": seq})
        return out

    if kind == "linear":
        a, b = int(params["a"]), int(params["b"])
        target = int(params["target"])
        rows = _chunked_matches(lambda X, Y: (a * X + b * Y) == target, grid_size)
        return [
            {"x": x, "y": y, "lhs": a * x + b * y,
             "sequence": [x, y, x + y, x + 2 * y, a * x + b * y]}
            for x, y in rows
        ]

    if kind == "pythag":
        target = int(params["target"])
        rows = _chunked_matches(lambda X, Y: (X * X + Y * Y) == target, grid_size)
        out = []
        for x, y in rows:
            c = int(math.isqrt(x * x + y * y))
            out.append({"x": x, "y": y, "c": c, "formula": f"{x}^2 + {y}^2 = {c}^2"})
        return out

    if kind == "quadratic":
        a, b, c = int(params["a"]), int(params["b"]), int(params["c"])
        xr = np.arange(-grid_size, grid_size + 1, dtype=np.int64)
        mask = (a * xr * xr + b * xr + c) == 0
        return [{"x": int(x), "value": int(a * x * x + b * x + c)} for x in xr[mask]]

    formula = eq.get("custom_formula", "")
    try:
        variables, lhs, rhs = parse_formula(formula)
    except FormulaError as e:
        return False, str(e)

    def fn(X, Y):
        xa = X if "x" in variables else np.zeros_like(X)
        ya = Y if "y" in variables else np.zeros_like(Y)
        return _try_eval(f"({lhs}) == ({rhs})", xa, ya)

    rows = _chunked_matches(fn, grid_size)
    out = []
    for x, y in rows:
        row = {}
        if "x" in variables:
            row["x"] = x
        if "y" in variables:
            row["y"] = y
        out.append(row)
    return out


def run_equation(eq, params, ctx, queue):
    eq_type = eq["solver_type"]
    start = time.perf_counter()
    n_combos = 0
    error = None

    opencl_ready = ctx is not None and queue is not None

    if eq_type == "python_loop":
        results = _solve_factorial(eq, params)
    elif not opencl_ready:
        results = _numpy_solve(eq, params)
        if isinstance(results, tuple):
            results, error = results
        kind = eq_kind(eq)
        gs = int(params.get("grid_size", 0))
        n_combos = gs * gs if gs else 0
        if kind == "quadratic":
            n_combos = 2 * gs + 1
    else:
        kind = eq_kind(eq)
        gs = int(params["grid_size"])
        if kind == "fib":
            results = _solve_fibonacci(eq, params, ctx, queue)
            n_combos = gs * gs
        elif kind == "linear":
            results = _solve_linear(eq, params, ctx, queue)
            n_combos = gs * gs
        elif kind == "pythag":
            results = _solve_pythagorean(eq, params, ctx, queue)
            n_combos = gs * gs
        elif kind == "quadratic":
            results = _solve_quadratic(eq, params, ctx, queue)
            n_combos = 2 * gs + 1
        else:
            results, error = _solve_custom(eq, params, ctx, queue)
            n_combos = gs * gs

    elapsed = time.perf_counter() - start
    return results, elapsed, n_combos, error


def save_equation(eq_data, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, f"{eq_data['id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(eq_data, f, indent=2)
    return path
