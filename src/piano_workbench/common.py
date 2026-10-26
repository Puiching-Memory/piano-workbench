import hashlib
import json
import shutil
import subprocess
from pathlib import Path


class WorkbenchError(ValueError):
    """Actionable input, dependency or validation error."""


def new_directory(path):
    path = Path(path)
    if path.exists():
        raise WorkbenchError(f"Output already exists: {path}. Choose a new output directory.")
    path.mkdir(parents=True)
    return path


def new_file(path):
    path = Path(path)
    if path.exists():
        raise WorkbenchError(f"Output already exists: {path}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def require_file(path):
    path = Path(path)
    if not path.is_file():
        raise WorkbenchError(f"Input file does not exist: {path}")
    return path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def executable(name):
    found = shutil.which(name)
    if not found:
        raise WorkbenchError(f"{name} was not found on PATH. Install FFmpeg including ffprobe.")
    return found


def run_process(args):
    try:
        return subprocess.run([str(x) for x in args], check=True, capture_output=True,
                              text=True, encoding='utf-8', errors='replace')
    except subprocess.CalledProcessError as exc:
        raise WorkbenchError(f"{Path(str(args[0])).name} failed:\n{exc.stderr[-2500:]}") from exc
