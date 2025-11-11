"""
Test web app endpoints and functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
from PIL import Image
from models import get_session, Photo, PhotoState, DetectedObject, PhotoTag, Category
from config import settings


def setup_test_photo():
    """Create a test photo with thumbnail for testing."""
    print("=" * 70)
    print("Setting up test photo...")
    print("=" * 70)
    
    session = get_session()
    
    try:
        # Clean up existing test photo (delete related objects first due to foreign keys)
        session.query(PhotoTag).filter_by(photo_id=888888).delete()
        session.query(DetectedObject).filter_by(photo_id=888888).delete()
        session.query(Photo).filter_by(id=888888).delete()
        session.commit()
        
        # Create test image
        test_img = Image.new('RGB', (800, 600), color='blue')
        
        # Save original
        original_path = Path(settings.PHOTOS_DIR) / "test_webapp_photo.jpg"
        original_path.parent.mkdir(parents=True, exist_ok=True)
        test_img.save(original_path, 'JPEG')
        
        # Create thumbnail
        settings.THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
        thumbnail_path = settings.THUMBNAIL_DIR / "thumb_test_webapp_photo.jpg"
        
        thumb_img = test_img.copy()
        thumb_img.thumbnail((settings.THUMBNAIL_SIZE, settings.THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
        thumb_img.save(thumbnail_path, 'JPEG', quality=85)
        
        # Create photo record
        photo = Photo(
            id=888888,
            file_path=str(original_path),
            filename="test_webapp_photo.jpg",
            thumbnail_path=str(thumbnail_path),  # Absolute path
            state=PhotoState.COMPLETED,
            width=800,
            height=600,
            file_size=original_path.stat().st_size
        )
        session.add(photo)
        
        # Add some test PhotoTags (unique tags)
        tag1 = PhotoTag(photo_id=888888, tag="test_object_1", confidence=0.95)
        tag2 = PhotoTag(photo_id=888888, tag="test_object_2", confidence=0.87)
        session.add(tag1)
        session.add(tag2)
        
        # Add some test DetectedObjects (instances)
        obj1 = DetectedObject(photo_id=888888, tag="test_object_1", confidence=0.95)
        obj2 = DetectedObject(photo_id=888888, tag="test_object_2", confidence=0.87)
        session.add(obj1)
        session.add(obj2)
        
        session.commit()
        
        print(f"✓ Test photo created:")
        print(f"  ID: {photo.id}")
        print(f"  File: {original_path}")
        print(f"  Thumbnail: {thumbnail_path}")
        print(f"  Thumbnail exists: {thumbnail_path.exists()}")
        print(f"  Objects: 2")
        
        return photo.id
        
    except Exception as e:
        print(f"✗ Failed to setup test photo: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return None
    finally:
        session.close()


def test_webapp_routes():
    """Test webapp routes."""
    print("\n" + "=" * 70)
    print("Testing Web App Routes")
    print("=" * 70)
    
    from webapp.app import app
    
    test_photo_id = 888888
    
    with app.test_client() as client:
        # Test 1: Index page
        print("\n[1/5] Testing index page (/)...")
        try:
            response = client.get('/')
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print("  ✓ Index page loads")
            else:
                print(f"  ✗ Index page error: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ Index page failed: {e}")
            return False
        
        # Test 2: Thumbnail endpoint
        print("\n[2/5] Testing thumbnail endpoint (/thumbnail/<id>)...")
        try:
            response = client.get(f'/thumbnail/{test_photo_id}')
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✓ Thumbnail serves correctly")
                print(f"  Content-Type: {response.content_type}")
                print(f"  Size: {len(response.data)} bytes")
            else:
                print(f"  ✗ Thumbnail error: {response.status_code}")
                print(f"  Response: {response.data.decode()[:200]}")
                return False
        except Exception as e:
            print(f"  ✗ Thumbnail failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 3: Photo detail page
        print("\n[3/5] Testing photo detail page (/photo/<id>)...")
        try:
            response = client.get(f'/photo/{test_photo_id}')
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print("  ✓ Photo detail page loads")
            else:
                print(f"  ✗ Photo detail error: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ Photo detail failed: {e}")
            return False
        
        # Test 4: Search page
        print("\n[4/5] Testing search page (/search)...")
        try:
            response = client.get('/search?q=test')
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print("  ✓ Search page loads")
            else:
                print(f"  ✗ Search error: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ Search failed: {e}")
            return False
        
        # Test 5: Stats API
        print("\n[5/5] Testing stats API (/api/stats)...")
        try:
            response = client.get('/api/stats')
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                stats = response.get_json()
                print("  ✓ Stats API working")
                print(f"  Total photos: {stats.get('total_photos')}")
                print(f"  Completed: {stats.get('completed')}")
            else:
                print(f"  ✗ Stats API error: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ Stats API failed: {e}")
            return False
    
    return True


def cleanup_test_photo():
    """Remove test photo and files."""
    print("\n" + "=" * 70)
    print("Cleaning up test photo...")
    print("=" * 70)
    
    session = get_session()
    
    try:
        # Delete database records
        session.query(PhotoTag).filter_by(photo_id=888888).delete()
        session.query(DetectedObject).filter_by(photo_id=888888).delete()
        session.query(Photo).filter_by(id=888888).delete()
        session.commit()
        
        # Delete files
        original_path = Path(settings.PHOTOS_DIR) / "test_webapp_photo.jpg"
        thumbnail_path = settings.THUMBNAIL_DIR / "thumb_test_webapp_photo.jpg"
        
        if original_path.exists():
            original_path.unlink()
        if thumbnail_path.exists():
            thumbnail_path.unlink()
        
        print("✓ Test photo cleaned up")
        
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        session.close()


def main():
    """Run web app tests."""
    print("\n" + "=" * 70)
    print("WEB APP FUNCTIONALITY TEST")
    print("=" * 70)
    print("\nThis will test all web app routes and thumbnail serving.")
    
    # Setup
    photo_id = setup_test_photo()
    if not photo_id:
        print("\n✗ Setup failed - cannot continue tests")
        return 1
    
    # Test routes
    success = test_webapp_routes()
    
    # Cleanup
    cleanup_test_photo()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    if success:
        print("✅ ALL WEB APP TESTS PASSED!")
        print("\nYour web app is fully functional:")
        print("  ✓ Index page loads")
        print("  ✓ Thumbnails serve correctly")
        print("  ✓ Photo detail pages work")
        print("  ✓ Search functionality works")
        print("  ✓ API endpoints respond")
        print("\nStart the web app:")
        print("  uv run python webapp/app.py")
        print("  Open: http://localhost:5000")
        return 0
    else:
        print("✗ SOME WEB APP TESTS FAILED")
        print("\nReview errors above and check:")
        print("  - Thumbnail paths in database")
        print("  - THUMBNAIL_DIR configuration")
        print("  - File permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())

