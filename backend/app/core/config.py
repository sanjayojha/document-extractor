from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str

    # Storage
    storage_dir: str = "./storage"

    # Upload validation
    max_upload_size_mb: int = 10
    allowed_content_types: list[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
    ]

    # LLM (used from Phase 2 onward)
    openai_api_key: str = ""


settings = Settings()