# Quick Start Guide

**Status**: ✅ All systems operational (7/7 tests passing)

---

## 🚀 Start the System

### One-Time Setup

```bash
# 1. Start Docker
docker compose up -d

# 2. Download models (first time only, ~4GB)
uv run python scripts/download_models.py

# 3. Initialize database (first time only)
uv run python -c 'from models import init_db; init_db()'
uv run python scripts/seed_categories.py

# 4. Clean up bad PDQ hashes (if upgrading from old version)
uv run python scripts/fix_pdq_hashes.py
```

### Every Time (2 terminals)

**Terminal 1 - Celery Worker**:
```bash
celery -A workers.celery_app worker --loglevel=info --concurrency=1
```

**Terminal 2 - Flask Web App**:
```bash
uv run python webapp/app.py
```

### Access

Open browser: **http://localhost:5000**

---

## 📸 Process Photos

```bash
# Process a directory
uv run python scripts/process_photos.py /path/to/photos

# The system will:
# 1. Extract objects (DETR)
# 2. Generate embeddings (OpenCLIP)
# 3. Extract text (PaddleOCR)
# 4. Detect faces (InsightFace)
# 5. Calculate hash (PDQ)
# 6. Check duplicates
```

---

## 🔍 Search Your Photos

### Via Web Interface
1. Go to http://localhost:5000
2. Use search box
3. Filter by category
4. Browse gallery

### Search Types
- **Keyword**: Searches tags and OCR text
- **Semantic**: Understands meaning (e.g., "beach" finds "ocean", "sand")
- **Hybrid**: Combines both for best results

---

## ✅ Verify System

```bash
# Run all tests
uv run python scripts/validate_system.py

# Should show: 7/7 tests passed
```

---

## 🛠️ Common Commands

```bash
# Check Docker status
docker compose ps

# View logs
docker compose logs -f postgres
docker compose logs -f redis

# Restart services
docker compose restart

# Stop everything
docker compose down
```

---

## 📊 What Gets Detected

### Object Detection (DETR)
- 91 object classes
- Bounding boxes
- Confidence scores
- Examples: person, car, phone, laptop, pizza, chair

### Text Extraction (PaddleOCR)
- Multilingual support
- Screenshot text
- Document text
- Sign text

### Face Detection (InsightFace)
- Face locations
- Face embeddings
- Can find similar faces

### Duplicates (PDQ Hash)
- Near-duplicate detection
- Perceptual hashing
- Quality scoring

---

## 🎯 System Architecture

```
Photos → Celery Worker → AI Models:
  ├─ DETR (object detection)
  ├─ OpenCLIP (semantic search)
  ├─ PaddleOCR (text extraction)
  ├─ InsightFace (face detection)
  └─ PDQ Hash (duplicates)
         ↓
   PostgreSQL + pgvector
         ↓
   Flask Web App → You!
```

---

## 📚 Documentation

- **[README.md](README.md)** - Complete documentation
- **[ALL_ISSUES_RESOLVED.md](ALL_ISSUES_RESOLVED.md)** - What was fixed
- **[DETR_IMPLEMENTATION.md](DETR_IMPLEMENTATION.md)** - Technical details
- **[PDQ_HASH_FIX.md](PDQ_HASH_FIX.md)** - Hash fix details

---

## 🎉 You're Ready!

All systems tested and working. Start processing your photos!

```bash
# Start everything
docker compose up -d
celery -A workers.celery_app worker --loglevel=info &
uv run python webapp/app.py
```

**Happy photo organizing!** 📸✨

