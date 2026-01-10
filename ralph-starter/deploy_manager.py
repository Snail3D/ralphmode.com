#!/usr/bin/env python3
"""
DP-001: Staging Deployment Manager for Ralph Mode Bot

This service handles:
- Auto-deploy passing builds to staging environment
- Run integration tests on staging
- Health check endpoints
- Auto-promote to canary if healthy
- Integration with build orchestrator

Usage:
    from deploy_manager import DeployManager

    dm = DeployManager()
    result = dm.deploy_to_staging(feedback_id=123)
    if result.success:
        print(f"Deployed to {result.staging_url}")
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

        # Health check configuration
        self.health_check_timeout = int(os.getenv('HEALTH_CHECK_TIMEOUT', '30'))
        self.health_check_retries = int(os.getenv('HEALTH_CHECK_RETRIES', '3'))

        # Integration test configuration
        self.integration_test_timeout = int(os.getenv('INTEGRATION_TEST_TIMEOUT', '300'))

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

    parser = argparse.ArgumentParser(description='Ralph Mode Deployment Manager (DP-001)')
    parser.add_argument('--feedback-id', type=int, required=True, help='Feedback ID to deploy')
    parser.add_argument('--check-health', action='store_true', help='Check staging health')

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

    # Deploy to staging
    result = dm.deploy_to_staging(args.feedback_id)

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
