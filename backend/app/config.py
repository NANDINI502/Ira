"""
Ira Configuration Module
All settings for the local AI assistant
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Ira"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    MODELS_DIR: Path = PROJECT_ROOT / "models"
    DOCUMENTS_DIR: Path = DATA_DIR / "documents"
    CHROMA_DB_DIR: Path = DATA_DIR / "chroma_db"
    
    # Ollama Configuration
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    
    # Models - adjust based on your GPU VRAM
    # 6GB VRAM: llava:7b, 10GB: llava:13b, 24GB: llava:34b
    LLM_MODEL: str = "llava:7b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # Chat Settings
    CONTEXT_WINDOW: int = 4096
    MAX_HISTORY_MESSAGES: int = 20
    TEMPERATURE: float = 0.7
    
    # Voice Settings
    WHISPER_MODEL_PATH: Path = MODELS_DIR / "whisper" / "ggml-base.en.bin"
    PIPER_MODEL_PATH: Path = MODELS_DIR / "piper" / "en_US-amy-medium.onnx"
    PIPER_CONFIG_PATH: Path = MODELS_DIR / "piper" / "en_US-amy-medium.onnx.json"
    VOICE_ENABLED: bool = True
    
    # RAG Settings
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5
    
    # Home Assistant (Optional)
    HOME_ASSISTANT_URL: Optional[str] = None  # e.g., "http://192.168.1.100:8123"
    HOME_ASSISTANT_TOKEN: Optional[str] = None
    
    # Database
    DATABASE_PATH: Path = DATA_DIR / "conversations.db"
    
    # Server
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
