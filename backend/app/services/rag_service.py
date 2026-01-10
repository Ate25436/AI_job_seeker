import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import chromadb
from openai import OpenAI

from ..security import sanitize_message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) service for handling question-answering
    using ChromaDB for vector search and OpenAI for answer generation.
    """
    
    def __init__(
        self,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "markdown_rag",
        openai_api_key: str | None = None,
    ):
        """
        Initialize the RAG service.
        
        Args:
            chroma_db_path: Path to the ChromaDB database
            collection_name: Name of the ChromaDB collection
        """
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        self.openai_api_key = openai_api_key
        self.openai_client = None
        self.chroma_client = None
        self.collection = None
        
    async def initialize(self) -> None:
        """Initialize the RAG service components."""
        try:
            # Initialize OpenAI client
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")

            self.openai_client = OpenAI(api_key=self.openai_api_key)
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path=self.chroma_db_path)
            
            # Get or create the collection
            try:
                self.collection = self.chroma_client.get_or_create_collection(self.collection_name)
                logger.info(f"Successfully connected to collection: {self.collection_name}")
            except Exception as e:
                logger.error(
                    "Failed to get or create collection %s: %s",
                    self.collection_name,
                    sanitize_message(str(e), secrets=[self.openai_api_key]),
                )
                raise
                
        except Exception as e:
            logger.error(
                "Failed to initialize RAG service: %s",
                sanitize_message(str(e), secrets=[self.openai_api_key]),
            )
            raise

    async def generate_answer(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, any]:
        """
        Generate an answer for the given question using RAG.
        
        Args:
            question: The user's question
            
        Returns:
            Dictionary containing answer, sources, and metadata
        """
        if not self.openai_client or not self.collection:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")
        
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        try:
            start_time = datetime.now()
            
            # Build conversation history
            history_lines = []
            if history:
                for item in history:
                    if isinstance(item, dict):
                        role = item.get("role")
                        content = item.get("content")
                    else:
                        role = getattr(item, "role", None)
                        content = getattr(item, "content", None)

                    if role in {"user", "assistant"} and content:
                        prefix = "User" if role == "user" else "Assistant"
                        history_lines.append(f"{prefix}: {content}")

            history_block = "".join(history_lines) if history_lines else "(なし)"

            # Generate embedding for the question
            q_emb_response = await asyncio.to_thread(
                self.openai_client.embeddings.create,
                model="text-embedding-3-small",
                input=question.strip()
            )
            q_emb = q_emb_response.data[0].embedding
            
            # Search for relevant documents
            results = await asyncio.to_thread(
                self.collection.query,
                query_embeddings=[q_emb],
                n_results=3
            )
            
            retrieved_docs = results["documents"][0]
            retrieved_meta = results["metadatas"][0]
            
            # Build context from retrieved documents
            context = ""
            sources = []
            for doc, meta in zip(retrieved_docs, retrieved_meta):
                file_name = meta.get('file', 'Unknown')
                heading = meta.get('heading', 'Unknown')
                heading_path = meta.get('heading_path', heading)
                
                context += f"\n[FILE: {file_name}] [SECTION: {heading_path}]\n{doc}\n"
                sources.append(f"{file_name} - {heading_path}")
            
            # Build conversation history
            history_lines = []
            if history:
                for item in history:
                    if isinstance(item, dict):
                        role = item.get("role")
                        content = item.get("content")
                    else:
                        role = getattr(item, "role", None)
                        content = getattr(item, "content", None)

                    if role in {"user", "assistant"} and content:
                        prefix = "User" if role == "user" else "Assistant"
                        history_lines.append(f"{prefix}: {content}")

            history_block = "".join(history_lines) if history_lines else "(なし)"

            # Generate answer using OpenAI
            prompt = f"""
あなたは与えられたコンテキスト（経験）に基づいて質問に回答する就活生です。

# 制約
- 以下の「コンテキスト」に含まれる情報のみを根拠として回答する
- コンテキストに答えがない場合は「申し訳ありません．事前知識に含まれていないのでお答えできません．」と答える
- 質問に「その」，「それ」，「そこ」などの指示語が含まれる場合は，必ず会話履歴を参照して指示語の指す内容を特定する

# 質問
{question}

# コンテキスト

## 会話履歴
{history_block}

## ドキュメント情報
{context}


# 回答:
"""
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            answer = response.choices[0].message.content
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "answer": answer,
                "sources": sources,
                "timestamp": end_time.isoformat(),
                "processing_time_ms": processing_time_ms
            }
            
        except Exception as e:
            logger.error(
                "Error generating answer: %s",
                sanitize_message(str(e), secrets=[self.openai_api_key]),
            )
            raise

    async def health_check(self) -> Dict[str, str]:
        """
        Perform a health check on the RAG service components.
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database_status": "unknown",
            "openai_status": "unknown"
        }
        
        try:
            # Check ChromaDB connection
            if self.chroma_client and self.collection:
                # Try a simple query to test database connectivity
                await asyncio.to_thread(self.collection.count)
                health_status["database_status"] = "healthy"
            else:
                health_status["database_status"] = "not_initialized"
                health_status["status"] = "unhealthy"
        except Exception as e:
            logger.error(
                "Database health check failed: %s",
                sanitize_message(str(e), secrets=[self.openai_api_key]),
            )
            health_status["database_status"] = "unhealthy"
            health_status["status"] = "unhealthy"
        
        try:
            # Check OpenAI API connection
            if self.openai_client:
                # Try a simple embedding request to test API connectivity
                await asyncio.to_thread(
                    self.openai_client.embeddings.create,
                    model="text-embedding-3-small",
                    input="health check"
                )
                health_status["openai_status"] = "healthy"
            else:
                health_status["openai_status"] = "not_initialized"
                health_status["status"] = "unhealthy"
        except Exception as e:
            logger.error(
                "OpenAI health check failed: %s",
                sanitize_message(str(e), secrets=[self.openai_api_key]),
            )
            health_status["openai_status"] = "unhealthy"
            health_status["status"] = "unhealthy"
        
        return health_status

    async def close(self) -> None:
        """Clean up resources."""
        # ChromaDB client doesn't need explicit closing
        # OpenAI client doesn't need explicit closing
        logger.info("RAG service closed")
