"""Prepare the runtime on read-only serverless hosts (e.g. Vercel).

Vercel's function filesystem is read-only except /tmp. SQLite needs a writable
path, so we copy the bundled seed database there on cold start.
"""
import os
import shutil
from pathlib import Path

SERVERLESS_ROOT = Path("/var/task")


def is_serverless(base_dir: Path) -> bool:
    """True on Vercel/Lambda where the app is deployed under /var/task."""
    return SERVERLESS_ROOT.is_dir() and base_dir.resolve() == SERVERLESS_ROOT


def ensure_vercel_database(base_dir: Path) -> None:
    if not is_serverless(base_dir):
        return

    tmp_db = Path("/tmp/db.sqlite3")
    if tmp_db.exists():
        return

    seed = base_dir / "data" / "seed.sqlite3"
    if not seed.is_file():
        raise RuntimeError(
            "Missing data/seed.sqlite3. Run generate_data locally, then copy "
            "db.sqlite3 to data/seed.sqlite3 before deploying."
        )

    shutil.copy2(seed, tmp_db)
