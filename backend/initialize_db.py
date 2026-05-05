#!/usr/bin/env python3
"""
Initialize the vector database with markdown content from information_source directory
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent))

from app.config import DEFAULT_CHROMA_DB_PATH, DEFAULT_INFO_SOURCE_PATH, resolve_path_value
from app.services.vector_db_manager import VectorDBManager


def load_env_files() -> None:
    """Load .env files without overriding explicitly exported variables."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / ".env",
        script_dir / ".env",
        script_dir.parent / ".env",
    ]
    for env_path in dict.fromkeys(candidates):
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)


async def main():
    """Initialize the vector database with markdown content."""
    load_env_files()

    parser = argparse.ArgumentParser(description="Initialize the vector database from markdown files.")
    parser.add_argument("--source", default=os.getenv("INFO_SOURCE_PATH", str(DEFAULT_INFO_SOURCE_PATH)))
    parser.add_argument("--db-path", default=os.getenv("CHROMA_DB_PATH", str(DEFAULT_CHROMA_DB_PATH)))
    parser.add_argument("--collection", default="markdown_rag")
    args = parser.parse_args()

    print("Initializing vector database...")
    
    # Check if information_source directory exists
    info_source_dir = Path(resolve_path_value(args.source, base_dir=Path(__file__).resolve().parent.parent))
    if not info_source_dir.exists():
        print(f"Error: {info_source_dir} directory not found!")
        print("Please make sure the information_source directory exists in the project root.")
        return
    
    try:
        # Initialize the VectorDBManager
        db_manager = VectorDBManager(
            db_path=resolve_path_value(args.db_path, base_dir=Path(__file__).resolve().parent),
            collection_name=args.collection,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        await db_manager.initialize()
        
        # Initialize from markdown files
        result = await db_manager.initialize_from_markdown(str(info_source_dir))
        
        print("Database initialization completed.")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Chunks processed: {result['chunks_processed']}")
        
        # Get collection info
        info = await db_manager.get_collection_info()
        print(f"Collection: {info['collection_name']}")
        print(f"Document count: {info['document_count']}")
        
        await db_manager.close()
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
