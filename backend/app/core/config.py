from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Sales Inbox Router"
    gemini_api_key: str = "your_gemini_api_key_here"
    candidate_id: str = "candidate@example.com"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "*"

    # Gemini model
    gemini_model: str = "gemini-3.6-flash"


    # Task API settings
    task_api_base_url: str = "http://localhost:8000"
    task_api_timeout_sec: float = 10.0

    # Batch and rate limit settings
    gemini_rpm_limit: int = 15          # free tier: 15 requests per minute
    gemini_batch_size: int = 10         # process N emails in parallel
    gemini_batch_delay_sec: float = 4.0 # seconds between batches
    gemini_max_retries: int = 3
    gemini_retry_base_delay: float = 2.0

    @property
    def candidate_id_normalized(self) -> str:
        return self.candidate_id.lower().strip()

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_all(self) -> None:
        """Call at startup. Logs or raises warnings if critical configs are missing."""
        errors = []
        if not self.gemini_api_key or self.gemini_api_key == "your_gemini_api_key_here":
            if self.environment == "production":
                errors.append("GEMINI_API_KEY is not set")
        if "@" not in self.candidate_id:
            errors.append("CANDIDATE_ID must be a valid email address")
        if errors:
            raise RuntimeError(f"Invalid configuration:\n" + "\n".join(f"  - {e}" for e in errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()
