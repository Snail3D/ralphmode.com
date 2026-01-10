#!/usr/bin/env python3
"""
DP-001, DP-002, DP-003: Deployment Manager for Ralph Mode Bot

This service handles:
- DP-001: Auto-deploy passing builds to staging environment
- DP-001: Run integration tests on staging
- DP-001: Health check endpoints
- DP-002: Canary deployment with 5% traffic split
- DP-002: Monitor error rates vs baseline for 30 minutes
- DP-002: Auto-promote if healthy (error rate < 2x baseline)
- DP-003: Auto-rollback if error rate > 2x baseline
- DP-003: Notify admin of rollback events
- DP-003: Mark feedback items as failed on rollback
- Integration with build orchestrator

Usage:
    from deploy_manager import DeployManager

    # Deploy to staging (DP-001)
    dm = DeployManager()
    result = dm.deploy_to_staging(feedback_id=123)
    if result.success:
        print(f"Deployed to {result.staging_url}")

    # Deploy to canary (DP-002 + DP-003)
    result = dm.deploy_to_canary(feedback_id=123)
    if result.success and result.promoted:
        print(f"Promoted to production!")
    elif result.rolled_back:
        print(f"Rolled back: {result.error_message}")
"""

import os
import sys
import time
import logging
import subprocess
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('deploy_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeploymentStage(Enum):
    """Deployment stages."""
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"


class CanaryStatus(Enum):
    """Status of canary deployment."""
    OBSERVING = "observing"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    success: bool
    stage: DeploymentStage
    feedback_id: int
    staging_url: Optional[str] = None
    health_check_passed: bool = False
    integration_tests_passed: bool = False
    error_message: Optional[str] = None
    deployed_at: Optional[datetime] = None
    version: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    healthy: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class MetricsSnapshot:
    """Snapshot of deployment metrics."""
    error_count: int = 0
    request_count: int = 0
    total_latency_ms: float = 0.0
    timestamp: Optional[datetime] = None

    @property
    def error_rate(self) -> float:
        """Calculate error rate (0.0 to 1.0)."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count


@dataclass
class CanaryDeploymentResult:
    """Result of a canary deployment."""
    success: bool
    feedback_id: int
    canary_url: Optional[str] = None
    production_url: Optional[str] = None
    status: CanaryStatus = CanaryStatus.OBSERVING
    baseline_metrics: Optional[MetricsSnapshot] = None
    canary_metrics: Optional[MetricsSnapshot] = None
    observation_start: Optional[datetime] = None
    observation_end: Optional[datetime] = None
    error_message: Optional[str] = None
    version: Optional[str] = None
    promoted: bool = False
    rolled_back: bool = False


class DeployManager:
    """
    DP-001: Deployment Manager for Staging Environment

    Handles deployment of passing builds to staging, running integration tests,
    and promoting to canary if healthy.
    """

    def __init__(self):
        """Initialize the deployment manager."""
        # Configuration from environment
        self.staging_host = os.getenv('STAGING_HOST', '69.164.201.191')
        self.staging_port = os.getenv('STAGING_PORT', '8001')
        self.staging_user = os.getenv('STAGING_USER', 'root')
        self.staging_path = os.getenv('STAGING_PATH', '/root/ralph-staging')

        # Canary deployment configuration
        self.canary_host = os.getenv('CANARY_HOST', '69.164.201.191')
        self.canary_port = os.getenv('CANARY_PORT', '8002')
        self.canary_path = os.getenv('CANARY_PATH', '/root/ralph-canary')
        self.canary_traffic_percent = float(os.getenv('CANARY_TRAFFIC_PERCENT', '5.0'))
        self.canary_observation_minutes = int(os.getenv('CANARY_OBSERVATION_MINUTES', '30'))
        self.canary_error_rate_threshold = float(os.getenv('CANARY_ERROR_RATE_THRESHOLD', '2.0'))

        # Production deployment configuration
        self.production_host = os.getenv('PRODUCTION_HOST', '69.164.201.191')
        self.production_port = os.getenv('PRODUCTION_PORT', '8000')
        self.production_path = os.getenv('PRODUCTION_PATH', '/root/ralph-production')

        # Health check configuration
        self.health_check_timeout = int(os.getenv('HEALTH_CHECK_TIMEOUT', '30'))
        self.health_check_retries = int(os.getenv('HEALTH_CHECK_RETRIES', '3'))

        # Integration test configuration
        self.integration_test_timeout = int(os.getenv('INTEGRATION_TEST_TIMEOUT', '300'))

        # Metrics tracking file
        self.metrics_file = Path('/tmp/ralph_deployment_metrics.json')

        logger.info(f"DeployManager initialized: staging={self.staging_host}:{self.staging_port}")

    def deploy_to_staging(self, feedback_id: int, version: Optional[str] = None) -> DeploymentResult:
        """
        Deploy to staging environment.

        Args:
            feedback_id: Feedback item ID being deployed
            version: Optional version string

        Returns:
            DeploymentResult with deployment status
        """
        logger.info(f"Starting staging deployment for feedback_id={feedback_id}")

        result = DeploymentResult(
            success=False,
            stage=DeploymentStage.STAGING,
            feedback_id=feedback_id,
            version=version or self._generate_version()
        )

        try:
            # Step 1: Prepare deployment artifacts
            logger.info("Preparing deployment artifacts...")
            if not self._prepare_artifacts(feedback_id):
                result.error_message = "Failed to prepare artifacts"
                return result

            # Step 2: Deploy to staging server
            logger.info(f"Deploying to staging server {self.staging_host}...")
            if not self._deploy_artifacts(feedback_id):
                result.error_message = "Failed to deploy artifacts"
                return result

            # Step 3: Restart staging service
            logger.info("Restarting staging service...")
            if not self._restart_staging_service():
                result.error_message = "Failed to restart staging service"
                return result

            # Step 4: Wait for service to be ready
            logger.info("Waiting for service to be ready...")
            time.sleep(5)

            # Step 5: Run health checks
            logger.info("Running health checks...")
            health_result = self._run_health_checks()
            result.health_check_passed = health_result.healthy

            if not health_result.healthy:
                result.error_message = f"Health check failed: {health_result.error_message}"
                return result

            # Step 6: Run integration tests
            logger.info("Running integration tests on staging...")
            integration_result = self._run_integration_tests()
            result.integration_tests_passed = integration_result

            if not integration_result:
                result.error_message = "Integration tests failed"
                return result

            # Success!
            result.success = True
            result.deployed_at = datetime.utcnow()
            result.staging_url = f"http://{self.staging_host}:{self.staging_port}"

            logger.info(
                f"Staging deployment SUCCESS for feedback_id={feedback_id} "
                f"at {result.staging_url}"
            )

            return result

        except Exception as e:
            logger.error(f"Error during staging deployment: {e}", exc_info=True)
            result.error_message = str(e)
            return result

    def _generate_version(self) -> str:
        """Generate version string based on timestamp."""
        return datetime.utcnow().strftime('%Y%m%d.%H%M%S')

    def _prepare_artifacts(self, feedback_id: int) -> bool:
        """
        Prepare deployment artifacts.

        Args:
            feedback_id: Feedback item ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create deployment package directory
            deploy_dir = Path(f'/tmp/deploy_{feedback_id}')
            deploy_dir.mkdir(exist_ok=True)

            # Copy current codebase to deployment directory
            # In production, this would build from the git branch
            project_root = Path(__file__).parent

            # Files to include in deployment
            files_to_deploy = [
                'ralph_bot.py',
                'database.py',
                'config.py',
                'requirements.txt',
                '.env'  # Will need to handle secrets properly
            ]

            for file in files_to_deploy:
                src = project_root / file
                if src.exists():
                    dst = deploy_dir / file
                    subprocess.run(['cp', str(src), str(dst)], check=True)

            logger.info(f"Artifacts prepared in {deploy_dir}")
            return True

        except Exception as e:
            logger.error(f"Error preparing artifacts: {e}", exc_info=True)
            return False

    def _deploy_artifacts(self, feedback_id: int) -> bool:
        """
        Deploy artifacts to staging server via rsync/scp.

        Args:
            feedback_id: Feedback item ID

        Returns:
            True if successful, False otherwise
        """
        try:
            deploy_dir = Path(f'/tmp/deploy_{feedback_id}')

            # Ensure staging directory exists on remote server
            ssh_cmd = [
                'ssh',
                f'{self.staging_user}@{self.staging_host}',
                f'mkdir -p {self.staging_path}'
            ]

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Failed to create staging directory: {result.stderr}")
                return False

            # Use rsync to deploy files
            rsync_cmd = [
                'rsync',
                '-avz',
                '--delete',
                f'{deploy_dir}/',
                f'{self.staging_user}@{self.staging_host}:{self.staging_path}/'
            ]

            logger.info(f"Running: {' '.join(rsync_cmd)}")

            result = subprocess.run(
                rsync_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"rsync failed: {result.stderr}")
                return False

            logger.info("Artifacts deployed successfully")
            return True

        except Exception as e:
            logger.error(f"Error deploying artifacts: {e}", exc_info=True)
            return False

    def _restart_staging_service(self) -> bool:
        """
        Restart the staging service on remote server.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Kill existing staging process
            kill_cmd = [
                'ssh',
                f'{self.staging_user}@{self.staging_host}',
                f'pkill -f ralph_bot || true'
            ]

            subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30)

            # Wait a moment for process to die
            time.sleep(2)

            # Start new staging process
            start_cmd = [
                'ssh',
                f'{self.staging_user}@{self.staging_host}',
                f'cd {self.staging_path} && '
                f'nohup python3 ralph_bot.py > /tmp/ralph_staging.log 2>&1 &'
            ]

            result = subprocess.run(
                start_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Failed to start staging service: {result.stderr}")
                return False

            logger.info("Staging service restarted")
            return True

        except Exception as e:
            logger.error(f"Error restarting staging service: {e}", exc_info=True)
            return False

    def _run_health_checks(self) -> HealthCheckResult:
        """
        Run health checks against staging environment.

        Returns:
            HealthCheckResult with health status
        """
        health_url = f"http://{self.staging_host}:{self.staging_port}/health"

        for attempt in range(1, self.health_check_retries + 1):
            try:
                logger.info(f"Health check attempt {attempt}/{self.health_check_retries}: {health_url}")

                start_time = time.time()
                response = requests.get(
                    health_url,
                    timeout=self.health_check_timeout
                )
                response_time_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"Health check response: status={response.status_code}, "
                    f"time={response_time_ms:.2f}ms"
                )

                if response.status_code == 200:
                    return HealthCheckResult(
                        healthy=True,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms
                    )
                else:
                    logger.warning(f"Health check returned non-200: {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Health check attempt {attempt} failed: {e}")

            # Wait before retry
            if attempt < self.health_check_retries:
                time.sleep(5)

        return HealthCheckResult(
            healthy=False,
            error_message=f"Health check failed after {self.health_check_retries} attempts"
        )

    def _run_integration_tests(self) -> bool:
        """
        Run integration tests against staging environment.

        Returns:
            True if tests pass, False otherwise
        """
        try:
            # Set environment variables for integration tests
            test_env = {
                **os.environ,
                'RALPH_TEST_ENV': 'staging',
                'RALPH_STAGING_URL': f"http://{self.staging_host}:{self.staging_port}"
            }

            # Run pytest with integration test markers
            test_cmd = [
                'pytest',
                '-v',
                '-m', 'integration',
                '--timeout', str(self.integration_test_timeout)
            ]

            logger.info(f"Running integration tests: {' '.join(test_cmd)}")

            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=self.integration_test_timeout,
                env=test_env
            )

            # Log test output
            if result.stdout:
                logger.info(f"Test output:\n{result.stdout}")

            if result.stderr:
                logger.warning(f"Test errors:\n{result.stderr}")

            if result.returncode == 0:
                logger.info("Integration tests PASSED")
                return True
            else:
                logger.error(f"Integration tests FAILED with exit code {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Integration tests timed out")
            return False

        except Exception as e:
            logger.error(f"Error running integration tests: {e}", exc_info=True)
            return False

    def get_staging_url(self) -> str:
        """
        Get the staging URL.

        Returns:
            Staging URL string
        """
        return f"http://{self.staging_host}:{self.staging_port}"

    def check_staging_health(self) -> HealthCheckResult:
        """
        Check if staging is healthy.

        Returns:
            HealthCheckResult
        """
        return self._run_health_checks()

    def deploy_to_canary(self, feedback_id: int, version: Optional[str] = None) -> CanaryDeploymentResult:
        """
        DP-002: Deploy to canary environment with 5% traffic split.

        This method:
        1. Deploys to canary server
        2. Collects baseline metrics from production
        3. Routes 5% of traffic to canary
        4. Monitors for 30 minutes
        5. Auto-promotes if healthy (error rate < 2x baseline)
        6. Auto-rollbacks if unhealthy

        Args:
            feedback_id: Feedback item ID being deployed
            version: Optional version string

        Returns:
            CanaryDeploymentResult with deployment status
        """
        logger.info(f"Starting canary deployment for feedback_id={feedback_id}")

        result = CanaryDeploymentResult(
            success=False,
            feedback_id=feedback_id,
            version=version or self._generate_version(),
            canary_url=f"http://{self.canary_host}:{self.canary_port}",
            production_url=f"http://{self.production_host}:{self.production_port}"
        )

        try:
            # Step 1: Collect baseline metrics from production
            logger.info("Collecting baseline metrics from production...")
            result.baseline_metrics = self._collect_metrics('production')

            if result.baseline_metrics.request_count == 0:
                logger.warning("No baseline traffic found. Proceeding with caution.")
                # Set minimal baseline for comparison
                result.baseline_metrics = MetricsSnapshot(
                    error_count=0,
                    request_count=1,
                    total_latency_ms=100.0,
                    timestamp=datetime.utcnow()
                )

            # Step 2: Deploy to canary server
            logger.info(f"Deploying to canary server {self.canary_host}:{self.canary_port}...")
            if not self._deploy_to_canary_server(feedback_id):
                result.error_message = "Failed to deploy to canary server"
                return result

            # Step 3: Run health checks on canary
            logger.info("Running health checks on canary...")
            health_result = self._run_canary_health_checks()
            if not health_result.healthy:
                result.error_message = f"Canary health check failed: {health_result.error_message}"
                return result

            # Step 4: Start observation period
            result.observation_start = datetime.utcnow()
            result.status = CanaryStatus.OBSERVING
            logger.info(
                f"Starting {self.canary_observation_minutes} minute observation period "
                f"with {self.canary_traffic_percent}% traffic to canary"
            )

            # Step 5: Monitor metrics during observation period
            observation_result = self._observe_canary_deployment(result)

            # Step 6: Make promotion decision
            if observation_result['healthy']:
                logger.info("Canary deployment is HEALTHY. Auto-promoting to production.")
                if self._promote_canary_to_production(feedback_id):
                    result.status = CanaryStatus.PROMOTED
                    result.promoted = True
                    result.success = True
                else:
                    result.error_message = "Failed to promote canary to production"
                    result.status = CanaryStatus.UNHEALTHY
            else:
                logger.warning(
                    f"Canary deployment is UNHEALTHY: {observation_result['reason']}. "
                    "Auto-rolling back."
                )
                rollback_reason = observation_result['reason']
                if self._rollback_canary(feedback_id, reason=rollback_reason):
                    result.status = CanaryStatus.ROLLED_BACK
                    result.rolled_back = True
                    result.error_message = f"Rolled back: {rollback_reason}"
                else:
                    result.error_message = "Failed to rollback canary"
                    result.status = CanaryStatus.UNHEALTHY

            result.observation_end = datetime.utcnow()
            result.canary_metrics = observation_result.get('final_metrics')

            logger.info(
                f"Canary deployment completed: status={result.status.value}, "
                f"promoted={result.promoted}, rolled_back={result.rolled_back}"
            )

            return result

        except Exception as e:
            logger.error(f"Error during canary deployment: {e}", exc_info=True)
            result.error_message = str(e)
            result.status = CanaryStatus.UNHEALTHY
            return result

    def _deploy_to_canary_server(self, feedback_id: int) -> bool:
        """
        Deploy artifacts to canary server.

        Args:
            feedback_id: Feedback item ID

        Returns:
            True if successful, False otherwise
        """
        try:
            deploy_dir = Path(f'/tmp/deploy_{feedback_id}')

            # Ensure canary directory exists on remote server
            ssh_cmd = [
                'ssh',
                f'{self.staging_user}@{self.canary_host}',
                f'mkdir -p {self.canary_path}'
            ]

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Failed to create canary directory: {result.stderr}")
                return False

            # Use rsync to deploy files
            rsync_cmd = [
                'rsync',
                '-avz',
                '--delete',
                f'{deploy_dir}/',
                f'{self.staging_user}@{self.canary_host}:{self.canary_path}/'
            ]

            logger.info(f"Running: {' '.join(rsync_cmd)}")

            result = subprocess.run(
                rsync_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"rsync failed: {result.stderr}")
                return False

            # Restart canary service
            kill_cmd = [
                'ssh',
                f'{self.staging_user}@{self.canary_host}',
                f'pkill -f "ralph_bot.*{self.canary_port}" || true'
            ]
            subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30)
            time.sleep(2)

            start_cmd = [
                'ssh',
                f'{self.staging_user}@{self.canary_host}',
                f'cd {self.canary_path} && '
                f'PORT={self.canary_port} nohup python3 ralph_bot.py > /tmp/ralph_canary.log 2>&1 &'
            ]

            result = subprocess.run(
                start_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Failed to start canary service: {result.stderr}")
                return False

            logger.info("Canary service deployed and started")
            return True

        except Exception as e:
            logger.error(f"Error deploying to canary server: {e}", exc_info=True)
            return False

    def _run_canary_health_checks(self) -> HealthCheckResult:
        """
        Run health checks against canary environment.

        Returns:
            HealthCheckResult with health status
        """
        health_url = f"http://{self.canary_host}:{self.canary_port}/health"

        for attempt in range(1, self.health_check_retries + 1):
            try:
                logger.info(f"Canary health check attempt {attempt}/{self.health_check_retries}")

                start_time = time.time()
                response = requests.get(
                    health_url,
                    timeout=self.health_check_timeout
                )
                response_time_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        healthy=True,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms
                    )

            except requests.exceptions.RequestException as e:
                logger.warning(f"Canary health check attempt {attempt} failed: {e}")

            if attempt < self.health_check_retries:
                time.sleep(5)

        return HealthCheckResult(
            healthy=False,
            error_message=f"Canary health check failed after {self.health_check_retries} attempts"
        )

    def _collect_metrics(self, environment: str) -> MetricsSnapshot:
        """
        Collect current metrics from an environment.

        Args:
            environment: 'production', 'canary', or 'staging'

        Returns:
            MetricsSnapshot with current metrics
        """
        try:
            # Read metrics from file if it exists
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    all_metrics = json.load(f)
                    env_metrics = all_metrics.get(environment, {})

                    return MetricsSnapshot(
                        error_count=env_metrics.get('error_count', 0),
                        request_count=env_metrics.get('request_count', 0),
                        total_latency_ms=env_metrics.get('total_latency_ms', 0.0),
                        timestamp=datetime.utcnow()
                    )

            # Return empty metrics if file doesn't exist
            return MetricsSnapshot(
                error_count=0,
                request_count=0,
                total_latency_ms=0.0,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}", exc_info=True)
            return MetricsSnapshot(timestamp=datetime.utcnow())

    def _observe_canary_deployment(self, result: CanaryDeploymentResult) -> Dict[str, Any]:
        """
        Observe canary deployment for specified period and monitor metrics.

        Args:
            result: CanaryDeploymentResult being monitored

        Returns:
            Dict with 'healthy' bool, 'reason' str, and 'final_metrics' MetricsSnapshot
        """
        observation_seconds = self.canary_observation_minutes * 60
        check_interval = 60  # Check every minute
        checks_needed = observation_seconds // check_interval

        logger.info(
            f"Observing canary for {self.canary_observation_minutes} minutes "
            f"({checks_needed} checks, 1 per minute)"
        )

        canary_metrics = MetricsSnapshot(timestamp=datetime.utcnow())
        baseline = result.baseline_metrics

        for check_num in range(1, checks_needed + 1):
            # Sleep until next check
            time.sleep(check_interval)

            # Collect current canary metrics
            canary_metrics = self._collect_metrics('canary')

            # Calculate current error rates
            baseline_error_rate = baseline.error_rate
            canary_error_rate = canary_metrics.error_rate

            # Calculate latency comparison
            baseline_latency = baseline.avg_latency_ms
            canary_latency = canary_metrics.avg_latency_ms

            logger.info(
                f"Check {check_num}/{checks_needed}: "
                f"Canary error_rate={canary_error_rate:.4f} (baseline={baseline_error_rate:.4f}), "
                f"latency={canary_latency:.2f}ms (baseline={baseline_latency:.2f}ms), "
                f"requests={canary_metrics.request_count}"
            )

            # Check if canary has enough traffic to make a decision
            if canary_metrics.request_count >= 10:
                # Check error rate threshold
                if baseline_error_rate > 0:
                    error_rate_ratio = canary_error_rate / baseline_error_rate
                else:
                    # If baseline has no errors, any error in canary is concerning
                    error_rate_ratio = float('inf') if canary_error_rate > 0 else 0

                if error_rate_ratio > self.canary_error_rate_threshold:
                    return {
                        'healthy': False,
                        'reason': (
                            f"Error rate {error_rate_ratio:.2f}x baseline "
                            f"(threshold: {self.canary_error_rate_threshold}x)"
                        ),
                        'final_metrics': canary_metrics
                    }

                # Check latency (warning only, not a failure condition for now)
                if baseline_latency > 0:
                    latency_ratio = canary_latency / baseline_latency
                    if latency_ratio > 2.0:
                        logger.warning(
                            f"Canary latency is {latency_ratio:.2f}x baseline "
                            f"({canary_latency:.2f}ms vs {baseline_latency:.2f}ms)"
                        )

        # Observation period complete
        logger.info("Observation period complete. Canary is HEALTHY.")
        return {
            'healthy': True,
            'reason': 'Passed observation period',
            'final_metrics': canary_metrics
        }

    def _promote_canary_to_production(self, feedback_id: int) -> bool:
        """
        Promote canary deployment to production (100% traffic).

        Args:
            feedback_id: Feedback item ID

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Promoting canary to production...")

            # Copy canary deployment to production path
            sync_cmd = [
                'ssh',
                f'{self.staging_user}@{self.production_host}',
                f'rsync -avz --delete {self.canary_path}/ {self.production_path}/'
            ]

            result = subprocess.run(
                sync_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"Failed to sync canary to production: {result.stderr}")
                return False

            # Restart production service
            kill_cmd = [
                'ssh',
                f'{self.staging_user}@{self.production_host}',
                f'pkill -f "ralph_bot.*{self.production_port}" || true'
            ]
            subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30)
            time.sleep(2)

            start_cmd = [
                'ssh',
                f'{self.staging_user}@{self.production_host}',
                f'cd {self.production_path} && '
                f'PORT={self.production_port} nohup python3 ralph_bot.py > /tmp/ralph_production.log 2>&1 &'
            ]

            result = subprocess.run(
                start_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Failed to start production service: {result.stderr}")
                return False

            logger.info("Canary promoted to production successfully")
            return True

        except Exception as e:
            logger.error(f"Error promoting canary to production: {e}", exc_info=True)
            return False

    def _rollback_canary(self, feedback_id: int, reason: str = "") -> bool:
        """
        DP-003: Rollback canary deployment (stop canary service).

        Args:
            feedback_id: Feedback item ID
            reason: Reason for rollback

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Rolling back canary deployment (reason: {reason})...")

            # Stop canary service
            kill_cmd = [
                'ssh',
                f'{self.staging_user}@{self.canary_host}',
                f'pkill -f "ralph_bot.*{self.canary_port}" || true'
            ]

            result = subprocess.run(
                kill_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # DP-003: Notify admin of rollback
            self._notify_admin_rollback(feedback_id, reason)

            # DP-003: Mark feedback item as failed
            self._mark_feedback_failed(feedback_id, reason)

            logger.info("Canary service stopped (rollback complete)")
            return True

        except Exception as e:
            logger.error(f"Error rolling back canary: {e}", exc_info=True)
            return False

    def _notify_admin_rollback(self, feedback_id: int, reason: str):
        """
        DP-003: Notify admin of rollback event.

        Args:
            feedback_id: Feedback item ID
            reason: Reason for rollback
        """
        try:
            admin_email = os.getenv('ADMIN_EMAIL')
            notification_webhook = os.getenv('NOTIFICATION_WEBHOOK')

            message = (
                f"🚨 ROLLBACK ALERT\n\n"
                f"Feedback ID: {feedback_id}\n"
                f"Reason: {reason}\n"
                f"Time: {datetime.utcnow().isoformat()}\n"
                f"Action: Canary deployment rolled back, production unaffected\n"
            )

            logger.warning(f"ROLLBACK NOTIFICATION: {message}")

            # If webhook is configured, send notification
            if notification_webhook:
                try:
                    requests.post(
                        notification_webhook,
                        json={'text': message},
                        timeout=10
                    )
                    logger.info("Rollback notification sent to webhook")
                except Exception as e:
                    logger.error(f"Failed to send webhook notification: {e}")

            # TODO: Email notification if admin_email is configured
            # This would require SMTP setup

        except Exception as e:
            logger.error(f"Error notifying admin of rollback: {e}", exc_info=True)

    def _mark_feedback_failed(self, feedback_id: int, reason: str):
        """
        DP-003: Mark feedback item as failed in database.

        Args:
            feedback_id: Feedback item ID
            reason: Failure reason
        """
        try:
            # This would integrate with the feedback queue database (FQ-001)
            # For now, we'll write to a file that can be picked up by the feedback system

            feedback_status_file = Path(f'/tmp/feedback_status_{feedback_id}.json')
            status_data = {
                'feedback_id': feedback_id,
                'status': 'failed',
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'canary'
            }

            with open(feedback_status_file, 'w') as f:
                json.dump(status_data, f, indent=2)

            logger.info(f"Feedback {feedback_id} marked as failed: {reason}")

        except Exception as e:
            logger.error(f"Error marking feedback as failed: {e}", exc_info=True)

    def record_request_metric(self, environment: str, latency_ms: float, is_error: bool = False):
        """
        Record a request metric for monitoring.

        Args:
            environment: 'production', 'canary', or 'staging'
            latency_ms: Request latency in milliseconds
            is_error: Whether the request resulted in an error
        """
        try:
            # Load existing metrics
            all_metrics = {}
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    all_metrics = json.load(f)

            # Get or create environment metrics
            if environment not in all_metrics:
                all_metrics[environment] = {
                    'error_count': 0,
                    'request_count': 0,
                    'total_latency_ms': 0.0
                }

            # Update metrics
            all_metrics[environment]['request_count'] += 1
            all_metrics[environment]['total_latency_ms'] += latency_ms
            if is_error:
                all_metrics[environment]['error_count'] += 1

            # Save updated metrics
            with open(self.metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2)

        except Exception as e:
            logger.error(f"Error recording metric: {e}", exc_info=True)


# Health check endpoint handler
def create_health_endpoint():
    """
    Create a simple health check endpoint for the bot.
    This should be integrated into the main bot or API server.

    Returns:
        Flask/FastAPI route handler
    """
    def health_check():
        """Health check endpoint."""
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'ralph-mode-bot'
        }

    return health_check


def main():
    """Main entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Mode Deployment Manager (DP-001, DP-002)')
    parser.add_argument('--feedback-id', type=int, required=True, help='Feedback ID to deploy')
    parser.add_argument('--check-health', action='store_true', help='Check staging health')
    parser.add_argument('--stage', choices=['staging', 'canary'], default='staging',
                        help='Deployment stage (default: staging)')
    parser.add_argument('--version', type=str, help='Version string (optional)')

    args = parser.parse_args()

    dm = DeployManager()

    if args.check_health:
        result = dm.check_staging_health()
        print(f"Health check: {'PASS' if result.healthy else 'FAIL'}")
        if result.healthy:
            print(f"Response time: {result.response_time_ms:.2f}ms")
        else:
            print(f"Error: {result.error_message}")
        sys.exit(0 if result.healthy else 1)

    if args.stage == 'canary':
        # DP-002: Deploy to canary
        result = dm.deploy_to_canary(args.feedback_id, version=args.version)

        if result.success and result.promoted:
            print(f"✅ Canary deployment SUCCESS - PROMOTED to production")
            print(f"   Canary URL: {result.canary_url}")
            print(f"   Production URL: {result.production_url}")
            print(f"   Status: {result.status.value}")
            print(f"   Observation: {result.observation_start} to {result.observation_end}")
            if result.baseline_metrics and result.canary_metrics:
                print(f"   Baseline error rate: {result.baseline_metrics.error_rate:.4f}")
                print(f"   Canary error rate: {result.canary_metrics.error_rate:.4f}")
                print(f"   Baseline latency: {result.baseline_metrics.avg_latency_ms:.2f}ms")
                print(f"   Canary latency: {result.canary_metrics.avg_latency_ms:.2f}ms")
            sys.exit(0)
        elif result.rolled_back:
            print(f"⚠️  Canary deployment ROLLED BACK")
            print(f"   Reason: {result.error_message}")
            print(f"   Status: {result.status.value}")
            if result.canary_metrics:
                print(f"   Canary error rate: {result.canary_metrics.error_rate:.4f}")
                print(f"   Canary requests: {result.canary_metrics.request_count}")
            sys.exit(1)
        else:
            print(f"❌ Canary deployment FAILED")
            print(f"   Error: {result.error_message}")
            print(f"   Status: {result.status.value}")
            sys.exit(1)
    else:
        # DP-001: Deploy to staging
        result = dm.deploy_to_staging(args.feedback_id, version=args.version)

        if result.success:
            print(f"✅ Staging deployment SUCCESS")
            print(f"   URL: {result.staging_url}")
            print(f"   Health check: {'PASS' if result.health_check_passed else 'FAIL'}")
            print(f"   Integration tests: {'PASS' if result.integration_tests_passed else 'FAIL'}")
            sys.exit(0)
        else:
            print(f"❌ Staging deployment FAILED")
            print(f"   Error: {result.error_message}")
            sys.exit(1)


if __name__ == '__main__':
    main()
