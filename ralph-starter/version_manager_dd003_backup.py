#!/usr/bin/env python3
"""
DD-003: Version Manager and Changelog Tracking for Ralph Mode Bot

This module tracks version history and changelogs to detect when user feedback
describes issues that have already been fixed in recent versions.

Features:
- Stores version changelog entries (fixes, features, improvements)
- Checks if feedback matches recently fixed issues
- Suggests version upgrades when user is on old version
- Uses semantic similarity to match feedback against changelog
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class VersionManager:
    """
    Manages version history and changelog tracking.

    For DD-003, we track the last 5 versions and their changelogs
    to detect when user feedback describes already-fixed issues.
    """

    def __init__(self):
        """Initialize version manager with hardcoded changelog for now."""
        # In production, this would come from a database or API
        # For now, we'll use a simple in-memory structure
        self.current_version = "0.3.0"

        # Changelog: last 5 versions with their fixes/features
        # Each entry has: version, date, type (fix/feature/improvement), description
        self.changelog = [
            {
                "version": "0.3.0",
                "date": "2026-01-10",
                "entries": [
                    {"type": "fix", "description": "Fixed duplicate detection using semantic similarity"},
                    {"type": "feature", "description": "Added duplicate merging and upvoting system"},
                    {"type": "improvement", "description": "Improved quality scoring algorithm"},
                ]
            },
            {
                "version": "0.2.5",
                "date": "2026-01-08",
                "entries": [
                    {"type": "fix", "description": "Fixed spam detection false positives"},
                    {"type": "fix", "description": "Fixed abuse detection for profanity filter"},
                    {"type": "feature", "description": "Added user quality score tracking"},
                ]
            },
            {
                "version": "0.2.0",
                "date": "2026-01-05",
                "entries": [
                    {"type": "fix", "description": "Fixed rate limiting for IP-based limits"},
                    {"type": "fix", "description": "Fixed subscription tier checking for Builder+ users"},
                    {"type": "feature", "description": "Added feedback type classification"},
                ]
            },
            {
                "version": "0.1.5",
                "date": "2026-01-03",
                "entries": [
                    {"type": "fix", "description": "Fixed security logging and PII redaction"},
                    {"type": "fix", "description": "Fixed JWT token validation edge cases"},
                    {"type": "improvement", "description": "Improved API rate limiting accuracy"},
                ]
            },
            {
                "version": "0.1.0",
                "date": "2026-01-01",
                "entries": [
                    {"type": "feature", "description": "Initial release of Ralph Mode Bot"},
                    {"type": "feature", "description": "Basic feedback collection system"},
                    {"type": "feature", "description": "Telegram bot integration"},
                ]
            }
        ]

    def get_recent_versions(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent N versions from changelog.

        Args:
            count: Number of versions to retrieve (default 5)

        Returns:
            List of version dictionaries
        """
        return self.changelog[:count]

    def get_all_fixes_in_recent_versions(self, count: int = 5) -> List[Tuple[str, str]]:
        """
        Get all fix descriptions from recent versions.

        Args:
            count: Number of versions to check (default 5)

        Returns:
            List of (version, fix_description) tuples
        """
        fixes = []

        for version_data in self.changelog[:count]:
            version = version_data["version"]
            for entry in version_data["entries"]:
                if entry["type"] == "fix":
                    fixes.append((version, entry["description"]))

        return fixes

    def get_version_date(self, version: str) -> Optional[str]:
        """
        Get the release date of a specific version.

        Args:
            version: Version string (e.g., "0.2.5")

        Returns:
            Date string or None if version not found
        """
        for version_data in self.changelog:
            if version_data["version"] == version:
                return version_data["date"]
        return None

    def is_version_outdated(self, user_version: str) -> bool:
        """
        Check if user's version is outdated.

        Args:
            user_version: User's current version

        Returns:
            True if outdated, False if current or newer
        """
        try:
            # Simple version comparison (assumes semantic versioning)
            user_parts = [int(x) for x in user_version.split(".")]
            current_parts = [int(x) for x in self.current_version.split(".")]

            # Pad to same length
            max_len = max(len(user_parts), len(current_parts))
            user_parts += [0] * (max_len - len(user_parts))
            current_parts += [0] * (max_len - len(current_parts))

            return user_parts < current_parts

        except (ValueError, AttributeError):
            # If version format is invalid, assume outdated to be safe
            logger.warning(f"DD-003: Invalid version format: {user_version}")
            return True

    def format_changelog_entry(self, version: str, description: str) -> str:
        """
        Format a changelog entry for display to user.

        Args:
            version: Version string
            description: Fix description

        Returns:
            Formatted string for user notification
        """
        date = self.get_version_date(version)
        date_str = f" ({date})" if date else ""
        return f"Version {version}{date_str}: {description}"


class AlreadyFixedDetector:
    """
    DD-003: Detects if user feedback describes an issue that's already fixed.

    Uses semantic similarity to compare feedback against changelog entries
    from recent versions.
    """

    def __init__(self, duplicate_detector=None, version_manager: Optional[VersionManager] = None):
        """
        Initialize already-fixed detector.

        Args:
            duplicate_detector: DuplicateDetector instance (for embeddings)
            version_manager: VersionManager instance
        """
        self.version_manager = version_manager or VersionManager()
        self.duplicate_detector = duplicate_detector

        # Threshold for matching feedback to changelog (slightly lower than duplicate threshold)
        # We want to catch likely matches but not be too aggressive
        self.similarity_threshold = 0.80

    def check_already_fixed(
        self,
        feedback_content: str,
        user_version: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str], float]:
        """
        Check if feedback describes an issue already fixed in recent versions.

        Args:
            feedback_content: User's feedback content
            user_version: User's current version (if known)

        Returns:
            Tuple of (is_fixed, version_fixed_in, fix_description, similarity_score)
        """
        if not self.duplicate_detector:
            logger.warning("DD-003: No duplicate detector available, cannot check for already-fixed issues")
            return (False, None, None, 0.0)

        try:
            # Generate embedding for feedback
            feedback_embedding = self.duplicate_detector._generate_embedding(feedback_content)

            if feedback_embedding is None:
                logger.warning("DD-003: Could not generate embedding for feedback")
                return (False, None, None, 0.0)

            # Get all fixes from recent versions
            recent_fixes = self.version_manager.get_all_fixes_in_recent_versions(count=5)

            logger.info(f"DD-003: Checking against {len(recent_fixes)} recent fixes")

            # Compare against each fix
            best_match = None
            best_similarity = 0.0

            for version, fix_description in recent_fixes:
                # Generate embedding for fix description
                fix_embedding = self.duplicate_detector._generate_embedding(fix_description)

                if fix_embedding is None:
                    continue

                # Calculate similarity
                similarity = self.duplicate_detector._cosine_similarity(
                    feedback_embedding,
                    fix_embedding
                )

                # Track best match
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = (version, fix_description)

                logger.debug(
                    f"DD-003: Similarity to '{fix_description[:50]}...' in v{version}: {similarity:.2f}"
                )

            # Check if best match exceeds threshold
            if best_similarity >= self.similarity_threshold and best_match:
                version_fixed, fix_desc = best_match
                logger.info(
                    f"DD-003: Feedback matches already-fixed issue in v{version_fixed} "
                    f"(similarity: {best_similarity:.2f})"
                )
                return (True, version_fixed, fix_desc, best_similarity)

            return (False, None, None, best_similarity)

        except Exception as e:
            logger.error(f"DD-003: Error checking for already-fixed issue: {e}")
            return (False, None, None, 0.0)

    def generate_notification_message(
        self,
        version_fixed: str,
        fix_description: str,
        user_version: Optional[str] = None,
        similarity_score: float = 0.0
    ) -> str:
        """
        Generate user notification message for already-fixed issue.

        Args:
            version_fixed: Version where issue was fixed
            fix_description: Description of the fix
            user_version: User's current version (if known)
            similarity_score: Similarity score for transparency

        Returns:
            Formatted notification message
        """
        message_parts = [
            "✅ Good news! This issue appears to have been fixed in a recent version.",
            "",
            self.version_manager.format_changelog_entry(version_fixed, fix_description),
        ]

        # Add upgrade suggestion if user version is known and outdated
        if user_version and self.version_manager.is_version_outdated(user_version):
            message_parts.extend([
                "",
                f"You're currently on version {user_version}. "
                f"Upgrade to version {self.version_manager.current_version} to get this fix!",
                "",
                "Your feedback has been automatically closed since the issue is resolved."
            ])
        else:
            message_parts.extend([
                "",
                "If you're still experiencing this issue on the latest version, "
                "please submit new feedback with more details.",
                "",
                "Your feedback has been closed as already fixed."
            ])

        # Add similarity score for transparency (optional, for debugging)
        if logger.isEnabledFor(logging.DEBUG):
            message_parts.append(f"\n(Similarity score: {similarity_score:.2f})")

        return "\n".join(message_parts)


# Singleton instance
_version_manager = None
_already_fixed_detector = None


def get_version_manager() -> VersionManager:
    """Get the global version manager instance."""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager


def get_already_fixed_detector(duplicate_detector=None) -> AlreadyFixedDetector:
    """
    Get the global already-fixed detector instance.

    Args:
        duplicate_detector: Optional DuplicateDetector instance

    Returns:
        AlreadyFixedDetector instance
    """
    global _already_fixed_detector
    if _already_fixed_detector is None:
        _already_fixed_detector = AlreadyFixedDetector(
            duplicate_detector=duplicate_detector,
            version_manager=get_version_manager()
        )
    return _already_fixed_detector


if __name__ == "__main__":
    # Test version manager
    print("=" * 60)
    print("DD-003: Version Manager Test")
    print("=" * 60)

    vm = get_version_manager()

    print(f"\nCurrent version: {vm.current_version}")
    print(f"\nRecent versions ({len(vm.get_recent_versions())} total):")

    for version_data in vm.get_recent_versions():
        print(f"\n  v{version_data['version']} ({version_data['date']}):")
        for entry in version_data['entries']:
            icon = "🐛" if entry['type'] == 'fix' else "✨" if entry['type'] == 'feature' else "⚡"
            print(f"    {icon} {entry['description']}")

    print(f"\n\nAll fixes in recent 5 versions:")
    for version, fix in vm.get_all_fixes_in_recent_versions():
        print(f"  v{version}: {fix}")

    # Test version comparison
    print(f"\n\nVersion comparison tests:")
    test_versions = ["0.1.0", "0.2.5", "0.3.0", "0.4.0"]
    for v in test_versions:
        outdated = vm.is_version_outdated(v)
        status = "outdated" if outdated else "current/newer"
        print(f"  v{v}: {status}")

    print("\n" + "=" * 60)
    print("\nDD-003: Already-Fixed Detector Test")
    print("=" * 60)

    # Test already-fixed detection (requires duplicate detector with Groq API)
    try:
        from duplicate_detector import get_duplicate_detector

        detector = get_duplicate_detector()
        fixed_detector = get_already_fixed_detector(duplicate_detector=detector)

        if not detector.api_key:
            print("\n⚠️  No Groq API key - cannot test semantic matching")
            print("   Set GROQ_API_KEY environment variable to test")
        else:
            print("\n✅ Testing with real semantic matching...")

            # Test case: feedback that should match a fixed issue
            test_feedback = "The spam filter keeps flagging legitimate feedback as spam"
            print(f"\nTest feedback: '{test_feedback}'")

            is_fixed, version, fix_desc, similarity = fixed_detector.check_already_fixed(
                test_feedback,
                user_version="0.2.0"
            )

            if is_fixed:
                print(f"\n✅ Detected as already fixed!")
                print(f"   Version: {version}")
                print(f"   Fix: {fix_desc}")
                print(f"   Similarity: {similarity:.2f}")
                print(f"\nNotification message:")
                print("-" * 60)
                print(fixed_detector.generate_notification_message(
                    version, fix_desc, "0.2.0", similarity
                ))
                print("-" * 60)
            else:
                print(f"\n❌ Not detected as already fixed (similarity: {similarity:.2f})")
                print("   This might be a new issue or threshold needs adjustment")

    except ImportError:
        print("\n⚠️  duplicate_detector module not available")
        print("   Run this after implementing DD-001")

    print("\n" + "=" * 60)
