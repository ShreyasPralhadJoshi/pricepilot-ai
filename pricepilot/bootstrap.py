"""Prepare the runtime on read-only serverless hosts (e.g. Vercel).

Vercel's function filesystem is read-only except /tmp. SQLite needs a writable
path, so we copy the bundled seed database there on cold start.
"""
import os
import shutil
from pathlib import Path


def ensure_vercel_database(base_dir: Path) -> None:
    if not os.environ.get("VERCEL"):
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
