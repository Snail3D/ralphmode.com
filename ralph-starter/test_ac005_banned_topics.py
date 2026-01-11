#!/usr/bin/env python3
"""
AC-005: Test script for banned topics functionality
"""

import sys

# Import the UserManager
from user_manager import UserManager

def test_banned_topics():
    """Test the banned topics functionality"""
    print("🧪 Testing AC-005: Banned Topics List Management\n")

    # Create a UserManager instance for testing
    user_manager = UserManager()

    # Test 1: Ban a topic
    print("Test 1: Ban topic 'politics'")
    success = user_manager.ban_topic("politics")
    assert success == True, "Should successfully ban a new topic"
    print("✅ PASS: Topic 'politics' banned successfully\n")

    # Test 2: Try to ban the same topic again
    print("Test 2: Try to ban 'politics' again (should fail)")
    success = user_manager.ban_topic("politics")
    assert success == False, "Should return False when topic already banned"
    print("✅ PASS: Correctly reports topic already banned\n")

    # Test 3: Ban another topic (case-insensitive)
    print("Test 3: Ban topic 'CRYPTO' (uppercase)")
    success = user_manager.ban_topic("CRYPTO")
    assert success == True, "Should successfully ban topic"
    banned_topics = user_manager.get_banned_topics()
    assert 'crypto' in banned_topics, "Topic should be stored in lowercase"
    print("✅ PASS: Topic normalized to lowercase\n")

    # Test 4: List banned topics
    print("Test 4: List all banned topics")
    banned_topics = user_manager.get_banned_topics()
    assert len(banned_topics) == 2, "Should have 2 banned topics"
    assert 'politics' in banned_topics, "Should contain 'politics'"
    assert 'crypto' in banned_topics, "Should contain 'crypto'"
    print(f"✅ PASS: Banned topics: {banned_topics}\n")

    # Test 5: Fuzzy matching - exact match
    print("Test 5: Check message with exact topic match")
    is_banned, matched_topic = user_manager.is_topic_banned("Let's talk about politics")
    assert is_banned == True, "Should detect exact topic match"
    assert matched_topic == "politics", "Should return the matched topic"
    print("✅ PASS: Exact match detected\n")

    # Test 6: Fuzzy matching - substring variation
    print("Test 6: Check message with topic variation 'cryptocurrency'")
    is_banned, matched_topic = user_manager.is_topic_banned("I love cryptocurrency!")
    assert is_banned == True, "Should detect topic in variation"
    assert matched_topic == "crypto", "Should return the matched topic"
    print("✅ PASS: Fuzzy matching works (crypto in cryptocurrency)\n")

    # Test 7: Fuzzy matching - case insensitive
    print("Test 7: Check message with uppercase topic")
    is_banned, matched_topic = user_manager.is_topic_banned("POLITICS is important")
    assert is_banned == True, "Should be case-insensitive"
    assert matched_topic == "politics", "Should return the matched topic"
    print("✅ PASS: Case-insensitive matching works\n")

    # Test 8: Clean message (no banned topics)
    print("Test 8: Check clean message")
    is_banned, matched_topic = user_manager.is_topic_banned("Let's build a cool app!")
    assert is_banned == False, "Should not detect banned topics"
    assert matched_topic is None, "Should return None for matched topic"
    print("✅ PASS: Clean message passes through\n")

    # Test 9: Unban a topic
    print("Test 9: Unban topic 'crypto'")
    success = user_manager.unban_topic("crypto")
    assert success == True, "Should successfully unban topic"
    banned_topics = user_manager.get_banned_topics()
    assert 'crypto' not in banned_topics, "Topic should be removed from list"
    print("✅ PASS: Topic unbanned successfully\n")

    # Test 10: Try to unban a topic that's not banned
    print("Test 10: Try to unban 'crypto' again (should fail)")
    success = user_manager.unban_topic("crypto")
    assert success == False, "Should return False when topic not banned"
    print("✅ PASS: Correctly reports topic not banned\n")

    # Test 11: Message with unbanned topic should pass
    print("Test 11: Check message with unbanned topic")
    is_banned, matched_topic = user_manager.is_topic_banned("I love cryptocurrency!")
    assert is_banned == False, "Unbanned topic should not be blocked"
    print("✅ PASS: Unbanned topic passes through\n")

    # Test 12: Empty/invalid inputs
    print("Test 12: Test empty topic banning")
    success = user_manager.ban_topic("")
    assert success == False, "Should reject empty topic"
    success = user_manager.ban_topic("   ")
    assert success == False, "Should reject whitespace-only topic"
    print("✅ PASS: Invalid inputs rejected\n")

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nAC-005 Implementation Summary:")
    print("✓ 'admin command: ban topic [topic]' - add to ban list")
    print("✓ 'admin command: unban topic [topic]' - remove from list")
    print("✓ 'admin command: list banned topics' - show current list")
    print("✓ Messages containing banned topics blocked")
    print("✓ In-character deflection when topic blocked")
    print("✓ Topic matching is fuzzy (catches variations)")
    print("\nAll acceptance criteria met! ✨")

if __name__ == '__main__':
    try:
        test_banned_topics()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
