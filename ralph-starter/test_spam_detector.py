#!/usr/bin/env python3
"""
Simple test for SP-001: Spam Pattern Detection

Tests the spam detector with various inputs to ensure it's working correctly.
"""

from feedback_screener import SpamDetector


def test_gibberish_detection():
    """Test gibberish detection."""
    detector = SpamDetector()

    # Test gibberish
    gibberish_samples = [
        "asdfasdfasdfasdfasdf",
        "aaaaaaaaaaaaaaaa",
        "jkjkjkjkjkjkjkjk",
        "qwerty qwerty qwerty qwerty",
        "hehehehehehehehehehe"
    ]

    print("Testing gibberish detection:")
    for sample in gibberish_samples:
        is_spam, reason = detector.detect_spam(sample, user_id=1)
        print(f"  '{sample}' -> Spam: {is_spam}, Reason: {reason}")

    # Test legitimate text
    legitimate_samples = [
        "I found a bug in Ralph Mode bot",
        "The feedback system is not working properly",
        "Can you add a feature to export chat history?"
    ]

    print("\nTesting legitimate text:")
    for sample in legitimate_samples:
        is_spam, reason = detector.detect_spam(sample, user_id=1)
        print(f"  '{sample}' -> Spam: {is_spam}, Reason: {reason}")


def test_promotional_detection():
    """Test promotional content detection."""
    detector = SpamDetector()

    promotional_samples = [
        "Buy now! Limited time offer! Visit http://example.com",
        "Click here for free trial! http://spam.com",
        "Make money from home! Join us at http://scam.com",
        "Special discount! Use promo code SAVE50"
    ]

    print("\n\nTesting promotional content detection:")
    for sample in promotional_samples:
        is_spam, reason = detector.detect_spam(sample, user_id=1)
        print(f"  '{sample[:50]}...' -> Spam: {is_spam}, Reason: {reason}")


def test_off_topic_detection():
    """Test off-topic detection."""
    detector = SpamDetector()

    off_topic_samples = [
        "I really love pizza and tacos and hamburgers and french fries",
        "The weather is nice today and I went for a walk in the park",
        "My cat is sleeping on the couch right now"
    ]

    print("\n\nTesting off-topic detection:")
    for sample in off_topic_samples:
        is_spam, reason = detector.detect_spam(sample, user_id=1)
        print(f"  '{sample}' -> Spam: {is_spam}, Reason: {reason}")

    on_topic_samples = [
        "Ralph bot is awesome! Great work on the AI dev team feature",
        "I found a bug where the typing indicator doesn't show",
        "Can you add voice message support to Ralph Mode?"
    ]

    print("\nTesting on-topic content:")
    for sample in on_topic_samples:
        is_spam, reason = detector.detect_spam(sample, user_id=1)
        print(f"  '{sample}' -> Spam: {is_spam}, Reason: {reason}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("SP-001: Spam Pattern Detection Tests")
    print("=" * 70)

    test_gibberish_detection()
    test_promotional_detection()
    test_off_topic_detection()

    print("\n" + "=" * 70)
    print("Tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
