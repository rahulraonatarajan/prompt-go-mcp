from __future__ import annotations
from dataclasses import dataclass
import os


def _get_bool(env_name: str, default: bool) -> bool:
    val = os.getenv(env_name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./promptgo.db")
    org: str = os.getenv("PG_ORG", "offlyn.ai")
    allow_web: bool = _get_bool("PG_ALLOW_WEB", False)
    budget_mode: str = os.getenv("PG_BUDGET_MODE", "observe")


def get_settings() -> Settings:
    return Settings()

