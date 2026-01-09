"""
FastAPI main application entry point
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import get_settings
from .models import QuestionRequest, AnswerResponse, HealthResponse, ErrorResponse
from .services.rag_service import RAGService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global RAG service instance
rag_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global rag_service
    
    # Startup
    logger.info("Starting AI Job Seeker API...")
    settings = get_settings()
    
    try:
        rag_service = RAGService(chroma_db_path=settings.chroma_db_path)
        await rag_service.initialize()
        logger.info("RAG service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG service: {e}")
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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed error messages."""
    logger.warning(f"Validation error for {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message=f"Invalid request data: {str(exc)}",
            timestamp=datetime.now()
        ).model_dump(mode='json')
    )

# Global exception handler for HTTP exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    logger.error(f"HTTP error {exc.status_code} for {request.url}: {exc.detail}")
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
    logger.error(f"Unexpected error for {request.url}: {exc}", exc_info=True)
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
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
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
        
        logger.info(f"Processing question: {question[:100]}...")
        
        # Generate answer using RAG service
        result = await rag_service.generate_answer(question, history=request.history)
        
        # Create response
        response = AnswerResponse(
            answer=result["answer"],
            sources=result["sources"],
            timestamp=datetime.fromisoformat(result["timestamp"]),
            processing_time_ms=result["processing_time_ms"]
        )
        
        logger.info(f"Question processed successfully in {result['processing_time_ms']}ms")
        return response
        
    except ValueError as e:
        logger.warning(f"Invalid question input: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"RAG service runtime error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is temporarily unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error processing question: {e}", exc_info=True)
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
        
        logger.info(f"Health check completed: {response.status}")
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            database_status="error",
            openai_status="error"
        )