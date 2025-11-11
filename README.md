# AI Photos Management System

A powerful AI-driven photo management system that helps content creators quickly find photos using object recognition, semantic search, OCR, face detection, and duplicate detection.

## Features

- 🔍 **Hybrid Search**: Combines keyword and semantic vector search for best results
- 🏷️ **Object Recognition**: Detects thousands of objects (iPhone, pizza, laptop, etc.)
- 📝 **OCR**: Extracts text from screenshots and documents
- 👤 **Face Detection**: Identifies faces in photos
- 🔄 **Duplicate Detection**: Finds near-duplicate images using perceptual hashing
- 🗂️ **Category Filtering**: Organize by broad categories (electronics, food, landscape, etc.)

## System Architecture

- **Web Interface**: Flask (simple, read-only gallery and search)
- **Object Detection**: DETR (facebook/detr-resnet-50) - GPU, transformer-based, high accuracy
- **Semantic Embeddings**: OpenCLIP (ViT-H-14) - GPU, fast semantic search
- **OCR**: PaddleOCR (multilingual) - CPU (ONNX Runtime / CUDA 13 compatibility)
- **Face Detection**: InsightFace (buffalo_l) - CPU (ONNX Runtime / CUDA 13 compatibility)
- **Duplicate Detection**: PDQ hashing (pdqhash library) - CPU
- **Database**: PostgreSQL 18 + pgvector
- **Queue**: Redis 8 + Celery

**Note**: PaddleOCR and InsightFace use CPU temporarily due to ONNX Runtime not supporting CUDA 13 yet. Will switch to GPU when support is available. See [Known Issues](#known-issues).

## Prerequisites

### Hardware Requirements

- **GPU**: NVIDIA GPU with CUDA 13.0+ support
  - Minimum: 16GB GPU memory (use 1 worker)
  - Recommended: 24GB+ GPU memory
  - Optimal: DGX Spark with 128GB unified memory (use 4 workers)
- **Storage**: ~10GB for models, plus space for your photos and thumbnails
- **RAM**: 16GB+ system RAM recommended

### Software Requirements

- **OS**: Ubuntu 22.04+ or Debian-based Linux
- **Python**: 3.12 (already set up in venv)
- **Docker**: Docker and Docker Compose
- **CUDA**: CUDA 13.0+ with compatible drivers

## Installation

### Step 1: Install System Dependencies

```bash
sudo apt update && sudo apt install -y \
    libheif-dev libde265-dev libx265-dev \
    libopencv-dev python3-opencv libglib2.0-0 \
    libsm6 libxext6 libxrender-dev libgomp1 \
    libpq-dev build-essential pkg-config
```

**What these packages do:**
- `libheif-dev`: HEIC image format support
- `libopencv-dev`: OpenCV dependencies for image processing
- `libpq-dev`: PostgreSQL client libraries
- `build-essential`: Compilation tools for Python packages

### Step 2: Install Python Dependencies

```bash
# Activate your venv (if not already activated)
source .venv/bin/activate

# Install all dependencies using uv
uv add flask sqlalchemy psycopg2-binary pgvector celery redis \
       open-clip-torch paddleocr insightface opencv-python \
       onnxruntime-gpu pdqhash scikit-learn tqdm python-dotenv \
       Pillow pillow-heif rawpy
```

### Step 3: Start Docker Services

```bash
# Start PostgreSQL and Redis
docker compose up -d

# Verify services are running
docker compose ps
```

**Troubleshooting:**
- If PostgreSQL fails to start: Check if port 5432 is already in use
- If Redis fails to start: Check if port 6379 is already in use
- Check logs: `docker compose logs postgres` or `docker compose logs redis`

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
nano .env
```

**Important settings to configure:**
- `PHOTOS_DIR`: Path to your photos directory (default: `/home/jasl/datasets/my_photos`)
- `POSTGRES_PASSWORD`: Change from default for production
- `SECRET_KEY`: Generate a random secret key for Flask
- `CELERY_WORKER_CONCURRENCY`: Set to 4 for DGX Spark, 1 for 16GB GPU

### Step 5: Download AI Models

This step pre-downloads all AI models (~6GB total):

```bash
python scripts/download_models.py
```

**Models downloaded:**
- DETR ResNet-50 (~160MB) - Object detection
- OpenCLIP ViT-H-14 (~3GB) - Semantic embeddings
- PaddleOCR (~100MB) - Text extraction
- InsightFace buffalo_l (~600MB) - Face detection

**Troubleshooting:**
- If download fails: Check internet connection and HuggingFace availability
- If out of disk space: Free up space and retry
- Models cached in: `~/.cache/ai_photos_models` (or your `MODEL_CACHE_DIR`)

### Step 6: Initialize Database

```bash
# Create database tables and enable pgvector extension
python -c "from models import init_db; init_db()"

# Seed categories and tag mappings
python scripts/seed_categories.py
```

**Expected output:**
```
✓ Database tables created successfully
✓ Created category: electronics
✓ Created category: food
...
```

### Step 7: Start Celery Worker

Open a **new terminal window** and run:

```bash
# Activate venv
source .venv/bin/activate

# Start Celery worker
# For DGX Spark (128GB unified memory):
celery -A workers.celery_app worker --loglevel=info --concurrency=4

# For standard GPU (16GB):
celery -A workers.celery_app worker --loglevel=info --concurrency=1
```

**Keep this terminal open** - you should see:
```
[2025-01-10 10:00:00] Initializing AI models...
[2025-01-10 10:00:30] ✓ DETR model loaded
[2025-01-10 10:01:00] ✓ OpenCLIP model loaded
...
[2025-01-10 10:02:00] ✓ All AI models loaded successfully
[2025-01-10 10:02:00] celery@hostname ready.
```

**Troubleshooting:**
- If models fail to load: Check GPU memory and CUDA availability
- If connection error: Ensure Redis is running (`docker compose ps`)
- If out of memory: Reduce `--concurrency` to 1

### Step 8: Process Photos

Open **another new terminal** and run:

```bash
# Activate venv
source .venv/bin/activate

# Run processing script
python scripts/process_photos.py
```

This will:
1. Scan your photos directory
2. Create database records for new photos
3. Queue processing tasks for each photo

**Expected time:**
- DGX Spark (4 workers): ~10,000 photos in 10-12 hours
- Standard GPU (1 worker): ~10,000 photos in 40-50 hours

**Monitor progress:**
```bash
# Check API stats
curl http://localhost:5000/api/stats

# Or open in browser
open http://localhost:5000/api/stats
```

### Step 9: Start Flask Web Application

Open **another new terminal** and run:

```bash
# Start Flask app (uv run ensures proper environment)
uv run python webapp/app.py

# Or if you prefer to activate venv manually:
source .venv/bin/activate
python webapp/app.py
```

### Step 10: Access the Application

Open your browser to:
- **Gallery**: http://localhost:5000
- **Search**: http://localhost:5000/search
- **Stats API**: http://localhost:5000/api/stats

## Usage

### Searching for Photos

1. Navigate to http://localhost:5000/search
2. Enter your search query (e.g., "iPhone", "pizza", "certificate")
3. Select search mode:
   - **Hybrid** (default): Best results, combines keyword and semantic search
   - **Keyword**: Exact tag and OCR text matching
   - **Semantic**: AI-powered semantic understanding
4. Optionally filter by categories
5. Click "Search"

### Viewing Photo Details

Click any photo to see:
- Detected objects with confidence scores
- Extracted text (OCR)
- Number of faces detected
- Duplicate warnings
- Full resolution image

## Advanced Usage

### Re-processing Failed Photos

```bash
# Re-queue failed photos
python scripts/process_photos.py
```

Failed and pending photos will be automatically re-queued.

### Monitoring Celery Tasks

Install Flower for a web-based monitoring dashboard:

```bash
uv add flower
celery -A workers.celery_app flower
```

Access at: http://localhost:5555

### Adding Custom Categories

```sql
-- Connect to PostgreSQL
docker exec -it ai_photos_postgres psql -U photos_user -d ai_photos

-- Add a new category
INSERT INTO categories (name, description, created_at) 
VALUES ('vehicles', 'Cars, motorcycles, and transportation', NOW());

-- Add tag mappings
INSERT INTO tag_category_mappings (tag, category_id) 
VALUES 
    ('car', (SELECT id FROM categories WHERE name = 'vehicles')),
    ('motorcycle', (SELECT id FROM categories WHERE name = 'vehicles'));
```

Then re-run the tag update job:

```python
# Update existing detected objects with new category
from models import get_session, DetectedObject, TagCategoryMapping

session = get_session()
mappings = session.query(TagCategoryMapping).all()

for mapping in mappings:
    session.query(DetectedObject).filter_by(tag=mapping.tag).update(
        {'category_id': mapping.category_id}
    )

session.commit()
session.close()
```

## Known Issues

### ONNX Runtime Models Use CPU (Temporary)

**Status**: ⚠️ ONNX Runtime doesn't support CUDA 13 yet

**Affected Models**:
- **PaddleOCR** (text extraction) - Currently runs on CPU
- **InsightFace** (face detection) - Currently runs on CPU

**Unaffected Models** (Running on GPU):
- **DETR** (object detection) - PyTorch, uses GPU ✅
- **OpenCLIP** (semantic embeddings) - PyTorch, uses GPU ✅

**Performance Impact**: Minimal (~100-200ms slower per photo)
- Total processing still under 1 second per photo
- Throughput: 40-60 photos/minute with 4 workers

**Future**: Will switch back to GPU when ONNX Runtime releases CUDA 13 support.

**Details**: See [ONNX_CUDA13_INFO.md](ONNX_CUDA13_INFO.md)

---

## Troubleshooting

### Issue: "CUDA out of memory"

**Solution:**
1. Reduce Celery concurrency to 1
2. Or run PaddleOCR on CPU by modifying `workers/ai_models.py`:
   ```python
   use_gpu = False  # Force CPU for PaddleOCR
   ```

### Issue: "Failed to load DETR model"

**Solution:**
1. Check internet connection
2. Clear cache and re-download:
   ```bash
   rm -rf ~/.cache/ai_photos_models/models--facebook--detr-resnet-50
   uv run python scripts/download_models.py
   ```

### Issue: "PDQ hash value too long for VARCHAR(64)"

**Solution:**
This was a bug in PDQ hash conversion (fixed in workers/ai_models.py). To clean up existing bad data:
```bash
uv run python scripts/fix_pdq_hashes.py
```

### Issue: "PostgreSQL connection refused"

**Solution:**
1. Ensure Docker is running: `docker compose ps`
2. Restart PostgreSQL: `docker compose restart postgres`
3. Check DATABASE_URL in `.env`

### Issue: "No photos found to process"

**Solution:**
1. Check `PHOTOS_DIR` in `.env` points to correct directory
2. Verify directory contains supported formats
3. Check file permissions

### Issue: "Thumbnail generation failed"

**Solution:**
1. Ensure `THUMBNAIL_DIR` is writable
2. Check system dependencies are installed (libheif, opencv)
3. For RAW files, ensure `rawpy` is installed

## Development

### Database Management

```bash
# Connect to PostgreSQL
docker exec -it ai_photos_postgres psql -U photos_user -d ai_photos

# Common queries
SELECT state, COUNT(*) FROM photos GROUP BY state;
SELECT name, COUNT(detected_objects.id) FROM categories 
  LEFT JOIN detected_objects ON categories.id = detected_objects.category_id 
  GROUP BY categories.name;
```

### Reset Database

**⚠️ WARNING: This deletes all data!**

```bash
python -c "from models import drop_all_tables, init_db; drop_all_tables(); init_db()"
python scripts/seed_categories.py
```

### Stop Services

```bash
# Stop Flask app: Ctrl+C in Flask terminal
# Stop Celery worker: Ctrl+C in Celery terminal

# Stop Docker services
docker compose down

# Stop and remove volumes (deletes all data!)
docker compose down -v
```

## Architecture Notes

### Why Flask instead of FastAPI?

This is a prototype focused on validating the AI pipeline. Flask provides:
- Simpler setup for read-only interfaces
- Easier debugging
- Faster prototype iteration

**Future migration to FastAPI is planned** for:
- Better async support
- Automatic API documentation
- Higher throughput

### Hybrid Search Explained

The system implements **Reciprocal Rank Fusion (RRF)** to combine:

1. **Keyword Search**: Finds exact tag matches and OCR text using PostgreSQL full-text search
2. **Semantic Search**: Uses OpenCLIP to understand meaning (e.g., "coffee" matches "beverage", "café")
3. **RRF Fusion**: Intelligently combines both results for optimal relevance

Formula: `RRF_score = Σ(1 / (60 + rank_i))`

### State Machine

Each photo progresses through states:

```
pending → preprocessing → processing_objects → processing_embeddings 
→ processing_ocr → processing_faces → processing_hash → checking_duplicates 
→ completed/partial/failed
```

**Partial state**: Some AI models succeeded, some failed. Results from successful steps are still saved and searchable.

## Performance Optimization

### For Large Photo Libraries (100K+ photos)

1. **Increase PostgreSQL resources** in `docker-compose.yml`:
   ```yaml
   command: postgres -c shared_buffers=2GB -c work_mem=50MB
   ```

2. **Use Redis persistence**:
   ```yaml
   command: redis-server --appendonly yes --save 60 1000
   ```

3. **Scale Celery workers** (requires multiple GPUs):
   ```bash
   celery -A workers.celery_app worker --concurrency=8
   ```

### Caching

The system implements Redis caching for:
- Search results (5-minute TTL)
- Category listings
- Frequently queried tags

## About DETR

**DETR (DEtection TRansformer)** is a state-of-the-art object detection model from Facebook AI Research.

### Why DETR?
- **High Accuracy**: Transformer-based architecture for precise object detection
- **91 Object Classes**: Detects common objects (person, car, phone, laptop, pizza, etc.)
- **Bounding Boxes**: Provides exact object locations
- **Complex Scenes**: Excellent at handling multiple objects and small items
- **No Hallucinations**: Only detects actual objects (unlike caption-based models)

### Detection Examples
- **Electronics**: laptop, cell phone, mouse, keyboard, tv, remote
- **Food**: pizza, sandwich, apple, banana, cake, donut
- **Furniture**: chair, couch, bed, dining table
- **Plus 70+ more categories**

See [DETR Implementation](DETR_IMPLEMENTATION.md) for technical details.

---

## License

This project is licensed under **AGPL-3.0** (GNU Affero General Public License v3.0).

### AI Models Licenses

The integrated AI models have their own licenses:
- **DETR**: Apache 2.0
- **OpenCLIP**: MIT
- **PaddleOCR**: Apache 2.0
- **InsightFace**: MIT/Apache 2.0

See the `LICENSE` file for the full AGPL-3.0 license text.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review Celery worker logs
3. Check Flask application logs
4. Verify Docker services are running

---

**Built with ❤️ for content creators**

