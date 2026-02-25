from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> int:
    try:
        run(["poetry", "run", "flask", "db", "stamp", "heads"])
        run(["poetry", "run", "flask", "db", "current"])
        print("[ok] Alembic allineato agli heads.")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"[error] comando fallito (exit={exc.returncode}): {exc.cmd}", file=sys.stderr)
        return exc.returncode or 2


if __name__ == "__main__":
    raise SystemExit(main())
