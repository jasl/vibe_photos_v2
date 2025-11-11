"""
Script to scan photos directory and queue processing tasks.
Scans for new photos, creates database records, and queues Celery tasks.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm
from config import settings
from models import Photo, PhotoState, get_session
from utils import is_supported_format, get_file_size
from workers.tasks import process_single_image


def scan_photos_directory() -> list:
    """
    Scan photos directory for supported image files.
    
    Returns:
        List of Path objects for image files
    """
    photos_dir = settings.PHOTOS_DIR
    
    if not photos_dir.exists():
        print(f"✗ Photos directory not found: {photos_dir}")
        print(f"  Please check PHOTOS_DIR in your .env file")
        return []
    
    print(f"Scanning directory: {photos_dir}")
    print(f"Supported formats: {', '.join(settings.SUPPORTED_FORMATS)}")
    
    image_files = []
    
    # Recursively find all image files
    for ext in settings.SUPPORTED_FORMATS:
        pattern = f"**/*.{ext}"
        found_files = list(photos_dir.rglob(pattern))
        image_files.extend(found_files)
        
        # Also search for uppercase extensions
        pattern_upper = f"**/*.{ext.upper()}"
        found_files_upper = list(photos_dir.rglob(pattern_upper))
        image_files.extend(found_files_upper)
    
    # Remove duplicates
    image_files = list(set(image_files))
    
    print(f"✓ Found {len(image_files)} image files")
    
    return image_files


def create_photo_records(image_files: list) -> list:
    """
    Create database records for new photos.
    
    Args:
        image_files: List of Path objects
        
    Returns:
        List of photo IDs that need processing
    """
    session = get_session()
    new_photos = []
    skipped_photos = 0
    
    print("\nCreating database records...")
    
    try:
        for image_file in tqdm(image_files, desc="Creating records"):
            file_path = str(image_file.absolute())
            
            # Check if already exists
            existing = session.query(Photo).filter_by(file_path=file_path).first()
            
            if existing:
                # Only queue if still pending or failed
                if existing.state in (PhotoState.PENDING, PhotoState.FAILED):
                    new_photos.append(existing.id)
                else:
                    skipped_photos += 1
                continue
            
            # Create new photo record
            try:
                file_size = get_file_size(image_file)
                
                photo = Photo(
                    file_path=file_path,
                    filename=image_file.name,
                    state=PhotoState.PENDING,
                    file_size=file_size,
                    created_at=datetime.fromtimestamp(image_file.stat().st_mtime)
                )
                
                session.add(photo)
                session.flush()
                
                new_photos.append(photo.id)
                
            except Exception as e:
                print(f"\n⚠️ Error creating record for {image_file.name}: {e}")
                continue
        
        session.commit()
        
        print(f"\n✓ Created {len(new_photos)} new photo records")
        if skipped_photos > 0:
            print(f"  Skipped {skipped_photos} already processed photos")
        
        return new_photos
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ Error creating photo records: {e}")
        raise
        
    finally:
        session.close()


def queue_processing_tasks(photo_ids: list):
    """
    Queue Celery tasks for photo processing.
    
    Args:
        photo_ids: List of photo IDs to process
    """
    if not photo_ids:
        print("\nNo photos to process.")
        return
    
    print(f"\nQueuing {len(photo_ids)} photos for processing...")
    print("This may take a while. Monitor progress at http://localhost:5000/api/stats")
    
    queued = 0
    failed = 0
    
    for photo_id in tqdm(photo_ids, desc="Queuing tasks"):
        try:
            # Queue the task
            process_single_image.delay(photo_id)
            queued += 1
            
        except Exception as e:
            print(f"\n⚠️ Failed to queue photo {photo_id}: {e}")
            failed += 1
            continue
    
    print(f"\n✓ Successfully queued {queued} tasks")
    if failed > 0:
        print(f"  Failed to queue {failed} tasks")
    
    print("\nProcessing has started!")
    print(f"  Monitor progress: http://localhost:5000/api/stats")
    print(f"  View gallery: http://localhost:5000")
    print(f"  Celery workers: Check worker logs for detailed progress")


def main():
    """Main function."""
    print("=" * 60)
    print("AI Photos Management - Photo Processing Script")
    print("=" * 60)
    print()
    
    # Check configuration
    print(f"Photos directory: {settings.PHOTOS_DIR}")
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")
    print(f"Redis: {settings.REDIS_URL}")
    print()
    
    # Scan for photos
    image_files = scan_photos_directory()
    
    if not image_files:
        print("\n✗ No photos found to process.")
        return 1
    
    # Confirm processing
    print(f"\nReady to process up to {len(image_files)} photos.")
    print("Note: Photos already processed will be skipped.")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() != "yes":
        print("Operation cancelled.")
        return 0
    
    # Create database records
    photo_ids = create_photo_records(image_files)
    
    # Queue processing tasks
    queue_processing_tasks(photo_ids)
    
    print("\n" + "=" * 60)
    print("✓ Script completed successfully")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

