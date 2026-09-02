import os
import subprocess


def _run(args, workdir=None):
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=workdir,
            check=False,
        )
    except FileNotFoundError:
        return None


def git_available():
    return _run(["--version"]) is not None


def git_root():
    r = _run(["rev-parse", "--show-toplevel"])
    return r.stdout.strip() if r and r.returncode == 0 else None


def sync_from_remote():
    root = git_root()
    if not root:
        return {"status": "error", "message": "Not a git repo."}
    r = _run(["fetch", "origin"], workdir=root)
    if r is None or r.returncode != 0:
        return {"status": "error", "message": "Could not fetch from origin (are you online?)."}
    status = _run(["status", "-sb"], workdir=root)
    line = status.stdout.strip().splitlines()[0] if status else ""
    behind = "behind" in line
    ahead = "ahead" in line

    if behind:
        pr = _run(["pull", "--rebase", "origin"], workdir=root)
        if pr.returncode == 0:
            return {"status": "pulled", "message": "Pulled latest changes from remote."}
        return {"status": "error", "message": "Pull failed. Pull manually."}
    if ahead:
        pp = _run(["push", "origin", "HEAD"], workdir=root)
        if pp is not None and pp.returncode == 0:
            return {"status": "pushed", "message": "Pushed local changes to remote."}
        return {"status": "ahead", "message": "Local has unpushed changes (push failed)."}
    return {"status": "clean", "message": "Up to date."}


def push_file(filepath, message):
    root = git_root()
    if not root:
        return False, "Not a git repo."
    rel = os.path.relpath(filepath, root).replace("\\", "/")
    if _run(["add", rel], workdir=root).returncode != 0:
        return False, "git add failed."
    if _run(["commit", "-m", message], workdir=root).returncode != 0:
        return False, "git commit failed (nothing to commit?)."
    p = _run(["push", "origin", "HEAD"], workdir=root)
    if p.returncode != 0:
        return False, f"git push failed: {p.stderr.strip()}"
    return True, "Pushed successfully."
