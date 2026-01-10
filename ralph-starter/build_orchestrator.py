#!/usr/bin/env python3
"""
BO-001 & BO-002: Build Orchestrator Service for Ralph Mode Bot

This service:
- Runs as a background daemon
- Polls the feedback queue for HIGH priority items
- Spawns isolated Ralph instances in Docker containers (BO-002)
- Monitors build progress and updates queue status
- Handles build completion and failure
- Integrates with feedback_queue.py for status updates

Usage:
    python build_orchestrator.py --daemon    # Run as background service
    python build_orchestrator.py --once      # Process one item and exit (for testing)
    python build_orchestrator.py --stop      # Stop running daemon
    python build_orchestrator.py --no-docker # Disable Docker isolation (for local dev)
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

# TS-001: Import test runner
from test_runner import TestRunner, TestResult

# DP-001: Import deploy manager
from deploy_manager import DeployManager, DeploymentResult

# WB-002: Import WebSocket server for live build streaming
from websocket_server import get_build_stream_server, BuildStreamServer

# NT-002: Import notification service for build started notifications
try:
    from notification_service import get_notification_service
    NOTIFICATION_SERVICE_AVAILABLE = True
except ImportError:
    NOTIFICATION_SERVICE_AVAILABLE = False
    logging.warning("NT-002: Notification service not available - build notifications disabled")

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

# Docker configuration (BO-002)
DOCKER_IMAGE = 'ralph-build:latest'
DOCKER_BUILD_DIR = Path(__file__).parent
REPO_URL = os.getenv('RALPH_REPO_URL', 'https://github.com/Snail3D/ralphmode.com.git')

# WB-003: Build dashboard URL (for NT-002 notifications)
BUILD_DASHBOARD_URL = os.getenv('BUILD_DASHBOARD_URL', 'https://ralphmode.com/builds')


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
    test_result: Optional[TestResult] = None  # TS-001: Store test results


class BuildOrchestrator:
    """
    BO-001 & BO-002: Build Orchestrator Service

    Monitors the feedback queue and spawns Ralph instances to build
    high-priority feedback items in isolated Docker containers.
    """

    def __init__(self, use_docker: bool = True):
        """
        Initialize the build orchestrator.

        Args:
            use_docker: Whether to use Docker isolation (BO-002). Default True.
        """
        self.running = True
        self.current_build: Optional[BuildContext] = None
        self.builds_completed = 0
        self.builds_failed = 0
        self.use_docker = use_docker

        # TS-001: Initialize test runner
        self.test_runner = TestRunner()

        # DP-001: Initialize deploy manager
        self.deploy_manager = DeployManager()

        # WB-002: Initialize WebSocket server for live build streaming
        self.stream_server: Optional[BuildStreamServer] = None
        try:
            self.stream_server = get_build_stream_server()
            logger.info("WebSocket server initialized for build streaming")
        except Exception as e:
            logger.warning(f"WebSocket server unavailable: {e}")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Verify Docker is available if enabled
        if self.use_docker:
            if not self._check_docker():
                logger.warning("Docker not available, falling back to non-isolated builds")
                self.use_docker = False

    def _check_docker(self) -> bool:
        """
        Check if Docker is available and the build image exists.

        Returns:
            True if Docker is ready, False otherwise
        """
        try:
            # Check if docker command exists
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.error("Docker not installed")
                return False

            # Check if build image exists
            result = subprocess.run(
                ['docker', 'images', '-q', DOCKER_IMAGE],
                capture_output=True,
                text=True,
                timeout=5
            )

            if not result.stdout.strip():
                logger.info(f"Docker image {DOCKER_IMAGE} not found, building...")
                return self._build_docker_image()

            logger.info(f"Docker ready with image {DOCKER_IMAGE}")
            return True

        except Exception as e:
            logger.error(f"Error checking Docker: {e}")
            return False

    def _build_docker_image(self) -> bool:
        """
        Build the Docker image for isolated builds.

        Returns:
            True if build succeeded, False otherwise
        """
        try:
            dockerfile = DOCKER_BUILD_DIR / "Dockerfile.build"

            if not dockerfile.exists():
                logger.error(f"Dockerfile not found: {dockerfile}")
                return False

            logger.info(f"Building Docker image {DOCKER_IMAGE}...")

            result = subprocess.run(
                ['docker', 'build', '-f', str(dockerfile), '-t', DOCKER_IMAGE, str(DOCKER_BUILD_DIR)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for image build
            )

            if result.returncode != 0:
                logger.error(f"Docker build failed: {result.stderr}")
                return False

            logger.info(f"Docker image {DOCKER_IMAGE} built successfully")
            return True

        except Exception as e:
            logger.error(f"Error building Docker image: {e}")
            return False

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
        # SF-003: Check if build loop is paused by admin
        pause_file = Path('/tmp/ralph_build_paused.flag')
        if pause_file.exists():
            logger.debug("Build loop is paused by admin")
            return

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

            # NT-002: Send build started notification to user
            if NOTIFICATION_SERVICE_AVAILABLE:
                try:
                    # Get stream URL if WebSocket server is available (WB-002)
                    stream_url = None
                    if self.stream_server:
                        # Build stream URL for this specific build
                        stream_url = f"{BUILD_DASHBOARD_URL}/stream/{feedback.id}"

                    # Get user's telegram_id from feedback.user relationship
                    telegram_id = feedback.user.telegram_id if feedback.user else None

                    if telegram_id:
                        notification_service = get_notification_service()
                        notification_service.send_build_started_sync(
                            user_id=telegram_id,
                            feedback_id=feedback.id,
                            feedback_type=feedback.feedback_type,
                            content_preview=feedback.content,
                            priority_score=feedback.priority_score,
                            stream_url=stream_url
                        )
                        logger.info(f"NT-002: Sent build started notification for feedback_id={feedback.id}")
                    else:
                        logger.warning(f"NT-002: No telegram_id found for feedback_id={feedback.id}")
                except Exception as e:
                    # Don't fail the build if notification fails
                    logger.error(f"NT-002: Failed to send build started notification: {e}")

            # Create task file for Ralph
            task_file = self._create_task_file(build_context)

            # Spawn Ralph process (Docker or local)
            logger.info(f"Spawning Ralph for feedback_id={feedback.id} (docker={self.use_docker})")

            if self.use_docker:
                # BO-002: Spawn in isolated Docker container
                process = self._spawn_docker_build(build_context, task_file)
            else:
                # BO-001: Spawn as local subprocess (fallback)
                process = self._spawn_local_build(build_context, task_file)

            if not process:
                logger.error(f"Failed to spawn build for feedback_id={feedback.id}")
                queue.update_status(feedback.id, "rejected", "Build spawn failed")
                return

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

    def _spawn_docker_build(self, context: BuildContext, task_file: Path) -> Optional[subprocess.Popen]:
        """
        Spawn build in isolated Docker container (BO-002).

        Args:
            context: Build context
            task_file: Path to task file

        Returns:
            Popen process or None on failure
        """
        try:
            # Branch name for this feedback item
            branch_name = f"feedback/FB-{context.feedback_id}"

            # Docker run command
            docker_cmd = [
                'docker', 'run',
                '--rm',  # Auto-remove container after completion
                '--name', f'ralph-build-{context.feedback_id}',  # Named container
                '-e', f'REPO_URL={REPO_URL}',
                '-e', f'FEEDBACK_ID={context.feedback_id}',
                '-e', f'TASK_FILE=/tmp/task.json',
                '-e', f'BRANCH_NAME={branch_name}',
                '-v', f'{task_file}:/tmp/task.json:ro',  # Mount task file as read-only
                DOCKER_IMAGE
            ]

            logger.info(f"Starting Docker container: {' '.join(docker_cmd)}")

            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            logger.info(f"Docker container started for feedback_id={context.feedback_id}")
            return process

        except Exception as e:
            logger.error(f"Error spawning Docker build: {e}", exc_info=True)
            return None

    def _spawn_local_build(self, context: BuildContext, task_file: Path) -> Optional[subprocess.Popen]:
        """
        Spawn build as local subprocess (fallback when Docker unavailable).

        Args:
            context: Build context
            task_file: Path to task file

        Returns:
            Popen process or None on failure
        """
        try:
            # Get the ralph.sh script path
            ralph_script = Path(__file__).parent / "scripts" / "ralph" / "ralph.sh"

            if not ralph_script.exists():
                logger.error(f"Ralph script not found: {ralph_script}")
                return None

            # Start Ralph as subprocess
            process = subprocess.Popen(
                [str(ralph_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    **os.environ,
                    'RALPH_TASK_FILE': str(task_file),
                    'RALPH_FEEDBACK_ID': str(context.feedback_id)
                }
            )

            logger.info(f"Local subprocess started for feedback_id={context.feedback_id}")
            return process

        except Exception as e:
            logger.error(f"Error spawning local build: {e}", exc_info=True)
            return None

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

    def _stream_output_line(self, feedback_id: int, line: str):
        """
        WB-002: Stream a line of output to WebSocket clients.

        Args:
            feedback_id: Feedback ID being built
            line: Output line to stream
        """
        if self.stream_server:
            try:
                self.stream_server.emit_build_output(feedback_id, line)
            except Exception as e:
                logger.error(f"Error streaming output: {e}")

    def _monitor_build(self, context: BuildContext, db: Session):
        """
        Monitor a build in progress.

        WB-002: Now streams output in real-time to WebSocket clients.

        This is non-blocking - it checks status and returns immediately.
        For long-running builds, the orchestrator will check on next poll.

        Args:
            context: Build context
            db: Database session
        """
        if not context.process:
            return

        # WB-002: Emit build status as in_progress
        if self.stream_server:
            self.stream_server.emit_build_status(
                context.feedback_id,
                'in_progress',
                'Building...'
            )

        # Check if process has completed (non-blocking)
        retcode = context.process.poll()

        if retcode is None:
            # Still running - WB-002: Read and stream output if available
            if context.process.stdout:
                try:
                    # Non-blocking read from stdout
                    import select
                    if select.select([context.process.stdout], [], [], 0.1)[0]:
                        line = context.process.stdout.readline()
                        if line:
                            self._stream_output_line(context.feedback_id, line.strip())
                except Exception as e:
                    logger.debug(f"Error reading stdout: {e}")

            elapsed = (datetime.utcnow() - context.started_at).total_seconds()

            # Check for timeout
            if elapsed > BUILD_TIMEOUT:
                logger.warning(f"Build timeout for feedback_id={context.feedback_id}")
                context.process.kill()
                self._handle_build_failure(context, db, "Build timeout")
                return

            logger.debug(f"Build in progress (feedback_id={context.feedback_id}, elapsed={elapsed:.0f}s)")

        elif retcode == 0:
            # Success! - WB-002: Read remaining output before success handler
            if context.process.stdout:
                try:
                    for line in context.process.stdout:
                        self._stream_output_line(context.feedback_id, line.strip())
                except Exception as e:
                    logger.error(f"Error reading remaining stdout: {e}")

            self._handle_build_success(context, db)

        else:
            # Failure - WB-002: Stream error output
            stdout, stderr = context.process.communicate()
            if stdout:
                for line in stdout.split('\n'):
                    if line.strip():
                        self._stream_output_line(context.feedback_id, line.strip())
            if stderr:
                for line in stderr.split('\n'):
                    if line.strip():
                        self._stream_output_line(context.feedback_id, f"ERROR: {line.strip()}")

            error_msg = f"Exit code {retcode}: {stderr[:500]}"
            self._handle_build_failure(context, db, error_msg)

    def _handle_build_success(self, context: BuildContext, db: Session):
        """
        Handle successful build completion.

        TS-001: After build success, run test suite before proceeding.

        Args:
            context: Build context
            db: Database session
        """
        logger.info(f"Build SUCCESS for feedback_id={context.feedback_id}")

        try:
            # WB-002: Update status to testing
            if self.stream_server:
                self.stream_server.emit_build_status(
                    context.feedback_id,
                    'testing',
                    'Running test suite...'
                )

            # TS-001: Run test suite after successful build
            logger.info(f"Running test suite for feedback_id={context.feedback_id}")
            test_result = self.test_runner.run_tests()
            context.test_result = test_result

            # TS-001: Failed tests = failed build
            if not test_result.passed:
                logger.error(f"Test suite FAILED for feedback_id={context.feedback_id}")
                error_msg = f"Test suite failed: {', '.join(test_result.error_messages)}"
                self._handle_build_failure(context, db, error_msg)
                return

            logger.info(
                f"Test suite PASSED for feedback_id={context.feedback_id} "
                f"({test_result.passed_tests}/{test_result.total_tests} tests, "
                f"coverage: {test_result.coverage_percentage:.2f}%)"
            )

            # BO-003: Reset consecutive failures on success
            feedback = db.query(Feedback).filter(Feedback.id == context.feedback_id).first()
            if feedback:
                if feedback.consecutive_failures > 0:
                    logger.info(
                        f"Resetting consecutive_failures for feedback_id={context.feedback_id} "
                        f"from {feedback.consecutive_failures} to 0"
                    )
                    feedback.consecutive_failures = 0
                    db.commit()

            # WB-002: Update status to deploying
            if self.stream_server:
                self.stream_server.emit_build_status(
                    context.feedback_id,
                    'deploying',
                    'Deploying to staging...'
                )

            # DP-001: Deploy to staging on test pass
            logger.info(f"Deploying to staging for feedback_id={context.feedback_id}")
            deploy_result = self.deploy_manager.deploy_to_staging(context.feedback_id)

            if not deploy_result.success:
                logger.error(f"Staging deployment FAILED: {deploy_result.error_message}")
                # Treat deployment failure as build failure
                self._handle_build_failure(context, db, f"Staging deployment failed: {deploy_result.error_message}")
                return

            logger.info(
                f"Staging deployment SUCCESS for feedback_id={context.feedback_id} "
                f"at {deploy_result.staging_url}"
            )

            # DP-001: Auto-promote to canary if healthy (future: DP-002)
            # For now, just mark as deployed to staging
            queue = get_feedback_queue(db)
            queue.update_status(context.feedback_id, "deployed_staging")

            # WB-002: Update status to complete
            if self.stream_server:
                self.stream_server.emit_build_status(
                    context.feedback_id,
                    'complete',
                    f'Build complete! Deployed to staging at {deploy_result.staging_url}'
                )

            self.builds_completed += 1
            self.current_build = None

        except Exception as e:
            logger.error(f"Error handling build success: {e}", exc_info=True)

    def _handle_build_failure(self, context: BuildContext, db: Session, reason: str):
        """
        BO-003: Handle build failure with enhanced failure tracking.

        Args:
            context: Build context
            db: Database session
            reason: Failure reason
        """
        logger.error(f"Build FAILED for feedback_id={context.feedback_id}: {reason}")

        # WB-002: Update status to failed
        if self.stream_server:
            self.stream_server.emit_build_status(
                context.feedback_id,
                'failed',
                f'Build failed: {reason}'
            )

        try:
            # Get feedback item
            feedback = db.query(Feedback).filter(Feedback.id == context.feedback_id).first()

            if not feedback:
                logger.error(f"Feedback {context.feedback_id} not found")
                self.builds_failed += 1
                self.current_build = None
                return

            # BO-003: Increment consecutive failures
            feedback.consecutive_failures += 1
            consecutive_failures = feedback.consecutive_failures

            # BO-003: Log detailed failure info
            logger.error(
                f"Build failure details: feedback_id={context.feedback_id}, "
                f"consecutive_failures={consecutive_failures}, "
                f"type={context.feedback_type}, "
                f"reason={reason}"
            )

            # BO-003: Reduce priority score by 50%
            if feedback.priority_score:
                old_priority = feedback.priority_score
                feedback.priority_score = feedback.priority_score * 0.5
                logger.info(
                    f"Reduced priority score for feedback_id={context.feedback_id}: "
                    f"{old_priority:.2f} -> {feedback.priority_score:.2f}"
                )

            # Update feedback status
            feedback.status = "queued"  # Return to queue with reduced priority
            feedback.updated_at = datetime.utcnow()
            feedback.rejection_reason = reason

            db.commit()

            # BO-003: Alert admin after 3+ consecutive failures
            if consecutive_failures >= 3:
                self._alert_admin_consecutive_failures(context.feedback_id, consecutive_failures, reason)

            # BO-003: Pause build loop after 5+ consecutive failures
            if consecutive_failures >= 5:
                logger.critical(
                    f"PAUSING BUILD LOOP: feedback_id={context.feedback_id} has {consecutive_failures} "
                    f"consecutive failures. Manual intervention required."
                )
                self._pause_build_loop(context.feedback_id, consecutive_failures, reason)

            self.builds_failed += 1
            self.current_build = None

        except Exception as e:
            logger.error(f"Error handling build failure: {e}", exc_info=True)

    def _alert_admin_consecutive_failures(self, feedback_id: int, consecutive_failures: int, reason: str):
        """
        BO-003: Alert admin about consecutive failures.

        Args:
            feedback_id: Feedback ID
            consecutive_failures: Number of consecutive failures
            reason: Failure reason
        """
        admin_id = os.getenv('TELEGRAM_ADMIN_ID')

        if not admin_id:
            logger.warning("TELEGRAM_ADMIN_ID not set, cannot alert admin")
            return

        try:
            # Log the alert (actual Telegram notification would require bot integration)
            alert_message = (
                f"🚨 BUILD FAILURE ALERT 🚨\n\n"
                f"Feedback ID: {feedback_id}\n"
                f"Consecutive Failures: {consecutive_failures}\n"
                f"Reason: {reason}\n\n"
                f"Action required: Review feedback item and resolve build issues."
            )

            logger.warning(f"ADMIN ALERT: {alert_message}")

            # TODO: Send actual Telegram message to admin
            # This would require access to the bot instance, which runs in a different process
            # For now, we log the alert and write to a file that can be monitored

            alert_file = Path('/tmp/ralph_admin_alerts.log')
            with open(alert_file, 'a') as f:
                f.write(f"{datetime.utcnow().isoformat()} - {alert_message}\n\n")

            logger.info(f"Admin alert written to {alert_file}")

        except Exception as e:
            logger.error(f"Error alerting admin: {e}", exc_info=True)

    def _pause_build_loop(self, feedback_id: int, consecutive_failures: int, reason: str):
        """
        BO-003: Pause build loop after 5+ consecutive failures.

        Args:
            feedback_id: Feedback ID
            consecutive_failures: Number of consecutive failures
            reason: Failure reason
        """
        try:
            # Create a pause file that the orchestrator checks
            pause_file = Path('/tmp/ralph_build_paused.flag')

            pause_data = {
                'paused_at': datetime.utcnow().isoformat(),
                'feedback_id': feedback_id,
                'consecutive_failures': consecutive_failures,
                'reason': reason,
                'message': (
                    f"Build loop paused due to {consecutive_failures} consecutive failures "
                    f"on feedback_id={feedback_id}. Manual intervention required."
                )
            }

            with open(pause_file, 'w') as f:
                json.dump(pause_data, f, indent=2)

            logger.critical(f"Build loop PAUSED. Pause file created at {pause_file}")

            # Stop the orchestrator
            self.running = False

            # Alert admin
            self._alert_admin_consecutive_failures(feedback_id, consecutive_failures, reason)

        except Exception as e:
            logger.error(f"Error pausing build loop: {e}", exc_info=True)


def start_daemon(use_docker: bool = True):
    """
    Start the orchestrator as a background daemon.

    Args:
        use_docker: Whether to use Docker isolation
    """
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
    orchestrator = BuildOrchestrator(use_docker=use_docker)
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

    parser = argparse.ArgumentParser(description='Ralph Mode Build Orchestrator (BO-001 & BO-002)')
    parser.add_argument('--daemon', action='store_true', help='Run as background daemon')
    parser.add_argument('--once', action='store_true', help='Process one item and exit (testing)')
    parser.add_argument('--stop', action='store_true', help='Stop running daemon')
    parser.add_argument('--no-docker', action='store_true', help='Disable Docker isolation (local builds only)')

    args = parser.parse_args()

    use_docker = not args.no_docker

    if args.stop:
        stop_daemon()
    elif args.daemon:
        start_daemon(use_docker=use_docker)
    elif args.once:
        orchestrator = BuildOrchestrator(use_docker=use_docker)
        orchestrator.run(once=True)
    else:
        # Run in foreground
        orchestrator = BuildOrchestrator(use_docker=use_docker)
        orchestrator.run()


if __name__ == '__main__':
    main()
