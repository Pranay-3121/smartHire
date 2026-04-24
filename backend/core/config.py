from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Resume Ranker"
    app_version: str = "1.0.0"
    debug: bool = False

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout: int = 60
    ollama_max_retries: int = 1

    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "resume_embeddings"

    upload_dir: str = "./uploads"
    export_dir: str = "./exports"

    max_file_size_mb: int = 10
    allowed_extensions: list[str] = ["pdf", "docx", "txt"]

    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure required directories exist
for _dir in [settings.upload_dir, settings.export_dir, Path(settings.log_file).parent, settings.chroma_persist_dir]:
    Path(_dir).mkdir(parents=True, exist_ok=True)
