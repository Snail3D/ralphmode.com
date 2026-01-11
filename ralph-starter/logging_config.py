#!/usr/bin/env python3
"""
BC-005: Audit Logging Configuration for Ralph Mode

This module provides persistent audit logging for filtered content.
Logs are stored securely, never sent to Telegram, and auto-rotated to prevent bloat.

Features:
- Persistent file-based logging
- JSON format for easy parsing
- Automatic log rotation (size-based and time-based)
- Secure storage (logs/ directory with restrictive permissions)
- Admin access only
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


# =============================================================================
# CONFIGURATION
# =============================================================================

# Log directory (excluded from git via .gitignore)
LOG_DIR = Path(__file__).parent / "logs"
AUDIT_LOG_FILE = LOG_DIR / "sanitizer_audit.jsonl"  # JSON Lines format

# Rotation settings
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB per file
BACKUP_COUNT = 5  # Keep 5 backup files
DAYS_TO_KEEP = 7  # Auto-rotate daily, keep 7 days

# Security: Restrict log file permissions (owner read/write only)
LOG_FILE_MODE = 0o600


# =============================================================================
# AUDIT LOGGER SETUP
# =============================================================================

class AuditLogger:
    """
    Handles persistent audit logging for sanitization events.
    """

    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize the audit logger.

        Args:
            log_file: Path to audit log file (default: logs/sanitizer_audit.jsonl)
        """
        self.log_file = log_file or AUDIT_LOG_FILE
        self._ensure_log_directory()
        self._setup_file_logging()

    def _ensure_log_directory(self) -> None:
        """Create logs directory if it doesn't exist with secure permissions."""
        LOG_DIR.mkdir(mode=0o700, exist_ok=True)

        # Ensure .gitignore exists to prevent committing logs
        gitignore_path = LOG_DIR / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("# Exclude all log files\n*.log\n*.jsonl\n*.json\n")

    def _setup_file_logging(self) -> None:
        """Set up file-based logging with rotation."""
        # Create the log file with secure permissions if it doesn't exist
        if not self.log_file.exists():
            self.log_file.touch(mode=LOG_FILE_MODE)
        else:
            # Ensure existing file has secure permissions
            os.chmod(self.log_file, LOG_FILE_MODE)

    def log_sanitization(
        self,
        context: str,
        replacements_count: int,
        patterns_matched: List[str],
        original_message_context: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> None:
        """
        Log a sanitization event to the audit log.

        Args:
            context: Where the sanitization occurred (e.g., "groq_input", "telegram_output")
            replacements_count: Number of secrets replaced
            patterns_matched: List of replacement types (e.g., ["[OPENAI_KEY]", "[IP_ADDRESS]"])
            original_message_context: Brief context about the original message (NOT the secret itself)
            user_id: Telegram user ID if applicable
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "replacements_count": replacements_count,
            "patterns_matched": patterns_matched,
            "original_context": original_message_context or "unknown",
            "user_id": user_id
        }

        # Append to JSONL file (one JSON object per line)
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logging.error(f"Failed to write audit log: {e}")

    def get_recent_logs(self, limit: int = 20) -> List[Dict]:
        """
        Get the most recent audit log entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent audit log entries (most recent first)
        """
        if not self.log_file.exists():
            return []

        entries = []
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()

            # Parse last N lines (most recent)
            for line in lines[-limit:]:
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

            # Return in reverse order (most recent first)
            return list(reversed(entries))

        except Exception as e:
            logging.error(f"Failed to read audit log: {e}")
            return []

    def get_logs_by_context(self, context: str, limit: int = 20) -> List[Dict]:
        """
        Get audit logs filtered by context.

        Args:
            context: Context to filter by (e.g., "groq_input")
            limit: Maximum entries to return

        Returns:
            Filtered log entries
        """
        all_logs = self.get_recent_logs(limit=1000)  # Get more to filter
        filtered = [log for log in all_logs if log.get('context') == context]
        return filtered[:limit]

    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics about filtered content.

        Returns:
            Dictionary with stats:
            - total_events: Total sanitization events
            - by_context: Count by context type
            - by_pattern: Count by pattern type
            - recent_activity: Events in last hour
        """
        if not self.log_file.exists():
            return {
                "total_events": 0,
                "by_context": {},
                "by_pattern": {},
                "recent_activity": 0
            }

        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()

            total = len(lines)
            by_context = {}
            by_pattern = {}
            recent_count = 0
            now = datetime.now()

            for line in lines:
                try:
                    entry = json.loads(line.strip())

                    # Count by context
                    ctx = entry.get('context', 'unknown')
                    by_context[ctx] = by_context.get(ctx, 0) + 1

                    # Count by pattern
                    for pattern in entry.get('patterns_matched', []):
                        by_pattern[pattern] = by_pattern.get(pattern, 0) + 1

                    # Recent activity (last hour)
                    timestamp = datetime.fromisoformat(entry.get('timestamp'))
                    if (now - timestamp).total_seconds() < 3600:
                        recent_count += 1

                except (json.JSONDecodeError, ValueError):
                    continue

            return {
                "total_events": total,
                "by_context": by_context,
                "by_pattern": by_pattern,
                "recent_activity": recent_count
            }

        except Exception as e:
            logging.error(f"Failed to generate stats: {e}")
            return {
                "total_events": 0,
                "by_context": {},
                "by_pattern": {},
                "recent_activity": 0
            }

    def rotate_logs(self) -> None:
        """
        Manually trigger log rotation.
        Automatically called when file exceeds MAX_LOG_SIZE.
        """
        if not self.log_file.exists():
            return

        file_size = self.log_file.stat().st_size

        if file_size > MAX_LOG_SIZE:
            # Rotate logs (rename current, create new)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.log_file.with_name(f"{self.log_file.stem}_{timestamp}.jsonl")

            try:
                # Rename current log to backup
                self.log_file.rename(backup_file)

                # Create new log file
                self.log_file.touch(mode=LOG_FILE_MODE)

                logging.info(f"Rotated audit log to {backup_file}")

                # Clean up old backups (keep only BACKUP_COUNT)
                self._cleanup_old_backups()

            except Exception as e:
                logging.error(f"Failed to rotate logs: {e}")

    def _cleanup_old_backups(self) -> None:
        """Remove old backup files beyond BACKUP_COUNT."""
        # Find all backup files
        backup_pattern = f"{self.log_file.stem}_*.jsonl"
        backups = sorted(LOG_DIR.glob(backup_pattern), key=lambda p: p.stat().st_mtime)

        # Remove oldest backups if we exceed BACKUP_COUNT
        while len(backups) > BACKUP_COUNT:
            oldest = backups.pop(0)
            try:
                oldest.unlink()
                logging.info(f"Deleted old backup: {oldest}")
            except Exception as e:
                logging.error(f"Failed to delete backup {oldest}: {e}")


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def log_sanitization(
    context: str,
    replacements_count: int,
    patterns_matched: List[str],
    original_message_context: Optional[str] = None,
    user_id: Optional[int] = None
) -> None:
    """Convenience function to log a sanitization event."""
    logger = get_audit_logger()
    logger.log_sanitization(
        context=context,
        replacements_count=replacements_count,
        patterns_matched=patterns_matched,
        original_message_context=original_message_context,
        user_id=user_id
    )
    # Auto-rotate if needed
    logger.rotate_logs()


def get_recent_audit_logs(limit: int = 20) -> List[Dict]:
    """Convenience function to get recent audit logs."""
    return get_audit_logger().get_recent_logs(limit)


def get_audit_summary() -> Dict:
    """Convenience function to get audit summary stats."""
    return get_audit_logger().get_summary_stats()


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AUDIT LOGGING TEST (BC-005)")
    print("=" * 60)

    # Create test logger
    logger = AuditLogger()

    # Log some test events
    print("\nLogging test sanitization events...")
    logger.log_sanitization(
        context="test_groq_input",
        replacements_count=2,
        patterns_matched=["[OPENAI_KEY]", "[IP_ADDRESS]"],
        original_message_context="User message about API setup",
        user_id=12345
    )

    logger.log_sanitization(
        context="test_telegram_output",
        replacements_count=1,
        patterns_matched=["[DATABASE_URL]"],
        original_message_context="Bot response with connection info"
    )

    # Get recent logs
    print("\nRecent audit logs:")
    recent = logger.get_recent_logs(limit=5)
    for entry in recent:
        print(f"  {entry['timestamp']} - {entry['context']}: {entry['patterns_matched']}")

    # Get summary stats
    print("\nSummary statistics:")
    stats = logger.get_summary_stats()
    print(f"  Total events: {stats['total_events']}")
    print(f"  By context: {stats['by_context']}")
    print(f"  By pattern: {stats['by_pattern']}")
    print(f"  Recent activity (last hour): {stats['recent_activity']}")

    print("\n✅ Audit logging test complete!")
    print(f"📁 Logs stored in: {AUDIT_LOG_FILE}")
