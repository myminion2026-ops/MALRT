"""Application configuration loaded from environment / .env file."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VT_API_KEY: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./malrt.db"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = {"env_prefix": "MALRT_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
