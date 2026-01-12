#!/usr/bin/env python3
"""
Restore the ChromaDB directory from a zip backup.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore the vector database directory from backup.")
    parser.add_argument("archive", help="Path to the zip archive")
    parser.add_argument("--db-path", default=os.getenv("CHROMA_DB_PATH", "./chroma_db"))
    parser.add_argument("--force", action="store_true", help="Overwrite existing database directory")
    args = parser.parse_args()

    archive = Path(args.archive)
    if not archive.exists():
        raise SystemExit(f"Archive not found: {archive}")

    db_path = Path(args.db_path)
    if db_path.exists():
        if not args.force:
            raise SystemExit(f"Database path already exists: {db_path} (use --force to overwrite)")
        shutil.rmtree(db_path)

    db_path.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(archive), str(db_path))
    print(f"Database restored to: {db_path}")


if __name__ == "__main__":
    main()
