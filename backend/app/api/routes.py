"""
API route definitions
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.post("/ask")
async def ask_question():
    # Placeholder for question endpoint
    return {"message": "Question endpoint placeholder"}

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.post("/reindex")
async def reindex_database():
    # Placeholder for reindex endpoint
    return {"message": "Reindex endpoint placeholder"}