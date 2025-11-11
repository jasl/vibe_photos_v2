"""Idempotent script to backfill category/tag mappings in existing databases."""

from collections import defaultdict

from models import Category, TagCategoryMapping, get_session

from scripts.seed_categories import SEED_DATA


def sync_categories_and_tags() -> None:
    """Ensure all seed categories and tag mappings exist without duplication."""
    session = get_session()

    created_categories = 0
    updated_descriptions = 0
    created_mappings = 0
    skipped_mappings = 0
    mismatched_tags = defaultdict(list)

    try:
        for category_name, category_data in SEED_DATA.items():
            category = session.query(Category).filter_by(name=category_name).first()

            if category is None:
                category = Category(
                    name=category_name,
                    description=category_data["description"],
                )
                session.add(category)
                session.flush()
                created_categories += 1
                print(f"✓ Created missing category '{category_name}'")
            elif category.description != category_data["description"]:
                category.description = category_data["description"]
                updated_descriptions += 1
                print(
                    "✓ Updated description for category "
                    f"'{category_name}' to match seed data"
                )

            for tag in category_data["tags"]:
                mapping = session.query(TagCategoryMapping).filter_by(tag=tag).first()

                if mapping is None:
                    session.add(
                        TagCategoryMapping(tag=tag, category_id=category.id)
                    )
                    created_mappings += 1
                    continue

                if mapping.category_id != category.id:
                    mismatched_tags[category_name].append(tag)
                    continue

                skipped_mappings += 1

        session.commit()

        print("\n=== Sync summary ===")
        print(f"New categories created: {created_categories}")
        print(f"Category descriptions updated: {updated_descriptions}")
        print(f"New tag mappings created: {created_mappings}")
        print(f"Existing mappings kept: {skipped_mappings}")

        if mismatched_tags:
            print("\n⚠ The following tags already map to a different category:")
            for category_name, tags in mismatched_tags.items():
                joined_tags = ", ".join(sorted(tags))
                print(
                    f"  - Desired category '{category_name}': {joined_tags}"
                )
            print("  Review these manually before reassigning.")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Starting category and tag sync...")
    sync_categories_and_tags()
    print("\n✓ Category/tag sync complete.")

