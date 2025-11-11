"""
Script to pre-download all AI models.
Downloads RAM++, OpenCLIP, PaddleOCR, and InsightFace models to cache directory.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
import torch
from transformers import AutoModel, AutoProcessor
import open_clip
from paddleocr import PaddleOCR
import insightface


def download_ram_plus():
    """Download RAM++ model from HuggingFace."""
    print("\n" + "=" * 60)
    print("Downloading RAM++ Model")
    print("=" * 60)
    print(f"Model: {settings.RAM_MODEL_NAME}")
    print(f"Cache directory: {settings.MODEL_CACHE_DIR}")
    
    # Check if already cached
    ram_cache = settings.MODEL_CACHE_DIR / "models--xinyu1205--recognize-anything-plus-model"
    if ram_cache.exists():
        print("⏭️  RAM++ already cached, skipping download")
        return True
    
    try:
        from huggingface_hub import snapshot_download
        
        print("📥 Downloading RAM++ model files...")
        
        # Download entire model repository (includes custom code)
        model_path = snapshot_download(
            repo_id=settings.RAM_MODEL_NAME,
            cache_dir=settings.MODEL_CACHE_DIR,
            allow_patterns=["*.py", "*.json", "*.bin", "*.safetensors", "*.txt"]
        )
        
        print(f"✓ RAM++ model downloaded successfully")
        print(f"  Model path: {model_path}")
        print(f"  Note: RAM++ uses custom model code (trust_remote_code=True)")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to download RAM++ model: {e}")
        print("\n💡 Alternative: Using BLIP for image captioning/tagging")
        print("  You can switch to: Salesforce/blip-image-captioning-large")
        return False


def download_openclip():
    """Download OpenCLIP model."""
    print("\n" + "=" * 60)
    print("Downloading OpenCLIP Model")
    print("=" * 60)
    print(f"Model: {settings.OPENCLIP_MODEL_NAME}")
    print(f"Pretrained: {settings.OPENCLIP_PRETRAINED}")
    print(f"Cache directory: {settings.MODEL_CACHE_DIR}")
    
    # Check if already cached
    openclip_cache = settings.MODEL_CACHE_DIR / "open_clip"
    if openclip_cache.exists() and list(openclip_cache.glob("*laion*.pt")):
        print("⏭️  OpenCLIP already cached, skipping download")
        return True
    
    try:
        print("📥 Downloading OpenCLIP model files...")
        
        # Download model, preprocess, and tokenizer
        model, _, preprocess = open_clip.create_model_and_transforms(
            settings.OPENCLIP_MODEL_NAME,
            pretrained=settings.OPENCLIP_PRETRAINED,
            cache_dir=settings.MODEL_CACHE_DIR
        )
        
        tokenizer = open_clip.get_tokenizer(settings.OPENCLIP_MODEL_NAME)
        
        print("✓ OpenCLIP model downloaded successfully")
        
        # Get embedding dimension
        with torch.no_grad():
            dummy_text = tokenizer(["test"])
            text_features = model.encode_text(dummy_text)
            print(f"  Embedding dimension: {text_features.shape[1]}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to download OpenCLIP model: {e}")
        return False


def download_paddleocr():
    """Download PaddleOCR models."""
    print("\n" + "=" * 60)
    print("Downloading PaddleOCR Models")
    print("=" * 60)
    print("Languages: English (en), with angle classification")
    
    # Check if already cached
    paddle_cache = Path.home() / ".paddleocr"
    if paddle_cache.exists() and list(paddle_cache.glob("**/en_*")):
        print("⏭️  PaddleOCR already cached, skipping download")
        return True
    
    try:
        print("📥 Downloading PaddleOCR model files...")
        
        # Initialize PaddleOCR (downloads models on first use)
        # Note: Newer PaddleOCR API is simpler - auto-detects GPU
        ocr = PaddleOCR(lang='en')
        
        print("✓ PaddleOCR models downloaded successfully")
        print("  Components: Detection, Recognition, Angle Classification")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to download PaddleOCR models: {e}")
        return False


def download_insightface():
    """Download InsightFace buffalo_l model."""
    print("\n" + "=" * 60)
    print("Downloading InsightFace Model")
    print("=" * 60)
    print(f"Model: {settings.INSIGHTFACE_MODEL_NAME}")
    
    # Check if already cached
    insightface_cache = settings.MODEL_CACHE_DIR / "insightface" / settings.INSIGHTFACE_MODEL_NAME
    if insightface_cache.exists() and list(insightface_cache.glob("*.onnx")):
        print("⏭️  InsightFace already cached, skipping download")
        return True
    
    try:
        print("📥 Downloading InsightFace model files...")
        
        # Initialize InsightFace app (downloads model on first use)
        app = insightface.app.FaceAnalysis(
            name=settings.INSIGHTFACE_MODEL_NAME,
            root=str(settings.MODEL_CACHE_DIR / 'insightface')
        )
        
        # Prepare with CPU (just to download, actual inference will use GPU if available)
        app.prepare(ctx_id=-1, det_size=(640, 640))
        
        print("✓ InsightFace model downloaded successfully")
        print(f"  Model: {settings.INSIGHTFACE_MODEL_NAME}")
        print("  Detection size: 640x640")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to download InsightFace model: {e}")
        return False


def check_disk_space():
    """Check available disk space in cache directory."""
    cache_dir = settings.MODEL_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    stat = os.statvfs(cache_dir)
    available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    
    print("\n" + "=" * 60)
    print("Disk Space Check")
    print("=" * 60)
    print(f"Cache directory: {cache_dir}")
    print(f"Available space: {available_gb:.2f} GB")
    
    required_gb = 10  # Estimated total size
    if available_gb < required_gb:
        print(f"\n⚠ WARNING: Low disk space!")
        print(f"  Required: ~{required_gb} GB")
        print(f"  Available: {available_gb:.2f} GB")
        response = input("Continue anyway? (yes/no): ")
        return response.lower() == "yes"
    
    print(f"✓ Sufficient disk space ({available_gb:.2f} GB available)")
    return True


def check_gpu():
    """Check GPU availability."""
    print("\n" + "=" * 60)
    print("GPU Check")
    print("=" * 60)
    
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        print(f"✓ CUDA available: {gpu_count} GPU(s) detected")
        
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024 ** 3)
            print(f"  GPU {i}: {gpu_name} ({gpu_memory:.2f} GB)")
        
        print(f"\nModels will be configured for: {settings.DEVICE}")
    else:
        print("⚠ CUDA not available - models will run on CPU")
        print("  Note: CPU inference will be significantly slower")
        print(f"  Current device setting: {settings.DEVICE}")


def check_cached_models():
    """Check which models are already cached."""
    print("\n" + "=" * 60)
    print("Cached Models Check")
    print("=" * 60)
    
    cache_dir = settings.MODEL_CACHE_DIR
    
    models_status = {
        "RAM++": False,
        "OpenCLIP": False,
        "PaddleOCR": False,
        "InsightFace": False
    }
    
    # Check RAM++
    ram_cache = cache_dir / "models--xinyu1205--recognize-anything-plus-model"
    if ram_cache.exists():
        models_status["RAM++"] = True
    
    # Check OpenCLIP (looks for laion weights)
    openclip_cache = cache_dir / "open_clip"
    if openclip_cache.exists() and list(openclip_cache.glob("*laion*.pt")):
        models_status["OpenCLIP"] = True
    
    # Check PaddleOCR (checks in home directory)
    paddle_cache = Path.home() / ".paddleocr"
    if paddle_cache.exists():
        models_status["PaddleOCR"] = True
    
    # Check InsightFace
    insightface_cache = cache_dir / "insightface" / settings.INSIGHTFACE_MODEL_NAME
    if insightface_cache.exists():
        models_status["InsightFace"] = True
    
    # Print status
    cached_count = sum(models_status.values())
    total_count = len(models_status)
    
    for model_name, is_cached in models_status.items():
        status = "✓ Cached" if is_cached else "⏳ Needs download"
        print(f"  {status}: {model_name}")
    
    print(f"\nTotal: {cached_count}/{total_count} models already cached")
    
    if cached_count == total_count:
        print("\n✓ All models are already downloaded!")
        print("  You can skip this step or re-run to verify.")
    
    return models_status


def main():
    """Main function to download all models."""
    print("\n" + "=" * 60)
    print("AI Photos Management - Model Download Script")
    print("=" * 60)
    print("\nThis script will download the following models:")
    print("  1. RAM++ (~2 GB) - Object recognition")
    print("  2. OpenCLIP ViT-H-14 (~3 GB) - Semantic embeddings")
    print("  3. PaddleOCR (~100 MB) - Text extraction")
    print("  4. InsightFace buffalo_l (~600 MB) - Face detection")
    print(f"\nTotal estimated download: ~6 GB")
    print(f"Cache directory: {settings.MODEL_CACHE_DIR}")
    
    # Check prerequisites
    if not check_disk_space():
        print("\n✗ Insufficient disk space. Aborting.")
        return 1
    
    check_gpu()
    
    # Check which models are already cached
    cached_models = check_cached_models()
    
    # Confirm download
    print("\n" + "-" * 60)
    response = input("Proceed with downloads? (yes/no): ").strip().lower()
    
    if response != "yes":
        print(f"\nDownload cancelled (you typed: '{response}').")
        return 0
    
    print("\n✓ Starting downloads...")
    
    # Download models
    results = {
        "RAM++": download_ram_plus(),
        "OpenCLIP": download_openclip(),
        "PaddleOCR": download_paddleocr(),
        "InsightFace": download_insightface()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    
    success_count = sum(results.values())
    total_count = len(results)
    
    for model_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {model_name}")
    
    print(f"\nTotal: {success_count}/{total_count} models downloaded successfully")
    
    if success_count == total_count:
        print("\n✓ All models downloaded successfully!")
        print("\nNext steps:")
        print("  1. Configure your .env file")
        print("  2. Start Docker services: docker-compose up -d")
        print("  3. Initialize database: python -c 'from models import init_db; init_db()'")
        print("  4. Seed categories: python scripts/seed_categories.py")
        print("  5. Start Celery worker")
        print("  6. Process photos: python scripts/process_photos.py")
        return 0
    else:
        print("\n⚠ Some models failed to download. Please check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

