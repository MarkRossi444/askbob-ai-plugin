from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "WiseOldMan.Ai"
    debug: bool = False
    log_level: str = "INFO"

    # AI
    anthropic_api_key: str = ""

    # Embeddings
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"

    # Database
    database_url: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Rate limiting
    rate_limit_per_minute: int = 20

    # CORS — comma-separated origins, or "*" for open access
    # For production, replace with specific domains (e.g. "https://wiseoldman.ai")
    allowed_origins: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()
