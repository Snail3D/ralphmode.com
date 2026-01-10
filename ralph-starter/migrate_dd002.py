#!/usr/bin/env python3
"""
DD-002: Database Migration - Add upvote_count column

This migration adds the upvote_count column to the feedback table.
"""

import sqlite3
import os

def migrate_database():
    """Add upvote_count column to feedback table."""
    db_path = "ralph_mode.db"

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Creating new database with updated schema...")
        # If database doesn't exist, init_db() will create it with the new schema
        from database import init_db
        init_db()
        print("✅ New database created with upvote_count column")
        return

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(feedback)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'upvote_count' in columns:
            print("✅ Column upvote_count already exists. No migration needed.")
            return

        # Add the column
        print("Adding upvote_count column to feedback table...")
        cursor.execute("""
            ALTER TABLE feedback
            ADD COLUMN upvote_count INTEGER NOT NULL DEFAULT 0
        """)

        conn.commit()
        print("✅ Migration successful! Added upvote_count column.")

        # Verify the column was added
        cursor.execute("PRAGMA table_info(feedback)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'upvote_count' in columns:
            print("✅ Verification passed: upvote_count column exists.")
        else:
            print("❌ Verification failed: upvote_count column not found after migration!")

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
