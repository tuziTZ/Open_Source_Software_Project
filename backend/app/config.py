from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MERCURY_", env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".mercury")
    db_path: Path | None = None
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    def resolved_db_path(self) -> Path:
        return self.db_path or (self.data_dir / "mercury.db")


settings = Settings()
