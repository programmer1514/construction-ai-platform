"""Application settings, read from environment variables (.env supported)."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.model: str = os.getenv("LLM_MODEL", "claude-sonnet-5-5").strip()
        self.force_demo: bool = os.getenv("DEMO_MODE", "0").strip().lower() in ("1", "true", "yes")
        self.max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2500"))
        self.timeout: float = float(os.getenv("LLM_TIMEOUT", "60"))
        self.max_image_mb: int = int(os.getenv("MAX_IMAGE_MB", "5"))
        origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        self.cors_origins: list[str] = [o.strip() for o in origins.split(",") if o.strip()]

    @property
    def live(self) -> bool:
        """True only when a real API key is configured and demo mode is not forced."""
        return bool(self.api_key) and not self.force_demo


settings = Settings()
