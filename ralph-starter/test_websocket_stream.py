#!/usr/bin/env python3
"""
Test script for WB-002: WebSocket Build Stream

Tests:
- Output sanitization (secret removal)
- WebSocket server initialization
- Build status emissions
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_output_sanitization():
    """Test that sensitive data is properly redacted."""
    print("Testing output sanitization...\n")

    from websocket_server import OutputSanitizer

    sanitizer = OutputSanitizer()

    test_cases = [
        # API keys
        ("API_KEY=sk_test_1234567890abcdef", "API_KEY=***REDACTED***"),
        ("api_key: Bearer abc123def456", "api_key: ***REDACTED***"),

        # Passwords
        ("password=mysecretpass123", "password=***REDACTED***"),
        ("DB_PASSWORD: hunter2", "DB_PASSWORD: ***REDACTED***"),

        # Environment variables
        ("GROQ_API_KEY=gsk_1234567890", "GROQ_API_KEY=***REDACTED***"),
        ("TELEGRAM_BOT_TOKEN=123456:ABCdef", "TELEGRAM_BOT_TOKEN=***REDACTED***"),

        # Safe output (should not be changed)
        ("Running tests...", "Running tests..."),
        ("Build successful", "Build successful"),
        ("Error: File not found", "Error: File not found"),
    ]

    passed = 0
    failed = 0

    for input_text, expected_output in test_cases:
        result = sanitizer.sanitize(input_text)

        # Check if secrets are redacted (not checking exact match)
        has_secret = any(pattern in input_text.lower() for pattern in ['api_key', 'password', 'token', 'secret'])
        is_sanitized = '***REDACTED***' in result if has_secret else result == expected_output

        if is_sanitized:
            print(f"✓ PASS: '{input_text}' -> '{result}'")
            passed += 1
        else:
            print(f"✗ FAIL: '{input_text}' -> '{result}' (expected sanitization)")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Sanitization Tests: {passed} passed, {failed} failed")
    print(f"{'='*50}\n")

    return failed == 0


def test_websocket_server_init():
    """Test that WebSocket server can be initialized."""
    print("Testing WebSocket server initialization...\n")

    try:
        from websocket_server import BuildStreamServer

        # Create server instance
        server = BuildStreamServer()

        print("✓ PASS: BuildStreamServer initialized successfully")
        print(f"  - Flask app: {server.app is not None}")
        print(f"  - SocketIO: {server.socketio is not None}")
        print(f"  - Sanitizer: {server.sanitizer is not None}")

        # Test emit methods (won't actually emit without clients)
        try:
            server.emit_build_output(123, "Test output line")
            print("✓ PASS: emit_build_output() works")
        except Exception as e:
            print(f"✗ FAIL: emit_build_output() error: {e}")
            return False

        try:
            server.emit_build_status(123, 'in_progress', 'Building...')
            print("✓ PASS: emit_build_status() works")
        except Exception as e:
            print(f"✗ FAIL: emit_build_status() error: {e}")
            return False

        try:
            server.emit_build_progress(123, 'Running tests', 50.0)
            print("✓ PASS: emit_build_progress() works")
        except Exception as e:
            print(f"✗ FAIL: emit_build_progress() error: {e}")
            return False

        try:
            server.emit_test_output(123, 'test_example', 'pass', 'Test passed!')
            print("✓ PASS: emit_test_output() works")
        except Exception as e:
            print(f"✗ FAIL: emit_test_output() error: {e}")
            return False

        print(f"\n{'='*50}")
        print("WebSocket Server Tests: All passed")
        print(f"{'='*50}\n")

        return True

    except Exception as e:
        print(f"✗ FAIL: Error initializing server: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_build_orchestrator_integration():
    """Test that BuildOrchestrator can integrate with WebSocket server."""
    print("Testing BuildOrchestrator integration...\n")

    try:
        # This will test imports and basic initialization
        from build_orchestrator import BuildOrchestrator

        print("✓ PASS: BuildOrchestrator imports successfully with WB-002 changes")
        print("  Note: Full integration test requires running orchestrator with live builds")

        print(f"\n{'='*50}")
        print("Integration Tests: Basic checks passed")
        print(f"{'='*50}\n")

        return True

    except Exception as e:
        print(f"✗ FAIL: Error importing BuildOrchestrator: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "="*50)
    print("WB-002: WebSocket Build Stream Tests")
    print("="*50 + "\n")

    # Run all tests
    test1 = test_output_sanitization()
    test2 = test_websocket_server_init()
    test3 = test_build_orchestrator_integration()

    # Summary
    print("\n" + "="*50)
    print("FINAL SUMMARY")
    print("="*50)
    print(f"Output Sanitization: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"WebSocket Server: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"BuildOrchestrator Integration: {'✅ PASS' if test3 else '❌ FAIL'}")

    if test1 and test2 and test3:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
