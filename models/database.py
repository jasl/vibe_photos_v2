"""
SQLAlchemy ORM models for AI Photos Management system.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Text, JSON, Index, BigInteger, Enum as SQLEnum,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
import enum

from config import settings

Base = declarative_base()


class PhotoState(str, enum.Enum):
    """Photo processing states."""
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    PROCESSING_OBJECTS = "processing_objects"
    PROCESSING_EMBEDDINGS = "processing_embeddings"
    PROCESSING_OCR = "processing_ocr"
    PROCESSING_FACES = "processing_faces"
    PROCESSING_HASH = "processing_hash"
    CHECKING_DUPLICATES = "checking_duplicates"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class Photo(Base):
    """Photo table storing image metadata and processing state."""
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(512), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    thumbnail_path = Column(String(512), nullable=True)
    state = Column(SQLEnum(PhotoState), default=PhotoState.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    detected_objects = relationship("DetectedObject", back_populates="photo", cascade="all, delete-orphan")
    photo_tags = relationship("PhotoTag", back_populates="photo", cascade="all, delete-orphan")
    semantic_embedding = relationship("SemanticEmbedding", back_populates="photo", uselist=False, cascade="all, delete-orphan")
    ocr_text = relationship("OCRText", back_populates="photo", uselist=False, cascade="all, delete-orphan")
    faces = relationship("Face", back_populates="photo", cascade="all, delete-orphan")
    photo_hash = relationship("PhotoHash", back_populates="photo", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Photo(id={self.id}, filename={self.filename}, state={self.state.value})>"


class Category(Base):
    """Category table for organizing detected objects."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tag_mappings = relationship("TagCategoryMapping", back_populates="category", cascade="all, delete-orphan")
    detected_objects = relationship("DetectedObject", back_populates="category")
    photo_tags = relationship("PhotoTag")

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class TagCategoryMapping(Base):
    """Mapping table for tags to categories."""
    __tablename__ = "tag_category_mappings"

    id = Column(Integer, primary_key=True, index=True)
    tag = Column(String(100), nullable=False, unique=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Relationships
    category = relationship("Category", back_populates="tag_mappings")

    def __repr__(self):
        return f"<TagCategoryMapping(tag={self.tag}, category_id={self.category_id})>"


class DetectedObject(Base):
    """Detected objects in photos with confidence scores."""
    __tablename__ = "detected_objects"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    tag = Column(String(100), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    bbox = Column(JSON, nullable=True)  # {x1, y1, x2, y2} from DETR

    # Relationships
    photo = relationship("Photo", back_populates="detected_objects")
    category = relationship("Category", back_populates="detected_objects")

    __table_args__ = (
        Index("idx_detected_objects_photo_tag", "photo_id", "tag"),
    )

    def __repr__(self):
        return f"<DetectedObject(photo_id={self.photo_id}, tag={self.tag}, confidence={self.confidence:.2f})>"


class PhotoTag(Base):
    """Unique tags per photo for efficient search and display."""
    __tablename__ = "photo_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    tag = Column(String(100), nullable=False, index=True)
    confidence = Column(Float, nullable=False)  # Highest confidence for this tag
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    
    # Relationships
    photo = relationship("Photo", back_populates="photo_tags")
    category = relationship("Category")
    
    __table_args__ = (
        UniqueConstraint("photo_id", "tag", name="uq_photo_tag"),
        Index("idx_photo_tags_tag", "tag"),
    )
    
    def __repr__(self):
        return f"<PhotoTag(photo_id={self.photo_id}, tag={self.tag}, confidence={self.confidence:.2f})>"


class SemanticEmbedding(Base):
    """Semantic embeddings for photos (OpenCLIP vectors)."""
    __tablename__ = "semantic_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, unique=True, index=True)
    embedding = Column(Vector(1024), nullable=False)  # OpenCLIP ViT-H-14 = 1024-dim
    model_version = Column(String(100), nullable=False, default="ViT-H-14/laion2b_s32b_b79k")

    # Relationships
    photo = relationship("Photo", back_populates="semantic_embedding")

    def __repr__(self):
        return f"<SemanticEmbedding(photo_id={self.photo_id}, model={self.model_version})>"


class OCRText(Base):
    """OCR extracted text from photos."""
    __tablename__ = "ocr_texts"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, unique=True, index=True)
    extracted_text = Column(Text, nullable=False)
    language = Column(String(10), nullable=True, default="en")
    ts_vector = Column(TSVECTOR, nullable=True)  # PostgreSQL full-text search

    # Relationships
    photo = relationship("Photo", back_populates="ocr_text")

    __table_args__ = (
        Index("idx_ocr_texts_ts_vector", "ts_vector", postgresql_using="gin"),
    )

    def __repr__(self):
        text_preview = self.extracted_text[:50] + "..." if len(self.extracted_text) > 50 else self.extracted_text
        return f"<OCRText(photo_id={self.photo_id}, text='{text_preview}')>"


class Face(Base):
    """Detected faces in photos with embeddings."""
    __tablename__ = "faces"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    bbox = Column(JSON, nullable=False)  # {"x": int, "y": int, "width": int, "height": int}
    embedding = Column(Vector(512), nullable=False)  # InsightFace buffalo_l = 512-dim
    cluster_id = Column(Integer, nullable=True, index=True)  # For future face clustering

    # Relationships
    photo = relationship("Photo", back_populates="faces")

    def __repr__(self):
        return f"<Face(id={self.id}, photo_id={self.photo_id}, cluster_id={self.cluster_id})>"


class PhotoHash(Base):
    """Perceptual hash for photos (PDQ hash)."""
    __tablename__ = "photo_hashes"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, unique=True, index=True)
    pdq_hash = Column(String(64), nullable=False, index=True)  # PDQ hash as hex string
    quality_score = Column(Float, nullable=True)

    # Relationships
    photo = relationship("Photo", back_populates="photo_hash")

    def __repr__(self):
        return f"<PhotoHash(photo_id={self.photo_id}, hash={self.pdq_hash[:16]}...)>"


class Duplicate(Base):
    """Duplicate photos detected by hash similarity."""
    __tablename__ = "duplicates"

    id = Column(Integer, primary_key=True, index=True)
    photo_id_1 = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    photo_id_2 = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    hamming_distance = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_duplicates_photos", "photo_id_1", "photo_id_2"),
    )

    def __repr__(self):
        return f"<Duplicate(photo_1={self.photo_id_1}, photo_2={self.photo_id_2}, distance={self.hamming_distance})>"


# Database initialization functions

def get_engine():
    """Create SQLAlchemy engine."""
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.FLASK_DEBUG,
        pool_pre_ping=True,
        pool_size=20,  # Increased for web app concurrent requests
        max_overflow=40,  # Allow bursts of connections
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_timeout=30  # Timeout for getting connection from pool
    )


def init_db():
    """Initialize database tables and pgvector extension."""
    from sqlalchemy import text
    
    engine = get_engine()
    
    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def get_session() -> Session:
    """Get database session."""
    engine = get_engine()
    return Session(engine)


def drop_all_tables():
    """Drop all tables (use with caution!)."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped")

