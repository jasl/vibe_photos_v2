# Project Structure

```
ai_photos_management_v2/
│
├── config/                          # Configuration management
│   ├── __init__.py
│   └── settings.py                  # Environment-based settings
│
├── models/                          # Database models
│   ├── __init__.py
│   ├── database.py                  # SQLAlchemy ORM models (9 tables)
│   └── schemas.py                   # Pydantic validation schemas
│
├── workers/                         # Celery workers and AI models
│   ├── __init__.py
│   ├── celery_app.py               # Celery configuration
│   ├── tasks.py                    # Photo processing task with state machine
│   └── ai_models.py                # AI model loading and inference
│
├── services/                        # Business logic
│   ├── __init__.py
│   └── search_service.py           # Hybrid search with RRF fusion
│
├── utils/                           # Utility functions
│   ├── __init__.py
│   ├── db.py                       # Database session management
│   └── image_utils.py              # Image conversion and thumbnails
│
├── webapp/                          # Flask web application
│   ├── app.py                      # Flask app with routes
│   ├── templates/                  # Jinja2 templates
│   │   ├── base.html               # Base template
│   │   ├── index.html              # Photo gallery
│   │   ├── search.html             # Search interface
│   │   ├── photo_detail.html       # Photo details
│   │   └── error.html              # Error page
│   └── static/                     # Static files (CSS, JS)
│
├── scripts/                         # Utility scripts
│   ├── __init__.py
│   ├── download_models.py          # Pre-download AI models
│   ├── seed_categories.py          # Seed categories and tags
│   ├── setup_database.py           # Initialize DB and seed data
│   ├── process_photos.py           # Scan and queue photos
│   ├── validate_system.py          # System validation tests
│   └── check_status.py             # System status checker
│
├── data/                            # Runtime data
│   └── thumbnails/                 # Generated thumbnails
│
├── logs/                            # Application logs
│
├── docker-compose.yml              # Docker services (PostgreSQL + Redis)
├── .env.example                    # Environment variables template
├── .env                            # Your environment config (git-ignored)
├── .gitignore                      # Git ignore rules
├── README.md                       # Comprehensive documentation
├── QUICKSTART.md                   # Quick start guide
├── PROJECT_STRUCTURE.md            # This file
├── pyproject.toml                  # Python project config (existing)
├── requirements.txt                # Python dependencies (existing)
└── uv.lock                         # UV lock file (existing)
```

## Database Schema

### Tables:

1. **photos** - Photo metadata and processing state
2. **categories** - Broad categories (electronics, food, etc.)
3. **tag_category_mappings** - Maps detected tags to categories
4. **detected_objects** - Objects detected by RAM++
5. **semantic_embeddings** - OpenCLIP vectors (1024-dim)
6. **ocr_texts** - Extracted text with ts_vector for search
7. **faces** - Face detections with embeddings (512-dim)
8. **photo_hashes** - PDQ perceptual hashes
9. **duplicates** - Duplicate photo relationships

## Key Components

### AI Models

1. **RAM++**: Object recognition (thousands of objects)
2. **OpenCLIP**: Semantic embeddings for hybrid search
3. **PaddleOCR**: Text extraction from images
4. **InsightFace**: Face detection and recognition
5. **PDQ Hash**: Perceptual hashing for duplicates

### Search System

- **Keyword Search**: PostgreSQL full-text search (ts_vector)
- **Semantic Search**: pgvector cosine similarity
- **Hybrid Search**: RRF fusion of both methods
- **Filters**: Categories, dates, duplicates

### Processing Pipeline

State machine: `pending` → `preprocessing` → `processing_objects` → `processing_embeddings` → `processing_ocr` → `processing_faces` → `processing_hash` → `checking_duplicates` → `completed`/`partial`/`failed`

## File Counts

- Python files: 20
- Templates: 5
- Scripts: 6
- Config files: 4
- Documentation: 3

Total: ~2000 lines of Python code

