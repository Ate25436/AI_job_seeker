#!/usr/bin/env python3
"""
Restore the ChromaDB directory from a zip backup.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import DEFAULT_CHROMA_DB_PATH, resolve_path_value


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore the vector database directory from backup.")
    parser.add_argument("archive", help="Path to the zip archive")
    parser.add_argument("--db-path", default=os.getenv("CHROMA_DB_PATH", str(DEFAULT_CHROMA_DB_PATH)))
    parser.add_argument("--force", action="store_true", help="Overwrite existing database directory")
    args = parser.parse_args()

    archive = Path(args.archive)
    if not archive.exists():
        raise SystemExit(f"Archive not found: {archive}")

    db_path = Path(resolve_path_value(args.db_path, base_dir=Path(__file__).resolve().parents[1]))
    if db_path.exists():
        if not args.force:
            raise SystemExit(f"Database path already exists: {db_path} (use --force to overwrite)")
        shutil.rmtree(db_path)

    db_path.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(archive), str(db_path))
    print(f"Database restored to: {db_path}")


if __name__ == "__main__":
    main()
