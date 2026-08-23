import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # App Information
    APP_NAME: str = "AI Financial Report Analyzer API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server Settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # LLM Settings
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_PRIMARY_MODEL: str = "groq/compound"
    GROQ_FALLBACK_MODELS: str = "groq/compound,openai/gpt-oss-120b,qwen/qwen3.6-27b,groq/compound-mini,llama-3.3-70b-versatile,llama-3.1-8b-instant,llama-3.1-405b-reasoning"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "groq/compound"
    
    # ChromaDB & Vector Store
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_TOP_K: int = 4
    
    # Document Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_SIZE_MB: int = 25
    
    # Firebase Settings
    FIREBASE_CREDENTIALS_PATH: str = "./serviceAccountKey.json"
    FIREBASE_STORAGE_BUCKET: str = ""
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def groq_model_candidates(self) -> List[str]:
        models = [m.strip() for m in self.GROQ_FALLBACK_MODELS.split(",") if m.strip()]
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for m in models:
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton instance."""
    return Settings()
