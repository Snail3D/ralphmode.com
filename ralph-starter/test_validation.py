#!/usr/bin/env python3
"""
Test file for SEC-012: API Input Validation
Quick validation tests to ensure schemas and validators work correctly.
"""

from schemas import (
    UserMessageInput, FileUploadInput, FeedbackSubmission,
    validate_model, validate_and_parse, FeedbackType
)
from validators import (
    detect_sql_injection, detect_xss, detect_path_traversal,
    validate_length, validate_filename, validate_telegram_user_id,
    validate_git_branch_name, validate_user_input
)


def test_schemas():
    """Test Pydantic schemas"""
    print("Testing Pydantic Schemas...")

    # Valid user message
    try:
        msg = UserMessageInput(user_id=12345, message="Hello world", message_type="text")
        print("✓ Valid user message accepted")
    except Exception as e:
        print(f"✗ Valid user message rejected: {e}")

    # Invalid user message (empty)
    try:
        msg = UserMessageInput(user_id=12345, message="", message_type="text")
        print("✗ Empty message accepted (should reject)")
    except Exception:
        print("✓ Empty message rejected")

    # Invalid user message (too long)
    try:
        msg = UserMessageInput(user_id=12345, message="x" * 20000, message_type="text")
        print("✗ Over-length message accepted (should reject)")
    except Exception:
        print("✓ Over-length message rejected")

    # Valid file upload
    try:
        file = FileUploadInput(
            user_id=12345,
            file_id="BQACAgIAAxkBAAIC",
            file_name="project.zip",
            file_size=1000000,
            mime_type="application/zip"
        )
        print("✓ Valid file upload accepted")
    except Exception as e:
        print(f"✗ Valid file upload rejected: {e}")

    # Invalid file upload (path traversal in filename)
    try:
        file = FileUploadInput(
            user_id=12345,
            file_id="BQACAgIAAxkBAAIC",
            file_name="../etc/passwd.zip",
            file_size=1000000,
            mime_type="application/zip"
        )
        print("✗ Path traversal filename accepted (should reject)")
    except Exception:
        print("✓ Path traversal filename rejected")

    # Invalid file upload (not a zip)
    try:
        file = FileUploadInput(
            user_id=12345,
            file_id="BQACAgIAAxkBAAIC",
            file_name="virus.exe",
            file_size=1000000,
            mime_type="application/zip"
        )
        print("✗ Non-zip filename accepted (should reject)")
    except Exception:
        print("✓ Non-zip filename rejected")

    # Valid feedback submission
    try:
        feedback = FeedbackSubmission(
            user_id=12345,
            feedback_type=FeedbackType.BUG,
            title="Button is broken",
            description="When I click the start button, nothing happens"
        )
        print("✓ Valid feedback accepted")
    except Exception as e:
        print(f"✗ Valid feedback rejected: {e}")

    print()


def test_security_detection():
    """Test security pattern detection"""
    print("Testing Security Detection...")

    # SQL Injection
    sql_test = "SELECT * FROM users WHERE id=1"
    is_suspicious, pattern = detect_sql_injection(sql_test)
    if is_suspicious:
        print("✓ SQL injection detected")
    else:
        print("✗ SQL injection NOT detected")

    # XSS
    xss_test = "<script>alert('xss')</script>"
    is_suspicious, pattern = detect_xss(xss_test)
    if is_suspicious:
        print("✓ XSS detected")
    else:
        print("✗ XSS NOT detected")

    # Path Traversal
    path_test = "../../etc/passwd"
    is_suspicious, pattern = detect_path_traversal(path_test)
    if is_suspicious:
        print("✓ Path traversal detected")
    else:
        print("✗ Path traversal NOT detected")

    # Safe text should pass
    safe_text = "This is a normal user message"
    is_valid, errors = validate_user_input(safe_text)
    if is_valid:
        print("✓ Safe text passed validation")
    else:
        print(f"✗ Safe text failed: {errors}")

    print()


def test_validators():
    """Test individual validators"""
    print("Testing Individual Validators...")

    # Length validation
    is_valid, error = validate_length("test", min_len=3, max_len=10)
    if is_valid:
        print("✓ Length validation passed")
    else:
        print(f"✗ Length validation failed: {error}")

    # Filename validation
    is_valid, error = validate_filename("project.zip", allowed_extensions=[".zip"])
    if is_valid:
        print("✓ Filename validation passed")
    else:
        print(f"✗ Filename validation failed: {error}")

    # Dangerous filename
    is_valid, error = validate_filename("../etc/passwd", allowed_extensions=[".txt"])
    if not is_valid:
        print("✓ Dangerous filename rejected")
    else:
        print("✗ Dangerous filename accepted (should reject)")

    # Telegram user ID
    is_valid, error = validate_telegram_user_id(12345)
    if is_valid:
        print("✓ Valid Telegram user ID accepted")
    else:
        print(f"✗ Valid Telegram user ID rejected: {error}")

    # Invalid Telegram user ID
    is_valid, error = validate_telegram_user_id(-1)
    if not is_valid:
        print("✓ Invalid Telegram user ID rejected")
    else:
        print("✗ Invalid Telegram user ID accepted (should reject)")

    # Git branch name
    is_valid, error = validate_git_branch_name("feature/add-validation")
    if is_valid:
        print("✓ Valid git branch name accepted")
    else:
        print(f"✗ Valid git branch name rejected: {error}")

    # Dangerous branch name
    is_valid, error = validate_git_branch_name("feature/../main")
    if not is_valid:
        print("✓ Dangerous branch name rejected")
    else:
        print("✗ Dangerous branch name accepted (should reject)")

    print()


def test_comprehensive_validation():
    """Test comprehensive input validation"""
    print("Testing Comprehensive Validation...")

    test_cases = [
        ("Normal text", True),
        ("SELECT * FROM users", False),  # SQL injection
        ("<script>alert('xss')</script>", False),  # XSS
        ("../../etc/passwd", False),  # Path traversal
        ("", False),  # Too short (default min is 0, but let's test with min)
    ]

    for text, should_pass in test_cases:
        is_valid, errors = validate_user_input(text, min_length=1)
        if is_valid == should_pass:
            status = "✓"
        else:
            status = "✗"

        result = "passed" if is_valid else "failed"
        expected = "pass" if should_pass else "fail"
        print(f"{status} '{text[:30]}...' {result} (expected: {expected})")
        if errors:
            print(f"   Errors: {', '.join(errors)}")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("SEC-012: API Input Validation - Test Suite")
    print("=" * 60)
    print()

    test_schemas()
    test_security_detection()
    test_validators()
    test_comprehensive_validation()

    print("=" * 60)
    print("Testing Complete!")
    print("=" * 60)
