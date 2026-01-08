"""
Configuration management for the application
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    chroma_db_path: str = "./chroma_db"
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()