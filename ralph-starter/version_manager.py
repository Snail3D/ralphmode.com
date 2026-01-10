#!/usr/bin/env python3
"""
VM-001: Semantic Version Manager for Ralph Mode Bot

This service handles:
- Semantic versioning (MAJOR.MINOR.PATCH)
- Auto-increment based on change type
- Version storage in VERSION file
- Git tag creation for each version

Change types:
- MAJOR: Breaking changes (incompatible API changes)
- MINOR: New features (feature_request, backward compatible)
- PATCH: Bug fixes and enhancements (bug_report, enhancement)

Usage:
    from version_manager import VersionManager

    vm = VersionManager()

    # Increment version based on change type
    new_version = vm.increment_version('minor')  # For new feature
    print(f"New version: {new_version}")

    # Get current version
    current = vm.get_current_version()
    print(f"Current: {current}")
"""

import os
import sys
import logging
import subprocess
import re
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('version_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of change for version bumping."""
    MAJOR = "major"  # Breaking changes
    MINOR = "minor"  # New features
    PATCH = "patch"  # Bug fixes


@dataclass
class Version:
    """Semantic version representation."""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """String representation of version."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        """Repr of version."""
        return f"Version({self.major}.{self.minor}.{self.patch})"

    @staticmethod
    def parse(version_string: str) -> 'Version':
        """
        Parse version string into Version object.

        Args:
            version_string: Version string like "1.2.3"

        Returns:
            Version object

        Raises:
            ValueError: If version string is invalid
        """
        # Remove 'v' prefix if present
        version_string = version_string.lstrip('v')

        # Parse semantic version
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_string)
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        return Version(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3))
        )

    def increment(self, change_type: ChangeType) -> 'Version':
        """
        Create new version by incrementing based on change type.

        Args:
            change_type: Type of change (MAJOR, MINOR, PATCH)

        Returns:
            New Version object
        """
        if change_type == ChangeType.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif change_type == ChangeType.MINOR:
            return Version(self.major, self.minor + 1, 0)
        elif change_type == ChangeType.PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        else:
            raise ValueError(f"Unknown change type: {change_type}")


class VersionManager:
    """
    VM-001: Version Manager for Semantic Versioning

    Manages semantic versioning for the Ralph Mode Bot, including
    auto-incrementing based on change type, storing versions in
    a VERSION file, and creating git tags.
    """

    def __init__(self, version_file: Optional[str] = None):
        """
        Initialize the version manager.

        Args:
            version_file: Path to VERSION file (default: ./VERSION)
        """
        # Version file location
        if version_file:
            self.version_file = Path(version_file)
        else:
            # Default to VERSION file in project root
            project_root = Path(__file__).parent
            self.version_file = project_root / 'VERSION'

        # Git repository root
        self.git_root = self._find_git_root()

        logger.info(f"VersionManager initialized: version_file={self.version_file}")

    def _find_git_root(self) -> Optional[Path]:
        """
        Find the git repository root.

        Returns:
            Path to git root or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            logger.warning("Not in a git repository")
            return None

    def get_current_version(self) -> Version:
        """
        Get the current version from VERSION file.

        Returns:
            Current Version object

        Raises:
            FileNotFoundError: If VERSION file doesn't exist
        """
        if not self.version_file.exists():
            logger.warning(f"VERSION file not found at {self.version_file}, starting at 0.1.0")
            return Version(0, 1, 0)

        try:
            version_string = self.version_file.read_text().strip()
            version = Version.parse(version_string)
            logger.info(f"Current version: {version}")
            return version
        except Exception as e:
            logger.error(f"Error reading VERSION file: {e}")
            raise

    def increment_version(
        self,
        change_type: Literal['major', 'minor', 'patch'],
        create_tag: bool = True,
        commit: bool = True
    ) -> Version:
        """
        Increment version based on change type.

        Args:
            change_type: Type of change ('major', 'minor', or 'patch')
            create_tag: Whether to create a git tag
            commit: Whether to commit the VERSION file change

        Returns:
            New Version object
        """
        # Get current version
        current_version = self.get_current_version()

        # Increment based on change type
        change_enum = ChangeType(change_type)
        new_version = current_version.increment(change_enum)

        logger.info(f"Incrementing version: {current_version} -> {new_version} ({change_type})")

        # Save new version to file
        self._save_version(new_version)

        # Commit VERSION file if requested
        if commit and self.git_root:
            self._commit_version_file(new_version)

        # Create git tag if requested
        if create_tag and self.git_root:
            self._create_git_tag(new_version)

        return new_version

    def _save_version(self, version: Version):
        """
        Save version to VERSION file.

        Args:
            version: Version to save
        """
        try:
            self.version_file.write_text(str(version) + '\n')
            logger.info(f"Version saved to {self.version_file}: {version}")
        except Exception as e:
            logger.error(f"Error saving version to file: {e}")
            raise

    def _commit_version_file(self, version: Version):
        """
        Commit VERSION file to git.

        Args:
            version: Version that was set
        """
        try:
            # Stage VERSION file
            subprocess.run(
                ['git', 'add', str(self.version_file)],
                check=True,
                capture_output=True
            )

            # Commit with version bump message
            commit_message = f"chore: Bump version to {version}"
            subprocess.run(
                ['git', 'commit', '-m', commit_message],
                check=True,
                capture_output=True
            )

            logger.info(f"VERSION file committed: {version}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error committing VERSION file: {e}")
            # Don't raise - tag creation might still work

    def _create_git_tag(self, version: Version):
        """
        Create a git tag for the version.

        Args:
            version: Version to tag
        """
        try:
            tag_name = f"v{version}"

            # Create annotated tag
            subprocess.run(
                ['git', 'tag', '-a', tag_name, '-m', f"Release {version}"],
                check=True,
                capture_output=True
            )

            logger.info(f"Git tag created: {tag_name}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating git tag: {e}")
            # Don't raise - version is still saved

    def get_change_type_from_feedback_type(self, feedback_type: str) -> ChangeType:
        """
        Determine change type from feedback type.

        Args:
            feedback_type: Feedback type (e.g., 'feature_request', 'bug_report')

        Returns:
            ChangeType enum value
        """
        # Map feedback types to change types
        if feedback_type == 'breaking_change':
            return ChangeType.MAJOR
        elif feedback_type in ['feature_request', 'feature']:
            return ChangeType.MINOR
        elif feedback_type in ['bug_report', 'bug', 'enhancement', 'improvement']:
            return ChangeType.PATCH
        else:
            # Default to patch for unknown types
            logger.warning(f"Unknown feedback type '{feedback_type}', defaulting to PATCH")
            return ChangeType.PATCH

    def set_version(self, version_string: str, create_tag: bool = True) -> Version:
        """
        Set version explicitly (for initialization or manual override).

        Args:
            version_string: Version string like "1.2.3"
            create_tag: Whether to create a git tag

        Returns:
            Version object
        """
        version = Version.parse(version_string)
        logger.info(f"Setting version to: {version}")

        self._save_version(version)

        if create_tag and self.git_root:
            self._create_git_tag(version)

        return version


def main():
    """Main entry point for CLI."""
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Mode Version Manager (VM-001)')
    parser.add_argument(
        'action',
        choices=['get', 'increment', 'set'],
        help='Action to perform'
    )
    parser.add_argument(
        '--change-type',
        choices=['major', 'minor', 'patch'],
        help='Change type for increment action'
    )
    parser.add_argument(
        '--version',
        type=str,
        help='Version string for set action'
    )
    parser.add_argument(
        '--no-tag',
        action='store_true',
        help='Skip git tag creation'
    )
    parser.add_argument(
        '--no-commit',
        action='store_true',
        help='Skip git commit of VERSION file'
    )

    args = parser.parse_args()

    vm = VersionManager()

    if args.action == 'get':
        # Get current version
        version = vm.get_current_version()
        print(f"Current version: {version}")

    elif args.action == 'increment':
        # Increment version
        if not args.change_type:
            print("Error: --change-type required for increment action")
            sys.exit(1)

        version = vm.increment_version(
            args.change_type,
            create_tag=not args.no_tag,
            commit=not args.no_commit
        )
        print(f"New version: {version}")

    elif args.action == 'set':
        # Set version explicitly
        if not args.version:
            print("Error: --version required for set action")
            sys.exit(1)

        version = vm.set_version(
            args.version,
            create_tag=not args.no_tag
        )
        print(f"Version set to: {version}")


if __name__ == '__main__':
    main()
