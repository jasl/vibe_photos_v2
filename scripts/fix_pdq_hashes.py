"""
Script to fix PDQ hashes that were stored incorrectly.

Old format: 512-character binary string (e.g., "010001...")
New format: 64-character hex string (e.g., "a3f2b1...")

This script deletes invalid hashes so they can be regenerated.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import get_session, PhotoHash
from sqlalchemy import func


def fix_pdq_hashes():
    """Delete PDQ hashes that are the wrong length."""
    print("=" * 60)
    print("PDQ Hash Cleanup Script")
    print("=" * 60)
    
    session = get_session()
    
    try:
        # Count total hashes
        total_count = session.query(func.count(PhotoHash.id)).scalar()
        print(f"\nTotal photo hashes in database: {total_count}")
        
        if total_count == 0:
            print("\n✓ No hashes to fix (database is empty)")
            return
        
        # Find hashes with wrong length (should be exactly 64 characters)
        invalid_hashes = session.query(PhotoHash).filter(
            func.length(PhotoHash.pdq_hash) != 64
        ).all()
        
        invalid_count = len(invalid_hashes)
        
        if invalid_count == 0:
            print("\n✓ All hashes are valid (64 characters)")
            print("\nNo cleanup needed!")
            return
        
        print(f"\n⚠️  Found {invalid_count} invalid hashes:")
        
        # Show sample of invalid hashes
        for i, hash_record in enumerate(invalid_hashes[:5]):
            hash_len = len(hash_record.pdq_hash)
            hash_preview = hash_record.pdq_hash[:20] + "..."
            print(f"  - Photo ID {hash_record.photo_id}: {hash_len} chars ({hash_preview})")
        
        if invalid_count > 5:
            print(f"  ... and {invalid_count - 5} more")
        
        # Confirm deletion
        print("\n" + "-" * 60)
        print("These invalid hashes will be deleted.")
        print("They will be regenerated when photos are reprocessed.")
        print("-" * 60)
        
        response = input("\nProceed with deletion? (yes/no): ").strip().lower()
        
        if response != "yes":
            print(f"\nDeletion cancelled (you typed: '{response}').")
            return
        
        # Delete invalid hashes
        print(f"\n🗑️  Deleting {invalid_count} invalid hashes...")
        
        deleted_count = session.query(PhotoHash).filter(
            func.length(PhotoHash.pdq_hash) != 64
        ).delete(synchronize_session='fetch')
        
        session.commit()
        
        print(f"✓ Deleted {deleted_count} invalid hashes")
        
        # Show final stats
        remaining_count = session.query(func.count(PhotoHash.id)).scalar()
        print(f"\nFinal stats:")
        print(f"  - Valid hashes remaining: {remaining_count}")
        print(f"  - Invalid hashes deleted: {deleted_count}")
        
        print("\n✓ Cleanup complete!")
        print("\nNext steps:")
        print("  1. Restart Celery worker to pick up the fix")
        print("  2. Invalid hashes will be regenerated automatically")
        print("  3. Or manually trigger reprocessing if needed")
        
    except Exception as e:
        print(f"\n✗ Error during cleanup: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    fix_pdq_hashes()

