#!/usr/bin/env python3
"""
MM-005: Test Prompt Library
2-3 sentence validation prompts per role

MM-006: Test Runner
Execute validation and score results

This module provides standardized test prompts for each role to validate
that models can perform their expected functions. Each test is short,
focused, and easy to score programmatically.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from model_manager import (
    get_model_manager,
    ModelRole,
    ModelAdapter,
    ModelManager
)

logger = logging.getLogger(__name__)


# ============================================================================
# MM-005: Test Prompt Library
# ============================================================================

@dataclass
class TestPrompt:
    """A single test prompt with expected behavior"""
    name: str
    role: ModelRole
    messages: List[Dict[str, str]]
    expected_behavior: str
    validation_fn: Optional[callable] = None
    max_tokens: int = 100
    temperature: float = 0.7


# Test prompts for RALPH role (personality/character)
RALPH_TESTS = [
    TestPrompt(
        name="ralph_personality",
        role=ModelRole.RALPH,
        messages=[
            {
                "role": "system",
                "content": "You are Ralph Wiggum, the lovable but confused boss. You say 'unpossible', misspell words occasionally, and are endearing but not incompetent at your actual job."
            },
            {
                "role": "user",
                "content": "Hi Ralph, how are you today?"
            }
        ],
        expected_behavior="Should respond in character as Ralph - friendly, slightly confused, possibly misspelling something",
        max_tokens=50,
        temperature=0.8
    ),
    TestPrompt(
        name="ralph_brevity",
        role=ModelRole.RALPH,
        messages=[
            {
                "role": "system",
                "content": "You are Ralph Wiggum. Keep responses short - one or two sentences max."
            },
            {
                "role": "user",
                "content": "What should we work on today?"
            }
        ],
        expected_behavior="Should give a brief response, not a long monologue",
        max_tokens=60,
        temperature=0.7
    ),
    TestPrompt(
        name="ralph_task_understanding",
        role=ModelRole.RALPH,
        messages=[
            {
                "role": "system",
                "content": "You are Ralph, the project boss. You understand tasks and can delegate them."
            },
            {
                "role": "user",
                "content": "We need to fix the login button. Who should work on this?"
            }
        ],
        expected_behavior="Should understand the task and suggest a worker or approach",
        max_tokens=80,
        temperature=0.7
    )
]


# Test prompts for WORKER role (coding agents)
WORKER_TESTS = [
    TestPrompt(
        name="worker_code_generation",
        role=ModelRole.WORKER,
        messages=[
            {
                "role": "system",
                "content": "You are a professional software engineer. Write clean, correct code."
            },
            {
                "role": "user",
                "content": "Write a Python function that checks if a number is even. Just the function, no explanation."
            }
        ],
        expected_behavior="Should generate a working Python function",
        max_tokens=100,
        temperature=0.3
    ),
    TestPrompt(
        name="worker_bug_analysis",
        role=ModelRole.WORKER,
        messages=[
            {
                "role": "system",
                "content": "You are debugging code. Explain issues clearly and concisely."
            },
            {
                "role": "user",
                "content": "This code crashes: x = [1,2,3]; print(x[5]). What's wrong?"
            }
        ],
        expected_behavior="Should identify the IndexError issue",
        max_tokens=80,
        temperature=0.3
    ),
    TestPrompt(
        name="worker_code_review",
        role=ModelRole.WORKER,
        messages=[
            {
                "role": "system",
                "content": "You are reviewing code. Be helpful but honest."
            },
            {
                "role": "user",
                "content": "Review this: def add(a,b): return a+b"
            }
        ],
        expected_behavior="Should provide constructive feedback",
        max_tokens=100,
        temperature=0.5
    )
]


# Test prompts for BUILDER role (build loop / Claude Code integration)
BUILDER_TESTS = [
    TestPrompt(
        name="builder_task_planning",
        role=ModelRole.BUILDER,
        messages=[
            {
                "role": "system",
                "content": "You are planning implementation steps. Be systematic and thorough."
            },
            {
                "role": "user",
                "content": "Plan how to add user authentication to a web app. List 3 main steps."
            }
        ],
        expected_behavior="Should provide clear, ordered steps",
        max_tokens=150,
        temperature=0.4
    ),
    TestPrompt(
        name="builder_file_navigation",
        role=ModelRole.BUILDER,
        messages=[
            {
                "role": "system",
                "content": "You understand codebase structure and can navigate files."
            },
            {
                "role": "user",
                "content": "Where would you expect to find database models in a typical Python web app?"
            }
        ],
        expected_behavior="Should mention common patterns like models/ or db/models.py",
        max_tokens=80,
        temperature=0.3
    ),
    TestPrompt(
        name="builder_error_handling",
        role=ModelRole.BUILDER,
        messages=[
            {
                "role": "system",
                "content": "You are analyzing build errors and suggesting fixes."
            },
            {
                "role": "user",
                "content": "ImportError: No module named 'requests'. How do I fix this?"
            }
        ],
        expected_behavior="Should suggest installing the package (pip install requests)",
        max_tokens=60,
        temperature=0.3
    )
]


# Test prompts for DESIGN role (UI/UX decisions - Frinky)
DESIGN_TESTS = [
    TestPrompt(
        name="design_color_choice",
        role=ModelRole.DESIGN,
        messages=[
            {
                "role": "system",
                "content": "You are a design expert making aesthetic decisions."
            },
            {
                "role": "user",
                "content": "What color should an error message be and why? One sentence."
            }
        ],
        expected_behavior="Should suggest red/orange and give a brief reason",
        max_tokens=40,
        temperature=0.5
    ),
    TestPrompt(
        name="design_layout_advice",
        role=ModelRole.DESIGN,
        messages=[
            {
                "role": "system",
                "content": "You give practical UI/UX advice."
            },
            {
                "role": "user",
                "content": "Should a login button be top-right or center of page?"
            }
        ],
        expected_behavior="Should give a reasoned preference",
        max_tokens=60,
        temperature=0.6
    ),
    TestPrompt(
        name="design_user_flow",
        role=ModelRole.DESIGN,
        messages=[
            {
                "role": "system",
                "content": "You understand user experience and flows."
            },
            {
                "role": "user",
                "content": "User clicks 'Delete Account'. What should happen next?"
            }
        ],
        expected_behavior="Should mention confirmation dialog or warning",
        max_tokens=80,
        temperature=0.5
    )
]


# Combined test library
TEST_LIBRARY: Dict[ModelRole, List[TestPrompt]] = {
    ModelRole.RALPH: RALPH_TESTS,
    ModelRole.WORKER: WORKER_TESTS,
    ModelRole.BUILDER: BUILDER_TESTS,
    ModelRole.DESIGN: DESIGN_TESTS
}


def get_tests_for_role(role: ModelRole) -> List[TestPrompt]:
    """
    Get all test prompts for a specific role.

    Args:
        role: The ModelRole to get tests for

    Returns:
        List of TestPrompt objects for that role
    """
    return TEST_LIBRARY.get(role, [])


def get_test_by_name(name: str) -> Optional[TestPrompt]:
    """
    Get a specific test by name.

    Args:
        name: Name of the test

    Returns:
        TestPrompt object or None if not found
    """
    for tests in TEST_LIBRARY.values():
        for test in tests:
            if test.name == name:
                return test
    return None


def list_all_tests() -> List[str]:
    """
    List all available test names.

    Returns:
        List of test names across all roles
    """
    names = []
    for tests in TEST_LIBRARY.values():
        names.extend([test.name for test in tests])
    return names


# ============================================================================
# MM-006: Test Runner
# ============================================================================

@dataclass
class TestResult:
    """Result of running a single test"""
    test_name: str
    role: ModelRole
    passed: bool
    response: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class ModelTester:
    """
    MM-006: Test Runner

    Executes validation tests against models and scores results.
    """

    def __init__(self, manager: Optional[ModelManager] = None):
        """
        Initialize the test runner.

        Args:
            manager: ModelManager instance. If None, uses global singleton.
        """
        self.manager = manager or get_model_manager()

    async def run_test(
        self,
        test: TestPrompt,
        adapter: Optional[ModelAdapter] = None
    ) -> TestResult:
        """
        Run a single test against a model.

        Args:
            test: The TestPrompt to run
            adapter: Optional specific adapter. If None, uses role's default model.

        Returns:
            TestResult with pass/fail and details
        """
        logger.info(f"MM-006: Running test '{test.name}' for role {test.role.value}")

        start_time = asyncio.get_event_loop().time()

        try:
            # Get response from model
            if adapter:
                # Use specific adapter
                response = await adapter.generate(
                    messages=test.messages,
                    max_tokens=test.max_tokens,
                    temperature=test.temperature
                )
            else:
                # Use role's default model
                response = await self.manager.generate(
                    role=test.role,
                    messages=test.messages,
                    max_tokens=test.max_tokens,
                    temperature=test.temperature
                )

            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Basic pass criteria: got a non-empty response
            passed = bool(response and len(response.strip()) > 0)

            # Apply custom validation if provided
            if test.validation_fn and response:
                try:
                    passed = test.validation_fn(response)
                except Exception as e:
                    logger.warning(f"MM-006: Validation function failed for {test.name}: {e}")
                    passed = False

            result = TestResult(
                test_name=test.name,
                role=test.role,
                passed=passed,
                response=response,
                latency_ms=latency_ms
            )

            logger.info(
                f"MM-006: Test '{test.name}': {'PASS' if passed else 'FAIL'} "
                f"({latency_ms:.0f}ms)"
            )

            return result

        except Exception as e:
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"MM-006: Test '{test.name}' failed with error: {e}")

            return TestResult(
                test_name=test.name,
                role=test.role,
                passed=False,
                error=str(e),
                latency_ms=latency_ms
            )

    async def run_role_tests(
        self,
        role: ModelRole,
        adapter: Optional[ModelAdapter] = None
    ) -> List[TestResult]:
        """
        Run all tests for a specific role.

        Args:
            role: The role to test
            adapter: Optional specific adapter

        Returns:
            List of TestResult objects
        """
        tests = get_tests_for_role(role)
        logger.info(f"MM-006: Running {len(tests)} tests for role {role.value}")

        results = []
        for test in tests:
            result = await self.run_test(test, adapter)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        logger.info(f"MM-006: Role {role.value}: {passed}/{len(results)} tests passed")

        return results

    async def run_all_tests(
        self,
        record_to_registry: bool = True
    ) -> Dict[ModelRole, List[TestResult]]:
        """
        Run all tests across all configured roles.

        Args:
            record_to_registry: Whether to save results to the model registry

        Returns:
            Dict mapping roles to their test results
        """
        logger.info("MM-006: Running full test suite across all roles")

        all_results = {}

        for role in ModelRole:
            # Check if a model is configured for this role
            adapter = self.manager.get_model(role)
            if not adapter:
                logger.warning(f"MM-006: No model configured for {role.value}, skipping tests")
                continue

            # Run tests for this role
            results = await self.run_role_tests(role, adapter)
            all_results[role] = results

            # Record to registry if requested
            if record_to_registry:
                model_name = f"{role.value}_{adapter.provider.value}_{adapter.config.model_id}"
                for result in results:
                    self.manager.record_test(
                        model_name=model_name,
                        test_name=result.test_name,
                        passed=result.passed,
                        details={
                            "response_preview": result.response[:100] if result.response else None,
                            "error": result.error,
                            "latency_ms": result.latency_ms
                        }
                    )

        # Print summary
        total_tests = sum(len(results) for results in all_results.values())
        total_passed = sum(
            sum(1 for r in results if r.passed)
            for results in all_results.values()
        )

        logger.info(f"MM-006: Test suite complete: {total_passed}/{total_tests} tests passed")

        return all_results

    def print_results(self, results: Dict[ModelRole, List[TestResult]]):
        """
        Pretty-print test results.

        Args:
            results: Dict of results from run_all_tests()
        """
        print("\n" + "=" * 70)
        print("MM-006: Test Results")
        print("=" * 70)

        for role, role_results in results.items():
            passed = sum(1 for r in role_results if r.passed)
            total = len(role_results)

            print(f"\n{role.value.upper()} ({passed}/{total} passed)")
            print("-" * 70)

            for result in role_results:
                status = "✅ PASS" if result.passed else "❌ FAIL"
                latency = f"{result.latency_ms:.0f}ms" if result.latency_ms else "N/A"
                print(f"  {status} {result.test_name} ({latency})")

                if result.error:
                    print(f"       Error: {result.error}")
                elif result.response:
                    preview = result.response[:80].replace("\n", " ")
                    if len(result.response) > 80:
                        preview += "..."
                    print(f"       Response: {preview}")

        # Overall summary
        total_tests = sum(len(results) for results in results.values())
        total_passed = sum(
            sum(1 for r in results if r.passed)
            for results in results.values()
        )

        print("\n" + "=" * 70)
        print(f"OVERALL: {total_passed}/{total_tests} tests passed")
        print("=" * 70 + "\n")


# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    """Run model tests from command line"""
    import sys

    tester = ModelTester()

    if len(sys.argv) > 1:
        # Run specific role tests
        role_name = sys.argv[1].upper()
        try:
            role = ModelRole[role_name]
            print(f"Running tests for {role.value}...")
            results = await tester.run_role_tests(role)
            tester.print_results({role: results})
        except KeyError:
            print(f"Unknown role: {role_name}")
            print(f"Available roles: {[r.name for r in ModelRole]}")
            sys.exit(1)
    else:
        # Run all tests
        print("Running full test suite...")
        results = await tester.run_all_tests(record_to_registry=True)
        tester.print_results(results)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
