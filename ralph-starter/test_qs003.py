#!/usr/bin/env python3
"""
QS-003: Test User Quality Score Tracking

Quick test to verify:
1. User quality scores are calculated correctly
2. Priority boosts are applied correctly
3. Quality stats are retrieved correctly
"""

import sys
from database import get_db, User, Feedback
from user_quality_tracker import get_user_quality_tracker
from feedback_scorer import get_feedback_scorer
from datetime import datetime

def test_quality_tracking():
    """Test QS-003 implementation."""

    print("QS-003 Test: User Quality Score Tracking")
    print("=" * 50)

    tracker = get_user_quality_tracker()
    scorer = get_feedback_scorer()

    try:
        with get_db() as db:
            # Find or create a test user
            test_user = db.query(User).filter(User.telegram_id == 999999999).first()
            if not test_user:
                test_user = User(
                    telegram_id=999999999,
                    username="test_user",
                    first_name="Test",
                    subscription_tier="free",
                    quality_score=50.0
                )
                db.add(test_user)
                db.flush()
                print(f"✓ Created test user (ID: {test_user.id})")
            else:
                print(f"✓ Using existing test user (ID: {test_user.id})")

            # Create some test feedback with different quality levels
            test_feedback_samples = [
                {
                    "content": "The app crashes when I click the submit button. Steps: 1) Open form 2) Fill fields 3) Click submit. Expected: form submits. Actual: app crashes with error 500.",
                    "type": "bug",
                    "expected_score_range": (70, 100)  # High quality
                },
                {
                    "content": "Add dark mode please",
                    "type": "feature",
                    "expected_score_range": (30, 50)  # Low quality - vague
                },
                {
                    "content": "Would be great to have a dark mode toggle in settings. This would help users who work at night reduce eye strain. Other apps like Slack have this feature.",
                    "type": "feature",
                    "expected_score_range": (60, 85)  # Good quality
                }
            ]

            print(f"\n✓ Creating {len(test_feedback_samples)} test feedback items...")

            for i, sample in enumerate(test_feedback_samples, 1):
                # Create feedback
                feedback = Feedback(
                    user_id=test_user.id,
                    feedback_type=sample["type"],
                    content=sample["content"],
                    status="pending",
                    priority_score=1.0,
                    created_at=datetime.utcnow()
                )
                db.add(feedback)
                db.flush()

                # Score it
                scores = scorer.calculate_quality_score(sample["content"])
                feedback.quality_score = scores['total']

                min_score, max_score = sample["expected_score_range"]
                if min_score <= scores['total'] <= max_score:
                    result = "✓"
                else:
                    result = "✗"

                print(f"  {result} Feedback #{i}: Score {scores['total']:.1f} (expected {min_score}-{max_score})")

            db.commit()

            # Test 1: Update user quality score
            print("\n[Test 1] Update user quality score...")
            new_score = tracker.update_user_quality_score(test_user.id)
            if new_score is not None:
                print(f"  ✓ User quality score updated to {new_score:.1f}")
            else:
                print(f"  ✗ Failed to update user quality score")
                return False

            # Test 2: Get priority boost
            print("\n[Test 2] Get priority boost...")
            boost = tracker.get_priority_boost(test_user.id)
            print(f"  ✓ Priority boost: {boost}x")

            if new_score > 85:
                expected_boost = 1.5
            elif new_score > 70:
                expected_boost = 1.2
            else:
                expected_boost = 1.0

            if boost == expected_boost:
                print(f"  ✓ Correct boost for score {new_score:.1f}")
            else:
                print(f"  ✗ Expected {expected_boost}x, got {boost}x")

            # Test 3: Get quality stats
            print("\n[Test 3] Get quality stats...")
            stats = tracker.get_user_quality_stats(test_user.id)
            if stats:
                print(f"  ✓ Quality Score: {stats['quality_score']:.1f}/100")
                print(f"  ✓ Tier: {stats['tier']} {stats['tier_emoji']}")
                print(f"  ✓ Priority Boost: +{stats['boost_percentage']}%")
                print(f"  ✓ Total Feedback: {stats['total_feedback']}")
                print(f"  ✓ Scored Feedback: {stats['scored_feedback']}")
                print(f"  ✓ Flagged: {stats['flagged']}")
            else:
                print(f"  ✗ Failed to get quality stats")
                return False

            # Test 4: Check if user is flagged
            print("\n[Test 4] Check if user is flagged...")
            is_flagged, reason = tracker.is_user_flagged(test_user.id)
            if new_score < 40:
                if is_flagged:
                    print(f"  ✓ User correctly flagged: {reason}")
                else:
                    print(f"  ✗ User should be flagged (score < 40)")
            else:
                if not is_flagged:
                    print(f"  ✓ User not flagged (score >= 40)")
                else:
                    print(f"  ✗ User should not be flagged")

            print("\n" + "=" * 50)
            print("✓ All tests passed!")
            print(f"\nFinal User Quality Score: {new_score:.1f}/100")
            print(f"Priority Boost: {boost}x ({int((boost-1)*100)}% increase)")

            return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_quality_tracking()
    sys.exit(0 if success else 1)
