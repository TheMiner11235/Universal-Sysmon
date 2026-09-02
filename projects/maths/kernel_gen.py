import re


class FormulaError(Exception):
    pass


ALLOWED_CHARS = re.compile(r"^[0-9a-zA-Z_+\-*/^()= .\[\]]+$")


def _is_number(tok):
    try:
        float(tok)
        return True
    except ValueError:
        return False


def parse_formula(formula):
    formula = formula.strip()
    if not ALLOWED_CHARS.match(formula):
        raise FormulaError("Formula contains disallowed characters.")
    if any(kw in formula for kw in ("import", "exec", "eval", "open(", "__", "lambda")):
        raise FormulaError("Formula contains forbidden constructs.")

    if "==" not in formula:
        raise FormulaError("Formula must contain '==' (e.g. x**2 + y**2 == 25).")

    lhs, rhs = [p.strip() for p in formula.split("==", 1)]

    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", lhs + rhs)
    variables = sorted(set(t for t in tokens if not _is_number(t)))

    filtered = []
    for v in variables:
        base = re.match(r"^[A-Za-z_]+", v).group(0)
        if base in ("x", "y"):
            filtered.append(base)
    variables = sorted(set(filtered))

    if not variables:
        raise FormulaError("No variables found in formula (need x, y, etc).")

    if len(variables) > 2:
        raise FormulaError("Only up to 2 variables (x, y) supported per equation.")

    for v in variables:
        if v not in ("x", "y"):
            raise FormulaError(f"Unknown variable '{v}'. Only x and y are supported.")

    return variables, lhs, rhs


def _to_cl(expr, variables):
    expr = expr.strip()
    expr = re.sub(r"\b([0-9]+)\b", r"\1", expr)

    tokens = re.findall(r"\*\*|[A-Za-z_][A-Za-z0-9_]*|\d+|[+\-*/()=]", expr)
    out = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "**":
            power = tokens[i + 1] if i + 1 < len(tokens) else "1"
            base = out.pop()
            out.append("(" + "*".join([base] * int(power)) + ")")
            i += 2
            continue
        if re.match(r"^[A-Za-z_]", tok):
            base = re.match(r"^[A-Za-z_]+", tok).group(0)
            if base in variables:
                out.append(f"{base}[i]")
            else:
                out.append(tok)
            i += 1
            continue
        out.append(tok)
        i += 1
    return " ".join(out)


def generate_kernel(formula):
    variables, lhs, rhs = parse_formula(formula)

    cl_lhs = _to_cl(lhs, variables)
    cl_rhs = _to_cl(rhs, variables)
    try:
        cl_rhs = str(int(eval(rhs)))
    except Exception:
        pass

    decls = []
    if "x" in variables:
        decls.append("__global const int* x")
    if "y" in variables:
        decls.append("__global const int* y")

    kernel_code = f"""
__kernel void check_eq({", ".join(decls)}, __global int* out) {{
    int i = get_global_id(0);
    if ({cl_lhs} == {cl_rhs}) {{
        out[i] = 1;
    }} else {{
        out[i] = 0;
    }}
}}
"""
    return kernel_code, variables
