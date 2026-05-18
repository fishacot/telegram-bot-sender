"""Production entry: migrations then bot polling."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    print("=== telegram-bot-sender: production start ===", flush=True)
    print("Running database migrations...", flush=True)
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])
    print("Migrations OK. Starting bot polling...", flush=True)
    subprocess.check_call([sys.executable, "-m", "app.main"])


if __name__ == "__main__":
    main()
