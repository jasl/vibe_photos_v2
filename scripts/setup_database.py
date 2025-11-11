"""
Quick setup script to initialize database and seed data.
Combines init_db and seed_categories into one command.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import init_db
from scripts.seed_categories import seed_categories


def main():
    """Run database initialization and seeding."""
    print("=" * 60)
    print("Database Setup - AI Photos Management")
    print("=" * 60)
    print()
    
    try:
        # Initialize database
        print("Step 1: Creating database tables...")
        init_db()
        print()
        
        # Seed categories
        print("Step 2: Seeding categories and tag mappings...")
        seed_categories()
        print()
        
        print("=" * 60)
        print("✓ Database setup completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Download models: python scripts/download_models.py")
        print("  2. Start Celery worker")
        print("  3. Process photos: python scripts/process_photos.py")
        print("  4. Start Flask app: python webapp/app.py")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

