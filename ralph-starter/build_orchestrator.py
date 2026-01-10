#!/usr/bin/env python3
"""
BO-001: Build Orchestrator Service for Ralph Mode Bot

This service:
- Runs as a background daemon
- Polls the feedback queue for HIGH priority items
- Spawns isolated Ralph instances to build feedback items
- Monitors build progress and updates queue status
- Handles build completion and failure
- Integrates with feedback_queue.py for status updates

Usage:
    python build_orchestrator.py --daemon    # Run as background service
    python build_orchestrator.py --once      # Process one item and exit (for testing)
    python build_orchestrator.py --stop      # Stop running daemon
"""

import os
import sys
import time
import logging
import subprocess
import json
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session

# Import our feedback queue
from database import get_db, Feedback
from feedback_queue import get_feedback_queue

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('build_orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# PID file for daemon management
PID_FILE = Path('/tmp/ralph_build_orchestrator.pid')

# Poll interval in seconds
POLL_INTERVAL = 30  # Check queue every 30 seconds

# Build timeout (2 hours max per build)
BUILD_TIMEOUT = 7200


@dataclass
class BuildContext:
    """Context for a single build job."""
    feedback_id: int
    feedback_type: str
    content: str
    priority_score: float
    user_id: int
    started_at: datetime
    process: Optional[subprocess.Popen] = None


class BuildOrchestrator:
    """
    BO-001: Build Orchestrator Service

    Monitors the feedback queue and spawns Ralph instances to build
    high-priority feedback items.
    """

    def __init__(self):
        """Initialize the build orchestrator."""
        self.running = True
        self.current_build: Optional[BuildContext] = None
        self.builds_completed = 0
        self.builds_failed = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

        # Kill current build if running
        if self.current_build and self.current_build.process:
            logger.info(f"Terminating current build (feedback_id={self.current_build.feedback_id})")
            self.current_build.process.terminate()
            try:
                self.current_build.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.current_build.process.kill()

    def run(self, once: bool = False):
        """
        Main orchestrator loop.

        Args:
            once: If True, process one item and exit (for testing)
        """
        logger.info("Build Orchestrator started")
        logger.info(f"Poll interval: {POLL_INTERVAL}s, Build timeout: {BUILD_TIMEOUT}s")

        while self.running:
            try:
                # Check for high-priority items in queue
                self._poll_queue()

                # Exit if running in once mode
                if once:
                    logger.info("Once mode: exiting after one iteration")
                    break

                # Sleep before next poll
                time.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Error in orchestrator loop: {e}", exc_info=True)
                time.sleep(POLL_INTERVAL)

        logger.info(f"Build Orchestrator stopped. Completed: {self.builds_completed}, Failed: {self.builds_failed}")

    def _poll_queue(self):
        """Poll the queue for high-priority items to build."""
        # Skip if already building something
        if self.current_build:
            logger.debug("Build in progress, skipping poll")
            return

        try:
            with get_db() as db:
                queue = get_feedback_queue(db)

                # Get next high-priority item (priority_score > 7)
                feedback = queue.get_next_high_priority()

                if feedback:
                    logger.info(
                        f"Found high-priority item: feedback_id={feedback.id}, "
                        f"priority={feedback.priority_score:.2f}, type={feedback.feedback_type}"
                    )
                    self._spawn_build(feedback, db)
                else:
                    logger.debug("No high-priority items in queue")

        except Exception as e:
            logger.error(f"Error polling queue: {e}", exc_info=True)

    def _spawn_build(self, feedback: Feedback, db: Session):
        """
        Spawn a Ralph instance to build this feedback item.

        Args:
            feedback: Feedback item to build
            db: Database session
        """
        try:
            # Create build context
            build_context = BuildContext(
                feedback_id=feedback.id,
                feedback_type=feedback.feedback_type,
                content=feedback.content,
                priority_score=feedback.priority_score,
                user_id=feedback.user_id,
                started_at=datetime.utcnow()
            )

            # Update status to in_progress
            queue = get_feedback_queue(db)
            queue.update_status(feedback.id, "in_progress")

            # Create task file for Ralph
            task_file = self._create_task_file(build_context)

            # Spawn Ralph process
            logger.info(f"Spawning Ralph for feedback_id={feedback.id}")

            # Get the ralph.sh script path
            ralph_script = Path(__file__).parent / "scripts" / "ralph" / "ralph.sh"

            if not ralph_script.exists():
                logger.error(f"Ralph script not found: {ralph_script}")
                queue.update_status(feedback.id, "rejected", "Ralph script not found")
                return

            # Start Ralph as subprocess
            # Note: In production, this would use Docker isolation (BO-002)
            process = subprocess.Popen(
                [str(ralph_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    **os.environ,
                    'RALPH_TASK_FILE': str(task_file),
                    'RALPH_FEEDBACK_ID': str(feedback.id)
                }
            )

            build_context.process = process
            self.current_build = build_context

            # Monitor the build (non-blocking)
            self._monitor_build(build_context, db)

        except Exception as e:
            logger.error(f"Error spawning build for feedback_id={feedback.id}: {e}", exc_info=True)

            # Mark as rejected on spawn failure
            try:
                queue = get_feedback_queue(db)
                queue.update_status(feedback.id, "rejected", f"Build spawn failed: {str(e)}")
            except Exception as update_error:
                logger.error(f"Failed to update status: {update_error}")

    def _create_task_file(self, context: BuildContext) -> Path:
        """
        Create a task file for Ralph to work on.

        Args:
            context: Build context

        Returns:
            Path to task file
        """
        task_data = {
            'feedback_id': context.feedback_id,
            'type': context.feedback_type,
            'content': context.content,
            'priority_score': context.priority_score,
            'user_id': context.user_id,
            'started_at': context.started_at.isoformat()
        }

        task_file = Path(f'/tmp/ralph_task_{context.feedback_id}.json')

        with open(task_file, 'w') as f:
            json.dump(task_data, f, indent=2)

        logger.info(f"Created task file: {task_file}")
        return task_file

    def _monitor_build(self, context: BuildContext, db: Session):
        """
        Monitor a build in progress.

        This is non-blocking - it checks status and returns immediately.
        For long-running builds, the orchestrator will check on next poll.

        Args:
            context: Build context
            db: Database session
        """
        if not context.process:
            return

        # Check if process has completed (non-blocking)
        retcode = context.process.poll()

        if retcode is None:
            # Still running
            elapsed = (datetime.utcnow() - context.started_at).total_seconds()

            # Check for timeout
            if elapsed > BUILD_TIMEOUT:
                logger.warning(f"Build timeout for feedback_id={context.feedback_id}")
                context.process.kill()
                self._handle_build_failure(context, db, "Build timeout")
                return

            logger.debug(f"Build in progress (feedback_id={context.feedback_id}, elapsed={elapsed:.0f}s)")

        elif retcode == 0:
            # Success!
            self._handle_build_success(context, db)

        else:
            # Failure
            stdout, stderr = context.process.communicate()
            error_msg = f"Exit code {retcode}: {stderr[:500]}"
            self._handle_build_failure(context, db, error_msg)

    def _handle_build_success(self, context: BuildContext, db: Session):
        """
        Handle successful build completion.

        Args:
            context: Build context
            db: Database session
        """
        logger.info(f"Build SUCCESS for feedback_id={context.feedback_id}")

        try:
            queue = get_feedback_queue(db)
            queue.update_status(context.feedback_id, "testing")

            self.builds_completed += 1
            self.current_build = None

        except Exception as e:
            logger.error(f"Error handling build success: {e}", exc_info=True)

    def _handle_build_failure(self, context: BuildContext, db: Session, reason: str):
        """
        Handle build failure.

        Args:
            context: Build context
            db: Database session
            reason: Failure reason
        """
        logger.error(f"Build FAILED for feedback_id={context.feedback_id}: {reason}")

        try:
            queue = get_feedback_queue(db)
            queue.update_status(context.feedback_id, "rejected", reason)

            self.builds_failed += 1
            self.current_build = None

        except Exception as e:
            logger.error(f"Error handling build failure: {e}", exc_info=True)


def start_daemon():
    """Start the orchestrator as a background daemon."""
    # Check if already running
    if PID_FILE.exists():
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # Check if process is actually running
        try:
            os.kill(pid, 0)
            logger.error(f"Build orchestrator already running (PID {pid})")
            sys.exit(1)
        except OSError:
            # Process not running, remove stale PID file
            PID_FILE.unlink()

    # Fork to background
    pid = os.fork()
    if pid > 0:
        # Parent process
        print(f"Build orchestrator started (PID {pid})")
        sys.exit(0)

    # Child process - daemonize
    os.setsid()
    os.umask(0)

    # Second fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    # Run orchestrator
    orchestrator = BuildOrchestrator()
    orchestrator.run()

    # Cleanup
    if PID_FILE.exists():
        PID_FILE.unlink()


def stop_daemon():
    """Stop the running daemon."""
    if not PID_FILE.exists():
        logger.error("Build orchestrator is not running")
        sys.exit(1)

    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, signal.SIGTERM)
        logger.info(f"Sent SIGTERM to process {pid}")

        # Wait for process to exit
        for _ in range(30):
            try:
                os.kill(pid, 0)
                time.sleep(1)
            except OSError:
                logger.info("Build orchestrator stopped")
                if PID_FILE.exists():
                    PID_FILE.unlink()
                sys.exit(0)

        # Force kill if still running
        logger.warning("Process did not stop, sending SIGKILL")
        os.kill(pid, signal.SIGKILL)

    except OSError as e:
        logger.error(f"Error stopping daemon: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Mode Build Orchestrator')
    parser.add_argument('--daemon', action='store_true', help='Run as background daemon')
    parser.add_argument('--once', action='store_true', help='Process one item and exit (testing)')
    parser.add_argument('--stop', action='store_true', help='Stop running daemon')

    args = parser.parse_args()

    if args.stop:
        stop_daemon()
    elif args.daemon:
        start_daemon()
    elif args.once:
        orchestrator = BuildOrchestrator()
        orchestrator.run(once=True)
    else:
        # Run in foreground
        orchestrator = BuildOrchestrator()
        orchestrator.run()


if __name__ == '__main__':
    main()
