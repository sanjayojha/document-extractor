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

    # LLM (OpenAI)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_request_timeout_seconds: int = 30
    max_llm_input_chars: int = 12000

    # Extraction confidence heuristics
    min_text_confidence: float = 0.35
    field_flag_threshold: float = 0.7
    cross_field_tolerance: float = 0.02

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()