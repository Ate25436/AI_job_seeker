"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
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
