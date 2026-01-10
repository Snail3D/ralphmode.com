#!/usr/bin/env python3
"""
Test PR-001: Priority Score Algorithm

Quick test to verify the priority scoring functions work correctly.
"""

from feedback_scorer import (
    calculate_priority_score,
    normalize_quality_score,
    estimate_complexity_from_feedback
)


def test_calculate_priority_score():
    """Test priority score calculation with known inputs."""
    print("Testing PR-001: Priority Score Algorithm\n")

    # Test case 1: High priority (from acceptance criteria example)
    # impact=9, frequency=9, urgency=10, quality=0.8, weight=2.0, complexity=3
    score1 = calculate_priority_score(9, 9, 10, 0.8, 2.0, 3)
    print(f"Test 1 - High priority: {score1}")
    assert score1 == 432.0, f"Expected 432.0, got {score1}"

    # Test case 2: Medium priority (from acceptance criteria example)
    # impact=5, frequency=5, urgency=5, quality=0.7, weight=1.0, complexity=5
    score2 = calculate_priority_score(5, 5, 5, 0.7, 1.0, 5)
    print(f"Test 2 - Medium priority: {score2}")
    assert score2 == 17.5, f"Expected 17.5, got {score2}"

    # Test case 3: Low priority (from acceptance criteria example)
    # impact=2, frequency=3, urgency=2, quality=0.5, weight=1.0, complexity=8
    score3 = calculate_priority_score(2, 3, 2, 0.5, 1.0, 8)
    print(f"Test 3 - Low priority: {score3}")
    assert score3 == 0.75, f"Expected 0.75, got {score3}"

    print("\n✓ All priority score calculations passed!")


def test_normalize_quality_score():
    """Test quality score normalization from 0-100 to 0.3-1.0."""
    print("\nTesting quality score normalization:\n")

    # Test boundary conditions
    assert normalize_quality_score(0) == 0.3, "Min quality should be 0.3"
    assert normalize_quality_score(100) == 1.0, "Max quality should be 1.0"

    # Test examples from docstring
    assert normalize_quality_score(70) == 0.79, "70 should map to 0.79"
    assert normalize_quality_score(40) == 0.58, "40 should map to 0.58"

    print(f"  0 → {normalize_quality_score(0)}")
    print(f" 40 → {normalize_quality_score(40)}")
    print(f" 70 → {normalize_quality_score(70)}")
    print(f"100 → {normalize_quality_score(100)}")

    print("\n✓ Quality normalization passed!")


def test_estimate_complexity():
    """Test complexity estimation from feedback content."""
    print("\nTesting complexity estimation:\n")

    # Simple fix (should be low complexity)
    simple = "Fix typo in button label"
    complexity_simple = estimate_complexity_from_feedback(simple, "bug")
    print(f"Simple bug: '{simple}' → complexity {complexity_simple}")
    assert 1 <= complexity_simple <= 4, f"Simple fix should be 1-4, got {complexity_simple}"

    # Medium feature (should be medium complexity)
    medium = "Add a new feature to show user progress"
    complexity_medium = estimate_complexity_from_feedback(medium, "feature")
    print(f"Medium feature: '{medium}' → complexity {complexity_medium}")
    assert 4 <= complexity_medium <= 7, f"Medium feature should be 4-7, got {complexity_medium}"

    # Complex change (should be high complexity)
    complex = "Refactor authentication system to use database with migration and new API endpoints"
    complexity_complex = estimate_complexity_from_feedback(complex, "feature")
    print(f"Complex feature: '{complex}' → complexity {complexity_complex}")
    assert 7 <= complexity_complex <= 10, f"Complex feature should be 7-10, got {complexity_complex}"

    print("\n✓ Complexity estimation passed!")


def test_validation():
    """Test input validation for priority score calculation."""
    print("\nTesting input validation:\n")

    try:
        # Invalid impact (out of range)
        calculate_priority_score(11, 5, 5, 0.5, 1.0, 5)
        assert False, "Should have raised ValueError for impact > 10"
    except ValueError as e:
        print(f"✓ Caught invalid impact: {e}")

    try:
        # Invalid quality (out of range)
        calculate_priority_score(5, 5, 5, 1.5, 1.0, 5)
        assert False, "Should have raised ValueError for quality > 1.0"
    except ValueError as e:
        print(f"✓ Caught invalid quality: {e}")

    try:
        # Invalid user weight (not 1.0 or 2.0)
        calculate_priority_score(5, 5, 5, 0.5, 3.0, 5)
        assert False, "Should have raised ValueError for invalid user weight"
    except ValueError as e:
        print(f"✓ Caught invalid user weight: {e}")

    print("\n✓ Input validation passed!")


def test_full_workflow():
    """Test complete workflow: quality → priority score."""
    print("\nTesting full workflow:\n")

    # Simulate feedback with quality score
    quality_score = 75  # Quality score from QS-001
    normalized_quality = normalize_quality_score(quality_score)

    # User is Priority tier
    user_weight = 2.0

    # High impact, high frequency, high urgency
    impact = 8
    frequency = 7
    urgency = 9

    # Estimate complexity from content
    content = "Users can't login after recent update. Happening to everyone."
    complexity = estimate_complexity_from_feedback(content, "bug")

    # Calculate priority
    priority = calculate_priority_score(
        impact, frequency, urgency, normalized_quality, user_weight, complexity
    )

    print(f"Feedback: '{content}'")
    print(f"Quality score: {quality_score}/100 → {normalized_quality}")
    print(f"Impact: {impact}, Frequency: {frequency}, Urgency: {urgency}")
    print(f"User weight: {user_weight}, Complexity: {complexity}")
    print(f"Final priority score: {priority}")
    print(f"\nThis should be HIGH priority (score > 7 after PR-002)")

    print("\n✓ Full workflow passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("PR-001: Priority Score Algorithm Tests")
    print("=" * 60 + "\n")

    test_calculate_priority_score()
    test_normalize_quality_score()
    test_estimate_complexity()
    test_validation()
    test_full_workflow()

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - PR-001 is ready!")
    print("=" * 60)
