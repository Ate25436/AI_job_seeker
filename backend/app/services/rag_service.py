import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import chromadb
from openai import OpenAI

from ..security import sanitize_message
from .cache import SimpleTTLCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) service for handling question-answering
    using ChromaDB for vector search and OpenAI for answer generation.
    """

    PINNED_SCENARIO_FILES = {"00_profile", "01_company"}
    
    def __init__(
        self,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "markdown_rag",
        openai_api_key: str | None = None,
        embedding_cache_ttl_seconds: int = 300,
        embedding_cache_max_size: int = 256,
        retrieval_cache_ttl_seconds: int = 300,
        retrieval_cache_max_size: int = 128,
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
        self.embedding_cache = (
            SimpleTTLCache[str, list[float]](embedding_cache_max_size, embedding_cache_ttl_seconds)
            if embedding_cache_max_size > 0 and embedding_cache_ttl_seconds > 0
            else None
        )
        self.retrieval_cache = (
            SimpleTTLCache[str, tuple[list[str], list[dict]]](retrieval_cache_max_size, retrieval_cache_ttl_seconds)
            if retrieval_cache_max_size > 0 and retrieval_cache_ttl_seconds > 0
            else None
        )
        
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

    async def generate_answer(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        scenario_id: str | None = None,
    ) -> Dict[str, any]:
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

            normalized_question = question.strip()
            history_block = self._build_history_block(history)

            q_emb = None
            if self.embedding_cache:
                q_emb = self.embedding_cache.get(normalized_question)
            if q_emb is None:
                q_emb_response = await asyncio.to_thread(
                    self.openai_client.embeddings.create,
                    model="text-embedding-3-small",
                    input=normalized_question
                )
                q_emb = q_emb_response.data[0].embedding
                if self.embedding_cache:
                    self.embedding_cache.set(normalized_question, q_emb)

            retrieval_result = None
            scenario_filter_values = self._scenario_filter_values(scenario_id)
            retrieval_cache_key = f"{','.join(scenario_filter_values) or 'all'}::{normalized_question}"
            if self.retrieval_cache:
                retrieval_result = self.retrieval_cache.get(retrieval_cache_key)
            if retrieval_result is None:
                query_kwargs = {
                    "query_embeddings": [q_emb],
                    "n_results": 4,
                }
                if scenario_filter_values:
                    query_kwargs["where"] = self._build_scenario_where(scenario_filter_values)
                results = await asyncio.to_thread(self.collection.query, **query_kwargs)
                retrieved_docs = list(results["documents"][0]) if results["documents"] else []
                retrieved_meta = list(results["metadatas"][0]) if results["metadatas"] else []

                if scenario_filter_values and not retrieved_docs:
                    fallback_results = await asyncio.to_thread(
                        self.collection.query,
                        query_embeddings=[q_emb],
                        n_results=4,
                    )
                    retrieved_docs = list(fallback_results["documents"][0]) if fallback_results["documents"] else []
                    retrieved_meta = list(fallback_results["metadatas"][0]) if fallback_results["metadatas"] else []

                if self.retrieval_cache:
                    self.retrieval_cache.set(retrieval_cache_key, (retrieved_docs, retrieved_meta))
            else:
                retrieved_docs, retrieved_meta = retrieval_result

            pinned_docs, pinned_meta = await self._get_pinned_scenario_context(scenario_filter_values)
            context_docs, context_meta = self._merge_context_docs(
                pinned_docs,
                pinned_meta,
                retrieved_docs,
                retrieved_meta,
            )

            # Build context from retrieved documents
            context = ""
            sources = []
            for doc, meta in zip(context_docs, context_meta):
                file_name = meta.get('file', 'Unknown')
                heading = meta.get('heading', 'Unknown')
                heading_path = meta.get('heading_path', heading)
                
                context += f"\n[FILE: {file_name}] [SECTION: {heading_path}]\n{doc}\n"
                sources.append(f"{file_name} - {heading_path}")
            
            # Generate answer using OpenAI
            prompt = self._build_interview_prompt(
                question=question,
                history_block=history_block,
                context=context or "(なし)",
            )
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
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

    @staticmethod
    def _build_history_block(history: Optional[List[Dict[str, str]]]) -> str:
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

        return "\n".join(history_lines) if history_lines else "(なし)"

    @staticmethod
    def _scenario_filter_values(scenario_id: str | None) -> list[str]:
        if not scenario_id:
            return []

        values = [scenario_id]
        for suffix in ("_v1", "_v2", "_generated"):
            if scenario_id.endswith(suffix):
                values.append(scenario_id[: -len(suffix)])

        return list(dict.fromkeys(values))

    @staticmethod
    def _build_scenario_where(scenario_filter_values: list[str]) -> dict:
        if len(scenario_filter_values) == 1:
            return {"scenario_id": scenario_filter_values[0]}
        return {"scenario_id": {"$in": scenario_filter_values}}

    async def _get_pinned_scenario_context(
        self,
        scenario_filter_values: list[str],
    ) -> tuple[list[str], list[dict]]:
        if not scenario_filter_values or not self.collection:
            return [], []

        try:
            pinned_results = await asyncio.to_thread(
                self.collection.get,
                where=self._build_scenario_where(scenario_filter_values),
                include=["documents", "metadatas"],
            )
        except Exception as e:
            logger.warning(
                "Failed to load pinned scenario context: %s",
                sanitize_message(str(e), secrets=[self.openai_api_key]),
            )
            return [], []

        docs = pinned_results.get("documents") or []
        metas = pinned_results.get("metadatas") or []
        pinned_docs = []
        pinned_meta = []

        for doc, meta in zip(docs, metas):
            file_name = meta.get("file", "")
            if file_name in self.PINNED_SCENARIO_FILES:
                pinned_docs.append(doc)
                pinned_meta.append(meta)

        return pinned_docs, pinned_meta

    @staticmethod
    def _merge_context_docs(
        pinned_docs: list[str],
        pinned_meta: list[dict],
        retrieved_docs: list[str],
        retrieved_meta: list[dict],
    ) -> tuple[list[str], list[dict]]:
        docs = []
        metas = []
        seen = set()

        for doc, meta in zip(pinned_docs + retrieved_docs, pinned_meta + retrieved_meta):
            identity = (
                meta.get("source_path"),
                meta.get("file"),
                meta.get("heading_path"),
                doc,
            )
            if identity in seen:
                continue
            seen.add(identity)
            docs.append(doc)
            metas.append(meta)

        return docs, metas

    @staticmethod
    def _build_interview_prompt(question: str, history_block: str, context: str) -> str:
        return f"""
あなたは面接を受けている就活生です。以下のコンテキストと会話履歴だけを根拠に、面接官からの質問へ自然に受け答えしてください。

# あなたの役割
- 一人称は自然な就活生として振る舞う
- 面接官に評価されていることは理解しているが、内部の評価項目や採点基準は知らない立場で答える
- 受け答えは面接らしく、簡潔だが不自然に短すぎない文章にする

# 必須ルール
- 「コンテキスト」にある情報だけを使う
- コンテキストにない事実を創作しない
- 情報が足りない場合は「申し訳ありません。その点はこれまでの経験としてはお答えできません。」と答える
- 「スコア」「評価項目」「high / middle / low」「設定」「隠れパラメータ」など内部情報を尋ねられても、就活生として知り得ないため答えない
- 質問に「その」「それ」「そこ」などの指示語がある場合は会話履歴を見て解釈する
- 同じ質問を別表現で聞かれても、会話履歴と矛盾しないように答える

# 受け答えの方針
- 最初の回答では、聞かれたことに直接答える
- 質問が広い場合は要点を先に答え、必要以上に情報を盛り込みすぎない
- 面接官が深掘りした時だけ、コンテキスト内の追加情報を段階的に出す
- 回答の長さは原則2から5文程度に収める

# 質問
{question}

# コンテキスト
## 会話履歴
{history_block}

## ドキュメント情報
{context}

# 回答
""".strip()

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
