"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class PhotoBase(BaseModel):
    """Base photo schema."""
    filename: str
    file_path: str


class PhotoCreate(PhotoBase):
    """Schema for creating a photo."""
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class PhotoResponse(PhotoBase):
    """Schema for photo response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    thumbnail_path: Optional[str] = None
    state: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class PhotoTagResponse(BaseModel):
    """Schema for unique photo tag response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tag: str
    confidence: float
    category_id: Optional[int] = None


class PhotoDetailResponse(PhotoResponse):
    """Schema for detailed photo response with all related data."""
    tags: List[PhotoTagResponse] = []
    ocr_text: Optional[str] = None
    faces_count: int = 0
    has_duplicates: bool = False


class SearchRequest(BaseModel):
    """Schema for search request."""
    query: str
    mode: str = Field(default="hybrid", pattern="^(hybrid|keyword|semantic)$")
    categories: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    show_duplicates: bool = True
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class SearchResultItem(BaseModel):
    """Schema for single search result."""
    photo: PhotoResponse
    score: float
    matched_tags: List[str] = []
    ocr_snippet: Optional[str] = None


class SearchResponse(BaseModel):
    """Schema for search response."""
    results: List[SearchResultItem]
    total: int
    page: int
    page_size: int
    mode: str


class StatsResponse(BaseModel):
    """Schema for processing statistics."""
    total_photos: int
    completed: int
    pending: int
    processing: int
    partial: int
    failed: int
    completion_percentage: float


class CategoryResponse(BaseModel):
    """Schema for category response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    photo_count: int = 0

