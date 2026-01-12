import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import glob
import re
import chromadb
from openai import OpenAI
import os
from threading import Lock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDBManager:
    """
    Manager for vector database operations including initialization, 
    re-indexing, and concurrent access safety.
    """
    
    def __init__(
        self,
        db_path: str = "./chroma_db",
        collection_name: str = "markdown_rag",
        openai_api_key: str | None = None,
    ):
        """
        Initialize the VectorDBManager.
        
        Args:
            db_path: Path to the ChromaDB database
            collection_name: Name of the ChromaDB collection
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.chroma_client = None
        self.collection = None
        self.openai_client = None
        self._lock = Lock()  # For concurrent access safety
        self.openai_api_key = openai_api_key
        
    async def initialize(self) -> None:
        """Initialize the vector database manager."""
        try:
            # Initialize OpenAI client for embeddings
            api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            self.openai_client = OpenAI(api_key=api_key)
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path=self.db_path)
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name
            )
            
            logger.info(f"VectorDBManager initialized with collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize VectorDBManager: {e}")
            raise

    def chunk_markdown(self, markdown_text: str) -> List[Tuple[str, str]]:
        """
        Chunk Markdown text by headings.
        
        Args:
            markdown_text: The Markdown text to chunk
            
        Returns:
            List of (heading, content) tuples
        """
        # Heading pattern: # or ## or ### etc.
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        markdown_text_list = markdown_text.split('\n')
        chunks = []
        current_heading = None
        current_content = [markdown_text_list.pop(0)] if markdown_text_list else []
        tree_bank = [current_content[0] if current_content else ""] + [""] * 5
        current_level = 1

        for line in markdown_text_list:
            heading_match = re.match(heading_pattern, line)
            
            if heading_match:
                # Found a heading
                new_level = len(heading_match.group(1))
                if current_level < new_level:
                    # New heading level is deeper, save current chunk
                    current_content_str = '\n'.join(current_content).strip()
                    tree_bank[current_level - 1] = current_content_str
                    current_content = [line]
                    current_level = new_level
                    current_heading = heading_match.group(2).strip()
                else:
                    chunks.append(
                        (current_heading, '\n'.join(filter(None, tree_bank[:current_level] + ['\n'.join(current_content).strip()])).strip())
                    )
                    current_content = [line]
                    current_level = new_level
                    current_heading = heading_match.group(2).strip()
            else:
                # Not a heading, add to current content
                current_content.append(line)
        
        if current_content:
            chunks.append(
                (current_heading, '\n'.join(filter(None, tree_bank[:current_level] + ['\n'.join(current_content).strip()])).strip())
            )
        
        return chunks

    def chunk_markdown_from_file(self, file_path: str) -> List[Tuple[str, str]]:
        """
        Read and chunk Markdown from a file.
        
        Args:
            file_path: Path to the Markdown file
            
        Returns:
            List of (heading, content) tuples
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            return self.chunk_markdown(markdown_text)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise

    def get_markdown_chunks(self, source_dir: str = "information_source") -> List[Dict[str, str]]:
        """
        Get all markdown chunks from the source directory.
        
        Args:
            source_dir: Directory containing markdown files
            
        Returns:
            List of chunk dictionaries with file_name, heading, content, and heading_path
        """
        file_paths = glob.glob(f'{source_dir}/**/*.md', recursive=True)
        logger.info(f"Found {len(file_paths)} markdown files in {source_dir}")
        
        chunks = []
        for file_path in file_paths:
            try:
                file_name = Path(file_path).stem
                file_chunks = self.chunk_markdown_from_file(file_path)
                
                for heading, content in file_chunks:
                    # Create a hierarchical heading path for better organization
                    heading_path = heading if heading else "Introduction"
                    
                    chunks.append({
                        "file_name": file_name,
                        "heading": heading if heading else "Introduction",
                        "content": content,
                        "heading_path": heading_path
                    })
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue
        
        logger.info(f"Generated {len(chunks)} chunks from markdown files")
        return chunks

    async def initialize_from_markdown(self, source_dir: str = "information_source") -> Dict[str, any]:
        """
        Initialize the vector database from markdown files in the source directory.
        
        Args:
            source_dir: Directory containing markdown files
            
        Returns:
            Dictionary with initialization results
        """
        if not self.chroma_client or not self.collection or not self.openai_client:
            raise RuntimeError("VectorDBManager not initialized. Call initialize() first.")
        
        with self._lock:  # Ensure thread safety
            try:
                # Get all markdown chunks
                chunks = self.get_markdown_chunks(source_dir)
                
                if not chunks:
                    logger.warning(f"No chunks found in {source_dir}")
                    return {"status": "warning", "message": "No chunks found", "chunks_processed": 0}
                
                # Clear existing collection data
                try:
                    # Get all existing IDs and delete them
                    existing_data = await asyncio.to_thread(self.collection.get)
                    if existing_data["ids"]:
                        await asyncio.to_thread(self.collection.delete, ids=existing_data["ids"])
                        logger.info(f"Cleared {len(existing_data['ids'])} existing entries")
                except Exception as e:
                    logger.warning(f"Error clearing existing data: {e}")
                
                # Process chunks in batches for better performance
                batch_size = 10
                total_processed = 0
                
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    
                    # Generate embeddings for the batch
                    texts = [chunk["content"] for chunk in batch]
                    
                    embeddings_response = await asyncio.to_thread(
                        self.openai_client.embeddings.create,
                        model="text-embedding-3-small",
                        input=texts
                    )
                    
                    # Prepare data for ChromaDB
                    ids = [f"chunk-{i + j}" for j in range(len(batch))]
                    documents = texts
                    embeddings = [emb.embedding for emb in embeddings_response.data]
                    metadatas = [
                        {
                            "file": chunk["file_name"],
                            "heading": chunk["heading"],
                            "heading_path": chunk["heading_path"]
                        }
                        for chunk in batch
                    ]
                    
                    # Add to ChromaDB
                    await asyncio.to_thread(
                        self.collection.add,
                        ids=ids,
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas
                    )
                    
                    total_processed += len(batch)
                    logger.info(f"Processed batch {i//batch_size + 1}, total chunks: {total_processed}")
                
                logger.info(f"Successfully initialized vector database with {total_processed} chunks")
                return {
                    "status": "success",
                    "message": f"Initialized with {total_processed} chunks",
                    "chunks_processed": total_processed
                }
                
            except Exception as e:
                logger.error(f"Error initializing from markdown: {e}")
                raise

    async def re_index(self, source_dir: str = "information_source") -> Dict[str, any]:
        """
        Re-index the vector database with fresh data from markdown files.
        
        Args:
            source_dir: Directory containing markdown files
            
        Returns:
            Dictionary with re-indexing results
        """
        logger.info("Starting re-indexing process")
        return await self.initialize_from_markdown(source_dir)

    async def query_similar(self, embedding: List[float], n_results: int = 3) -> Dict[str, any]:
        """
        Query for similar documents using an embedding vector.
        
        Args:
            embedding: The query embedding vector
            n_results: Number of results to return
            
        Returns:
            Query results from ChromaDB
        """
        if not self.collection:
            raise RuntimeError("VectorDBManager not initialized. Call initialize() first.")
        
        with self._lock:  # Ensure thread safety for reads
            try:
                results = await asyncio.to_thread(
                    self.collection.query,
                    query_embeddings=[embedding],
                    n_results=n_results
                )
                return results
            except Exception as e:
                logger.error(f"Error querying similar documents: {e}")
                raise

    async def get_collection_info(self) -> Dict[str, any]:
        """
        Get information about the current collection.
        
        Returns:
            Dictionary with collection information
        """
        if not self.collection:
            raise RuntimeError("VectorDBManager not initialized. Call initialize() first.")
        
        try:
            count = await asyncio.to_thread(self.collection.count)
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "db_path": self.db_path
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            raise

    async def close(self) -> None:
        """Clean up resources."""
        # ChromaDB client doesn't need explicit closing
        # OpenAI client doesn't need explicit closing
        logger.info("VectorDBManager closed")
