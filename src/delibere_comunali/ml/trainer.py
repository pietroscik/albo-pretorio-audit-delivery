"""Model trainer – delegates to scripts/train_model.py."""

import runpy
import sys
from pathlib import Path


def _get_script_path() -> Path:
    current = Path(__file__).resolve()
    for _ in range(6):
        candidate = current / "scripts" / "train_model.py"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError(
        "Script scripts/train_model.py non trovato a partire da "
        f"{Path(__file__).resolve()}"
    )


def main():
    script_path = _get_script_path()
    sys.argv[0] = str(script_path)
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()