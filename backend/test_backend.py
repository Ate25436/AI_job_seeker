"""
Basic tests for the AI Job Seeker backend API
"""
import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app and services
from app.main import app
from app.services.rag_service import RAGService
from app.services.vector_db_manager import VectorDBManager


class TestFastAPIEndpoints:
    """Test FastAPI endpoints"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test the root endpoint returns correct response"""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "timestamp" in data
        assert data["message"] == "AI Job Seeker API is running"
    
    def test_health_endpoint_without_rag_service(self):
        """Test health endpoint when RAG service is not initialized"""
        # This test runs before RAG service is initialized
        response = self.client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database_status"] == "not_initialized"
        assert data["openai_status"] == "not_initialized"
    
    def test_ask_endpoint_without_rag_service(self):
        """Test ask endpoint when RAG service is not initialized"""
        response = self.client.post("/api/ask", json={"question": "Test question"})
        assert response.status_code == 503
        data = response.json()
        assert "RAG service is not available" in data["message"]
    
    def test_ask_endpoint_empty_question(self):
        """Test ask endpoint with empty question"""
        response = self.client.post("/api/ask", json={"question": ""})
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "validation_error" in data["error"]
    
    def test_ask_endpoint_whitespace_question(self):
        """Test ask endpoint with whitespace-only question"""
        response = self.client.post("/api/ask", json={"question": "   "})
        assert response.status_code == 503  # Service unavailable because RAG service not initialized
        data = response.json()
        assert "RAG service is not available" in data["message"]
    
    def test_ask_endpoint_invalid_json(self):
        """Test ask endpoint with invalid request format"""
        response = self.client.post("/api/ask", json={})
        assert response.status_code == 422  # Validation error


class TestRAGService:
    """Test RAG Service functionality"""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client"""
        mock_client = Mock()
        
        # Mock embedding response
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock()]
        mock_embedding_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_embedding_response
        
        # Mock chat completion response
        mock_chat_response = Mock()
        mock_chat_response.choices = [Mock()]
        mock_chat_response.choices[0].message.content = "Test answer"
        mock_client.chat.completions.create.return_value = mock_chat_response
        
        return mock_client
    
    @pytest.fixture
    def mock_chroma_collection(self):
        """Mock ChromaDB collection"""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "documents": [["Test document content"]],
            "metadatas": [[{"file": "test.md", "heading": "Test", "heading_path": "Test"}]]
        }
        mock_collection.count.return_value = 1
        return mock_collection
    
    @pytest.mark.asyncio
    async def test_rag_service_initialization(self):
        """Test RAG service initialization"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('chromadb.PersistentClient') as mock_chroma:
                mock_client = Mock()
                mock_collection = Mock()
                mock_client.get_collection.return_value = mock_collection
                mock_chroma.return_value = mock_client
                
                rag_service = RAGService()
                await rag_service.initialize()
                
                assert rag_service.openai_client is not None
                assert rag_service.chroma_client is not None
                assert rag_service.collection is not None
    
    @pytest.mark.asyncio
    async def test_rag_service_initialization_no_api_key(self):
        """Test RAG service initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            rag_service = RAGService()
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                await rag_service.initialize()
    
    @pytest.mark.asyncio
    async def test_generate_answer_not_initialized(self):
        """Test generate_answer when service is not initialized"""
        rag_service = RAGService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await rag_service.generate_answer("Test question")
    
    @pytest.mark.asyncio
    async def test_generate_answer_empty_question(self):
        """Test generate_answer with empty question"""
        rag_service = RAGService()
        rag_service.openai_client = Mock()
        rag_service.collection = Mock()
        
        with pytest.raises(ValueError, match="empty"):
            await rag_service.generate_answer("")
    
    @pytest.mark.asyncio
    async def test_generate_answer_success(self, mock_openai_client, mock_chroma_collection):
        """Test successful answer generation"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            rag_service = RAGService()
            rag_service.openai_client = mock_openai_client
            rag_service.collection = mock_chroma_collection
            
            # Mock asyncio.to_thread to return the mock responses directly
            with patch('asyncio.to_thread') as mock_to_thread:
                mock_to_thread.side_effect = [
                    mock_openai_client.embeddings.create.return_value,  # embedding call
                    mock_chroma_collection.query.return_value,  # collection query
                    mock_openai_client.chat.completions.create.return_value  # chat completion
                ]
                
                result = await rag_service.generate_answer("Test question")
                
                assert "answer" in result
                assert "sources" in result
                assert "timestamp" in result
                assert "processing_time_ms" in result
                assert result["answer"] == "Test answer"
                assert len(result["sources"]) > 0


class TestVectorDBManager:
    """Test Vector Database Manager functionality"""
    
    @pytest.mark.asyncio
    async def test_vector_db_manager_initialization(self):
        """Test VectorDBManager initialization"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('chromadb.PersistentClient') as mock_chroma:
                mock_client = Mock()
                mock_collection = Mock()
                mock_client.get_or_create_collection.return_value = mock_collection
                mock_chroma.return_value = mock_client
                
                db_manager = VectorDBManager()
                await db_manager.initialize()
                
                assert db_manager.openai_client is not None
                assert db_manager.chroma_client is not None
                assert db_manager.collection is not None
    
    @pytest.mark.asyncio
    async def test_vector_db_manager_initialization_no_api_key(self):
        """Test VectorDBManager initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            db_manager = VectorDBManager()
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                await db_manager.initialize()
    
    def test_chunk_markdown_basic(self):
        """Test basic markdown chunking"""
        db_manager = VectorDBManager()
        markdown_text = """# Heading 1
Content for heading 1

## Heading 2
Content for heading 2

### Heading 3
Content for heading 3"""
        
        chunks = db_manager.chunk_markdown(markdown_text)
        assert len(chunks) >= 1
        # Check that we get some chunks with headings
        headings = [chunk[0] for chunk in chunks if chunk[0]]
        assert len(headings) > 0
    
    def test_chunk_markdown_empty(self):
        """Test markdown chunking with empty content"""
        db_manager = VectorDBManager()
        chunks = db_manager.chunk_markdown("")
        # Should handle empty content gracefully
        assert isinstance(chunks, list)
    
    @pytest.mark.asyncio
    async def test_get_collection_info_not_initialized(self):
        """Test get_collection_info when not initialized"""
        db_manager = VectorDBManager()
        with pytest.raises(RuntimeError, match="not initialized"):
            await db_manager.get_collection_info()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])