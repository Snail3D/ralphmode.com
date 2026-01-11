#!/usr/bin/env python3
"""
Git Helper for Ralph Mode

Assists with git operations during onboarding and setup.
Makes git commands friendly and accessible with Ralph's personality.
"""

import os
import subprocess
import logging
from typing import Tuple, List, Optional


class GitHelper:
    """Helper for git operations with Ralph's personality."""

    def __init__(self):
        """Initialize the Git Helper."""
        self.logger = logging.getLogger(__name__)

    def check_git_installed(self) -> Tuple[bool, str]:
        """Check if git is installed.

        Returns:
            Tuple of (is_installed, version_or_error)
        """
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, "Git not responding"
        except FileNotFoundError:
            return False, "Git not installed"
        except Exception as e:
            self.logger.error(f"Error checking git: {e}")
            return False, str(e)

    def check_git_repo(self, path: str = ".") -> Tuple[bool, str]:
        """Check if current directory is a git repository.

        Args:
            path: Path to check (default: current directory)

        Returns:
            Tuple of (is_repo, message)
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "Git repository found"
            else:
                return False, "Not a git repository"
        except Exception as e:
            self.logger.error(f"Error checking git repo: {e}")
            return False, str(e)

    def get_git_status(self, path: str = ".") -> Tuple[bool, str]:
        """Get git status output.

        Args:
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, status_output)
        """
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except Exception as e:
            self.logger.error(f"Error getting git status: {e}")
            return False, str(e)

    def get_untracked_files(self, path: str = ".") -> Tuple[bool, List[str]]:
        """Get list of untracked files.

        Args:
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, list_of_files)
        """
        success, status = self.get_git_status(path)
        if not success:
            return False, []

        untracked = []
        for line in status.split('\n'):
            if line.startswith('??'):
                # Extract filename from "?? filename" format
                filename = line[3:].strip()
                untracked.append(filename)

        return True, untracked

    def get_modified_files(self, path: str = ".") -> Tuple[bool, List[str]]:
        """Get list of modified files.

        Args:
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, list_of_files)
        """
        success, status = self.get_git_status(path)
        if not success:
            return False, []

        modified = []
        for line in status.split('\n'):
            if line.startswith(' M') or line.startswith('M '):
                # Extract filename from status format
                filename = line[3:].strip()
                modified.append(filename)

        return True, modified

    def git_add_files(self, files: List[str], path: str = ".") -> Tuple[bool, str]:
        """Add files to git staging area.

        Args:
            files: List of files to add
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, message)
        """
        if not files:
            return False, "No files specified"

        try:
            # Use git add with list of files
            result = subprocess.run(
                ['git', 'add'] + files,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, f"Added {len(files)} file(s) to staging area"
            else:
                return False, result.stderr.strip()
        except Exception as e:
            self.logger.error(f"Error adding files: {e}")
            return False, str(e)

    def git_add_all(self, path: str = ".") -> Tuple[bool, str]:
        """Add all files to git staging area.

        Args:
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ['git', 'add', '.'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, "All files added to staging area"
            else:
                return False, result.stderr.strip()
        except Exception as e:
            self.logger.error(f"Error adding all files: {e}")
            return False, str(e)

    def git_commit(self, message: str, path: str = ".") -> Tuple[bool, str]:
        """Create a git commit.

        Args:
            message: Commit message
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, message)
        """
        if not message:
            return False, "Commit message required"

        try:
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                # Check if it's because there's nothing to commit
                if "nothing to commit" in result.stdout.lower():
                    return False, "Nothing to commit (working tree clean)"
                return False, result.stderr.strip()
        except Exception as e:
            self.logger.error(f"Error creating commit: {e}")
            return False, str(e)

    def git_push(self, remote: str = "origin", branch: str = "main", set_upstream: bool = False, path: str = ".") -> Tuple[bool, str]:
        """Push commits to remote repository.

        Args:
            remote: Remote name (default: origin)
            branch: Branch name (default: main)
            set_upstream: Whether to set upstream tracking (default: False)
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ['git', 'push']
            if set_upstream:
                cmd.extend(['-u', remote, branch])
            else:
                cmd.extend([remote, branch])

            result = subprocess.run(
                cmd,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, "Push successful!"
            else:
                return False, result.stderr.strip()
        except Exception as e:
            self.logger.error(f"Error pushing to remote: {e}")
            return False, str(e)

    def get_current_branch(self, path: str = ".") -> Tuple[bool, str]:
        """Get current git branch name.

        Args:
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, branch_name)
        """
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except Exception as e:
            self.logger.error(f"Error getting branch: {e}")
            return False, str(e)

    def has_remote(self, remote: str = "origin", path: str = ".") -> Tuple[bool, str]:
        """Check if a remote exists.

        Args:
            remote: Remote name to check (default: origin)
            path: Repository path (default: current directory)

        Returns:
            Tuple of (exists, remote_url_or_error)
        """
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', remote],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, f"Remote '{remote}' not found"
        except Exception as e:
            self.logger.error(f"Error checking remote: {e}")
            return False, str(e)

    def get_commit_count(self, path: str = ".") -> Tuple[bool, int]:
        """Get total number of commits.

        Args:
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, commit_count)
        """
        try:
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                count = int(result.stdout.strip())
                return True, count
            else:
                # No commits yet
                return True, 0
        except Exception as e:
            self.logger.error(f"Error getting commit count: {e}")
            return False, 0

    def validate_commit_message(self, message: str) -> Tuple[bool, str]:
        """Validate a commit message for best practices.

        Args:
            message: Proposed commit message

        Returns:
            Tuple of (is_valid, feedback_message)
        """
        if not message or not message.strip():
            return False, "Commit message cannot be empty"

        message = message.strip()

        # Check minimum length
        if len(message) < 10:
            return False, "Commit message too short. Try to be more descriptive!"

        # Check maximum length for first line
        first_line = message.split('\n')[0]
        if len(first_line) > 72:
            return False, "First line too long. Keep it under 72 characters!"

        # Check if starts with capital letter
        if not first_line[0].isupper():
            return False, "Start commit message with a capital letter!"

        # Check if ends with period (not recommended)
        if first_line.endswith('.'):
            return False, "Don't end commit message with a period!"

        # All good!
        return True, "Great commit message! 🎉"

    def suggest_commit_message(self, path: str = ".") -> Tuple[bool, str]:
        """Suggest a commit message based on changes.

        Args:
            path: Repository path (default: current directory)

        Returns:
            Tuple of (success, suggested_message)
        """
        # Get list of changed files
        success_untracked, untracked = self.get_untracked_files(path)
        success_modified, modified = self.get_modified_files(path)

        if not (success_untracked or success_modified):
            return False, "Could not analyze changes"

        total_changes = len(untracked) + len(modified)

        if total_changes == 0:
            return False, "No changes to commit"

        # Check for common patterns
        if any('.env' in f for f in untracked + modified):
            return True, "Add environment configuration"
        elif any('README' in f for f in untracked + modified):
            return True, "Update project documentation"
        elif any('.py' in f for f in untracked + modified):
            return True, "Add initial Python files"
        elif any('.js' in f for f in untracked + modified):
            return True, "Add initial JavaScript files"
        else:
            return True, f"Initial commit with {total_changes} file(s)"


# Singleton instance
_git_helper_instance = None


def get_git_helper() -> GitHelper:
    """Get the GitHelper singleton instance.

    Returns:
        GitHelper instance
    """
    global _git_helper_instance
    if _git_helper_instance is None:
        _git_helper_instance = GitHelper()
    return _git_helper_instance
