"""Workers package for AI Photos Management."""

from importlib import import_module
from typing import Any

from .celery_app import app

__all__ = [
    "app",
    "process_single_image",
    "ai_models",
    "initialize_models",
    "warmup_models",
    "recognize_objects",
    "generate_image_embedding",
    "generate_text_embedding",
    "extract_text",
    "detect_faces",
    "calculate_pdq_hash",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin lazy importer
    if name == "process_single_image":
        from .tasks import process_single_image

        return process_single_image

    if name == "ai_models":
        return import_module(".ai_models", __name__)

    if name in {
        "initialize_models",
        "warmup_models",
        "recognize_objects",
        "generate_image_embedding",
        "generate_text_embedding",
        "extract_text",
        "detect_faces",
        "calculate_pdq_hash",
    }:
        module = import_module(".ai_models", __name__)
        return getattr(module, name)

    raise AttributeError(f"module 'workers' has no attribute {name!r}")

