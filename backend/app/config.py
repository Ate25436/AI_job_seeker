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
    cors_allow_origins: list[str] = Field(default_factory=list)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(valid_levels))}")
        return normalized

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def apply_environment_defaults(self):
        if self.environment in {"development", "test"}:
            if not self.cors_allow_origins:
                self.cors_allow_origins = ["*"]
        else:
            if not self.cors_allow_origins:
                raise ValueError("CORS_ALLOW_ORIGINS is required in production/staging")
            if "*" in self.cors_allow_origins:
                raise ValueError("CORS_ALLOW_ORIGINS cannot include '*' in production/staging")
        return self


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
        "cors_allow_origins": settings.cors_allow_origins,
        "openai_api_key": mask_secret(settings.openai_api_key),
    }


def get_settings() -> Settings:
    return Settings()
