"""
Seed script for initial categories and tag-to-category mappings.
Populates the database with predefined categories and common tag mappings.
"""

from models import Category, TagCategoryMapping, get_session


# Seed data for categories and their associated tags
SEED_DATA = {
    "electronics": {
        "description": "Electronic devices and tech products",
        "tags": [
            "iPhone", "iPad", "MacBook", "laptop", "computer", "phone", "camera",
            "tablet", "headphones", "monitor", "keyboard", "mouse", "smartphone",
            "smartwatch", "earbuds", "speaker", "screen", "display", "device",
            "electronics", "gadget", "technology", "tech", "cell phone", "tv",
            "remote", "remote control"
        ]
    },
    "food": {
        "description": "Food and beverages",
        "tags": [
            "pizza", "burger", "coffee", "cake", "pasta", "sushi", "salad",
            "beverage", "fruit", "bread", "dessert", "meal", "breakfast",
            "lunch", "dinner", "snack", "sandwich", "soup", "rice", "noodles",
            "tea", "juice", "food", "drink", "restaurant", "dish", "plate",
            "bowl", "banana", "apple", "orange", "broccoli", "carrot", "hot dog"
        ]
    },
    "landscape": {
        "description": "Natural landscapes and outdoor scenes",
        "tags": [
            "mountain", "beach", "sunset", "forest", "ocean", "sky", "nature",
            "park", "river", "lake", "tree", "cloud", "sunrise", "hill",
            "valley", "coast", "island", "waterfall", "desert", "field",
            "garden", "scenery", "outdoor", "landscape", "view"
        ]
    },
    "documents": {
        "description": "Screenshots, documents, and text-based images",
        "tags": [
            "screenshot", "document", "receipt", "certificate", "text", "paper",
            "form", "invoice", "ticket", "card", "letter", "note", "page",
            "book", "magazine", "newspaper", "report", "contract", "presentation",
            "slide", "spreadsheet", "chart", "graph", "table"
        ]
    },
    "people": {
        "description": "Photos with people",
        "tags": [
            "person", "face", "portrait", "group", "crowd", "selfie", "family",
            "people", "man", "woman", "child", "baby", "friend", "couple",
            "team", "gathering", "party", "meeting", "wedding", "smile",
            "human", "individual"
        ]
    },
    "vehicles": {
        "description": "Cars, public transport, and other vehicles",
        "tags": [
            "car", "bus", "truck", "train", "airplane", "boat", "bicycle",
            "motorcycle", "scooter", "van", "taxi", "transport", "vehicle",
            "traffic", "jeep", "pickup", "race car"
        ]
    }
}


def seed_categories():
    """Seed categories and tag mappings into the database."""
    session = get_session()
    
    try:
        # Check if already seeded
        existing_count = session.query(Category).count()
        if existing_count > 0:
            print(f"⚠ Database already has {existing_count} categories. Skipping seed.")
            print("  To re-seed, please clear the categories table first.")
            return
        
        print("Starting database seeding...")
        print("=" * 60)
        
        for category_name, category_data in SEED_DATA.items():
            # Create category
            category = Category(
                name=category_name,
                description=category_data["description"]
            )
            session.add(category)
            session.flush()  # Flush to get the category ID
            
            print(f"\n✓ Created category: {category_name}")
            print(f"  Description: {category_data['description']}")
            print(f"  Tags: {len(category_data['tags'])} tags")
            
            # Create tag mappings
            tag_count = 0
            for tag in category_data["tags"]:
                # Check if tag already exists
                existing_mapping = session.query(TagCategoryMapping).filter_by(tag=tag).first()
                if existing_mapping:
                    print(f"  ⚠ Tag '{tag}' already mapped to category {existing_mapping.category_id}, skipping")
                    continue
                
                mapping = TagCategoryMapping(
                    tag=tag,
                    category_id=category.id
                )
                session.add(mapping)
                tag_count += 1
            
            print(f"  ✓ Added {tag_count} tag mappings")
        
        # Commit all changes
        session.commit()
        
        print("\n" + "=" * 60)
        print("✓ Database seeding completed successfully!")
        print("\nSummary:")
        
        # Print summary
        total_categories = session.query(Category).count()
        total_mappings = session.query(TagCategoryMapping).count()
        
        print(f"  Total categories: {total_categories}")
        print(f"  Total tag mappings: {total_mappings}")
        
        # Print categories with counts
        print("\nCategories:")
        for category in session.query(Category).all():
            count = session.query(TagCategoryMapping).filter_by(category_id=category.id).count()
            print(f"  - {category.name}: {count} tags")
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ Error during seeding: {e}")
        raise
    finally:
        session.close()


def clear_categories():
    """Clear all categories and tag mappings (use with caution!)."""
    session = get_session()
    
    try:
        mapping_count = session.query(TagCategoryMapping).count()
        category_count = session.query(Category).count()
        
        if category_count == 0 and mapping_count == 0:
            print("Database is already empty.")
            return
        
        print(f"⚠ WARNING: This will delete {category_count} categories and {mapping_count} tag mappings!")
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() != "yes":
            print("Operation cancelled.")
            return
        
        # Delete all mappings first (foreign key constraint)
        session.query(TagCategoryMapping).delete()
        session.query(Category).delete()
        session.commit()
        
        print("✓ All categories and tag mappings have been deleted.")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error during cleanup: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_categories()
    else:
        seed_categories()

