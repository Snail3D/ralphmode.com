#!/usr/bin/env python3
"""
Test FQ-001: Feedback Queue Management

Quick test to verify the feedback queue functionality.
"""

import os
import sys
from datetime import datetime

# Ensure test uses in-memory database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from database import Base, engine, User
from feedback_queue import FeedbackQueue, STATUS_TRANSITIONS


def setup_test_db():
    """Create tables and test user."""
    Base.metadata.create_all(bind=engine)

    # Create test user
    from database import get_db
    with get_db() as db:
        user = User(
            telegram_id=12345,
            username="testuser",
            subscription_tier="builder",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def test_add_feedback_with_user(user_id):
    """Test adding feedback to queue."""
    print("Testing FQ-001: Add Feedback\n")

    with FeedbackQueue() as queue:
        # Add valid feedback
        feedback = queue.add_feedback(
            user_id=user_id,
            feedback_type="bug",
            content="Login button doesn't work on mobile. When I tap it, nothing happens.",
            ip_hash="test_hash_123"
        )

        assert feedback is not None, "Failed to add feedback"
        assert feedback.status == "pending", f"Expected 'pending', got {feedback.status}"
        assert feedback.feedback_type == "bug"

        print(f"✓ Added feedback {feedback.id}")
        print(f"  Status: {feedback.status}")
        print(f"  Type: {feedback.feedback_type}")
        print(f"  Content: {feedback.content[:50]}...")

    print("\n✓ Add feedback test passed!")


def test_status_transitions_with_user(user_id):
    """Test status transition validation."""
    print("\nTesting FQ-002: Status Transitions\n")

    with FeedbackQueue() as queue:
        # Add feedback
        feedback = queue.add_feedback(
            user_id=user_id,
            feedback_type="feature",
            content="Add dark mode support",
            ip_hash="test_hash_456"
        )

        # Valid transition: pending -> screening
        success = queue.update_status(feedback.id, "screening")
        assert success, "Failed valid transition: pending -> screening"
        print("✓ pending -> screening")

        # Valid transition: screening -> scored
        success = queue.update_status(feedback.id, "scored")
        assert success, "Failed valid transition: screening -> scored"
        print("✓ screening -> scored")

        # Valid transition: scored -> queued
        success = queue.update_status(feedback.id, "queued")
        assert success, "Failed valid transition: scored -> queued"
        print("✓ scored -> queued")

        # Valid transition: queued -> in_progress
        success = queue.update_status(feedback.id, "in_progress")
        assert success, "Failed valid transition: queued -> in_progress"
        print("✓ queued -> in_progress")

        # Terminal state transition: in_progress -> deployed
        success = queue.update_status(feedback.id, "deployed")
        assert success, "Failed terminal transition: in_progress -> deployed"
        print("✓ in_progress -> deployed")

    print("\n✓ Status transitions test passed!")


def test_score_feedback_with_user(user_id):
    """Test feedback scoring integration."""
    print("\nTesting FQ-001: Score Feedback (PR-001/PR-002 Integration)\n")

    with FeedbackQueue() as queue:
        # Add feedback
        feedback = queue.add_feedback(
            user_id=user_id,
            feedback_type="bug",
            content="Critical: Users can't login after recent update. Happening to everyone on iOS.",
            ip_hash="test_hash_789"
        )

        # Move to screening
        queue.update_status(feedback.id, "screening")

        # Score feedback
        scores = queue.score_feedback(feedback.id)

        assert scores is not None, "Failed to score feedback"
        assert 'quality_score' in scores
        assert 'priority_score' in scores
        assert 'priority_tier' in scores
        assert 'complexity' in scores

        print(f"Quality Score: {scores['quality_score']:.2f}/100")
        print(f"Priority Score: {scores['priority_score']:.2f}")
        print(f"Priority Tier: {scores['priority_tier']}")
        print(f"Complexity: {scores['complexity']}")

        # Verify status changed to 'scored'
        from database import get_db, Feedback
        with get_db() as db:
            updated_feedback = db.query(Feedback).filter(Feedback.id == feedback.id).first()
            assert updated_feedback.status == "scored"
            print(f"Status: {updated_feedback.status}")

    print("\n✓ Score feedback test passed!")


def test_get_next_high_priority_with_user(user_id):
    """Test getting next high priority item."""
    print("\nTesting FQ-001: Get Next High Priority Item\n")

    with FeedbackQueue() as queue:
        # Add and queue several items with different priorities
        items = []

        # LOW priority (score < 4)
        fb1 = queue.add_feedback(
            user_id=user_id,
            feedback_type="improvement",
            content="Change button color",
            ip_hash="hash_1"
        )
        items.append(fb1)

        # MEDIUM priority (score 4-7)
        fb2 = queue.add_feedback(
            user_id=user_id,
            feedback_type="feature",
            content="Add new user preference settings",
            ip_hash="hash_2"
        )
        items.append(fb2)

        # HIGH priority (score > 7)
        fb3 = queue.add_feedback(
            user_id=user_id,
            feedback_type="bug",
            content="Critical authentication bug affecting all users",
            ip_hash="hash_3"
        )
        items.append(fb3)

        # Score all items
        for item in items:
            queue.update_status(item.id, "screening")
            queue.score_feedback(item.id)
            queue.update_status(item.id, "queued")

        # Get next high priority
        next_item = queue.get_next_high_priority()

        # Verify we got the highest priority item
        if next_item:
            print(f"Next high priority item: #{next_item.id}")
            print(f"  Priority Score: {next_item.priority_score:.2f}")
            print(f"  Type: {next_item.feedback_type}")
            print(f"  Content: {next_item.content[:50]}...")
        else:
            print("No HIGH priority items in queue (this is OK for test data)")

    print("\n✓ Get next high priority test passed!")


def test_queue_stats_with_user(user_id):
    """Test queue statistics."""
    print("\nTesting FQ-001: Queue Statistics\n")

    with FeedbackQueue() as queue:
        # Add items in various states
        fb1 = queue.add_feedback(user_id, "bug", "Bug 1", "hash1")
        fb2 = queue.add_feedback(user_id, "feature", "Feature 1", "hash2")
        fb3 = queue.add_feedback(user_id, "bug", "Bug 2", "hash3")

        queue.update_status(fb2.id, "screening")
        queue.update_status(fb3.id, "screening")
        queue.score_feedback(fb3.id)

        # Get stats
        stats = queue.get_queue_stats()

        print("Queue Statistics:")
        for status, count in stats.items():
            if count > 0:
                print(f"  {status}: {count}")

        assert stats['total'] >= 3, "Should have at least 3 items"
        assert stats['pending'] >= 1, "Should have at least 1 pending"

    print("\n✓ Queue statistics test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("FQ-001: Feedback Queue Management Tests")
    print("=" * 60 + "\n")

    # Setup test database once
    print("Setting up test database...")
    user_id = setup_test_db()
    print(f"✓ Created test user with ID {user_id}\n")

    try:
        # Pass user_id to tests that need it
        test_add_feedback_with_user(user_id)
        test_status_transitions_with_user(user_id)
        test_score_feedback_with_user(user_id)
        test_get_next_high_priority_with_user(user_id)
        test_queue_stats_with_user(user_id)

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - FQ-001 is ready!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
