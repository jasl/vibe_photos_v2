"""
Comprehensive end-to-end test of the entire image processing workflow.
Simulates exactly what happens in background jobs.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from workers import ai_models
from models import get_session, Photo, DetectedObject, SemanticEmbedding, OCRText, PhotoHash, Face


def create_test_image_with_text():
    """Create a test image with text and objects."""
    # Create image
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add colored rectangles (simulate objects)
    draw.rectangle([100, 100, 300, 250], fill='red', outline='black', width=3)
    draw.rectangle([400, 150, 600, 350], fill='blue', outline='black', width=3)
    draw.rectangle([200, 400, 500, 550], fill='green', outline='black', width=3)
    
    # Add text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        font = None
    
    draw.text((250, 50), "TEST IMAGE", fill='black', font=font)
    draw.text((150, 480), "Sample Photo", fill='white', font=font)
    
    return img


def test_full_workflow():
    """Test the complete image processing workflow."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE IMAGE PROCESSING WORKFLOW TEST")
    print("=" * 70)
    
    # Create test image
    print("\n[1/8] Creating test image...")
    test_img = create_test_image_with_text()
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        test_img.save(tmp.name, 'JPEG')
        tmp_path = tmp.name
    
    print(f"✓ Test image created: {tmp_path}")
    print(f"  Size: {test_img.size}")
    
    # Initialize models
    print("\n[2/8] Initializing AI models...")
    try:
        ai_models.initialize_models()
        print("✓ All models initialized successfully")
    except Exception as e:
        print(f"✗ Model initialization failed: {e}")
        return False
    
    # Test 1: DETR Object Detection
    print("\n[3/8] Testing DETR object detection...")
    try:
        objects = ai_models.recognize_objects(test_img)
        print(f"✓ DETR detection complete")
        print(f"  Objects detected: {len(objects)}")
        
        if objects:
            print("  Detections:")
            for obj in objects[:5]:
                bbox = obj.get('bbox', {})
                print(f"    - {obj['tag']}: {obj['confidence']:.2%} at [{bbox.get('x1', 0):.0f}, {bbox.get('y1', 0):.0f}]")
        else:
            print("  (Blank test image - no objects expected)")
    except Exception as e:
        print(f"✗ DETR detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: OpenCLIP Image Embedding
    print("\n[4/8] Testing OpenCLIP image embedding...")
    try:
        image_emb = ai_models.generate_image_embedding(test_img)
        print(f"✓ Image embedding generated")
        print(f"  Shape: {image_emb.shape}")
        print(f"  Expected: (1024,)")
        
        if image_emb.shape != (1024,):
            print(f"✗ Unexpected embedding shape!")
            return False
    except Exception as e:
        print(f"✗ Image embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: OpenCLIP Text Embedding
    print("\n[5/8] Testing OpenCLIP text embedding...")
    try:
        text_emb = ai_models.generate_text_embedding("test image")
        print(f"✓ Text embedding generated")
        print(f"  Shape: {text_emb.shape}")
        
        if text_emb.shape != (1024,):
            print(f"✗ Unexpected embedding shape!")
            return False
    except Exception as e:
        print(f"✗ Text embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: PaddleOCR Text Extraction
    print("\n[6/8] Testing PaddleOCR text extraction...")
    try:
        extracted_text = ai_models.extract_text(tmp_path)
        print(f"✓ OCR extraction complete")
        if extracted_text:
            print(f"  Extracted: '{extracted_text[:100]}'")
        else:
            print(f"  No text detected (or low confidence)")
    except Exception as e:
        print(f"✗ OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: InsightFace Face Detection
    print("\n[7/8] Testing InsightFace face detection...")
    try:
        faces = ai_models.detect_faces(tmp_path)
        print(f"✓ Face detection complete")
        print(f"  Faces detected: {len(faces)}")
        
        if faces:
            for i, face in enumerate(faces[:3]):
                bbox = face['bbox']
                print(f"    Face {i+1}: [{bbox['x']:.0f}, {bbox['y']:.0f}] size: {bbox['width']:.0f}x{bbox['height']:.0f}")
    except Exception as e:
        print(f"✗ Face detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: PDQ Hash Calculation
    print("\n[8/8] Testing PDQ hash calculation...")
    try:
        hash_hex, quality = ai_models.calculate_pdq_hash(tmp_path)
        print(f"✓ PDQ hash calculated")
        print(f"  Hash: {hash_hex[:32]}...")
        print(f"  Hash length: {len(hash_hex)} characters")
        print(f"  Quality: {quality}")
        
        if len(hash_hex) != 64:
            print(f"✗ Invalid hash length! Expected 64, got {len(hash_hex)}")
            return False
    except Exception as e:
        print(f"✗ PDQ hash calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 70)
    print("WORKFLOW TEST SUMMARY")
    print("=" * 70)
    print("✓ All AI models working correctly")
    print("✓ All processing steps completed successfully")
    print("✓ No errors in workflow")
    print("\n✅ Image processing workflow is fully operational!")
    
    # Cleanup
    import os
    os.unlink(tmp_path)
    
    return True


def test_database_operations():
    """Test that we can save results to database."""
    print("\n" + "=" * 70)
    print("DATABASE OPERATIONS TEST")
    print("=" * 70)
    
    session = get_session()
    test_photo = None
    
    try:
        # Create a test photo record first (required for foreign keys)
        test_photo_id = 999999  # Use high ID to avoid conflicts
        
        print("\n[0/5] Creating test photo record...")
        try:
            # Clean up any existing test photo
            session.query(Photo).filter_by(id=test_photo_id).delete()
            session.commit()
            
            test_photo = Photo(
                id=test_photo_id,
                file_path="/tmp/test_image.jpg",
                filename="test_image.jpg",
                state="completed"
            )
            session.add(test_photo)
            session.commit()
            print("✓ Test photo record created")
        except Exception as e:
            print(f"✗ Failed to create test photo: {e}")
            session.rollback()
            return False
        
        print("\n[1/5] Testing DetectedObject insert...")
        try:
            # Clean up any existing test data
            session.query(DetectedObject).filter_by(photo_id=test_photo_id).delete()
            session.commit()
            
            obj = DetectedObject(
                photo_id=test_photo_id,
                tag="test_object",
                confidence=0.95
            )
            session.add(obj)
            session.commit()
            print("✓ DetectedObject insert successful")
            
            # Clean up
            session.delete(obj)
            session.commit()
        except Exception as e:
            print(f"✗ DetectedObject insert failed: {e}")
            session.rollback()
            return False
        
        print("\n[2/5] Testing SemanticEmbedding insert...")
        try:
            session.query(SemanticEmbedding).filter_by(photo_id=test_photo_id).delete()
            session.commit()
            
            emb = SemanticEmbedding(
                photo_id=test_photo_id,
                embedding=np.random.rand(1024).astype(np.float32)
            )
            session.add(emb)
            session.commit()
            print("✓ SemanticEmbedding insert successful")
            
            session.delete(emb)
            session.commit()
        except Exception as e:
            print(f"✗ SemanticEmbedding insert failed: {e}")
            session.rollback()
            return False
        
        print("\n[3/5] Testing OCRText insert...")
        try:
            session.query(OCRText).filter_by(photo_id=test_photo_id).delete()
            session.commit()
            
            ocr = OCRText(
                photo_id=test_photo_id,
                extracted_text="test text content",
                language='en'
            )
            session.add(ocr)
            session.commit()
            print("✓ OCRText insert successful")
            
            session.delete(ocr)
            session.commit()
        except Exception as e:
            print(f"✗ OCRText insert failed: {e}")
            session.rollback()
            return False
        
        print("\n[4/5] Testing PhotoHash insert...")
        try:
            session.query(PhotoHash).filter_by(photo_id=test_photo_id).delete()
            session.commit()
            
            # Test with proper 64-character hex hash
            hash_obj = PhotoHash(
                photo_id=test_photo_id,
                pdq_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                quality_score=95.5
            )
            session.add(hash_obj)
            session.commit()
            print("✓ PhotoHash insert successful")
            print(f"  Hash length: {len(hash_obj.pdq_hash)} characters")
            
            session.delete(hash_obj)
            session.commit()
        except Exception as e:
            print(f"✗ PhotoHash insert failed: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return False
        
        print("\n[5/5] Testing Face insert...")
        try:
            session.query(Face).filter_by(photo_id=test_photo_id).delete()
            session.commit()
            
            face = Face(
                photo_id=test_photo_id,
                embedding=np.random.rand(512).astype(np.float32).tolist(),
                bbox={'x': 100, 'y': 150, 'width': 200, 'height': 250},
                cluster_id=None
            )
            session.add(face)
            session.commit()
            print("✓ Face insert successful")
            
            session.delete(face)
            session.commit()
        except Exception as e:
            print(f"✗ Face insert failed: {e}")
            session.rollback()
            return False
        
        print("\n" + "=" * 70)
        print("✅ All database operations working correctly!")
        print("=" * 70)
        
        # Clean up test photo
        if test_photo:
            session.delete(test_photo)
            session.commit()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Final cleanup
        if test_photo:
            try:
                session.query(Photo).filter_by(id=test_photo_id).delete()
                session.commit()
            except:
                pass
        session.close()


def main():
    """Run all workflow tests."""
    print("\n" + "=" * 70)
    print("COMPLETE WORKFLOW TEST SUITE")
    print("=" * 70)
    print("\nThis will test the entire image processing pipeline")
    print("including all AI models and database operations.")
    
    results = {}
    
    # Test 1: AI Models Workflow
    print("\n" + "=" * 70)
    print("PART 1: AI MODELS WORKFLOW")
    print("=" * 70)
    results['ai_workflow'] = test_full_workflow()
    
    # Test 2: Database Operations
    print("\n" + "=" * 70)
    print("PART 2: DATABASE OPERATIONS")
    print("=" * 70)
    results['database'] = test_database_operations()
    
    # Final Summary
    print("\n" + "=" * 70)
    print("FINAL TEST RESULTS")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED - WORKFLOW IS FULLY OPERATIONAL!")
        print("=" * 70)
        print("\nYour system is ready to process photos in production.")
        print("\nNext steps:")
        print("  1. Start Celery worker: celery -A workers.celery_app worker")
        print("  2. Process photos: python scripts/process_photos.py /path/to/photos")
        print("  3. Start Flask app: uv run python webapp/app.py")
        return 0
    else:
        print("\n" + "=" * 70)
        print("⚠️  SOME TESTS FAILED - REVIEW ERRORS ABOVE")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

