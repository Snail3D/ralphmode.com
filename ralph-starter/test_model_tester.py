#!/usr/bin/env python3
"""
Quick test script for MM-005: Test Prompt Library
"""

from model_tester import (
    get_tests_for_role,
    get_test_by_name,
    list_all_tests,
    TEST_LIBRARY
)
from model_manager import ModelRole


def test_prompt_library():
    """Test that the prompt library is properly structured"""
    print("=" * 60)
    print("MM-005: Testing Test Prompt Library")
    print("=" * 60)

    # Test 1: All roles have tests
    print("\n✅ Test 1: Checking all roles have test prompts...")
    for role in ModelRole:
        tests = get_tests_for_role(role)
        print(f"   {role.value}: {len(tests)} tests")
        assert len(tests) >= 2, f"Role {role.value} should have at least 2 tests"

    # Test 2: List all tests
    print("\n✅ Test 2: Listing all test names...")
    all_tests = list_all_tests()
    print(f"   Total tests: {len(all_tests)}")
    print(f"   Tests: {', '.join(all_tests[:5])}...")

    # Test 3: Get specific test by name
    print("\n✅ Test 3: Testing get_test_by_name...")
    test = get_test_by_name("ralph_personality")
    assert test is not None, "Should find ralph_personality test"
    assert test.role == ModelRole.RALPH, "ralph_personality should be for RALPH role"
    print(f"   Found test: {test.name}")
    print(f"   Expected behavior: {test.expected_behavior}")

    # Test 4: Verify test structure
    print("\n✅ Test 4: Verifying test prompt structure...")
    for role, tests in TEST_LIBRARY.items():
        for test in tests:
            assert test.name, "Test must have a name"
            assert test.role == role, "Test role must match"
            assert test.messages, "Test must have messages"
            assert len(test.messages) > 0, "Test must have at least one message"
            assert test.expected_behavior, "Test must have expected_behavior"
            assert test.max_tokens > 0, "max_tokens must be positive"
            assert 0 <= test.temperature <= 2, "temperature should be in valid range"

    print(f"   Verified {len(all_tests)} test prompts")

    # Test 5: Show sample test
    print("\n✅ Test 5: Sample test prompt...")
    worker_test = get_test_by_name("worker_code_generation")
    print(f"   Test name: {worker_test.name}")
    print(f"   Role: {worker_test.role.value}")
    print(f"   Messages:")
    for msg in worker_test.messages:
        print(f"     - {msg['role']}: {msg['content'][:60]}...")
    print(f"   Expected: {worker_test.expected_behavior}")
    print(f"   Max tokens: {worker_test.max_tokens}")
    print(f"   Temperature: {worker_test.temperature}")

    print("\n" + "=" * 60)
    print("✅ MM-005: All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_prompt_library()
