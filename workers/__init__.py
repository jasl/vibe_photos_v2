"""Workers package for AI Photos Management."""

from .celery_app import app
from .tasks import process_single_image
from .ai_models import (
    initialize_models,
    warmup_models,
    recognize_objects,
    generate_image_embedding,
    generate_text_embedding,
    extract_text,
    detect_faces,
    calculate_pdq_hash
)

__all__ = [
    "app",
    "process_single_image",
    "initialize_models",
    "warmup_models",
    "recognize_objects",
    "generate_image_embedding",
    "generate_text_embedding",
    "extract_text",
    "detect_faces",
    "calculate_pdq_hash",
]

