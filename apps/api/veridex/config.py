from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from veridex.domain.taxonomy import repo_root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERIDEX_", extra="ignore")

    database_url: str = "postgresql+psycopg://veridex:veridex@localhost:5433/veridex"
    storage_root: Path = Path("storage")
    cors_origins: str = "http://localhost:3000"
    detector: str = "yolo"
    ocr: str = "paddle"
    weights_path: Path = Path("weights/yolo.pt")
    allow_unreviewed_model: bool = False
    max_upload_bytes: int = 500_000_000
    max_duration_ms: int = 600_000
    pipeline_version: str = "1"

    @property
    def repo(self) -> Path:
        return repo_root()

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings()


def config_dir() -> Path:
    return Path(__file__).resolve().parent / "pipeline" / "config"
