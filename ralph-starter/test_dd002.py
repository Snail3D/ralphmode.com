#!/usr/bin/env python3
"""
DD-002: Test Duplicate Merging and Upvoting

This script tests the duplicate detection and merging functionality.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_db, Feedback, User
from duplicate_detector import get_duplicate_detector

def test_dd002():
    """Test duplicate merging and upvoting functionality."""
    print("=" * 70)
    print("DD-002: Duplicate Merging and Upvoting Test")
    print("=" * 70)

    # Initialize database
    print("\n1. Setting up test database...")
    init_db()

    try:
        # Create test user
        with get_db() as db:
            # Clean up existing test data
            db.query(Feedback).delete()
            db.query(User).filter(User.telegram_id == 999999).delete()
            db.commit()

            # Create test user
            user = User(
                telegram_id=999999,
                username="test_user",
                subscription_tier="free"
            )
            db.add(user)
            db.flush()

            print(f"   Created test user: {user.id}")

            # Create original feedback
            original = Feedback(
                user_id=user.id,
                feedback_type="bug",
                content="The login button is not working on mobile devices",
                status="pending",
                priority_score=5.0,
                created_at=datetime.utcnow()
            )
            db.add(original)
            db.flush()

            original_id = original.id
            print(f"   Created original feedback #{original_id}: '{original.content}'")

            # Create duplicate feedback
            duplicate = Feedback(
                user_id=user.id,
                feedback_type="bug",
                content="Mobile login button doesn't work",
                status="pending",
                priority_score=5.0,
                created_at=datetime.utcnow()
            )
            db.add(duplicate)
            db.flush()

            duplicate_id = duplicate.id
            print(f"   Created duplicate feedback #{duplicate_id}: '{duplicate.content}'")

        # Test duplicate detection
        print("\n2. Testing duplicate detection...")
        detector = get_duplicate_detector()

        is_dup, found_original_id, similarity = detector.check_duplicate(
            content="Mobile login button doesn't work",
            feedback_type="bug"
        )

        if is_dup:
            print(f"   ✅ Duplicate detected!")
            print(f"   Original ID: {found_original_id}")
            print(f"   Similarity: {similarity:.2f}")
        else:
            print(f"   ❌ Duplicate NOT detected (this may be expected if Groq API key is not set)")
            print(f"   Skipping merge test...")
            return

        # Test duplicate merging
        print("\n3. Testing duplicate merging...")
        success, message = detector.merge_duplicate(
            duplicate_feedback_id=duplicate_id,
            original_feedback_id=original_id,
            similarity_score=similarity
        )

        if success:
            print(f"   ✅ Merge successful: {message}")
        else:
            print(f"   ❌ Merge failed: {message}")
            return

        # Verify merge results
        print("\n4. Verifying merge results...")
        with get_db() as db:
            # Check original feedback
            original = db.query(Feedback).filter(Feedback.id == original_id).first()
            if original:
                print(f"   Original feedback #{original_id}:")
                print(f"     - upvote_count: {original.upvote_count}")
                print(f"     - priority_score: {original.priority_score}")
                print(f"     - status: {original.status}")

                if original.upvote_count == 1:
                    print(f"   ✅ Upvote count incremented correctly")
                else:
                    print(f"   ❌ Expected upvote_count=1, got {original.upvote_count}")

                # Priority score should be 5.0 (original) + 0.5 (upvote) = 5.5
                expected_priority = 5.5
                if abs(original.priority_score - expected_priority) < 0.01:
                    print(f"   ✅ Priority score updated correctly (+0.5)")
                else:
                    print(f"   ❌ Expected priority_score={expected_priority}, got {original.priority_score}")

            # Check duplicate feedback
            duplicate = db.query(Feedback).filter(Feedback.id == duplicate_id).first()
            if duplicate:
                print(f"\n   Duplicate feedback #{duplicate_id}:")
                print(f"     - is_duplicate_of: {duplicate.is_duplicate_of}")
                print(f"     - status: {duplicate.status}")
                print(f"     - rejection_reason: {duplicate.rejection_reason}")

                if duplicate.is_duplicate_of == original_id:
                    print(f"   ✅ Duplicate marked correctly")
                else:
                    print(f"   ❌ Expected is_duplicate_of={original_id}, got {duplicate.is_duplicate_of}")

                if duplicate.status == "rejected":
                    print(f"   ✅ Duplicate status set to rejected")
                else:
                    print(f"   ❌ Expected status='rejected', got '{duplicate.status}'")

        print("\n" + "=" * 70)
        print("DD-002 Test Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_dd002()
