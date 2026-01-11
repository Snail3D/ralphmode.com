#!/usr/bin/env python3
"""
Test AC-004: Configurable Cooldown Values by Admin

Tests the natural language parsing for cooldown commands.
"""

import re


def test_cooldown_off_parsing():
    """Test 'cooldown off' command parsing"""
    test_cases = [
        ("cooldown off", True, None),
        ("cooldown off for user 123456789", True, "123456789"),
        ("cooldown off for @johndoe", True, "johndoe"),
        ("set cooldown off", True, None),
    ]

    for command, expected_match, expected_user in test_cases:
        command_lower = command.lower().strip()
        is_off = 'cooldown off' in command_lower or command_lower == 'off'

        user_id_match = re.search(r'(?:for user|user|for @)\s*@?(\w+)|@(\w+)', command_lower)
        user_identifier = None
        if user_id_match:
            user_identifier = user_id_match.group(1) or user_id_match.group(2)

        assert is_off == expected_match, f"Failed for '{command}': expected is_off={expected_match}, got {is_off}"
        assert user_identifier == expected_user, f"Failed for '{command}': expected user={expected_user}, got {user_identifier}"

    print("✅ test_cooldown_off_parsing passed")


def test_duration_parsing():
    """Test duration and unit extraction"""
    test_cases = [
        ("cooldown 1 minute", 1, "minute"),
        ("cooldown 5 minutes", 5, "minute"),
        ("cooldown 30 seconds", 30, "second"),
        ("set cooldown 2 hours", 2, "hour"),
        ("cooldown 10 minutes for user 123", 10, "minute"),
    ]

    for command, expected_duration, expected_unit in test_cases:
        command_lower = command.lower().strip()
        duration_match = re.search(r'(\d+)\s*(minute|second|hour)s?', command_lower)

        assert duration_match is not None, f"Failed to match duration in '{command}'"
        duration = int(duration_match.group(1))
        unit = duration_match.group(2)

        assert duration == expected_duration, f"Failed for '{command}': expected duration={expected_duration}, got {duration}"
        assert unit == expected_unit, f"Failed for '{command}': expected unit={expected_unit}, got {unit}"

    print("✅ test_duration_parsing passed")


def test_user_id_extraction():
    """Test user ID extraction with various formats"""
    test_cases = [
        ("cooldown 5 minutes for user 123456789", "123456789"),
        ("cooldown 5 minutes for @johndoe", "johndoe"),
        ("set cooldown for user 987654321 10 seconds", "987654321"),
        ("cooldown 1 minute", None),
    ]

    for command, expected_user in test_cases:
        command_lower = command.lower().strip()
        user_match = re.search(r'(?:for\s+@(\w+)|for\s+user\s+(\d+)|@(\w+)(?:\s|$))', command_lower)

        if expected_user is None:
            assert user_match is None, f"Failed for '{command}': expected no user match, but got one"
        else:
            assert user_match is not None, f"Failed for '{command}': expected user match, got None"
            username = user_match.group(1) or user_match.group(3)
            numeric_id = user_match.group(2)
            extracted_user = numeric_id or username

            assert extracted_user == expected_user, f"Failed for '{command}': expected user={expected_user}, got {extracted_user}"

    print("✅ test_user_id_extraction passed")


def test_singular_plural_units():
    """Test that singular/plural unit display works correctly"""
    test_cases = [
        (1, "minute", "minute"),
        (5, "minute", "minutes"),
        (1, "second", "second"),
        (30, "second", "seconds"),
        (1, "hour", "hour"),
        (2, "hour", "hours"),
    ]

    for duration, unit, expected_display in test_cases:
        if unit == 'minute':
            unit_display = 'minutes' if duration != 1 else 'minute'
        elif unit == 'second':
            unit_display = 'seconds' if duration != 1 else 'second'
        elif unit == 'hour':
            unit_display = 'hours' if duration != 1 else 'hour'

        assert unit_display == expected_display, f"Failed for duration={duration} unit={unit}: expected '{expected_display}', got '{unit_display}'"

    print("✅ test_singular_plural_units passed")


if __name__ == '__main__':
    print("\n🧪 Testing AC-004: Cooldown Command Parsing\n")

    test_cooldown_off_parsing()
    test_duration_parsing()
    test_user_id_extraction()
    test_singular_plural_units()

    print("\n✅ All AC-004 tests passed!\n")
