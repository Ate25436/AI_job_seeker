#!/usr/bin/env python3
"""
Initialize the vector database with markdown content from information_source directory
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent))

from app.services.vector_db_manager import VectorDBManager


async def main():
    """Initialize the vector database with markdown content."""
    print("Initializing vector database...")
    
    # Check if information_source directory exists
    info_source_dir = Path("../information_source")
    if not info_source_dir.exists():
        print(f"Error: {info_source_dir} directory not found!")
        print("Please make sure the information_source directory exists in the project root.")
        return
    
    try:
        # Initialize the VectorDBManager
        db_manager = VectorDBManager(db_path="./chroma_db")
        await db_manager.initialize()
        
        # Initialize from markdown files
        result = await db_manager.initialize_from_markdown(str(info_source_dir))
        
        print(f"✅ Database initialization completed!")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Chunks processed: {result['chunks_processed']}")
        
        # Get collection info
        info = await db_manager.get_collection_info()
        print(f"Collection: {info['collection_name']}")
        print(f"Document count: {info['document_count']}")
        
        await db_manager.close()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())