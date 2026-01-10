#!/usr/bin/env python3
"""
VM-003: Database Migration - Add version_preference column

This migration adds the version_preference column to the users table.
"""

import sqlite3
import os

def migrate_database():
    """Add version_preference column to users table."""
    db_path = "ralph_mode.db"

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Creating new database with updated schema...")
        # If database doesn't exist, init_db() will create it with the new schema
        from database import init_db
        init_db()
        print("✅ New database created with version_preference column")
        return

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'version_preference' in columns:
            print("✅ Column version_preference already exists. No migration needed.")
            return

        # Add the column
        print("Adding version_preference column to users table...")
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN version_preference VARCHAR(20) DEFAULT 'stable'
        """)

        conn.commit()
        print("✅ Migration successful! Added version_preference column.")

        # Verify the column was added
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'version_preference' in columns:
            print("✅ Verification passed: version_preference column exists.")
        else:
            print("❌ Verification failed: version_preference column not found after migration!")

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
