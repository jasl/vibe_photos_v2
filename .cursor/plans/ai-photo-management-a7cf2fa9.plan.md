<!-- a7cf2fa9-f01b-44b4-88f7-c2c1216a9e7a dc908cea-fc3e-4d6b-8ab4-cd1129bdf0b1 -->
# AI Photo Management System - Prototype Implementation

## System Architecture

Flask-based prototype to process and search photos using multiple AI models:

- **Object Recognition**: RAM++ for detecting objects (iPhone, pizza, laptop)
- **Semantic Embeddings**: OpenCLIP for hybrid search (text→image semantic matching)
- **OCR**: PaddleOCR for text extraction from screenshots/documents
- **Face Detection**: InsightFace for face recognition  
- **Duplicate Detection**: PDQ hashing (pdqhash library)
- **Database**: PostgreSQL 18 + pgvector (Docker)
- **Queue**: Redis 8 + Celery (Docker)
- **Web Interface**: Flask (read-only gallery and hybrid search)

## Implementation Structure

```
ai_photos_management_v2/
├── config/
│   └── settings.py          # Environment-based configuration
├── models/
│   ├── database.py          # SQLAlchemy ORM models
│   └── schemas.py           # Pydantic schemas
├── workers/
│   ├── ai_models.py         # Model loading & inference
│   ├── tasks.py             # Celery task definitions
│   └── celery_app.py        # Celery configuration
├── webapp/
│   ├── app.py               # Flask application
│   ├── routes.py            # Route handlers
│   ├── templates/           # Jinja2 templates
│   │   ├── index.html       # Photo gallery
│   │   └── search.html      # Search interface
│   └── static/              # CSS, JS
├── services/
│   ├── image_processor.py   # Processing orchestration
│   └── search_service.py    # Hybrid search (keyword + semantic + RRF)
├── utils/
│   ├── db.py               # Database session management
│   └── image_utils.py      # Format conversion, thumbnails
├── scripts/
│   ├── download_models.py  # Pre-download AI models
│   └── process_photos.py   # Initial processing script
├── docker-compose.yml      # PostgreSQL + Redis
├── .env.example           # Environment template
└── README.md              # Setup guide
```

## RAM++ Implementation Research

**Model:** `xinyu1205/recognize-anything-plus-model` (HuggingFace)

**Task:** Zero-shot image classification

**Implementation:**

- Use `transformers` library with AutoModel and AutoProcessor
- Load: `AutoModel.from_pretrained("xinyu1205/recognize-anything-plus-model")`
- Preprocessing: Use model's processor for proper input formatting
- Output: List of tags with confidence scores
- Reference: `hello-universe/ram-plus-inference` demo on HuggingFace

## System Requirements

**Host System Dependencies (Ubuntu/Debian):**

```bash
sudo apt update && sudo apt install -y \
    libheif-dev libde265-dev libx265-dev \
    libopencv-dev python3-opencv libglib2.0-0 \
    libsm6 libxext6 libxrender-dev libgomp1 \
    libpq-dev build-essential pkg-config
```

**Hardware:**

- NVIDIA GPU with CUDA 13.0+ (DGX Spark with 128GB unified memory)
- Minimum 16GB GPU memory (24GB+ recommended)

## Database Schema (SQLAlchemy ORM)

**Tables:**

- `photos`: id, file_path, filename, thumbnail_path, state, created_at, processed_at, file_size, width, height, error_message
- `categories`: id, name, description, created_at
- `tag_category_mappings`: id, tag, category_id
- `detected_objects`: id, photo_id, tag, confidence, category_id (FK)
- `semantic_embeddings`: id, photo_id, embedding (pgvector), model_version
- `ocr_texts`: id, photo_id, extracted_text, language, ts_vector
- `faces`: id, photo_id, bbox (JSON), embedding (pgvector), cluster_id
- `photo_hashes`: id, photo_id, pdq_hash (hex string)
- `duplicates`: id, photo_id_1, photo_id_2, hamming_distance

**Indexes:**

- Full-text: `ocr_texts.ts_vector`
- GIN: `detected_objects.tag`
- pgvector HNSW: `semantic_embeddings.embedding`

## AI Models Configuration

**Loading Strategy:**

- Load all models **once** at Celery worker startup
- Keep in memory throughout worker lifetime (no load/unload)
- Enable fp16 for reduced memory (~12-16GB total)
- DGX Spark: Run 4 concurrent workers (128GB unified memory)
- Smaller GPUs: Use 1 worker (16GB GPU memory)

**Models:**

1. **RAM++** - `xinyu1205/recognize-anything-plus-model` (~2GB, transformers library)
2. **OpenCLIP** - ViT-H-14/laion2b_s32b_b79k (~3GB, 1024-dim embeddings)
3. **PaddleOCR** - multilingual (~100MB, can run on CPU if GPU tight)
4. **InsightFace** - buffalo_l (~600MB, 512-dim face embeddings)
5. **PDQ Hash** - pdqhash library (Facebook's PDQ, Hamming distance ≤ 8 for duplicates)

## Category Mapping (Database-Driven)

**Seed Categories & Tag Mappings:**

- **electronics**: iPhone, iPad, MacBook, laptop, computer, phone, camera, tablet
- **food**: pizza, burger, coffee, cake, pasta, sushi, salad, beverage
- **landscape**: mountain, beach, sunset, forest, ocean, sky, nature, park
- **documents**: screenshot, document, receipt, certificate, text, paper
- **people**: person, face, portrait, group, crowd, selfie, family

**Future:** Admin UI to add/edit categories

**Re-indexing:** Background job updates `detected_objects.category_id` for affected tags (no image re-processing)

## Photo Processing State Machine

**States:**

`pending` → `preprocessing` → `processing_objects` → `processing_embeddings` → `processing_ocr` → `processing_faces` → `processing_hash` → `checking_duplicates` → `completed`/`partial`/`failed`

**Celery Task: `process_single_image(photo_id)`**

1. **Preprocessing**: Convert HEIC/RAW→JPEG, generate thumbnail (400px)
2. **Objects**: RAM++ tagging, map to categories
3. **Embeddings**: OpenCLIP 1024-dim vector
4. **OCR**: PaddleOCR text extraction + ts_vector
5. **Faces**: InsightFace detection, embeddings, bboxes
6. **Hash**: PDQ hash calculation using pdqhash library
7. **Duplicates**: Find matches (Hamming ≤ 8)
8. **State**: Update to `completed` or `partial`

**Error Handling:** Try-except per step, save partial results, log errors, continue to next step

## Hybrid Search (Keyword + Semantic Vector Search)

**Search Strategy:**

When user submits a text query, execute **both** searches in parallel:

1. **Keyword Search** (PostgreSQL Full-Text):

   - Search `ocr_texts.ts_vector` for OCR text matches
   - Search `detected_objects.tag` for object tag matches
   - Use `ts_rank` for relevance scoring

2. **Semantic Vector Search** (pgvector):

   - Generate query embedding using OpenCLIP text encoder
   - Search `semantic_embeddings.embedding` using cosine distance (`<=>`)
   - Find top-K most similar images

3. **Result Fusion** (RRF - Reciprocal Rank Fusion):

   - Combine results from both searches using RRF algorithm
   - Formula: `RRF_score = Σ(1 / (k + rank_i))` where k=60
   - Sort by final RRF score for optimal relevance

**Additional Filters:**

- Category filter: Multi-select (electronics, food, etc.)
- Date range: Filter on `created_at`
- Duplicate filter: Show/hide duplicates
- Search mode toggle: Hybrid (default), Keyword-only, Semantic-only

## Flask Web Interface

**Routes:**

- `GET /` - Gallery (grid, 50/page, date desc)
- `GET /search` - Search with hybrid mode and filters
- `GET /photo/<id>` - Photo details
- `GET /thumbnail/<id>` - Serve thumbnails
- `GET /api/stats` - Processing statistics

**UI Features:**

- Responsive grid, lazy-loaded thumbnails
- Search bar with tag autocomplete
- Category checkboxes
- Search mode toggle (Hybrid/Keyword/Semantic)
- Processing progress indicator
- Photo detail: full image, tags, OCR text, faces, duplicates

## Docker Services

```yaml
postgres:
  image: pgvector/pgvector:pg18
  ports: ["5432:5432"]
  volumes: [postgres_data:/var/lib/postgresql/data]

redis:
  image: redis:8-alpine
  ports: ["6379:6379"]
  volumes: [redis_data:/data]
```

## Configuration (config/settings.py)

From environment variables:

- `PHOTOS_DIR` (default: `/home/jasl/datasets/my_photos`)
- `DATABASE_URL`, `REDIS_URL`
- `MODEL_CACHE_DIR` (default: `~/.cache/ai_photos_models`)
- `THUMBNAIL_DIR`, `THUMBNAIL_SIZE` (default: 400)
- `DEVICE` (auto-detect CUDA)
- `DUPLICATE_THRESHOLD` (default: 8)
- `SUPPORTED_FORMATS` (jpg, jpeg, png, heic, webp, cr2, nef, etc.)

## Deployment Steps

**1. Install system dependencies:**

```bash
sudo apt update && sudo apt install -y \
    libheif-dev libde265-dev libx265-dev \
    libopencv-dev python3-opencv libglib2.0-0 \
    libsm6 libxext6 libxrender-dev libgomp1 \
    libpq-dev build-essential pkg-config
```

**2. Start Docker services:**

```bash
docker-compose up -d
```

**3. Install Python dependencies:**

```bash
uv add flask sqlalchemy psycopg2-binary pgvector celery redis \
       open-clip-torch paddleocr insightface opencv-python \
       onnxruntime-gpu pdqhash scikit-learn tqdm python-dotenv \
       Pillow pillow-heif rawpy
```

**4. Download AI models (pre-cache ~6GB):**

```bash
python scripts/download_models.py
```

Downloads: RAM++ (~2GB), OpenCLIP (~3GB), PaddleOCR (~100MB), InsightFace (~600MB)

**5. Configure environment:**

```bash
cp .env.example .env
# Edit .env: PHOTOS_DIR, DATABASE_URL, REDIS_URL, etc.
```

**6. Initialize database:**

```bash
python -c "from models.database import init_db; init_db()"
```

**7. Start Celery worker:**

```bash
# DGX Spark (128GB unified memory)
celery -A workers.celery_app worker --loglevel=info --concurrency=4

# Standard GPU (16GB)
celery -A workers.celery_app worker --loglevel=info --concurrency=1
```

**8. Process photos:**

```bash
python scripts/process_photos.py
```

**9. Start Flask app:**

```bash
python webapp/app.py
```

**10. Access:** `http://localhost:5000`

## Validation Points

1. RAM++ detects common objects (iPhone, pizza, laptop)
2. Tags map correctly to categories
3. OCR runs on text-heavy images only
4. Face detection accurate, no false positives
5. PDQ duplicate detection threshold validated (test with crops, filters)
6. Processing: <15s/image on GPU
7. Hybrid search returns expected results (test keyword vs semantic vs hybrid)
8. Partial results saved on step failures
9. GPU memory fits in available space
10. Thumbnails render correctly

## Performance Expectations

- **DGX Spark (4 workers)**: ~10,000 photos in 10-12 hours (~4s/photo)
- **Standard GPU (1 worker)**: ~10,000 photos in 40-50 hours (~15s/photo)
- **Hybrid search**: <200ms (parallel execution)
- **Gallery load**: <1s with lazy loading

## Optimization & Monitoring

**Logging & Observability:**

- Log each state transition with timestamp, photo_id, processing time
- Track metrics: success rate per step, avg processing time per model, GPU memory usage
- Structured logging (JSON format) for easy analysis
- Celery task monitoring dashboard (Flower)

**Caching Strategy:**

- Cache frequently queried categories and tags using Redis
- Cache search results for popular queries (TTL: 5 minutes)
- Cache thumbnail paths to reduce database queries
- Cache invalidation on new photo processing

**Performance Tuning:**

- Test Hamming distance threshold (≤ 8): Validate with sample duplicates
- Monitor GPU memory: CUDA profiling, alert if >90% usage
- Model quantization (future): INT8 if memory constrained
- Query optimization: Indexes on category_id, created_at, state

**Alternative Models for Reference:**

- Object Recognition: DETR, YOLOv5 (if RAM++ insufficient)
- Semantic Embeddings: CLIP-ViT-B/32 (smaller), CoCa (alternative)
- OCR: Tesseract, EasyOCR (if PaddleOCR struggles)
- Face Detection: FaceNet, DeepFace (InsightFace recommended)

**Scalability Notes:**

- Current plan: prototype and small-to-medium deployments
- Production: Redis clustering, multiple Celery worker nodes
- Flask→FastAPI migration for async support

## Future Enhancements

- Image-to-image similarity search (upload image to find similar)
- Face clustering for "People" grouping
- Admin UI for category management
- Bulk re-processing/re-tagging
- Export search results
- FastAPI migration

### To-dos

- [ ] Create docker-compose.yml with PostgreSQL 18 (pgvector) and Redis 8 services
- [ ] Create config/settings.py with environment-based configuration and .env.example template
- [ ] Implement SQLAlchemy ORM models: photos (with state field), categories, tag_category_mappings, detected_objects, semantic_embeddings, ocr_texts (with ts_vector), faces, photo_hashes, duplicates
- [ ] Create database seed script for categories and tag mappings (electronics, food, landscape, documents, people)
- [ ] Create utils/image_utils.py for format conversion (HEIC/RAW to JPEG) and thumbnail generation
- [ ] Create scripts/download_models.py to pre-download RAM++ (transformers), OpenCLIP, PaddleOCR, and InsightFace models
- [ ] Implement workers/ai_models.py with startup model loading (RAM++, OpenCLIP, PaddleOCR, InsightFace, pdqhash) and inference functions
- [ ] Create workers/celery_app.py and workers/tasks.py with state machine implementation for process_single_image task
- [ ] Implement services/search_service.py with hybrid search: PostgreSQL full-text (ts_vector), pgvector semantic search (OpenCLIP), and RRF result fusion
- [ ] Create Flask app (webapp/app.py, routes.py) with routes: gallery, search with hybrid mode, photo detail, thumbnails, stats API
- [ ] Design Jinja2 templates with responsive grid gallery, search interface (with hybrid/keyword/semantic mode toggle), and photo detail page
- [ ] Create scripts/process_photos.py to scan photos directory, create database records, and queue Celery tasks with tqdm progress
- [ ] Write comprehensive README.md with system dependencies (apt install commands), Docker setup, model download, deployment steps, and troubleshooting
- [ ] Create validation test suite for object recognition accuracy, category mapping, OCR, face detection, PDQ duplicate detection, and hybrid search relevance