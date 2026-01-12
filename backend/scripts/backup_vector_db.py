#!/usr/bin/env python3
"""
Create a zip backup of the ChromaDB directory.
"""
from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup the vector database directory.")
    parser.add_argument("--db-path", default=os.getenv("CHROMA_DB_PATH", "./chroma_db"))
    parser.add_argument("--output-dir", default="backups")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise SystemExit(f"Database path not found: {db_path}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive_base = output_dir / f"chroma_db_backup_{timestamp}"
    archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=db_path)

    print(f"Backup created: {archive_path}")


if __name__ == "__main__":
    main()
