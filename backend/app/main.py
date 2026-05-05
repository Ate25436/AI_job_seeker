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
from .models import (
    AnswerResponse,
    CandidateBriefingResponse,
    CandidateBriefingSection,
    ErrorResponse,
    EvaluationCriterionResponse,
    GameBriefingResponse,
    GameAnswerResponse,
    GameEndRequest,
    GameEndResponse,
    GameQuestionRequest,
    GameResultResponse,
    GameSessionResponse,
    GameStartRequest,
    HealthResponse,
    CompanyBriefingResponse,
    QuestionRequest,
    ScoreSubmissionRequest,
    ScoreSubmissionResponse,
)
from .services.game_session_service import GameSessionService
from .services.rag_service import RAGService
from .services.scenario_service import CATEGORY_LABELS, COMPETENCY_DEFINITIONS, ScenarioService
from .services.vector_db_manager import VectorDBManager
from .security import sanitize_message

# Global RAG service instance
rag_service = None
scenario_service = ScenarioService()
game_session_service = GameSessionService()
settings = get_settings()

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)


def _ensure_rag_service_available() -> RAGService:
    global rag_service

    if not rag_service:
        logger.error("RAG service not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please try again later.",
        )
    return rag_service


def _build_answer_response(result: dict) -> AnswerResponse:
    return AnswerResponse(
        answer=result["answer"],
        sources=result["sources"],
        timestamp=datetime.fromisoformat(result["timestamp"]),
        processing_time_ms=result["processing_time_ms"],
    )


async def _generate_general_answer(
    question: str,
    history: list[dict] | None,
    scenario_id: str | None,
) -> AnswerResponse:
    service = _ensure_rag_service_available()
    result = await service.generate_answer(question, history=history, scenario_id=scenario_id)
    return _build_answer_response(result)


async def _generate_game_answer(session_id: str, question: str) -> GameAnswerResponse:
    service = _ensure_rag_service_available()
    session = game_session_service.require_session(session_id)
    history = game_session_service.build_history_payload(session_id)
    scenario_id = session["scenario"]["scenario_meta"]["scenario_id"]
    result = await service.generate_answer(
        question,
        history=history,
        scenario_id=scenario_id,
    )
    session = game_session_service.append_turn(session_id, question, result["answer"])
    return GameAnswerResponse(
        session_id=session_id,
        status=session["status"],
        remaining_seconds=game_session_service._remaining_seconds(session),
        answer=result["answer"],
        sources=result["sources"],
        timestamp=datetime.fromisoformat(result["timestamp"]),
        processing_time_ms=result["processing_time_ms"],
    )


def _build_game_briefing_response(scenario: dict) -> GameBriefingResponse:
    candidate_profile = scenario["candidate_profile"]
    company_profile = scenario["company_profile"]
    candidate_name = candidate_profile["full_name"]

    entry_sheet_sections = [
        CandidateBriefingSection(
            title="志望動機を教えてください。",
            summary=(
                f"私が{company_profile['company_name']}を志望する理由は、{company_profile['philosophy']}という理念のもとで、"
                f"{company_profile['job_role']}として価値を出せる環境に魅力を感じているからです。"
                f"もともと{candidate_profile['desired_industry']}を志望しており、大学で学ぶ中で技術を実際の課題解決につなげたいと考えるようになりました。"
                f"その中で、{', '.join(company_profile['business_areas'][:2])}など幅広い領域に取り組み、対話を通じて開発を進める姿勢に強く惹かれました。"
                f"入社後は、技術を学び続けながら社会実装に関わり、チームの中で着実に開発を進めることで会社に貢献したいと考えています。"
            ),
        ),
        CandidateBriefingSection(
            title="学生時代に力を入れたことを教えてください。",
            summary=(
                "学生時代に最も力を入れたのは学園祭の出店企画です。"
                "準備の初期段階では役割分担が曖昧で全体の動きが止まりがちだったため、"
                "私は自分から企画案と担当表を作成してメンバーに提案し、議論の土台を整えました。"
                "その後も進捗共有や必要な声かけを続け、準備を前に進めることを意識しました。"
                "この経験で、状況が停滞している時でも自分から動き、周囲を巻き込みながら物事を進める力を身につけました。"
                "業務でも、曖昧な状況を整理しながら主体的に行動し、チームの前進に貢献したいと考えています。"
            ),
        ),
        CandidateBriefingSection(
            title="チームワークを発揮した経験を教えてください。",
            summary=(
                "チームワークを発揮した経験として、学園祭準備や学内の開発活動での進捗共有と役割調整があります。"
                "私は自分の作業を進めるだけでなく、状況を見ながら必要な情報を分かりやすく共有し、"
                "参加が遅れているメンバーには個別に声をかけていました。技術に詳しくない相手にも伝わるよう言葉を選び、"
                "一度相手の意見を聞いた上で調整することを意識しました。"
                "この経験から、相手に合わせた情報共有と役割調整がチームの成果につながることを学びました。"
                "業務でも、周囲と連携しながら状況を整え、チーム全体が動きやすい環境づくりに貢献したいと考えています。"
            ),
        ),
    ]

    evaluation_criteria = [
        EvaluationCriterionResponse(
            competency_id=competency_id,
            label=definition["label"],
            category_id=definition["category_id"],
            category_label=CATEGORY_LABELS[definition["category_id"]],
            question_tags=list(definition["question_tags"]),
            high_signal=definition["high_signal"],
            low_signal=definition["low_signal"],
        )
        for competency_id, definition in COMPETENCY_DEFINITIONS.items()
    ]

    return GameBriefingResponse(
        scenario_title=scenario["scenario_meta"]["title"],
        candidate_profile=CandidateBriefingResponse(
            full_name=candidate_profile["full_name"],
            age=candidate_profile["age"],
            university=candidate_profile["university"],
            faculty_type=candidate_profile["faculty_type"],
            grade=candidate_profile["grade"],
            desired_industry=candidate_profile["desired_industry"],
            desired_job_family=candidate_profile["desired_job_family"],
            current_status_summary=candidate_profile["current_status_summary"],
            personality_summary=candidate_profile["personality_summary"],
            entry_sheet_sections=entry_sheet_sections,
        ),
        company_profile=CompanyBriefingResponse(
            company_name=company_profile["company_name"],
            industry=company_profile["industry"],
            philosophy=company_profile["philosophy"],
            business_areas=list(company_profile["business_areas"]),
            job_role=company_profile["job_role"],
            ideal_candidate_traits=list(company_profile["ideal_candidate_traits"]),
            candidate_fit_points=list(company_profile["candidate_fit_points"]),
        ),
        evaluation_criteria=evaluation_criteria,
    )

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
                    try:
                        await vector_manager.initialize()
                        await vector_manager.initialize_from_markdown(str(info_source_dir))
                    finally:
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

# Response model for re-indexing endpoint
class ReindexResponse(BaseModel):
    status: str
    message: str
    chunks_processed: int

# CORS configuration for web browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
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
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
    _ensure_rag_service_available()

    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty or contain only whitespace."
            )

        if settings.environment == "development":
            logger.info(
                "Processing general question: %s... (scenario_id=%s)",
                question[:100],
                request.scenario_id or "none",
            )
        else:
            logger.info(
                "Processing general question with length: %s (scenario_id=%s)",
                len(question),
                request.scenario_id or "none",
            )

        response = await _generate_general_answer(
            question,
            history=request.history,
            scenario_id=request.scenario_id,
        )

        logger.info("General question processed successfully in %sms", response.processing_time_ms)
        return response

    except HTTPException:
        raise
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


@app.get("/api/game/briefing", response_model=GameBriefingResponse)
async def get_game_briefing(scenario_file: str = "frontiersoft_taro.yaml"):
    """Get pre-interview briefing data for the home screen."""
    try:
        scenario = scenario_service.load_fixed_scenario(scenario_file)
        return _build_game_briefing_response(scenario)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/api/game/start", response_model=GameSessionResponse)
async def start_game_session(request: GameStartRequest):
    """Start a new interviewer training session."""
    try:
        if request.scenario_mode == "generated":
            scenario = scenario_service.generate_scenario(seed=request.seed)
        else:
            scenario = scenario_service.load_fixed_scenario(request.scenario_file)

        session = game_session_service.start_session(scenario)
        return GameSessionResponse(
            session_id=session["session_id"],
            status=session["status"],
            started_at=session["started_at"],
            expires_at=session["expires_at"],
            candidate_name=scenario["candidate_profile"]["full_name"],
            company_name=scenario["company_profile"]["company_name"],
            scenario_title=scenario["scenario_meta"]["title"],
            remaining_seconds=game_session_service._remaining_seconds(session),
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/api/game/ask", response_model=GameAnswerResponse)
async def ask_game_question(request: GameQuestionRequest):
    """Ask a question within an active game session."""
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty or contain only whitespace.",
            )

        response = await _generate_game_answer(request.session_id, question)
        logger.info(
            "Game question processed successfully in %sms for session %s",
            response.processing_time_ms,
            request.session_id,
        )
        return response
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@app.post("/api/game/end", response_model=GameEndResponse)
async def end_game_session(request: GameEndRequest):
    """End an active game session manually."""
    try:
        session = game_session_service.end_session(request.session_id, reason="manual")
        return GameEndResponse(
            session_id=session["session_id"],
            status=session["status"],
            ended_at=session["ended_at"],
            end_reason=session["end_reason"],
            remaining_seconds=0,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        ) from exc


@app.post("/api/game/score", response_model=ScoreSubmissionResponse)
async def submit_game_score(request: ScoreSubmissionRequest):
    """Submit interviewer scores after the session ends."""
    expected_keys = set(COMPETENCY_DEFINITIONS.keys())
    if set(request.scores.keys()) != expected_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scores must contain all competency ids exactly once.",
        )
    invalid_scores = [key for key, value in request.scores.items() if not isinstance(value, int) or value < 1 or value > 5]
    if invalid_scores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scores must be integers from 1 to 5. Invalid keys: {invalid_scores}",
        )

    try:
        session = game_session_service.submit_scores(request.session_id, request.scores)
        return ScoreSubmissionResponse(
            session_id=session["session_id"],
            status=session["status"],
            submitted_at=session["score_submitted_at"],
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@app.get("/api/game/result/{session_id}", response_model=GameResultResponse)
async def get_game_result(session_id: str):
    """Get the current session result snapshot."""
    try:
        result = game_session_service.build_result(session_id)
        return GameResultResponse(**result)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        ) from exc


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
        try:
            await vector_manager.initialize()
            result = await vector_manager.re_index(str(info_source_dir))
        finally:
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
