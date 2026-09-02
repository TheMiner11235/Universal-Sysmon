import json
import os
from datetime import datetime

from InquirerPy import inquirer
from InquirerPy.separator import Separator
from InquirerPy.utils import get_style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import git_sync
import solver
from device import get_device_info
from kernel_gen import FormulaError, generate_kernel, parse_formula
from results import list_results, save_results

NEON_GREEN = "#00FF41"
NEON_CYAN = "#00FFFF"
NEON_MAGENTA = "#FF00FF"
NEON_YELLOW = "#FFFF00"
NEON_RED = "#FF0040"
BG = "#000000"

console = Console(theme=None)


def _t(text, color=NEON_GREEN):
    return Text(text, style=f"{color} on {BG}")


def _style():
    return get_style(
        {
            "answer": NEON_GREEN,
            "questionmark": NEON_MAGENTA,
            "pointer": NEON_GREEN,
            "instruction": NEON_YELLOW,
            "separator": NEON_MAGENTA,
            "question": NEON_CYAN,
            "input": NEON_CYAN,
            "answermark": NEON_MAGENTA,
        }
    )


def banner():
    b = Panel(
        _t("MATH-GPU SOLVER\n", NEON_MAGENTA)
        + _t("GPU/CPU brute-force equation solver", NEON_CYAN)
        + "\n" + _t("detects your hardware and picks the fastest path", NEON_GREEN),
        border_style=NEON_MAGENTA,
        title=_t("MATH", NEON_YELLOW),
    )
    console.print(b)


def _build_param(schema, cur_value):
    d_min, d_max, d_label = schema.get("min", 0), schema.get("max", 100000), schema.get("label", "Value")
    val = inquirer.number(
        message=f"{d_label} (min={d_min}, max={d_max})",
        default=str(cur_value),
        min_allowed=d_min,
        max_allowed=d_max,
        invalid_message="Number out of range.",
        style=_style(),
    ).execute()
    return int(float(val))


def prompt_params(eq):
    params = {}
    for name, schema in eq["params"].items():
        cur = eq.get("param_values", {}).get(name, schema.get("default", 0))
        params[name] = _build_param(schema, cur)
    return params


def run_an_equation(ctx, queue, info):
    eqs = solver.load_equations()
    if not eqs:
        console.print(_t("No equations found in equations/ folder.", NEON_RED))
        return
    choices = [(f"{e['name']}: {e['description']}", e) for e in eqs]
    eq = inquirer.select(
        message="Select an equation to run",
        choices=choices,
        instruction="(arrows to move, enter to select)",
        pointer=">",
        style=_style(),
    ).execute()

    params = prompt_params(eq)
    console.print(_t(f"Solving {eq['name']} on {info['name']} ({info['type']})...", NEON_CYAN))

    results, elapsed, n_combos, error = solver.run_equation(eq, params, ctx, queue)

    if error:
        console.print(_t(f"Could not solve: {error}", NEON_RED))
        return

    found = len(results)
    grid = params.get("grid_size", "?")
    combo_disp = f"{n_combos:,}" if n_combos else "n/a"

    table = Table(border_style=NEON_MAGENTA, header_style=f"bold {NEON_YELLOW}")
    table.add_column("Property", style=NEON_CYAN)
    table.add_column("Value", style=NEON_GREEN)
    table.add_row("Device", f"{info['name']} ({info['type']})")
    table.add_row("Problem", eq["name"])
    verb = _formula_text(eq, params)
    table.add_row("Equation", verb)
    table.add_row("Search space", f"{combo_disp} combinations")
    table.add_row("Found", f"{found:,} solutions")
    table.add_row("Elapsed", f"{elapsed:.4f}s")
    console.print(table)

    payload = {
        "id": eq["id"],
        "name": eq["name"],
        "formula": _formula_text(eq, params),
        "device": info["name"],
        "device_type": info["type"].lower(),
        "parameters": params,
        "total_combinations": n_combos,
        "solutions_found": found,
        "elapsed_seconds": round(elapsed, 4),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }

    path = save_results(payload)
    console.print(Panel(_t(f"Saved {found} solutions to {os.path.relpath(path)}", NEON_GREEN), border_style=NEON_GREEN))

    print_count = inquirer.confirm(
        message="Preview solution values in terminal?", default=False,
        style=_style(),
    ).execute()
    if print_count:
        preview = results[:10]
        pt = Table(border_style=NEON_MAGENTA, header_style=f"bold {NEON_YELLOW}")
        if preview and isinstance(preview[0], dict):
            for k in preview[0].keys():
                pt.add_column(k.title(), style=NEON_GREEN)
            for r in preview:
                pt.add_row(*[str(v) for v in r.values()])
        console.print(pt)


def _formula_text(eq, params):
    f = eq.get("formula", "")
    if eq.get("builtin") and f == "custom_fib":
        return f"fib(x, y) reaches {params.get('target')} in {params.get('steps')} steps"
    if eq.get("builtin") and f.startswith("a*x + b*y"):
        return f"{params.get('a')}x + {params.get('b')}y == {params.get('target')}"
    if eq.get("builtin") and f == "x*x + y*y == target":
        return f"x^2 + y^2 == {params.get('target')}"
    if eq.get("builtin") and f.startswith("a*x*x + b*x + c"):
        return f"{params.get('a')}x^2 + {params.get('b')}x + {params.get('c')} == 0"
    if f == "n! == target":
        return f"n! == {params.get('target')}"
    return eq.get("custom_formula", f)


def add_equation():
    console.print(Panel(_t("Add a New Equation\nPaste a formula like:  x**2 + y**2 == 25", NEON_CYAN), border_style=NEON_CYAN))
    formula = inquirer.text(
        message="Formula (uses x and/or y, must contain ==)", default="x*x + y*y == 25",
        style=_style(),
    ).execute().strip()

    try:
        variables, lhs, rhs = parse_formula(formula)
        code, vars_ = generate_kernel(formula)
    except FormulaError as e:
        console.print(_t(f"Error: {e}", NEON_RED))
        return

    name = inquirer.text(message="Name for this equation", default=formula, style=_style()).execute().strip().lower()
    name = "".join(c if c.isalnum() or c in "_- " else "" for c in name).replace(" ", "_")
    if not name:
        name = "custom_equation"

    console.print(_t(f"Detected variables: {', '.join(variables)}", NEON_CYAN))
    console.print(Panel(_t("Generated OpenCL kernel:", NEON_YELLOW) + "\n" + code, border_style=NEON_CYAN))

    eq_data = {
        "id": name,
        "name": name.replace("_", " ").title(),
        "description": formula,
        "formula": formula,
        "custom_formula": formula,
        "solver_type": "gpu",
        "builtin": False,
        "params": {
            "grid_size": {"default": 10000, "min": 100, "max": 100000, "label": "Search range (0 to N)"}
        },
        "param_values": {"grid_size": 10000},
    }

    target_dir = os.path.join(solver.EQUATIONS_DIR, "custom")
    os.makedirs(target_dir, exist_ok=True)
    path = solver.save_equation(eq_data, target_dir)
    console.print(Panel(_t(f"Saved equation to {os.path.relpath(path)}", NEON_GREEN), border_style=NEON_GREEN))

    commit = inquirer.confirm(
        message="Commit and push this equation to git?", default=True,
        style=_style(),
    ).execute()
    if commit:
        ok, msg = git_sync.push_file(path, f"add equation: {name}")
        if ok:
            console.print(Panel(_t("Pushed to git successfullly.", NEON_GREEN), border_style=NEON_GREEN))
        else:
            console.print(Panel(_t(f"Could not push: {msg}", NEON_RED), border_style=NEON_RED))


def view_results():
    files = list_results()
    if not files:
        console.print(_t("No saved results yet.", NEON_YELLOW))
        return
    choice = inquirer.select(
        message="Select a saved result to view",
        choices=[(os.path.relpath(f), f) for f in files],
        style=_style(),
    ).execute()
    with open(choice, "r", encoding="utf-8") as f:
        data = json.load(f)
    console.print(Panel(json.dumps(data, indent=2), border_style=NEON_CYAN, title=data.get("name", "result")))


def run(ctx, queue, info, startup_msg=None):
    banner()
    if startup_msg:
        console.print(_t(startup_msg, NEON_YELLOW))
    while True:
        action = inquirer.select(
            message="Main menu",
            choices=[
                Separator("=== MAIN ==="),
                ("Run an equation", "run"),
                ("Add a new equation", "add"),
                ("View saved results", "results"),
                Separator("=== GIT ==="),
                ("Sync with git", "sync"),
                Separator(""),
                ("Quit", "quit"),
            ],
            style=_style(),
        ).execute()

        if action == "run":
            run_an_equation(ctx, queue, info)
        elif action == "add":
            add_equation()
        elif action == "results":
            view_results()
        elif action == "sync":
            res = git_sync.sync_from_remote()
            color = NEON_GREEN if res["status"] in ("clean", "pushed") else (NEON_YELLOW if res["status"] == "pulled" else NEON_RED)
            console.print(_t(res["message"], color))
        else:
            console.print(_t("Goodbye.", NEON_MAGENTA))
            break
