"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application settings"""
    
    # Project
    PROJECT_NAME: str = "Fund Performance Analysis System"
    VERSION: str = "1.0.0"
    
    # API
    API_V1_STR: str = "/api"
    
    # CORS
    # Default to standard dev origins; override via .env with JSON list, e.g.:
    # ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_allowed_origins(cls, v):
        """Allow env to provide JSON list, comma-separated string, or empty.

        - Empty/None: fallback to default dev origins
        - JSON string: parse into list
        - Comma-separated: split and strip
        """
        if v is None:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["http://localhost:3000", "http://127.0.0.1:3000"]
            # Try JSON list first
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            # Fallback to comma-separated
            return [item.strip() for item in s.split(",") if item.strip()]
        return v
    
    # Database
    DATABASE_URL: str = "postgresql://funduser:fundpass@localhost:5432/funddb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Anthropic (optional)
    ANTHROPIC_API_KEY: str = ""
    
    # Vector Store
    VECTOR_STORE_PATH: str = "./vector_store"
    FAISS_INDEX_PATH: str = "./faiss_index"
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Document Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # RAG
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
