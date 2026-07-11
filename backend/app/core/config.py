"""
Centralized application configuration.

Uses pydantic-settings so every tunable pipeline parameter (see PRD section 6.3)
can be overridden via environment variables without touching code - important
for tuning the highlight-detection algorithm quickly during the hackathon.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CLIPCOACH_", extra="ignore")

    # --- General ---
    app_name: str = "ClipCoach API"
    environment: str = "development"
    debug: bool = True

    # --- CORS ---
    # Comma-separated list of allowed origins (set via CLIPCOACH_CORS_ORIGINS in prod).
    cors_origins: str = "http://localhost:3000"

    # --- Storage ---
    storage_dir: Path = Path(__file__).resolve().parents[2] / "storage_data"
    max_upload_size_mb: int = 500

    # --- Highlight detection algorithm defaults (PRD 6.3) ---
    analysis_window_seconds: float = 0.5
    min_gap_between_clips_seconds: float = 8.0
    clip_pre_roll_seconds: float = 3.0
    clip_post_roll_seconds: float = 4.0
    target_duration_seconds: float = 90.0
    audio_weight: float = 0.6
    motion_weight: float = 0.4
    # Keep this low — motion only needs a coarse excitement curve, and higher
    # fps dominates runtime on long AV1/H.265 uploads.
    motion_sample_fps: float = 2.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
