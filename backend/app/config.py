"""
Configuration management for the application
"""
from typing import Literal
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    openai_api_key: SecretStr = Field(..., min_length=8)
    chroma_db_path: str = "./chroma_db"
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"
    cors_allow_origins_raw: str = Field(default="", validation_alias="CORS_ALLOW_ORIGINS")
    embedding_cache_ttl_seconds: int = 300
    embedding_cache_max_size: int = 256
    retrieval_cache_ttl_seconds: int = 300
    retrieval_cache_max_size: int = 128
    auto_init_vector_db: bool = False
    info_source_path: str = "./information_source"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(valid_levels))}")
        return normalized

    @field_validator(
        "embedding_cache_ttl_seconds",
        "embedding_cache_max_size",
        "retrieval_cache_ttl_seconds",
        "retrieval_cache_max_size",
    )
    @classmethod
    def validate_cache_limits(cls, value: int, info):
        if value < 0:
            raise ValueError(f"{info.field_name} must be >= 0")
        return value

    @model_validator(mode="after")
    def apply_environment_defaults(self):
        origins = parse_cors_allow_origins(self.cors_allow_origins_raw)
        if self.environment in {"development", "test"}:
            return self
        else:
            if not origins:
                raise ValueError("CORS_ALLOW_ORIGINS is required in production/staging")
            if "*" in origins:
                raise ValueError("CORS_ALLOW_ORIGINS cannot include '*' in production/staging")
        return self

    @property
    def cors_allow_origins_list(self) -> list[str]:
        origins = parse_cors_allow_origins(self.cors_allow_origins_raw)
        if not origins and self.environment in {"development", "test"}:
            return ["*"]
        return origins


def parse_cors_allow_origins(raw_value: str | None) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    return list(raw_value)


def mask_secret(value: SecretStr | str | None) -> str:
    if value is None:
        return ""
    secret = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
    if len(secret) <= 4:
        return "****"
    return f"{secret[:2]}****{secret[-2:]}"


def settings_for_log(settings: Settings) -> dict:
    return {
        "environment": settings.environment,
        "chroma_db_path": settings.chroma_db_path,
        "log_level": settings.log_level,
        "cors_allow_origins": settings.cors_allow_origins_list,
        "embedding_cache_ttl_seconds": settings.embedding_cache_ttl_seconds,
        "embedding_cache_max_size": settings.embedding_cache_max_size,
        "retrieval_cache_ttl_seconds": settings.retrieval_cache_ttl_seconds,
        "retrieval_cache_max_size": settings.retrieval_cache_max_size,
        "auto_init_vector_db": settings.auto_init_vector_db,
        "info_source_path": settings.info_source_path,
        "openai_api_key": mask_secret(settings.openai_api_key),
    }


def get_settings() -> Settings:
    return Settings()
