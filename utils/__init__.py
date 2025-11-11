"""Utils package for AI Photos Management."""

from .db import get_db_session, execute_with_session
from .image_utils import (
    ImageConversionError,
    convert_to_jpeg,
    generate_thumbnail,
    get_image_dimensions,
    get_file_size,
    process_image_for_storage,
    is_supported_format,
    is_raw_format,
    is_heic_format
)

__all__ = [
    # Database utils
    "get_db_session",
    "execute_with_session",
    # Image utils
    "ImageConversionError",
    "convert_to_jpeg",
    "generate_thumbnail",
    "get_image_dimensions",
    "get_file_size",
    "process_image_for_storage",
    "is_supported_format",
    "is_raw_format",
    "is_heic_format",
]

