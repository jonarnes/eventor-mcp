from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration (env / .env)."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    eventor_base_url: str = Field(
        default="https://eventor.orientering.no",
        validation_alias="EVENTOR_BASE_URL",
    )
    eventor_api_key: str = Field(default="", validation_alias="EVENTOR_API_KEY")
    eventor_api_key_header: str = Field(default="ApiKey", validation_alias="EVENTOR_API_KEY_HEADER")
    eventor_timeout_seconds: float = Field(default=30.0, validation_alias="EVENTOR_TIMEOUT_SECONDS")

    cache_enabled: bool = Field(default=True, validation_alias="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(default=300, ge=0, validation_alias="CACHE_TTL_SECONDS")
    cache_max_entries: int = Field(default=256, ge=1, validation_alias="CACHE_MAX_ENTRIES")

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_dir: Path | None = Field(default=None, validation_alias="LOG_DIR")
    log_rotation_when: Literal[
        "S", "M", "H", "D", "W0", "W1", "W2", "W3", "W4", "W5", "W6", "midnight"
    ] = Field(default="midnight", validation_alias="LOG_ROTATION_WHEN")
    log_backup_count: int = Field(default=14, ge=0, validation_alias="LOG_BACKUP_COUNT")

    stats_max_date_range_days: int = Field(default=730, ge=1, validation_alias="STATS_MAX_DATE_RANGE_DAYS")
    stats_max_events_in_summary: int = Field(
        default=500, ge=1, validation_alias="STATS_MAX_EVENTS_IN_SUMMARY"
    )

    @field_validator("eventor_base_url")
    @classmethod
    def strip_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def upper_level(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def api_key_and_header_sanity(self) -> Settings:
        """
        Common .env mistake: paste the API key into EVENTOR_API_KEY_HEADER and leave
        EVENTOR_API_KEY empty. Eventor keys are typically 32 hex chars; the header
        name is usually the literal ``ApiKey`` (see Eventor API guide).
        """

        key = self.eventor_api_key.strip()
        hdr = self.eventor_api_key_header.strip()

        if not key and _looks_like_eventor_api_key_token(hdr):
            raise ValueError(
                "EVENTOR_API_KEY is empty, but EVENTOR_API_KEY_HEADER looks like your API key "
                f"({hdr[:8]}…). Put that value in EVENTOR_API_KEY and set "
                "EVENTOR_API_KEY_HEADER=ApiKey (unless your Eventor documentation says otherwise)."
            )
        return self


def _looks_like_eventor_api_key_token(s: str) -> bool:
    """Heuristic: Eventor organisation API keys are often 32 hex digits (no dashes)."""

    if re.fullmatch(r"[0-9a-fA-F]{32}", s):
        return True
    if re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        s,
    ):
        return True
    return False
