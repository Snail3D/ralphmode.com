#!/usr/bin/env python3
"""
Tests for DP-001: Staging Deployment Manager

Run with: pytest test_deploy_manager.py -v
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from deploy_manager import (
    DeployManager,
    DeploymentResult,
    DeploymentStage,
    HealthCheckResult
)


class TestDeployManager:
    """Test suite for DeployManager."""

    def setup_method(self):
        """Setup test fixtures."""
        self.deploy_manager = DeployManager()

    def test_initialization(self):
        """Test DeployManager initialization."""
        assert self.deploy_manager is not None
        assert self.deploy_manager.staging_host == os.getenv('STAGING_HOST', '69.164.201.191')
        assert self.deploy_manager.staging_port == os.getenv('STAGING_PORT', '8001')

    def test_generate_version(self):
        """Test version generation."""
        version = self.deploy_manager._generate_version()
        assert version is not None
        assert len(version) > 0
        # Format should be YYYYMMDD.HHMMSS
        assert '.' in version

    def test_get_staging_url(self):
        """Test staging URL construction."""
        url = self.deploy_manager.get_staging_url()
        assert url.startswith('http://')
        assert self.deploy_manager.staging_host in url
        assert self.deploy_manager.staging_port in url

    @patch('deploy_manager.subprocess.run')
    def test_prepare_artifacts_success(self, mock_run):
        """Test successful artifact preparation."""
        mock_run.return_value = Mock(returncode=0)

        result = self.deploy_manager._prepare_artifacts(feedback_id=123)

        # Should create deployment directory
        assert result is True

    @patch('deploy_manager.subprocess.run')
    def test_prepare_artifacts_failure(self, mock_run):
        """Test artifact preparation failure."""
        mock_run.side_effect = Exception("Copy failed")

        result = self.deploy_manager._prepare_artifacts(feedback_id=123)

        assert result is False

    @patch('deploy_manager.subprocess.run')
    def test_deploy_artifacts_success(self, mock_run):
        """Test successful artifact deployment."""
        mock_run.return_value = Mock(returncode=0, stderr='')

        # First create artifacts
        with patch.object(self.deploy_manager, '_prepare_artifacts', return_value=True):
            self.deploy_manager._prepare_artifacts(123)

        result = self.deploy_manager._deploy_artifacts(feedback_id=123)

        # Should use rsync
        assert result is True
        assert mock_run.called

    @patch('deploy_manager.subprocess.run')
    def test_deploy_artifacts_rsync_failure(self, mock_run):
        """Test rsync failure during deployment."""
        # First call (mkdir) succeeds, second call (rsync) fails
        mock_run.side_effect = [
            Mock(returncode=0, stderr=''),  # mkdir success
            Mock(returncode=1, stderr='rsync error')  # rsync failure
        ]

        result = self.deploy_manager._deploy_artifacts(feedback_id=123)

        assert result is False

    @patch('deploy_manager.subprocess.run')
    def test_restart_staging_service_success(self, mock_run):
        """Test successful service restart."""
        mock_run.return_value = Mock(returncode=0)

        result = self.deploy_manager._restart_staging_service()

        assert result is True
        # Should call both kill and start commands
        assert mock_run.call_count >= 2

    @patch('deploy_manager.subprocess.run')
    def test_restart_staging_service_failure(self, mock_run):
        """Test service restart failure."""
        # Kill succeeds, start fails
        mock_run.side_effect = [
            Mock(returncode=0),  # kill success
            Mock(returncode=1, stderr='start failed')  # start failure
        ]

        result = self.deploy_manager._restart_staging_service()

        assert result is False

    @patch('deploy_manager.requests.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.deploy_manager._run_health_checks()

        assert result.healthy is True
        assert result.status_code == 200
        assert result.response_time_ms is not None

    @patch('deploy_manager.requests.get')
    def test_health_check_failure_non_200(self, mock_get):
        """Test health check with non-200 status."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = self.deploy_manager._run_health_checks()

        assert result.healthy is False

    @patch('deploy_manager.requests.get')
    def test_health_check_failure_timeout(self, mock_get):
        """Test health check timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        result = self.deploy_manager._run_health_checks()

        assert result.healthy is False
        assert 'failed after' in result.error_message

    @patch('deploy_manager.requests.get')
    def test_health_check_retries(self, mock_get):
        """Test health check retry logic."""
        import requests
        # Fail twice, succeed on third attempt
        mock_get.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            requests.exceptions.Timeout("Timeout"),
            Mock(status_code=200)
        ]

        result = self.deploy_manager._run_health_checks()

        assert result.healthy is True
        assert mock_get.call_count == 3

    @patch('deploy_manager.subprocess.run')
    def test_integration_tests_success(self, mock_run):
        """Test successful integration tests."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='All tests passed',
            stderr=''
        )

        result = self.deploy_manager._run_integration_tests()

        assert result is True

    @patch('deploy_manager.subprocess.run')
    def test_integration_tests_failure(self, mock_run):
        """Test failed integration tests."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='Test failures',
            stderr='2 tests failed'
        )

        result = self.deploy_manager._run_integration_tests()

        assert result is False

    @patch('deploy_manager.subprocess.run')
    def test_integration_tests_timeout(self, mock_run):
        """Test integration test timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('pytest', 300)

        result = self.deploy_manager._run_integration_tests()

        assert result is False

    @patch.object(DeployManager, '_prepare_artifacts')
    @patch.object(DeployManager, '_deploy_artifacts')
    @patch.object(DeployManager, '_restart_staging_service')
    @patch.object(DeployManager, '_run_health_checks')
    @patch.object(DeployManager, '_run_integration_tests')
    def test_deploy_to_staging_success(
        self,
        mock_integration,
        mock_health,
        mock_restart,
        mock_deploy,
        mock_prepare
    ):
        """Test complete successful staging deployment."""
        # Mock all steps to succeed
        mock_prepare.return_value = True
        mock_deploy.return_value = True
        mock_restart.return_value = True
        mock_health.return_value = HealthCheckResult(
            healthy=True,
            status_code=200,
            response_time_ms=50.0
        )
        mock_integration.return_value = True

        result = self.deploy_manager.deploy_to_staging(feedback_id=123)

        assert result.success is True
        assert result.stage == DeploymentStage.STAGING
        assert result.feedback_id == 123
        assert result.staging_url is not None
        assert result.health_check_passed is True
        assert result.integration_tests_passed is True
        assert result.deployed_at is not None

    @patch.object(DeployManager, '_prepare_artifacts')
    def test_deploy_to_staging_prepare_fails(self, mock_prepare):
        """Test deployment failure at artifact preparation."""
        mock_prepare.return_value = False

        result = self.deploy_manager.deploy_to_staging(feedback_id=123)

        assert result.success is False
        assert 'Failed to prepare artifacts' in result.error_message

    @patch.object(DeployManager, '_prepare_artifacts')
    @patch.object(DeployManager, '_deploy_artifacts')
    @patch.object(DeployManager, '_restart_staging_service')
    @patch.object(DeployManager, '_run_health_checks')
    def test_deploy_to_staging_health_check_fails(
        self,
        mock_health,
        mock_restart,
        mock_deploy,
        mock_prepare
    ):
        """Test deployment failure at health check."""
        mock_prepare.return_value = True
        mock_deploy.return_value = True
        mock_restart.return_value = True
        mock_health.return_value = HealthCheckResult(
            healthy=False,
            error_message='Service not responding'
        )

        result = self.deploy_manager.deploy_to_staging(feedback_id=123)

        assert result.success is False
        assert 'Health check failed' in result.error_message

    @patch.object(DeployManager, '_prepare_artifacts')
    @patch.object(DeployManager, '_deploy_artifacts')
    @patch.object(DeployManager, '_restart_staging_service')
    @patch.object(DeployManager, '_run_health_checks')
    @patch.object(DeployManager, '_run_integration_tests')
    def test_deploy_to_staging_integration_tests_fail(
        self,
        mock_integration,
        mock_health,
        mock_restart,
        mock_deploy,
        mock_prepare
    ):
        """Test deployment failure at integration tests."""
        mock_prepare.return_value = True
        mock_deploy.return_value = True
        mock_restart.return_value = True
        mock_health.return_value = HealthCheckResult(healthy=True, status_code=200)
        mock_integration.return_value = False

        result = self.deploy_manager.deploy_to_staging(feedback_id=123)

        assert result.success is False
        assert 'Integration tests failed' in result.error_message


@pytest.mark.integration
class TestDeployManagerIntegration:
    """Integration tests for DeployManager (requires actual staging environment)."""

    def test_staging_health_check_integration(self):
        """Test actual health check against staging (if available)."""
        dm = DeployManager()

        # This will only pass if staging is actually running
        result = dm.check_staging_health()

        # Log result but don't fail test if staging is down
        if result.healthy:
            assert result.status_code == 200
            assert result.response_time_ms > 0
        else:
            pytest.skip(f"Staging not available: {result.error_message}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
