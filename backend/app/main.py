"""
FastAPI main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Job Seeker API",
    description="RAG-based Q&A system for job seekers",
    version="1.0.0"
)

# CORS configuration for web browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Job Seeker API is running"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}