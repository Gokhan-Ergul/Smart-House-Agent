"""Centralized settings: env vars, paths, and LLM factory."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.5, alias="GEMINI_TEMPERATURE")

    smart_house_api_url: str = Field(
        default="http://127.0.0.1:242",
        alias="SMART_HOUSE_API_URL",
    )

    home_status_path: Path = Field(
        default_factory=lambda: _project_root() / "home_status.json",
        alias="HOME_STATUS_PATH",
    )
    user_memory_path: Path = Field(
        default_factory=lambda: _project_root() / "user_memory.txt",
        alias="USER_MEMORY_PATH",
    )
    rules_operations_path: Path = Field(
        default_factory=lambda: _project_root() / "rules_operations.json",
        alias="RULES_OPERATIONS_PATH",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_llm(settings: Settings | None = None) -> ChatGoogleGenerativeAI:
    settings = settings or get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=settings.gemini_temperature,
    )


def configure_logging(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
