"""Production entry: migrations then bot polling."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    print("Running database migrations...")
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])
    print("Starting bot...")
    subprocess.check_call([sys.executable, "-m", "app.main"])


if __name__ == "__main__":
    main()
