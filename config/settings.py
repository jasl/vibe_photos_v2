"""
Configuration management for AI Photos Management system.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import List
import torch
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Database Configuration
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ai_photos")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "photos_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "change_me_in_production")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}"
    )

    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_WORKER_CONCURRENCY: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))

    # Photo Directory Configuration
    PHOTOS_DIR: Path = Path(os.getenv("PHOTOS_DIR", "/home/jasl/datasets/my_photos"))
    # Use absolute path for thumbnails to avoid path resolution issues
    THUMBNAIL_DIR: Path = Path(os.getenv("THUMBNAIL_DIR", str(Path(__file__).parent.parent / "data" / "thumbnails"))).resolve()
    THUMBNAIL_SIZE: int = int(os.getenv("THUMBNAIL_SIZE", "400"))

    # AI Model Configuration
    MODEL_CACHE_DIR: Path = Path(os.getenv("MODEL_CACHE_DIR", "~/.cache/ai_photos_models")).expanduser()
    
    # Auto-detect CUDA availability
    _device_env = os.getenv("DEVICE", "auto")
    if _device_env == "auto":
        DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        DEVICE: str = _device_env

    # Processing Configuration
    DUPLICATE_THRESHOLD: int = int(os.getenv("DUPLICATE_THRESHOLD", "8"))
    SUPPORTED_FORMATS: List[str] = os.getenv(
        "SUPPORTED_FORMATS",
        "jpg,jpeg,png,heic,webp,cr2,nef,dng,arw,raw"
    ).split(",")

    # Object detection filtering
    NOISY_DETECTION_TAGS: List[str] = [
        tag.strip()
        for tag in os.getenv("NOISY_DETECTION_TAGS", "person").split(",")
        if tag.strip()
    ]
    NOISY_TAG_MIN_AREA_RATIO: float = float(os.getenv("NOISY_TAG_MIN_AREA_RATIO", "0.02"))
    NOISY_TAG_MIN_CONFIDENCE: float = float(os.getenv("NOISY_TAG_MIN_CONFIDENCE", "0.35"))
    NOISY_TAG_MAX_INSTANCES: int = int(os.getenv("NOISY_TAG_MAX_INSTANCES", "3"))

    # Flask Configuration
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change_me_in_production_to_random_secret")

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # 'json' or 'text'

    # Model-specific settings
    DETR_MODEL_NAME: str = os.getenv("DETR_MODEL_NAME", "facebook/detr-resnet-50")
    OPENCLIP_MODEL_NAME: str = "ViT-H-14"
    OPENCLIP_PRETRAINED: str = "laion2b_s32b_b79k"
    INSIGHTFACE_MODEL_NAME: str = "buffalo_l"
    
    # Search Configuration
    SEARCH_TOP_K: int = int(os.getenv("SEARCH_TOP_K", "100"))
    RRF_K: int = int(os.getenv("RRF_K", "60"))  # Reciprocal Rank Fusion constant

    # Pagination
    GALLERY_PAGE_SIZE: int = int(os.getenv("GALLERY_PAGE_SIZE", "50"))

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        cls.THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        logs_dir = Path("./logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_database_url_async(cls) -> str:
        """Get async database URL for SQLAlchemy 2.0."""
        return cls.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)."""
        print("=" * 60)
        print("AI Photos Management - Configuration")
        print("=" * 60)
        print(f"Photos Directory: {cls.PHOTOS_DIR}")
        print(f"Thumbnail Directory: {cls.THUMBNAIL_DIR}")
        print(f"Model Cache: {cls.MODEL_CACHE_DIR}")
        print(f"Device: {cls.DEVICE}")
        print(f"Duplicate Threshold: {cls.DUPLICATE_THRESHOLD}")
        print(f"Supported Formats: {', '.join(cls.SUPPORTED_FORMATS)}")
        print(f"Celery Workers: {cls.CELERY_WORKER_CONCURRENCY}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("=" * 60)


# Create singleton instance
settings = Settings()

# Ensure directories exist on import
settings.ensure_directories()

