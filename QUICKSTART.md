# Quick Start Guide

Get the AI Photos Management system up and running in 10 steps.

## Prerequisites

- Ubuntu 22.04+ with NVIDIA GPU
- CUDA 13.0+ installed
- Docker and Docker Compose installed
- Python 3.12 venv already set up (✓)

## Quick Start

### 1. Install System Dependencies (One-time setup)

```bash
sudo apt update && sudo apt install -y \
    libheif-dev libde265-dev libx265-dev \
    libopencv-dev python3-opencv libglib2.0-0 \
    libsm6 libxext6 libxrender-dev libgomp1 \
    libpq-dev build-essential pkg-config
```

### 2. Install Python Packages

```bash
source .venv/bin/activate

uv add flask sqlalchemy psycopg2-binary pgvector celery redis \
       open-clip-torch paddleocr insightface opencv-python \
       onnxruntime-gpu pdqhash scikit-learn tqdm python-dotenv \
       Pillow pillow-heif rawpy
```

### 3. Start Docker Services

```bash
docker-compose up -d
```

Wait 10 seconds for PostgreSQL to initialize.

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (especially PHOTOS_DIR)
```

### 5. Download AI Models (~6GB, takes 10-20 minutes)

```bash
python scripts/download_models.py
```

Type `yes` when prompted.

### 6. Initialize Database

```bash
python scripts/setup_database.py
```

### 7. Validate System

```bash
python scripts/validate_system.py
```

Ensure all tests pass.

### 8. Start Celery Worker (Terminal 1)

```bash
# DGX Spark (128GB unified memory)
celery -A workers.celery_app worker --loglevel=info --concurrency=4

# Standard GPU (16GB)
celery -A workers.celery_app worker --loglevel=info --concurrency=1
```

Wait for "All AI models loaded successfully" message (~2-3 minutes).

### 9. Start Flask App (Terminal 2)

```bash
python webapp/app.py
```

### 10. Process Photos (Terminal 3)

```bash
python scripts/process_photos.py
```

Type `yes` when prompted.

## Access the Application

- **Gallery**: http://localhost:5000
- **Search**: http://localhost:5000/search  
- **API Stats**: http://localhost:5000/api/stats

## Monitoring Progress

Check processing progress:

```bash
# Via API
curl http://localhost:5000/api/stats | python -m json.tool

# Or open in browser
open http://localhost:5000/api/stats
```

## Common Commands

```bash
# Stop all services
docker-compose down  # Stop Docker
# Ctrl+C in Celery and Flask terminals

# Restart processing
python scripts/process_photos.py

# Check photo states
docker exec -it ai_photos_postgres psql -U photos_user -d ai_photos \
    -c "SELECT state, COUNT(*) FROM photos GROUP BY state;"

# View logs
docker-compose logs postgres
docker-compose logs redis
```

## Troubleshooting

**Issue**: Models won't load

```bash
# Check GPU
nvidia-smi

# Re-download models
python scripts/download_models.py
```

**Issue**: No photos found

```bash
# Verify PHOTOS_DIR in .env
cat .env | grep PHOTOS_DIR

# Check directory exists
ls -la /home/jasl/datasets/my_photos
```

**Issue**: Search returns no results

- Wait for photo processing to complete
- Check stats: `curl http://localhost:5000/api/stats`
- Verify photos are in `completed` state

---

For detailed documentation, see `README.md`.

