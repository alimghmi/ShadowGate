from importlib.resources import files
from pathlib import Path


def _read_file(path: str | Path):
    file = files("shadowgate") / str(path)
    if not file.is_file():
        raise FileNotFoundError(f"{path} not found.")

    return file.read_text(encoding="utf-8")
