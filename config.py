from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM Backend (vLLM)
    LM_STUDIO_URL: str = "http://localhost:8000/v1/completions"
    LM_MODEL: str = "TinyLlama/TinyLlama-1.1B-Chat-v0.4"

    # 🔥 VULNERABILITY: Hardcoded secret key — discoverable via /docs or source
    SECRET_KEY: str = "vertex-brain-secret-key-change-in-production-2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Paths
    BASE_DIR: Path = Path(__file__).parent
    UPLOAD_DIR: Path = Path(__file__).parent / "uploads"
    DB_PATH: str = "sqlite+aiosqlite:///./vertex_brain.db"
    CHROMA_DIR: str = "./chroma_store"

    # RAG
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K_RESULTS: int = 5

    # App
    APP_NAME: str = "VertexBrain"
    VERSION: str = "2.0.0"

    class Config:
        env_file = ".env"


settings = Settings()
settings.UPLOAD_DIR.mkdir(exist_ok=True)