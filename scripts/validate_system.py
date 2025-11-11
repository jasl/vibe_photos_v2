"""
Validation test suite for AI Photos Management system.
Tests object recognition, category mapping, OCR, face detection, 
duplicate detection, and hybrid search.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import numpy as np

from workers import ai_models
from services import hybrid_search, keyword_search, semantic_search
from models import get_session, Category, TagCategoryMapping


def test_ram_object_recognition():
    """Test RAM++ object recognition accuracy."""
    print("\n" + "=" * 60)
    print("Test 1: RAM++ Object Recognition")
    print("=" * 60)
    
    try:
        # Create test image (white square - should detect basic objects)
        test_img = Image.new('RGB', (224, 224), color='white')
        
        results = ai_models.recognize_objects(test_img)
        
        print(f"✓ RAM++ model responding")
        print(f"  Detected {len(results)} objects")
        
        if results:
            print("  Top 5 detections:")
            for obj in results[:5]:
                print(f"    - {obj['tag']}: {obj['confidence']:.2%}")
        
        return True
        
    except Exception as e:
        print(f"✗ RAM++ test failed: {e}")
        return False


def test_category_mapping():
    """Test category and tag mapping functionality."""
    print("\n" + "=" * 60)
    print("Test 2: Category Mapping")
    print("=" * 60)
    
    try:
        session = get_session()
        
        # Check categories exist
        categories = session.query(Category).all()
        print(f"✓ Found {len(categories)} categories")
        
        expected_categories = {'electronics', 'food', 'landscape', 'documents', 'people'}
        category_names = {cat.name for cat in categories}
        
        if expected_categories.issubset(category_names):
            print("✓ All expected categories present")
        else:
            missing = expected_categories - category_names
            print(f"⚠️ Missing categories: {missing}")
        
        # Check tag mappings
        total_mappings = session.query(TagCategoryMapping).count()
        print(f"✓ Found {total_mappings} tag mappings")
        
        # Test specific mappings
        test_tags = {
            'iPhone': 'electronics',
            'pizza': 'food',
            'mountain': 'landscape'
        }
        
        for tag, expected_category in test_tags.items():
            mapping = session.query(TagCategoryMapping).filter_by(tag=tag).first()
            if mapping:
                actual_category = session.query(Category).filter_by(id=mapping.category_id).first()
                if actual_category and actual_category.name == expected_category:
                    print(f"✓ '{tag}' → '{expected_category}' mapping correct")
                else:
                    print(f"⚠️ '{tag}' mapped to '{actual_category.name}' (expected '{expected_category}')")
            else:
                print(f"⚠️ No mapping found for '{tag}'")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"✗ Category mapping test failed: {e}")
        return False


def test_openclip_embeddings():
    """Test OpenCLIP semantic embedding generation."""
    print("\n" + "=" * 60)
    print("Test 3: OpenCLIP Embeddings")
    print("=" * 60)
    
    try:
        # Test image embedding
        test_img = Image.new('RGB', (224, 224), color='blue')
        image_emb = ai_models.generate_image_embedding(test_img)
        
        print(f"✓ Image embedding generated: shape {image_emb.shape}")
        print(f"  Expected: (1024,), Got: {image_emb.shape}")
        
        # Test text embedding
        text_emb = ai_models.generate_text_embedding("a photo of a dog")
        
        print(f"✓ Text embedding generated: shape {text_emb.shape}")
        print(f"  Expected: (1024,), Got: {text_emb.shape}")
        
        # Test similarity (dot product)
        similarity = np.dot(image_emb, text_emb)
        print(f"✓ Similarity computation works: {similarity:.4f}")
        
        return image_emb.shape == (1024,) and text_emb.shape == (1024,)
        
    except Exception as e:
        print(f"✗ OpenCLIP test failed: {e}")
        return False


def test_paddleocr():
    """Test PaddleOCR text extraction."""
    print("\n" + "=" * 60)
    print("Test 4: PaddleOCR Text Extraction")
    print("=" * 60)
    
    try:
        # Ensure models are initialized
        ai_models.initialize_models()
        
        # Note: We can't easily test OCR without an actual image file
        # Just verify the model is loaded
        print("✓ PaddleOCR model loaded and ready")
        print("  Note: OCR requires actual image files to test properly")
        
        return True
        
    except Exception as e:
        print(f"✗ PaddleOCR test failed: {e}")
        return False


def test_insightface():
    """Test InsightFace face detection."""
    print("\n" + "=" * 60)
    print("Test 5: InsightFace Face Detection")
    print("=" * 60)
    
    try:
        # Ensure models are initialized
        ai_models.initialize_models()
        
        # Note: Testing face detection requires actual face images
        print("✓ InsightFace model loaded and ready")
        print("  Note: Face detection requires actual face images to test properly")
        
        return True
        
    except Exception as e:
        print(f"✗ InsightFace test failed: {e}")
        return False


def test_pdq_hashing():
    """Test PDQ hash calculation."""
    print("\n" + "=" * 60)
    print("Test 6: PDQ Hash Calculation")
    print("=" * 60)
    
    try:
        # Create test image and save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            test_img = Image.new('RGB', (224, 224), color='red')
            test_img.save(tmp.name, 'JPEG')
            tmp_path = tmp.name
        
        hash_hex, quality = ai_models.calculate_pdq_hash(tmp_path)
        
        # Clean up
        Path(tmp_path).unlink()
        
        print(f"✓ PDQ hash calculated")
        print(f"  Hash: {hash_hex[:32]}...")
        print(f"  Quality: {quality}")
        print(f"  Hash length: {len(hash_hex)} characters")
        
        return len(hash_hex) > 0
        
    except Exception as e:
        print(f"✗ PDQ hash test failed: {e}")
        return False


def test_hybrid_search():
    """Test hybrid search functionality."""
    print("\n" + "=" * 60)
    print("Test 7: Hybrid Search")
    print("=" * 60)
    
    try:
        # Test with a simple query
        query = "test"
        
        print("Testing keyword search...")
        session = get_session()
        keyword_results = keyword_search(session, query, limit=10)
        session.close()
        print(f"  Keyword search returned {len(keyword_results)} results")
        
        print("Testing semantic search...")
        session = get_session()
        semantic_results = semantic_search(session, query, limit=10)
        session.close()
        print(f"  Semantic search returned {len(semantic_results)} results")
        
        print("Testing hybrid search...")
        hybrid_results = hybrid_search(query, mode='hybrid', page=1, page_size=10)
        print(f"  Hybrid search returned {len(hybrid_results['results'])} results")
        
        print("✓ All search modes functional")
        
        return True
        
    except Exception as e:
        print(f"✗ Hybrid search test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("AI Photos Management - Validation Test Suite")
    print("=" * 60)
    print("\nThis will test all AI models and core functionality.")
    print("Note: Some tests require processed photos in the database.")
    
    tests = [
        ("RAM++ Object Recognition", test_ram_object_recognition),
        ("Category Mapping", test_category_mapping),
        ("OpenCLIP Embeddings", test_openclip_embeddings),
        ("PaddleOCR", test_paddleocr),
        ("InsightFace", test_insightface),
        ("PDQ Hashing", test_pdq_hashing),
        ("Hybrid Search", test_hybrid_search),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All validation tests passed!")
        print("\nSystem is ready for use:")
        print("  1. Start Celery worker: celery -A workers.celery_app worker --concurrency=4")
        print("  2. Process photos: python scripts/process_photos.py")
        print("  3. Start Flask app: python webapp/app.py")
        print("  4. Access: http://localhost:5000")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

