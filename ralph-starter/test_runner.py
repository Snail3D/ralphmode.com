#!/usr/bin/env python3
"""
TS-001: Automated Test Suite Integration

This module provides test execution and coverage tracking for the build orchestrator.
Tests must pass 100% before a build can proceed to deployment.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Results from a test run."""
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_seconds: float
    coverage_percentage: Optional[float]
    coverage_decreased: bool
    error_messages: List[str]
    test_output: str
    timestamp: datetime


class TestRunner:
    """
    TS-001: Automated Test Suite Integration

    Runs pytest with coverage tracking and validates test results.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the test runner.

        Args:
            project_root: Root directory of the project. Defaults to current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.coverage_baseline_file = self.project_root / '.coverage_baseline'

    def run_tests(self, timeout: int = 600) -> TestResult:
        """
        Run the full test suite with coverage tracking.

        Args:
            timeout: Maximum time in seconds for tests to run. Default 10 minutes.

        Returns:
            TestResult with detailed test execution results
        """
        logger.info("Running test suite with coverage...")
        start_time = datetime.utcnow()

        try:
            # Get baseline coverage if available
            baseline_coverage = self._load_baseline_coverage()

            # Run pytest with coverage
            result = subprocess.run(
                [
                    'pytest',
                    '--cov=.',  # Coverage for entire project
                    '--cov-report=term-missing',  # Show missing lines
                    '--cov-report=json',  # JSON output for parsing
                    '-v',  # Verbose output
                    '--tb=short',  # Short traceback format
                    '--color=yes',  # Colored output
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            # Parse test results from output
            test_stats = self._parse_pytest_output(result.stdout, result.stderr)

            # Load coverage data
            coverage_data = self._load_coverage_json()
            current_coverage = coverage_data.get('totals', {}).get('percent_covered')

            # Check if coverage decreased
            coverage_decreased = False
            if baseline_coverage is not None and current_coverage is not None:
                if current_coverage < baseline_coverage:
                    coverage_decreased = True
                    logger.warning(
                        f"Coverage decreased: {baseline_coverage:.2f}% -> {current_coverage:.2f}%"
                    )

            # Determine if tests passed
            all_tests_passed = (
                result.returncode == 0 and
                test_stats['failed_tests'] == 0
            )

            # TS-001: Coverage must not decrease
            if coverage_decreased:
                all_tests_passed = False
                logger.error(f"FAIL: Coverage decreased from {baseline_coverage:.2f}% to {current_coverage:.2f}%")

            # Collect error messages
            error_messages = []
            if result.returncode != 0:
                error_messages.append(f"pytest exit code: {result.returncode}")
            if test_stats['failed_tests'] > 0:
                error_messages.append(f"{test_stats['failed_tests']} test(s) failed")
            if coverage_decreased:
                error_messages.append(
                    f"Coverage decreased: {baseline_coverage:.2f}% -> {current_coverage:.2f}%"
                )

            test_result = TestResult(
                passed=all_tests_passed,
                total_tests=test_stats['total_tests'],
                passed_tests=test_stats['passed_tests'],
                failed_tests=test_stats['failed_tests'],
                skipped_tests=test_stats['skipped_tests'],
                duration_seconds=duration,
                coverage_percentage=current_coverage,
                coverage_decreased=coverage_decreased,
                error_messages=error_messages,
                test_output=f"{result.stdout}\n{result.stderr}",
                timestamp=datetime.utcnow()
            )

            # Log summary
            self._log_test_summary(test_result, baseline_coverage)

            # Update baseline if tests passed
            if all_tests_passed and current_coverage is not None:
                self._save_baseline_coverage(current_coverage)

            return test_result

        except subprocess.TimeoutExpired:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Tests timed out after {timeout} seconds")

            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                duration_seconds=duration,
                coverage_percentage=None,
                coverage_decreased=False,
                error_messages=[f"Tests timed out after {timeout} seconds"],
                test_output="",
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Error running tests: {e}", exc_info=True)

            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                duration_seconds=duration,
                coverage_percentage=None,
                coverage_decreased=False,
                error_messages=[f"Error running tests: {str(e)}"],
                test_output="",
                timestamp=datetime.utcnow()
            )

    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, int]:
        """
        Parse pytest output to extract test statistics.

        Args:
            stdout: Standard output from pytest
            stderr: Standard error from pytest

        Returns:
            Dictionary with test statistics
        """
        stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0
        }

        # Look for pytest summary line like: "5 passed, 1 failed, 2 skipped in 1.23s"
        combined_output = stdout + stderr

        for line in combined_output.split('\n'):
            line_lower = line.lower()

            # Parse summary line
            if 'passed' in line_lower or 'failed' in line_lower or 'skipped' in line_lower:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        count = int(part)
                        if i + 1 < len(parts):
                            status = parts[i + 1].lower()
                            if 'passed' in status:
                                stats['passed_tests'] = count
                            elif 'failed' in status or 'error' in status:
                                stats['failed_tests'] = count
                            elif 'skipped' in status:
                                stats['skipped_tests'] = count

        # Calculate total
        stats['total_tests'] = (
            stats['passed_tests'] +
            stats['failed_tests'] +
            stats['skipped_tests']
        )

        return stats

    def _load_coverage_json(self) -> Dict[str, Any]:
        """
        Load coverage data from coverage.json file.

        Returns:
            Coverage data dictionary, or empty dict if not found
        """
        coverage_file = self.project_root / 'coverage.json'

        if not coverage_file.exists():
            logger.warning(f"Coverage file not found: {coverage_file}")
            return {}

        try:
            with open(coverage_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading coverage data: {e}")
            return {}

    def _load_baseline_coverage(self) -> Optional[float]:
        """
        Load baseline coverage percentage.

        Returns:
            Baseline coverage percentage, or None if not available
        """
        if not self.coverage_baseline_file.exists():
            return None

        try:
            with open(self.coverage_baseline_file, 'r') as f:
                data = json.load(f)
                return data.get('coverage_percentage')
        except Exception as e:
            logger.error(f"Error loading baseline coverage: {e}")
            return None

    def _save_baseline_coverage(self, coverage_percentage: float):
        """
        Save current coverage as the baseline.

        Args:
            coverage_percentage: Coverage percentage to save as baseline
        """
        try:
            data = {
                'coverage_percentage': coverage_percentage,
                'timestamp': datetime.utcnow().isoformat()
            }

            with open(self.coverage_baseline_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved coverage baseline: {coverage_percentage:.2f}%")

        except Exception as e:
            logger.error(f"Error saving baseline coverage: {e}")

    def _log_test_summary(self, result: TestResult, baseline_coverage: Optional[float]):
        """
        Log a summary of test results.

        Args:
            result: Test result to summarize
            baseline_coverage: Baseline coverage percentage (if available)
        """
        logger.info("=" * 70)
        logger.info("TEST SUITE RESULTS")
        logger.info("=" * 70)
        logger.info(f"Status: {'PASSED ✓' if result.passed else 'FAILED ✗'}")
        logger.info(f"Total Tests: {result.total_tests}")
        logger.info(f"  Passed: {result.passed_tests}")
        logger.info(f"  Failed: {result.failed_tests}")
        logger.info(f"  Skipped: {result.skipped_tests}")
        logger.info(f"Duration: {result.duration_seconds:.2f}s")

        if result.coverage_percentage is not None:
            logger.info(f"Coverage: {result.coverage_percentage:.2f}%")
            if baseline_coverage is not None:
                diff = result.coverage_percentage - baseline_coverage
                diff_str = f"{diff:+.2f}%"
                logger.info(f"  Baseline: {baseline_coverage:.2f}%")
                logger.info(f"  Change: {diff_str}")

        if result.error_messages:
            logger.error("Errors:")
            for error in result.error_messages:
                logger.error(f"  - {error}")

        logger.info("=" * 70)

    def get_test_summary(self, result: TestResult) -> str:
        """
        Get a human-readable test summary.

        Args:
            result: Test result to summarize

        Returns:
            Formatted summary string
        """
        lines = [
            "Test Suite Results",
            "=" * 50,
            f"Status: {'PASSED' if result.passed else 'FAILED'}",
            f"Tests: {result.passed_tests}/{result.total_tests} passed",
        ]

        if result.failed_tests > 0:
            lines.append(f"Failed: {result.failed_tests}")

        if result.skipped_tests > 0:
            lines.append(f"Skipped: {result.skipped_tests}")

        lines.append(f"Duration: {result.duration_seconds:.1f}s")

        if result.coverage_percentage is not None:
            lines.append(f"Coverage: {result.coverage_percentage:.2f}%")

        if result.error_messages:
            lines.append("\nErrors:")
            for error in result.error_messages:
                lines.append(f"  - {error}")

        return "\n".join(lines)


def main():
    """CLI entry point for running tests."""
    import argparse

    parser = argparse.ArgumentParser(description='Run test suite with coverage')
    parser.add_argument('--timeout', type=int, default=600, help='Test timeout in seconds')
    parser.add_argument('--project-root', type=Path, help='Project root directory')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    runner = TestRunner(project_root=args.project_root)
    result = runner.run_tests(timeout=args.timeout)

    print("\n" + runner.get_test_summary(result))

    # Exit with appropriate code
    exit(0 if result.passed else 1)


if __name__ == '__main__':
    main()
