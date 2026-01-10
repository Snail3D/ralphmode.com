#!/usr/bin/env python3
"""
VM-002: Changelog Generator for Ralph Mode Bot

This module handles:
- Auto-generating changelogs from feedback items addressed in each version
- Storing version history with release notes
- Human-readable changelog formatting
- API access to version history

Usage:
    from changelog_generator import ChangelogGenerator

    cg = ChangelogGenerator()

    # Generate changelog for a new version
    changelog = cg.generate_changelog(
        version="1.2.0",
        feedback_ids=[123, 124, 125]
    )
    print(changelog)

    # Get full version history
    history = cg.get_version_history()
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

from database import get_db, Feedback, Base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)


# =============================================================================
# Database Model for Version History
# =============================================================================

class VersionHistory(Base):
    """Version history model - tracks all releases with changelogs."""

    __tablename__ = "version_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), unique=True, nullable=False, index=True)
    released_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    changelog = Column(Text, nullable=False)  # Human-readable changelog
    feedback_items = Column(Text, nullable=True)  # JSON list of feedback IDs
    change_type = Column(String(20), nullable=False)  # major, minor, patch

    # Index for chronological queries
    __table_args__ = (
        Index("idx_version_released_at", "released_at"),
    )

    def __repr__(self):
        return f"<VersionHistory(version={self.version}, released_at={self.released_at})>"


@dataclass
class ChangelogEntry:
    """Represents a single changelog entry."""
    version: str
    released_at: datetime
    change_type: str
    changes: List[str]
    feedback_ids: List[int]


class ChangelogGenerator:
    """
    VM-002: Changelog Generator

    Automatically generates human-readable changelogs from feedback items
    addressed in each version release.
    """

    def __init__(self, changelog_file: Optional[str] = None):
        """
        Initialize the changelog generator.

        Args:
            changelog_file: Path to CHANGELOG.md file (default: ./CHANGELOG.md)
        """
        # Changelog file location
        if changelog_file:
            self.changelog_file = Path(changelog_file)
        else:
            # Default to CHANGELOG.md in project root
            project_root = Path(__file__).parent
            self.changelog_file = project_root / 'CHANGELOG.md'

        logger.info(f"ChangelogGenerator initialized: changelog_file={self.changelog_file}")

    def generate_changelog(
        self,
        version: str,
        feedback_ids: List[int],
        change_type: str = "minor"
    ) -> str:
        """
        Generate changelog text from feedback items.

        Args:
            version: Version number (e.g., "1.2.0")
            feedback_ids: List of feedback IDs addressed in this version
            change_type: Type of change (major, minor, patch)

        Returns:
            Human-readable changelog text
        """
        with get_db() as db:
            # Fetch feedback items
            feedback_items = (
                db.query(Feedback)
                .filter(Feedback.id.in_(feedback_ids))
                .all()
            )

            if not feedback_items:
                logger.warning(f"No feedback items found for version {version}")
                return f"## Version {version}\n\nNo changes recorded.\n"

            # Group by feedback type
            changes_by_type = {
                "feature_request": [],
                "bug_report": [],
                "enhancement": [],
                "improvement": [],
                "other": []
            }

            for item in feedback_items:
                feedback_type = item.feedback_type
                # Map feedback types to changelog categories
                if feedback_type in ["feature_request", "feature"]:
                    category = "feature_request"
                elif feedback_type in ["bug_report", "bug"]:
                    category = "bug_report"
                elif feedback_type in ["enhancement", "improvement"]:
                    category = "enhancement"
                else:
                    category = "other"

                # Extract title from content (first line)
                title = item.content.split('\n')[0][:100]
                changes_by_type[category].append({
                    "id": item.id,
                    "title": title,
                    "content": item.content
                })

            # Build changelog text
            changelog_parts = [
                f"## Version {version}",
                f"Released: {datetime.utcnow().strftime('%Y-%m-%d')}",
                ""
            ]

            # Add features
            if changes_by_type["feature_request"]:
                changelog_parts.append("### ✨ New Features")
                for change in changes_by_type["feature_request"]:
                    changelog_parts.append(f"- {change['title']} (#{change['id']})")
                changelog_parts.append("")

            # Add bug fixes
            if changes_by_type["bug_report"]:
                changelog_parts.append("### 🐛 Bug Fixes")
                for change in changes_by_type["bug_report"]:
                    changelog_parts.append(f"- {change['title']} (#{change['id']})")
                changelog_parts.append("")

            # Add enhancements
            if changes_by_type["enhancement"]:
                changelog_parts.append("### 🔧 Enhancements")
                for change in changes_by_type["enhancement"]:
                    changelog_parts.append(f"- {change['title']} (#{change['id']})")
                changelog_parts.append("")

            # Add other changes
            if changes_by_type["other"]:
                changelog_parts.append("### 📝 Other Changes")
                for change in changes_by_type["other"]:
                    changelog_parts.append(f"- {change['title']} (#{change['id']})")
                changelog_parts.append("")

            changelog_text = "\n".join(changelog_parts)

            logger.info(f"Generated changelog for version {version} with {len(feedback_items)} items")

            return changelog_text

    def save_version_history(
        self,
        version: str,
        changelog: str,
        feedback_ids: List[int],
        change_type: str
    ):
        """
        Save version history to database.

        Args:
            version: Version number
            changelog: Generated changelog text
            feedback_ids: List of feedback IDs
            change_type: Type of change (major, minor, patch)
        """
        import json

        with get_db() as db:
            # Check if version already exists
            existing = db.query(VersionHistory).filter(
                VersionHistory.version == version
            ).first()

            if existing:
                logger.warning(f"Version {version} already exists, updating")
                existing.changelog = changelog
                existing.feedback_items = json.dumps(feedback_ids)
                existing.change_type = change_type
                existing.released_at = datetime.utcnow()
            else:
                # Create new version history entry
                version_history = VersionHistory(
                    version=version,
                    changelog=changelog,
                    feedback_items=json.dumps(feedback_ids),
                    change_type=change_type,
                    released_at=datetime.utcnow()
                )
                db.add(version_history)

            db.commit()
            logger.info(f"Version history saved for {version}")

    def update_changelog_file(self, version: str, changelog: str):
        """
        Update CHANGELOG.md file with new version.

        Args:
            version: Version number
            changelog: Changelog text for this version
        """
        try:
            # Read existing changelog if it exists
            if self.changelog_file.exists():
                existing_content = self.changelog_file.read_text()
            else:
                existing_content = "# Changelog\n\nAll notable changes to Ralph Mode Bot will be documented in this file.\n\n"

            # Prepend new changelog (most recent first)
            # Find the position after the header
            header_end = existing_content.find('\n\n') + 2
            if header_end == 1:  # Not found
                header_end = 0

            new_content = (
                existing_content[:header_end] +
                changelog + "\n\n" +
                existing_content[header_end:]
            )

            # Write updated changelog
            self.changelog_file.write_text(new_content)
            logger.info(f"CHANGELOG.md updated with version {version}")

        except Exception as e:
            logger.error(f"Error updating CHANGELOG.md: {e}")
            # Don't raise - changelog file is optional

    def get_version_history(self, limit: int = 50) -> List[ChangelogEntry]:
        """
        Get version history from database.

        Args:
            limit: Maximum number of versions to return

        Returns:
            List of ChangelogEntry objects
        """
        import json

        with get_db() as db:
            versions = (
                db.query(VersionHistory)
                .order_by(VersionHistory.released_at.desc())
                .limit(limit)
                .all()
            )

            entries = []
            for version in versions:
                # Parse feedback IDs from JSON
                try:
                    feedback_ids = json.loads(version.feedback_items) if version.feedback_items else []
                except:
                    feedback_ids = []

                # Parse changes from changelog
                changes = self._parse_changelog_changes(version.changelog)

                entries.append(ChangelogEntry(
                    version=version.version,
                    released_at=version.released_at,
                    change_type=version.change_type,
                    changes=changes,
                    feedback_ids=feedback_ids
                ))

            return entries

    def _parse_changelog_changes(self, changelog: str) -> List[str]:
        """
        Parse changelog text into list of changes.

        Args:
            changelog: Changelog text

        Returns:
            List of change descriptions
        """
        changes = []
        lines = changelog.split('\n')

        for line in lines:
            # Look for bullet points
            if line.strip().startswith('-'):
                change = line.strip()[1:].strip()
                if change:
                    changes.append(change)

        return changes

    def get_version_by_number(self, version: str) -> Optional[ChangelogEntry]:
        """
        Get specific version from history.

        Args:
            version: Version number to retrieve

        Returns:
            ChangelogEntry or None if not found
        """
        import json

        with get_db() as db:
            version_history = (
                db.query(VersionHistory)
                .filter(VersionHistory.version == version)
                .first()
            )

            if not version_history:
                return None

            # Parse feedback IDs
            try:
                feedback_ids = json.loads(version_history.feedback_items) if version_history.feedback_items else []
            except:
                feedback_ids = []

            # Parse changes
            changes = self._parse_changelog_changes(version_history.changelog)

            return ChangelogEntry(
                version=version_history.version,
                released_at=version_history.released_at,
                change_type=version_history.change_type,
                changes=changes,
                feedback_ids=feedback_ids
            )

    def generate_and_save(
        self,
        version: str,
        feedback_ids: List[int],
        change_type: str = "minor",
        update_file: bool = True
    ) -> str:
        """
        Generate changelog and save to database and file.

        This is the main method to use when releasing a new version.

        Args:
            version: Version number
            feedback_ids: List of feedback IDs addressed
            change_type: Type of change (major, minor, patch)
            update_file: Whether to update CHANGELOG.md file

        Returns:
            Generated changelog text
        """
        # Generate changelog
        changelog = self.generate_changelog(version, feedback_ids, change_type)

        # Save to database
        self.save_version_history(version, changelog, feedback_ids, change_type)

        # Update CHANGELOG.md file
        if update_file:
            self.update_changelog_file(version, changelog)

        return changelog


def main():
    """Main entry point for CLI."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Ralph Mode Changelog Generator (VM-002)')
    parser.add_argument(
        'action',
        choices=['generate', 'history', 'get'],
        help='Action to perform'
    )
    parser.add_argument(
        '--version',
        type=str,
        help='Version number (for generate/get)'
    )
    parser.add_argument(
        '--feedback-ids',
        type=str,
        help='Comma-separated list of feedback IDs (for generate)'
    )
    parser.add_argument(
        '--change-type',
        choices=['major', 'minor', 'patch'],
        default='minor',
        help='Change type (for generate)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Number of versions to show (for history)'
    )

    args = parser.parse_args()

    cg = ChangelogGenerator()

    if args.action == 'generate':
        # Generate changelog for new version
        if not args.version or not args.feedback_ids:
            print("Error: --version and --feedback-ids required for generate action")
            return

        feedback_ids = [int(x.strip()) for x in args.feedback_ids.split(',')]

        changelog = cg.generate_and_save(
            version=args.version,
            feedback_ids=feedback_ids,
            change_type=args.change_type
        )

        print(f"Generated changelog for version {args.version}:")
        print("-" * 60)
        print(changelog)

    elif args.action == 'history':
        # Get version history
        history = cg.get_version_history(limit=args.limit)

        print(f"Version History (last {len(history)} releases):")
        print("=" * 60)

        for entry in history:
            print(f"\nVersion {entry.version} ({entry.change_type})")
            print(f"Released: {entry.released_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Changes: {len(entry.changes)} items")
            print(f"Feedback IDs: {entry.feedback_ids}")

    elif args.action == 'get':
        # Get specific version
        if not args.version:
            print("Error: --version required for get action")
            return

        entry = cg.get_version_by_number(args.version)

        if not entry:
            print(f"Version {args.version} not found")
            return

        print(f"Version {entry.version} ({entry.change_type})")
        print(f"Released: {entry.released_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nChanges:")
        for change in entry.changes:
            print(f"  - {change}")
        print(f"\nFeedback IDs: {entry.feedback_ids}")


if __name__ == '__main__':
    main()
