#!/usr/bin/env python3
"""
Migration script to migrate all SQL files to SQLite databases.

This script:
1. Creates necessary database schemas
2. Migrates logins.sql to data.db
3. Migrates tokens.sql to data.db
4. Migrates classes.sql to 2025.db
5. Migrates students.sql to 2025.db
6. Migrates tables-*.sql (counts) to 2025.db
"""

from pathlib import Path
from data_manager import (
    create_tables,
    migrate_logins_to_db,
    migrate_tokens_to_db,
    migrate_classes_to_db,
    migrate_students_to_db,
    migrate_counts_to_db,
)
from config import DATABASE_FILE, YEAR_DATABASE_FILE, DATA_DIR, CURRENT_YEAR_DIR

def main():
    print("=" * 60)
    print("Starting database migration...")
    print("=" * 60)

    # Create schemas if databases don't exist
    print("\n1. Creating database schemas...")
    schema_file = DATA_DIR / 'schema.sql'
    year_schema_file = CURRENT_YEAR_DIR / 'schema.sql'

    if schema_file.exists():
        create_tables(DATABASE_FILE, schema_file)
        print(f"   ✓ Created schema in {DATABASE_FILE}")
    else:
        print(f"   ⚠ Warning: {schema_file} not found")

    if year_schema_file.exists():
        create_tables(YEAR_DATABASE_FILE, year_schema_file)
        print(f"   ✓ Created schema in {YEAR_DATABASE_FILE}")
    else:
        print(f"   ⚠ Warning: {year_schema_file} not found")

    # Migrate logins
    print("\n2. Migrating logins.sql to data.db...")
    try:
        migrate_logins_to_db()
        print("   ✓ Logins migrated successfully")
    except Exception as e:
        print(f"   ✗ Error migrating logins: {e}")

    # Migrate tokens
    print("\n3. Migrating tokens.sql to data.db...")
    try:
        migrate_tokens_to_db()
        print("   ✓ Tokens migrated successfully")
    except Exception as e:
        print(f"   ✗ Error migrating tokens: {e}")

    # Migrate classes
    print("\n4. Migrating classes.sql to 2025.db...")
    try:
        migrate_classes_to_db()
        print("   ✓ Classes migrated successfully")
    except Exception as e:
        print(f"   ✗ Error migrating classes: {e}")

    # Migrate students
    print("\n5. Migrating students.sql to 2025.db...")
    try:
        migrate_students_to_db()
        print("   ✓ Students migrated successfully")
    except Exception as e:
        print(f"   ✗ Error migrating students: {e}")

    # Migrate counts
    print("\n6. Migrating tables-*.sql (counts) to 2025.db...")
    try:
        migrate_counts_to_db()
        print("   ✓ Counts migrated successfully")
    except Exception as e:
        print(f"   ✗ Error migrating counts: {e}")

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print(f"\nDatabases created:")
    print(f"  • {DATABASE_FILE}")
    print(f"  • {YEAR_DATABASE_FILE}")
    print("\nYou can now start the server with: python3 backend/program.py")

if __name__ == "__main__":
    main()
