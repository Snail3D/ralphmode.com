#!/usr/bin/env python3
"""
Rollback Manager for Ralph Mode Onboarding

Tracks setup changes and allows users to undo steps that went wrong.
Provides safety net for the onboarding process.
"""

import logging
import json
import os
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path


class RollbackManager:
    """Manages rollback functionality for onboarding steps."""

    def __init__(self, backup_dir: str = ".ralph_backups"):
        """Initialize the rollback manager.

        Args:
            backup_dir: Directory to store backups (default: .ralph_backups)
        """
        self.logger = logging.getLogger(__name__)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True, parents=True)

        # Rollback history file
        self.history_file = self.backup_dir / "rollback_history.json"
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load rollback history from disk.

        Returns:
            List of historical rollback actions
        """
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading rollback history: {e}")
            return []

    def _save_history(self) -> None:
        """Save rollback history to disk."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving rollback history: {e}")

    def track_change(
        self,
        user_id: int,
        step_name: str,
        change_type: str,
        details: Dict[str, Any]
    ) -> Optional[str]:
        """Track a setup change for potential rollback.

        Args:
            user_id: User ID
            step_name: Name of the setup step (e.g., "ssh_key_generation")
            change_type: Type of change (e.g., "file_created", "config_modified")
            details: Details about the change (file paths, old values, etc.)

        Returns:
            Change ID for referencing this change, or None on error
        """
        change_id = f"{user_id}_{step_name}_{int(datetime.utcnow().timestamp())}"

        change_record = {
            "change_id": change_id,
            "user_id": user_id,
            "step_name": step_name,
            "change_type": change_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "rolled_back": False
        }

        self.history.append(change_record)
        self._save_history()

        self.logger.info(f"Tracked change: {change_id} - {step_name} ({change_type})")
        return change_id

    def track_file_creation(
        self,
        user_id: int,
        step_name: str,
        file_path: str
    ) -> Optional[str]:
        """Track a file that was created during setup.

        Args:
            user_id: User ID
            step_name: Setup step name
            file_path: Path to the created file

        Returns:
            Change ID or None
        """
        return self.track_change(
            user_id=user_id,
            step_name=step_name,
            change_type="file_created",
            details={"file_path": file_path}
        )

    def track_file_modification(
        self,
        user_id: int,
        step_name: str,
        file_path: str,
        backup_content: Optional[str] = None
    ) -> Optional[str]:
        """Track a file modification with optional backup.

        Args:
            user_id: User ID
            step_name: Setup step name
            file_path: Path to the modified file
            backup_content: Original content (if available)

        Returns:
            Change ID or None
        """
        # Create backup if content provided
        backup_path = None
        if backup_content is not None:
            backup_path = self._create_backup(file_path, backup_content)

        return self.track_change(
            user_id=user_id,
            step_name=step_name,
            change_type="file_modified",
            details={
                "file_path": file_path,
                "backup_path": backup_path
            }
        )

    def track_env_variable(
        self,
        user_id: int,
        step_name: str,
        variable_name: str,
        old_value: Optional[str] = None
    ) -> Optional[str]:
        """Track an environment variable change.

        Args:
            user_id: User ID
            step_name: Setup step name
            variable_name: Name of the env variable
            old_value: Previous value (None if newly created)

        Returns:
            Change ID or None
        """
        return self.track_change(
            user_id=user_id,
            step_name=step_name,
            change_type="env_variable",
            details={
                "variable_name": variable_name,
                "old_value": old_value
            }
        )

    def _create_backup(self, file_path: str, content: str) -> Optional[str]:
        """Create a backup of file content.

        Args:
            file_path: Original file path
            content: Content to backup

        Returns:
            Path to backup file or None on error
        """
        try:
            # Create a unique backup filename
            timestamp = int(datetime.utcnow().timestamp())
            backup_filename = f"backup_{Path(file_path).name}_{timestamp}"
            backup_path = self.backup_dir / backup_filename

            with open(backup_path, 'w') as f:
                f.write(content)

            self.logger.info(f"Created backup: {backup_path}")
            return str(backup_path)

        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return None

    def get_recent_changes(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent changes for a user.

        Args:
            user_id: User ID
            limit: Maximum number of changes to return

        Returns:
            List of recent changes (newest first)
        """
        user_changes = [
            change for change in self.history
            if change["user_id"] == user_id and not change["rolled_back"]
        ]

        # Sort by timestamp (newest first)
        user_changes.sort(key=lambda x: x["timestamp"], reverse=True)

        return user_changes[:limit]

    def get_changes_by_step(
        self,
        user_id: int,
        step_name: str
    ) -> List[Dict[str, Any]]:
        """Get all changes for a specific step.

        Args:
            user_id: User ID
            step_name: Setup step name

        Returns:
            List of changes for the step
        """
        return [
            change for change in self.history
            if (change["user_id"] == user_id and
                change["step_name"] == step_name and
                not change["rolled_back"])
        ]

    def rollback_change(
        self,
        change_id: str
    ) -> tuple[bool, str]:
        """Rollback a specific change.

        Args:
            change_id: ID of the change to rollback

        Returns:
            Tuple of (success, message)
        """
        # Find the change
        change = None
        for c in self.history:
            if c["change_id"] == change_id:
                change = c
                break

        if not change:
            return False, f"Change {change_id} not found"

        if change["rolled_back"]:
            return False, "This change was already rolled back"

        # Perform rollback based on type
        change_type = change["change_type"]
        details = change["details"]

        try:
            if change_type == "file_created":
                success, msg = self._rollback_file_creation(details)
            elif change_type == "file_modified":
                success, msg = self._rollback_file_modification(details)
            elif change_type == "env_variable":
                success, msg = self._rollback_env_variable(details)
            else:
                return False, f"Unknown change type: {change_type}"

            if success:
                # Mark as rolled back
                change["rolled_back"] = True
                change["rollback_timestamp"] = datetime.utcnow().isoformat()
                self._save_history()

            return success, msg

        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False, f"Rollback failed: {str(e)}"

    def _rollback_file_creation(self, details: Dict[str, Any]) -> tuple[bool, str]:
        """Rollback a file creation (delete the file).

        Args:
            details: Change details

        Returns:
            Tuple of (success, message)
        """
        file_path = details.get("file_path")
        if not file_path:
            return False, "No file path in details"

        path = Path(file_path)
        if not path.exists():
            return True, f"File {file_path} already removed"

        try:
            path.unlink()
            return True, f"Removed file: {file_path}"
        except Exception as e:
            return False, f"Failed to remove {file_path}: {e}"

    def _rollback_file_modification(self, details: Dict[str, Any]) -> tuple[bool, str]:
        """Rollback a file modification (restore from backup).

        Args:
            details: Change details

        Returns:
            Tuple of (success, message)
        """
        file_path = details.get("file_path")
        backup_path = details.get("backup_path")

        if not file_path:
            return False, "No file path in details"

        if not backup_path:
            return False, "No backup available for this change"

        backup = Path(backup_path)
        if not backup.exists():
            return False, f"Backup file {backup_path} not found"

        try:
            # Restore from backup
            shutil.copy2(backup_path, file_path)
            return True, f"Restored {file_path} from backup"
        except Exception as e:
            return False, f"Failed to restore {file_path}: {e}"

    def _rollback_env_variable(self, details: Dict[str, Any]) -> tuple[bool, str]:
        """Rollback an environment variable change.

        Args:
            details: Change details

        Returns:
            Tuple of (success, message)
        """
        variable_name = details.get("variable_name")
        old_value = details.get("old_value")

        if not variable_name:
            return False, "No variable name in details"

        env_file = Path(".env")
        if not env_file.exists():
            return False, ".env file not found"

        try:
            # Read current .env
            with open(env_file, 'r') as f:
                lines = f.readlines()

            # Remove or update the variable
            new_lines = []
            variable_found = False

            for line in lines:
                if line.startswith(f"{variable_name}="):
                    variable_found = True
                    if old_value is not None:
                        # Restore old value
                        new_lines.append(f"{variable_name}={old_value}\n")
                    # else: skip line (removes the variable)
                else:
                    new_lines.append(line)

            # Write back to .env
            with open(env_file, 'w') as f:
                f.writelines(new_lines)

            if old_value is None:
                return True, f"Removed {variable_name} from .env"
            else:
                return True, f"Restored {variable_name} to previous value"

        except Exception as e:
            return False, f"Failed to update .env: {e}"

    def rollback_step(
        self,
        user_id: int,
        step_name: str
    ) -> tuple[bool, str, List[str]]:
        """Rollback all changes for a specific step.

        Args:
            user_id: User ID
            step_name: Name of the step to rollback

        Returns:
            Tuple of (overall_success, summary_message, detail_messages)
        """
        changes = self.get_changes_by_step(user_id, step_name)

        if not changes:
            return False, f"No changes found for step: {step_name}", []

        results = []
        success_count = 0
        fail_count = 0

        # Rollback changes in reverse order (newest first)
        changes.sort(key=lambda x: x["timestamp"], reverse=True)

        for change in changes:
            success, msg = self.rollback_change(change["change_id"])
            results.append(msg)

            if success:
                success_count += 1
            else:
                fail_count += 1

        overall_success = fail_count == 0
        summary = f"Rolled back {success_count}/{len(changes)} changes for {step_name}"

        if fail_count > 0:
            summary += f" ({fail_count} failed)"

        return overall_success, summary, results

    def clear_history(self, user_id: int) -> int:
        """Clear rollback history for a user.

        Args:
            user_id: User ID

        Returns:
            Number of entries cleared
        """
        original_count = len(self.history)

        # Keep only entries not belonging to this user
        self.history = [
            change for change in self.history
            if change["user_id"] != user_id
        ]

        cleared_count = original_count - len(self.history)

        if cleared_count > 0:
            self._save_history()

        return cleared_count

    def get_rollback_summary(
        self,
        user_id: int
    ) -> str:
        """Get a human-readable summary of recent changes.

        Args:
            user_id: User ID

        Returns:
            Formatted summary message
        """
        changes = self.get_recent_changes(user_id, limit=10)

        if not changes:
            return "*No Recent Changes* 📋\n\nRalph hasn't tracked any setup changes yet!"

        lines = ["*Recent Setup Changes* 📋\n"]

        for i, change in enumerate(changes, 1):
            step = change["step_name"].replace("_", " ").title()
            change_type = change["change_type"].replace("_", " ").title()
            timestamp = change["timestamp"].split("T")[1].split(".")[0]  # Time only

            lines.append(f"{i}. **{step}** - {change_type}")
            lines.append(f"   _Changed at: {timestamp}_")

            # Add specific details
            details = change["details"]
            if "file_path" in details:
                lines.append(f"   📄 File: `{details['file_path']}`")
            elif "variable_name" in details:
                lines.append(f"   🔧 Variable: `{details['variable_name']}`")

            lines.append("")  # Blank line

        lines.append("\n_You can undo these changes if something goes wrong!_")

        return "\n".join(lines)


def get_rollback_manager() -> RollbackManager:
    """Get the rollback manager instance.

    Returns:
        RollbackManager instance
    """
    return RollbackManager()
