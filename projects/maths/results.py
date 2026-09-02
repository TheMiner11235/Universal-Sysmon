import json
import os

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def save_results(data):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    safe_name = _safe_id(data.get("id", "result"))
    counter = 1
    path = os.path.join(RESULTS_DIR, f"{safe_name}.json")
    while os.path.exists(path):
        path = os.path.join(RESULTS_DIR, f"{safe_name}_{counter}.json")
        counter += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def list_results():
    if not os.path.isdir(RESULTS_DIR):
        return []
    return sorted(
        os.path.join(RESULTS_DIR, f) for f in os.listdir(RESULTS_DIR) if f.endswith(".json")
    )


def _safe_id(eq_id):
    return "".join(c if (c.isalnum() or c in "_-") else "_" for c in eq_id)
