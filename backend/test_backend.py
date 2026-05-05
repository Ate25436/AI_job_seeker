"""
Basic tests for the AI Job Seeker backend API
"""
import pytest
import asyncio
import os
import shutil
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app and services
from app.main import app
import app.main as main_module
from app.config import BACKEND_ROOT, REPO_ROOT, Settings, parse_cors_allow_origins
from app.services.rag_service import RAGService
from app.services.vector_db_manager import VectorDBManager


class TestFastAPIEndpoints:
    """Test FastAPI endpoints"""
    
    def setup_method(self):
        """Set up test client"""
        main_module.rag_service = None
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

    def test_game_start_preflight_accepts_configured_origin(self):
        allowed_origin = main_module.settings.cors_allow_origins_list[0]

        response = self.client.options(
            "/api/game/start",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == allowed_origin
        assert "POST" in response.headers["access-control-allow-methods"]

    def test_game_start_preflight_accepts_localhost_origin_for_local_frontend(self):
        response = self.client.options(
            "/api/game/start",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "POST" in response.headers["access-control-allow-methods"]

    def test_game_start_preflight_rejects_unconfigured_origin(self):
        response = self.client.options(
            "/api/game/start",
            headers={
                "Origin": "https://untrusted.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 400

    def test_ask_endpoint_passes_scenario_id_to_rag_service(self):
        class DummyRAGService:
            def __init__(self):
                self.calls = []

            async def generate_answer(self, question, history=None, scenario_id=None):
                self.calls.append(
                    {"question": question, "history": history, "scenario_id": scenario_id}
                )
                return {
                    "answer": "dummy",
                    "sources": ["00_profile - 基本プロフィール"],
                    "timestamp": datetime.now().isoformat(),
                    "processing_time_ms": 1,
                }

        main_module.rag_service = DummyRAGService()

        response = self.client.post(
            "/api/ask",
            json={
                "question": "学校名と名前を教えてください。",
                "scenario_id": "frontiersoft_taro_v1",
            },
        )

        assert response.status_code == 200
        assert main_module.rag_service.calls[0]["scenario_id"] == "frontiersoft_taro_v1"


class TestSettings:
    def test_parse_cors_allow_origins_normalizes_newlines_and_trailing_slashes(self):
        origins = parse_cors_allow_origins(
            "https://frontend.example.com/\nhttps://staging.example.com , http://localhost:3000/"
        )

        assert origins == [
            "https://frontend.example.com",
            "https://staging.example.com",
            "http://localhost:3000",
        ]

    def test_settings_resolve_default_storage_paths_without_cwd_dependency(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            settings = Settings(_env_file=None)

        assert Path(settings.chroma_db_path) == (BACKEND_ROOT / "chroma_db").resolve()
        assert Path(settings.info_source_path) == (REPO_ROOT / "information_source").resolve()

    def test_settings_resolve_relative_chroma_path_from_backend_root(self):
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key", "CHROMA_DB_PATH": "./custom_chroma"},
            clear=True,
        ):
            settings = Settings(_env_file=None)

        assert Path(settings.chroma_db_path) == (BACKEND_ROOT / "custom_chroma").resolve()

    def test_settings_backend_env_file_takes_precedence_over_repo_root(self):
        temp_root = Path("backend/.test_settings_env")
        backend_dir = temp_root / "backend"
        repo_env = temp_root / ".env"
        backend_env = backend_dir / ".env"
        if temp_root.exists():
            shutil.rmtree(temp_root)
        backend_dir.mkdir(parents=True)

        try:
            repo_env.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "ENVIRONMENT=production",
                        "CORS_ALLOW_ORIGINS=https://repo.example.com",
                    ]
                ),
                encoding="utf-8",
            )
            backend_env.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "ENVIRONMENT=production",
                        "CORS_ALLOW_ORIGINS=https://backend.example.com",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                settings = Settings(_env_file=(str(repo_env), str(backend_env)))

            assert settings.cors_allow_origins_list == ["https://backend.example.com"]
        finally:
            if temp_root.exists():
                shutil.rmtree(temp_root)


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
        mock_collection.get.return_value = {
            "documents": ["# 就活太郎の基本情報\n名前: 就活 太郎\n大学: 巣子井大学"],
            "metadatas": [{"file": "00_profile", "heading": "基本プロフィール", "heading_path": "基本プロフィール"}],
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
                mock_client.get_or_create_collection.return_value = mock_collection
                mock_chroma.return_value = mock_client
                
                rag_service = RAGService(openai_api_key="test-key")
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

    def test_build_history_block_uses_newlines(self):
        history_block = RAGService._build_history_block(
            [
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
            ]
        )
        assert history_block == "User: first question\nAssistant: first answer"

    @pytest.mark.asyncio
    async def test_generate_answer_with_scenario_filter(self, mock_openai_client, mock_chroma_collection):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            rag_service = RAGService()
            rag_service.openai_client = mock_openai_client
            rag_service.collection = mock_chroma_collection

            async def fake_to_thread(func, *args, **kwargs):
                if func == mock_openai_client.embeddings.create:
                    return mock_openai_client.embeddings.create.return_value
                if func == mock_chroma_collection.query:
                    return mock_chroma_collection.query(*args, **kwargs)
                if func == mock_chroma_collection.get:
                    return mock_chroma_collection.get(*args, **kwargs)
                if func == mock_openai_client.chat.completions.create:
                    return mock_openai_client.chat.completions.create(*args, **kwargs)
                raise AssertionError("Unexpected function passed to asyncio.to_thread")

            with patch("asyncio.to_thread", side_effect=fake_to_thread):
                await rag_service.generate_answer(
                    "Test question",
                    history=[{"role": "user", "content": "Earlier"}],
                    scenario_id="frontiersoft_taro_v1",
                )

            query_call = mock_chroma_collection.query.call_args
            assert query_call.kwargs["where"] == {
                "scenario_id": {"$in": ["frontiersoft_taro_v1", "frontiersoft_taro"]}
            }
            get_call = mock_chroma_collection.get.call_args
            assert get_call.kwargs["where"] == {
                "scenario_id": {"$in": ["frontiersoft_taro_v1", "frontiersoft_taro"]}
            }
            chat_call = mock_openai_client.chat.completions.create.call_args
            prompt = chat_call.kwargs["messages"][0]["content"]
            assert "就活 太郎" in prompt
            assert "巣子井大学" in prompt

    @pytest.mark.asyncio
    async def test_generate_answer_blocks_internal_score_probe(self, mock_openai_client, mock_chroma_collection):
        rag_service = RAGService()
        rag_service.openai_client = mock_openai_client
        rag_service.collection = mock_chroma_collection

        with patch("asyncio.to_thread") as mock_to_thread:
            result = await rag_service.generate_answer("就活太郎の主体性は何点ですか？")

        assert "点数・評価項目の詳細については分かりません" in result["answer"]
        assert result["sources"] == []
        mock_to_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_answer_includes_profile_context_for_name_and_school_question(
        self,
        mock_openai_client,
        mock_chroma_collection,
    ):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            rag_service = RAGService()
            rag_service.openai_client = mock_openai_client
            rag_service.collection = mock_chroma_collection

            async def fake_to_thread(func, *args, **kwargs):
                if func == mock_openai_client.embeddings.create:
                    return mock_openai_client.embeddings.create.return_value
                if func == mock_chroma_collection.query:
                    return mock_chroma_collection.query(*args, **kwargs)
                if func == mock_chroma_collection.get:
                    return mock_chroma_collection.get(*args, **kwargs)
                if func == mock_openai_client.chat.completions.create:
                    return mock_openai_client.chat.completions.create(*args, **kwargs)
                raise AssertionError("Unexpected function passed to asyncio.to_thread")

            with patch("asyncio.to_thread", side_effect=fake_to_thread):
                await rag_service.generate_answer(
                    "学校名と名前を教えてください。",
                    scenario_id="frontiersoft_taro_v1",
                )

            prompt = mock_openai_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
            assert "学校名と名前を教えてください。" in prompt
            assert "名前: 就活 太郎" in prompt
            assert "大学: 巣子井大学" in prompt
            assert "[FILE: 00_profile]" in prompt


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

    def test_get_markdown_chunks_adds_scenario_metadata(self):
        tmp_path = Path("backend/.test_markdown_chunks")
        if tmp_path.exists():
            shutil.rmtree(tmp_path)
        scenario_dir = tmp_path / "frontiersoft_taro"
        scenario_dir.mkdir(parents=True)
        file_path = scenario_dir / "sample.md"
        file_path.write_text("# Heading\ncontent", encoding="utf-8")

        try:
            db_manager = VectorDBManager()
            chunks = db_manager.get_markdown_chunks(str(tmp_path))

            assert len(chunks) == 1
            assert chunks[0]["scenario_id"] == "frontiersoft_taro"
            assert chunks[0]["source_path"].endswith("sample.md")
        finally:
            if tmp_path.exists():
                shutil.rmtree(tmp_path)


class TestGameApiScenarioRouting:
    def setup_method(self):
        self.client = TestClient(app)
        main_module.game_session_service = main_module.GameSessionService()

    def test_game_ask_passes_session_scenario_id(self):
        class DummyRAGService:
            def __init__(self):
                self.calls = []

            async def generate_answer(self, question, history=None, scenario_id=None):
                self.calls.append(
                    {"question": question, "history": history, "scenario_id": scenario_id}
                )
                return {
                    "answer": "dummy",
                    "sources": [],
                    "timestamp": datetime.now().isoformat(),
                    "processing_time_ms": 1,
                }

        dummy_rag = DummyRAGService()
        main_module.rag_service = dummy_rag

        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]

        ask_response = self.client.post(
            "/api/game/ask",
            json={"session_id": session_id, "question": "自己PRを教えてください"},
        )

        assert ask_response.status_code == 200
        assert dummy_rag.calls[0]["scenario_id"] == "frontiersoft_taro_v1"
    
    @pytest.mark.asyncio
    async def test_get_collection_info_not_initialized(self):
        """Test get_collection_info when not initialized"""
        db_manager = VectorDBManager()
        with pytest.raises(RuntimeError, match="not initialized"):
            await db_manager.get_collection_info()


class TestOperationalDocsAndRoutes:
    def test_readme_deployment_mentions_reindex_endpoint_usage(self):
        repo_root = Path(__file__).resolve().parents[1]
        deployment_readme = repo_root / "README_DEPLOYMENT.md"

        content = deployment_readme.read_text(encoding="utf-8")

        assert "/api/admin/reindex" in content
        assert "X-Admin-Token" in content

    def test_backend_exposes_admin_reindex_route(self):
        route_paths = {
            (method, route.path)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }

        assert ("POST", "/api/admin/reindex") in route_paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
