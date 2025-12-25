from __future__ import annotations

from pathlib import Path
import sys


def ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent
    src_dir = root / "src"
    src_str = str(src_dir)
    if src_dir.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)


def main() -> None:
    ensure_src_on_path()
    from quizbank import run_gui

    run_gui()


if __name__ == "__main__":
    main()
