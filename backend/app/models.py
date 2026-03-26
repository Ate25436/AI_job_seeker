"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import datetime


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    history: Optional[List[ChatMessage]] = None


class AnswerResponse(BaseModel):
    answer: str
    sources: List[str] = []
    timestamp: datetime
    processing_time_ms: int


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database_status: str = "unknown"
    openai_status: str = "unknown"


class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime


class GameStartRequest(BaseModel):
    scenario_mode: Literal["fixed", "generated"] = "fixed"
    scenario_file: str = "frontiersoft_taro.yaml"
    seed: Optional[int] = None


class GameSessionResponse(BaseModel):
    session_id: str
    status: str
    started_at: datetime
    expires_at: datetime
    candidate_name: str
    company_name: str
    scenario_title: str
    remaining_seconds: int


class GameQuestionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=1000)


class GameAnswerResponse(AnswerResponse):
    session_id: str
    status: str
    remaining_seconds: int


class GameEndRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class GameEndResponse(BaseModel):
    session_id: str
    status: str
    ended_at: datetime
    end_reason: str
    remaining_seconds: int


class ScoreSubmissionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    scores: Dict[str, int]


class ScoreSubmissionResponse(BaseModel):
    session_id: str
    status: str
    submitted_at: datetime


class GameResultResponse(BaseModel):
    session_id: str
    status: str
    started_at: datetime
    expires_at: datetime
    ended_at: Optional[datetime] = None
    end_reason: Optional[str] = None
    candidate_name: str
    company_name: str
    scenario_title: str
    answer_count: int
    remaining_seconds: int
    score_submitted: bool
    submitted_scores: Optional[Dict[str, int]] = None
    correct_scores: Optional[Dict[str, int]] = None
    score_diffs: Optional[Dict[str, int]] = None
    category_balance: Optional[Dict[str, str]] = None
