"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Core ---
    HERALD_SECRET: str = "changeme"  # Admin login password & cookie signing key
    DATABASE_URL: str = "sqlite:///data/herald.db"
    RATE_LIMIT_PER_MINUTE: int = 60  # Webhook rate limit per IP or API key

    # --- SMTP ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
