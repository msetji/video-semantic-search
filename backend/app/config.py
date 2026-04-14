from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    media_root: Path = Field(default_factory=lambda: _repo_root() / "data")
    faiss_index_path: Path = Field(
        default_factory=lambda: _repo_root() / "backend" / "database" / "faiss.index"
    )
    sqlite_metadata_path: Path = Field(
        default_factory=lambda: _repo_root() / "backend" / "database" / "metadata.sqlite"
    )
    # One-time migration: if present and SQLite missing, rows are imported when FAISS loads.
    legacy_metadata_json_path: Path = Field(
        default_factory=lambda: _repo_root() / "backend" / "database" / "metadata.json"
    )
    max_frames_per_video: int = Field(
        default=7200,
        description="Max sampled frames per MP4 at 1 FPS (~2 hours); longer clips are truncated.",
    )
    clip_model_id: str = "openai/clip-vit-base-patch32"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])


settings = Settings()
