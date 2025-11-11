"""
System status checker for AI Photos Management.
Displays current processing status and system health.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from models import get_session, Photo, PhotoState


def check_docker_services():
    """Check if Docker services are running."""
    print("\n" + "=" * 60)
    print("Docker Services")
    print("=" * 60)
    
    import subprocess
    
    try:
        result = subprocess.run(
            ['docker-compose', 'ps'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if 'postgres' in result.stdout and 'Up' in result.stdout:
            print("✓ PostgreSQL: Running")
        else:
            print("✗ PostgreSQL: Not running")
            
        if 'redis' in result.stdout and 'Up' in result.stdout:
            print("✓ Redis: Running")
        else:
            print("✗ Redis: Not running")
            
    except Exception as e:
        print(f"✗ Docker services check failed: {e}")
        print("  Run: docker-compose ps")


def check_database_connection():
    """Check database connection and photo counts."""
    print("\n" + "=" * 60)
    print("Database Status")
    print("=" * 60)
    
    try:
        session = get_session()
        
        # Get photo counts by state
        total = session.query(Photo).count()
        completed = session.query(Photo).filter(Photo.state == PhotoState.COMPLETED).count()
        pending = session.query(Photo).filter(Photo.state == PhotoState.PENDING).count()
        failed = session.query(Photo).filter(Photo.state == PhotoState.FAILED).count()
        partial = session.query(Photo).filter(Photo.state == PhotoState.PARTIAL).count()
        
        processing_states = [
            PhotoState.PREPROCESSING,
            PhotoState.PROCESSING_OBJECTS,
            PhotoState.PROCESSING_EMBEDDINGS,
            PhotoState.PROCESSING_OCR,
            PhotoState.PROCESSING_FACES,
            PhotoState.PROCESSING_HASH,
            PhotoState.CHECKING_DUPLICATES
        ]
        processing = session.query(Photo).filter(Photo.state.in_(processing_states)).count()
        
        session.close()
        
        print(f"✓ Database connection successful")
        print(f"\nPhoto Processing Status:")
        print(f"  Total photos: {total}")
        print(f"  ✓ Completed: {completed}")
        print(f"  ⏳ Processing: {processing}")
        print(f"  ⏸️  Pending: {pending}")
        print(f"  ⚠️  Partial: {partial}")
        print(f"  ✗ Failed: {failed}")
        
        if total > 0:
            completion_pct = (completed / total) * 100
            print(f"\n  Progress: {completion_pct:.1f}% complete")
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")


def check_flask_app():
    """Check if Flask app is running."""
    print("\n" + "=" * 60)
    print("Flask Web Application")
    print("=" * 60)
    
    try:
        response = requests.get('http://localhost:5000/api/stats', timeout=2)
        
        if response.status_code == 200:
            print("✓ Flask app is running")
            print("  URL: http://localhost:5000")
            
            stats = response.json()
            print(f"\n  API Stats:")
            print(f"    Total: {stats['total_photos']}")
            print(f"    Completed: {stats['completed']}")
            print(f"    Progress: {stats['completion_percentage']:.1f}%")
        else:
            print(f"⚠️ Flask app returned status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Flask app is not running")
        print("  Start with: python webapp/app.py")
    except Exception as e:
        print(f"✗ Flask app check failed: {e}")


def check_celery_worker():
    """Check if Celery worker is running."""
    print("\n" + "=" * 60)
    print("Celery Worker")
    print("=" * 60)
    
    try:
        from workers.celery_app import app
        
        # Check active workers
        inspect = app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            print(f"✓ Celery worker(s) running: {len(active_workers)}")
            for worker_name in active_workers.keys():
                print(f"  - {worker_name}")
                
            # Check active tasks
            for worker, tasks in active_workers.items():
                print(f"\n  Active tasks on {worker}: {len(tasks)}")
        else:
            print("✗ No Celery workers detected")
            print("  Start with: celery -A workers.celery_app worker --concurrency=4")
            
    except Exception as e:
        print(f"✗ Celery worker check failed: {e}")
        print("  Make sure Redis is running")


def main():
    """Run all status checks."""
    print("\n" + "=" * 60)
    print("AI Photos Management - System Status")
    print("=" * 60)
    
    check_docker_services()
    check_database_connection()
    check_celery_worker()
    check_flask_app()
    
    print("\n" + "=" * 60)
    print("Status Check Complete")
    print("=" * 60)
    print("\nNext steps:")
    print("  - View gallery: http://localhost:5000")
    print("  - Search photos: http://localhost:5000/search")
    print("  - Check logs: docker-compose logs")
    print()


if __name__ == "__main__":
    main()

