#!/usr/bin/env python3
"""
Initialize the database - create all tables
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from database import init_db, Base, engine
from sqlalchemy import inspect


def main():
    print("🔧 Initializing database...")

    # Check if tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        print(f"⚠️  Database already has tables: {existing_tables}")
        response = input("Drop and recreate? (y/N): ").strip().lower()
        if response == 'y':
            print("🗑️  Dropping existing tables...")
            Base.metadata.drop_all(bind=engine)
        else:
            print("✅ Keeping existing tables")
            return

    # Create all tables
    print("📦 Creating tables...")
    init_db()

    # Verify
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✅ Created tables: {tables}")

    # Show table schemas
    for table in tables:
        columns = inspector.get_columns(table)
        print(f"\n  📋 {table}:")
        for col in columns:
            print(f"      - {col['name']}: {col['type']}")


if __name__ == "__main__":
    main()