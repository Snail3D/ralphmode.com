#!/usr/bin/env python3
"""
Quick test for SP-002 Abuse Detection
"""

from feedback_screener import AbuseDetector

def test_abuse_detection():
    detector = AbuseDetector()

    test_cases = [
        # (content, expected_result, description)
        ("This bot is great!", False, "Clean feedback"),
        ("I love the Ralph Mode bot", False, "Positive feedback"),
        ("Can you add dark mode?", False, "Feature request"),

        # Profanity tests
        ("This is fucking terrible", True, "Profanity"),
        ("What a piece of shit", True, "Profanity"),

        # Threat tests
        ("I'm going to kill you", True, "Death threat"),
        ("You should die", True, "Threat"),

        # Harassment tests
        ("You're a pathetic excuse for a developer", True, "Harassment"),
        ("Kill yourself", True, "Harassment - kys"),

        # Personal attack tests
        ("You're an idiot and a moron", True, "Personal attacks (2+)"),
        ("This is idiotic", False, "Single personal attack word"),

        # Edge cases
        ("Hell yeah, this is great!", False, "Casual language not abuse"),
    ]

    print("=" * 60)
    print("SP-002: Abuse Detection Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for content, should_be_abuse, description in test_cases:
        is_abuse, reason, category = detector.detect_abuse(content, user_id=1)

        if is_abuse == should_be_abuse:
            print(f"✅ PASS: {description}")
            print(f"   Content: '{content}'")
            if is_abuse:
                print(f"   Detected: {category} - {reason}")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Content: '{content}'")
            print(f"   Expected abuse: {should_be_abuse}, Got: {is_abuse}")
            if is_abuse:
                print(f"   Reason: {reason} ({category})")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_abuse_detection()
    exit(0 if success else 1)
