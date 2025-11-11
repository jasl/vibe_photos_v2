"""Models package for AI Photos Management."""

from .database import (
    Base,
    Photo,
    Category,
    TagCategoryMapping,
    DetectedObject,
    PhotoTag,
    SemanticEmbedding,
    OCRText,
    Face,
    PhotoHash,
    Duplicate,
    PhotoState,
    get_engine,
    get_session,
    init_db,
    drop_all_tables
)

from .schemas import (
    PhotoBase,
    PhotoCreate,
    PhotoResponse,
    PhotoDetailResponse,
    PhotoTagResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    StatsResponse,
    CategoryResponse
)

__all__ = [
    # Database models
    "Base",
    "Photo",
    "Category",
    "TagCategoryMapping",
    "DetectedObject",
    "PhotoTag",
    "SemanticEmbedding",
    "OCRText",
    "Face",
    "PhotoHash",
    "Duplicate",
    "PhotoState",
    # Database functions
    "get_engine",
    "get_session",
    "init_db",
    "drop_all_tables",
    # Pydantic schemas
    "PhotoBase",
    "PhotoCreate",
    "PhotoResponse",
    "PhotoDetailResponse",
    "PhotoTagResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
    "StatsResponse",
    "CategoryResponse",
]

