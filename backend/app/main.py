"""
FastAPI main application entry point
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from .config import get_settings, settings_for_log
from .models import QuestionRequest, AnswerResponse, HealthResponse, ErrorResponse
from .services.rag_service import RAGService
from .services.vector_db_manager import VectorDBManager
from .security import sanitize_message

# Global RAG service instance
rag_service = None
settings = get_settings()

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global rag_service
    
    # Startup
    logger.info("Starting AI Job Seeker API...")
    logger.info("Loaded settings: %s", settings_for_log(settings))
    
    try:
        rag_service = RAGService(
            chroma_db_path=settings.chroma_db_path,
            openai_api_key=settings.openai_api_key.get_secret_value(),
            embedding_cache_ttl_seconds=settings.embedding_cache_ttl_seconds,
            embedding_cache_max_size=settings.embedding_cache_max_size,
            retrieval_cache_ttl_seconds=settings.retrieval_cache_ttl_seconds,
            retrieval_cache_max_size=settings.retrieval_cache_max_size,
        )
        await rag_service.initialize()
        logger.info("RAG service initialized successfully")

        if settings.auto_init_vector_db:
            info_source_dir = Path(settings.info_source_path)
            if not info_source_dir.exists():
                logger.warning(
                    "Auto init skipped: info source path not found: %s",
                    settings.info_source_path,
                )
            else:
                count = await asyncio.to_thread(rag_service.collection.count)
                if count == 0:
                    logger.info("Auto init: seeding vector database from %s", info_source_dir)
                    vector_manager = VectorDBManager(
                        db_path=settings.chroma_db_path,
                        collection_name="markdown_rag",
                        openai_api_key=settings.openai_api_key.get_secret_value(),
                    )
                    await vector_manager.initialize()
                    await vector_manager.initialize_from_markdown(str(info_source_dir))
                    await vector_manager.close()
                else:
                    logger.info("Auto init skipped: collection already has %s documents", count)
    except Exception as e:
        logger.error("Failed to initialize RAG service: %s", sanitize_message(str(e)))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Job Seeker API...")
    if rag_service:
        await rag_service.close()

app = FastAPI(
    title="AI Job Seeker API",
    description="RAG-based Q&A system for job seekers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for web browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed error messages."""
    logger.warning(
        "Validation error for %s %s: %s",
        request.method,
        request.url.path,
        sanitize_message(str(exc)),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message="Invalid request data.",
            timestamp=datetime.now()
        ).model_dump(mode='json')
    )

# Global exception handler for HTTP exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    logger.error(
        "HTTP error %s for %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        sanitize_message(str(exc.detail)),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="http_error",
            message=exc.detail,
            timestamp=datetime.now()
        ).model_dump(mode='json')
    )

# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors with generic error message."""
    logger.error(
        "Unexpected error for %s %s: %s",
        request.method,
        request.url.path,
        sanitize_message(str(exc)),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred. Please try again later.",
            timestamp=datetime.now()
        ).model_dump(mode='json')
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    start_time = datetime.now()
    
    # Log request
    logger.info("Request: %s %s", request.method, request.url.path)
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info("Response: %s - %.3fs", response.status_code, process_time)
    response.headers["X-Response-Time-ms"] = str(int(process_time * 1000))
    
    return response

@app.get("/")
async def root():
    """Root endpoint returning API status."""
    return {"message": "AI Job Seeker API is running", "timestamp": datetime.now().isoformat()}

@app.post("/api/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Process a question and return an AI-generated answer using RAG.
    
    Args:
        request: QuestionRequest containing the user's question
        
    Returns:
        AnswerResponse with the generated answer, sources, and metadata
        
    Raises:
        HTTPException: If RAG service is not available or question processing fails
    """
    global rag_service
    
    if not rag_service:
        logger.error("RAG service not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please try again later."
        )
    
    try:
        # Validate question content
        question = request.question.strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty or contain only whitespace."
            )
        
        if settings.environment == "development":
            logger.info("Processing question: %s...", question[:100])
        else:
            logger.info("Processing question with length: %s", len(question))
        
        # Generate answer using RAG service
        result = await rag_service.generate_answer(question, history=request.history)
        
        # Create response
        response = AnswerResponse(
            answer=result["answer"],
            sources=result["sources"],
            timestamp=datetime.fromisoformat(result["timestamp"]),
            processing_time_ms=result["processing_time_ms"]
        )
        
        logger.info("Question processed successfully in %sms", result["processing_time_ms"])
        return response
        
    except ValueError as e:
        logger.warning("Invalid question input: %s", sanitize_message(str(e)))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error("RAG service runtime error: %s", sanitize_message(str(e)))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is temporarily unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(
            "Unexpected error processing question: %s",
            sanitize_message(str(e)),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your question. Please try again."
        )

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Perform a comprehensive health check of the API and its dependencies.
    
    Returns:
        HealthResponse with status information for all system components
    """
    global rag_service
    
    try:
        if not rag_service:
            logger.warning("Health check: RAG service not initialized")
            return HealthResponse(
                status="unhealthy",
                timestamp=datetime.now(),
                database_status="not_initialized",
                openai_status="not_initialized"
            )
        
        # Perform health check using RAG service
        health_result = await rag_service.health_check()
        
        response = HealthResponse(
            status=health_result["status"],
            timestamp=datetime.fromisoformat(health_result["timestamp"]),
            database_status=health_result["database_status"],
            openai_status=health_result["openai_status"]
        )
        
        logger.info("Health check completed: %s", response.status)
        return response
        
    except Exception as e:
        logger.error("Health check failed: %s", sanitize_message(str(e)), exc_info=True)
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            database_status="error",
            openai_status="error"
        )


@app.post("/api/admin/reindex", response_model=ReindexResponse)
async def reindex_vector_db(request: Request):
    """Re-index vector database from markdown sources."""
    token = request.headers.get("X-Admin-Token")
    if not settings.reindex_token:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Reindexing is not configured."
        )
    if not token or token != settings.reindex_token.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token."
        )

    info_source_dir = Path(settings.info_source_path)
    if not info_source_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Info source path not found: {settings.info_source_path}"
        )

    try:
        vector_manager = VectorDBManager(
            db_path=settings.chroma_db_path,
            collection_name="markdown_rag",
            openai_api_key=settings.openai_api_key.get_secret_value(),
        )
        await vector_manager.initialize()
        result = await vector_manager.re_index(str(info_source_dir))
        await vector_manager.close()
        return ReindexResponse(
            status=result["status"],
            message=result["message"],
            chunks_processed=result["chunks_processed"],
        )
    except Exception as e:
        logger.error("Reindex failed: %s", sanitize_message(str(e)), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-index vector database."
        )
class ReindexResponse(BaseModel):
    status: str
    message: str
    chunks_processed: int
