#!/usr/bin/env python3
"""
Dependency Checker for Ralph Mode (OB-023, OB-025)

Checks system dependencies (Node.js, npm, etc.) for onboarding wizard.
Provides version detection, comparison, and upgrade guidance.
Handles dependency installation with progress feedback.
"""

import logging
import subprocess
import re
import asyncio
from typing import Tuple, Optional, Dict, Any, Callable
from enum import Enum


class DependencyStatus(Enum):
    """Status of a dependency check."""
    INSTALLED = "installed"
    OUTDATED = "outdated"
    NOT_FOUND = "not_found"
    ERROR = "error"


class InstallationResult(Enum):
    """Result of a dependency installation attempt."""
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class DependencyChecker:
    """Checks system dependencies for Ralph Mode setup."""

    # Minimum required versions
    MIN_NODE_VERSION = "18.0.0"

    def __init__(self):
        """Initialize the dependency checker."""
        self.logger = logging.getLogger(__name__)

    def _parse_version(self, version_string: str) -> Tuple[int, int, int]:
        """Parse a semantic version string into (major, minor, patch).

        Args:
            version_string: Version string like "18.20.0" or "v18.20.0"

        Returns:
            Tuple of (major, minor, patch) as integers

        Raises:
            ValueError: If version string is invalid
        """
        # Remove 'v' prefix if present
        version_string = version_string.lstrip('v')

        # Extract version numbers using regex
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_string)
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def _compare_versions(self, version: str, min_version: str) -> bool:
        """Compare two semantic versions.

        Args:
            version: Version to check (e.g., "18.20.0")
            min_version: Minimum required version (e.g., "18.0.0")

        Returns:
            True if version >= min_version, False otherwise
        """
        try:
            current = self._parse_version(version)
            minimum = self._parse_version(min_version)
            return current >= minimum
        except ValueError as e:
            self.logger.warning(f"Version comparison failed: {e}")
            return False

    def check_nodejs(self) -> Tuple[DependencyStatus, str, Optional[str]]:
        """Check Node.js installation and version.

        Returns:
            Tuple of (status, message, version)
            - status: DependencyStatus enum
            - message: Human-readable message
            - version: Version string if detected, None otherwise
        """
        try:
            # Check if node is installed
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return (
                    DependencyStatus.NOT_FOUND,
                    "Node.js not found in PATH",
                    None
                )

            # Parse version
            version_output = result.stdout.strip()
            version = version_output.lstrip('v')

            # Compare with minimum version
            if self._compare_versions(version, self.MIN_NODE_VERSION):
                return (
                    DependencyStatus.INSTALLED,
                    f"Node.js {version} installed ✅",
                    version
                )
            else:
                return (
                    DependencyStatus.OUTDATED,
                    f"Node.js {version} is outdated (need {self.MIN_NODE_VERSION}+)",
                    version
                )

        except subprocess.TimeoutExpired:
            return (
                DependencyStatus.ERROR,
                "Node.js version check timed out",
                None
            )
        except FileNotFoundError:
            return (
                DependencyStatus.NOT_FOUND,
                "Node.js not installed",
                None
            )
        except Exception as e:
            self.logger.error(f"Node.js check failed: {e}")
            return (
                DependencyStatus.ERROR,
                f"Node.js check failed: {str(e)}",
                None
            )

    def check_npm(self) -> Tuple[DependencyStatus, str, Optional[str]]:
        """Check npm installation and version.

        Returns:
            Tuple of (status, message, version)
            - status: DependencyStatus enum
            - message: Human-readable message
            - version: Version string if detected, None otherwise
        """
        try:
            # Check if npm is installed
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return (
                    DependencyStatus.NOT_FOUND,
                    "npm not found in PATH",
                    None
                )

            # Parse version
            version = result.stdout.strip()

            return (
                DependencyStatus.INSTALLED,
                f"npm {version} installed ✅",
                version
            )

        except subprocess.TimeoutExpired:
            return (
                DependencyStatus.ERROR,
                "npm version check timed out",
                None
            )
        except FileNotFoundError:
            return (
                DependencyStatus.NOT_FOUND,
                "npm not installed",
                None
            )
        except Exception as e:
            self.logger.error(f"npm check failed: {e}")
            return (
                DependencyStatus.ERROR,
                f"npm check failed: {str(e)}",
                None
            )

    def get_nodejs_upgrade_guide(self) -> str:
        """Get upgrade guidance for Node.js.

        Returns:
            Formatted markdown string with upgrade instructions
        """
        return """**How to Install/Upgrade Node.js** 📦

**Option 1: Official Download** (Easiest)
→ Visit: https://nodejs.org
→ Download the LTS version (18.x or newer)
→ Run the installer

**Option 2: Using nvm** (Recommended for developers)
nvm lets you manage multiple Node.js versions!

**Install nvm:**
```bash
# macOS/Linux
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Windows - use nvm-windows
# Download from: https://github.com/coreybutler/nvm-windows/releases
```

**Then install Node.js:**
```bash
nvm install 18
nvm use 18
```

**Verify installation:**
```bash
node --version  # Should show v18.x.x or higher
npm --version   # Should show npm version
```
"""

    def get_npm_installation_guide(self) -> str:
        """Get installation guidance for npm.

        Returns:
            Formatted markdown string with npm installation instructions
        """
        return """**How to Install npm** 📦

npm usually comes with Node.js, but if it's missing:

**Option 1: Reinstall Node.js**
→ npm is bundled with Node.js
→ Download from: https://nodejs.org

**Option 2: Install npm separately** (rare)
```bash
# macOS/Linux
curl -L https://www.npmjs.com/install.sh | sh

# Windows - reinstall Node.js instead
```

**Verify installation:**
```bash
npm --version
```
"""

    async def run_npm_install(
        self,
        project_path: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[InstallationResult, str, Optional[str]]:
        """Run npm install with progress feedback.

        Args:
            project_path: Path to the project directory
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (result, message, error_details)
            - result: InstallationResult enum
            - message: Human-readable message
            - error_details: Error details if failed, None otherwise
        """
        try:
            if progress_callback:
                progress_callback("Starting npm install... 📦")

            # Run npm install
            process = await asyncio.create_subprocess_exec(
                "npm", "install",
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Stream output
            stdout_lines = []
            stderr_lines = []

            async def read_stdout():
                async for line in process.stdout:
                    line_str = line.decode().strip()
                    stdout_lines.append(line_str)
                    if progress_callback and line_str:
                        progress_callback(f"npm: {line_str}")

            async def read_stderr():
                async for line in process.stderr:
                    line_str = line.decode().strip()
                    stderr_lines.append(line_str)

            # Wait for both streams and process completion
            await asyncio.gather(read_stdout(), read_stderr())
            await process.wait()

            if process.returncode == 0:
                if progress_callback:
                    progress_callback("npm install completed successfully! ✅")
                return (
                    InstallationResult.SUCCESS,
                    "Dependencies installed successfully",
                    None
                )
            else:
                error_msg = "\n".join(stderr_lines) if stderr_lines else "Unknown error"
                if progress_callback:
                    progress_callback(f"npm install failed ❌")
                return (
                    InstallationResult.FAILURE,
                    f"npm install failed (exit code {process.returncode})",
                    error_msg
                )

        except FileNotFoundError:
            return (
                InstallationResult.FAILURE,
                "npm not found - please install Node.js first",
                None
            )
        except Exception as e:
            self.logger.error(f"npm install failed: {e}")
            return (
                InstallationResult.FAILURE,
                f"npm install error: {str(e)}",
                str(e)
            )

    async def run_pip_install(
        self,
        requirements_path: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[InstallationResult, str, Optional[str]]:
        """Run pip install with progress feedback.

        Args:
            requirements_path: Path to requirements.txt
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (result, message, error_details)
            - result: InstallationResult enum
            - message: Human-readable message
            - error_details: Error details if failed, None otherwise
        """
        try:
            if progress_callback:
                progress_callback("Starting pip install... 🐍")

            # Run pip install
            process = await asyncio.create_subprocess_exec(
                "pip3", "install", "-r", requirements_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Stream output
            stdout_lines = []
            stderr_lines = []

            async def read_stdout():
                async for line in process.stdout:
                    line_str = line.decode().strip()
                    stdout_lines.append(line_str)
                    if progress_callback and line_str:
                        # Show meaningful progress lines
                        if "Collecting" in line_str or "Installing" in line_str or "Successfully" in line_str:
                            progress_callback(f"pip: {line_str}")

            async def read_stderr():
                async for line in process.stderr:
                    line_str = line.decode().strip()
                    stderr_lines.append(line_str)

            # Wait for both streams and process completion
            await asyncio.gather(read_stdout(), read_stderr())
            await process.wait()

            if process.returncode == 0:
                if progress_callback:
                    progress_callback("pip install completed successfully! ✅")
                return (
                    InstallationResult.SUCCESS,
                    "Python dependencies installed successfully",
                    None
                )
            else:
                error_msg = "\n".join(stderr_lines) if stderr_lines else "Unknown error"
                if progress_callback:
                    progress_callback(f"pip install failed ❌")
                return (
                    InstallationResult.FAILURE,
                    f"pip install failed (exit code {process.returncode})",
                    error_msg
                )

        except FileNotFoundError:
            return (
                InstallationResult.FAILURE,
                "pip3 not found - please install Python first",
                None
            )
        except Exception as e:
            self.logger.error(f"pip install failed: {e}")
            return (
                InstallationResult.FAILURE,
                f"pip install error: {str(e)}",
                str(e)
            )

    def check_all_dependencies(self) -> Dict[str, Any]:
        """Check all required dependencies.

        Returns:
            Dictionary with check results:
            {
                'nodejs': {'status': DependencyStatus, 'message': str, 'version': str},
                'npm': {'status': DependencyStatus, 'message': str, 'version': str},
                'all_satisfied': bool
            }
        """
        results = {}

        # Check Node.js
        node_status, node_msg, node_ver = self.check_nodejs()
        results['nodejs'] = {
            'status': node_status,
            'message': node_msg,
            'version': node_ver
        }

        # Check npm
        npm_status, npm_msg, npm_ver = self.check_npm()
        results['npm'] = {
            'status': npm_status,
            'message': npm_msg,
            'version': npm_ver
        }

        # Determine if all dependencies are satisfied
        results['all_satisfied'] = (
            node_status == DependencyStatus.INSTALLED and
            npm_status == DependencyStatus.INSTALLED
        )

        return results


# Singleton instance
_dependency_checker = None


def get_dependency_checker() -> DependencyChecker:
    """Get the singleton dependency checker instance.

    Returns:
        DependencyChecker instance
    """
    global _dependency_checker
    if _dependency_checker is None:
        _dependency_checker = DependencyChecker()
    return _dependency_checker


# CLI testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== Dependency Checker Test ===\n")

    checker = get_dependency_checker()

    # Check Node.js
    print("Checking Node.js...")
    node_status, node_msg, node_ver = checker.check_nodejs()
    print(f"  Status: {node_status.value}")
    print(f"  Message: {node_msg}")
    print(f"  Version: {node_ver}\n")

    if node_status != DependencyStatus.INSTALLED:
        print(checker.get_nodejs_upgrade_guide())

    # Check npm
    print("Checking npm...")
    npm_status, npm_msg, npm_ver = checker.check_npm()
    print(f"  Status: {npm_status.value}")
    print(f"  Message: {npm_msg}")
    print(f"  Version: {npm_ver}\n")

    if npm_status != DependencyStatus.INSTALLED:
        print(checker.get_npm_installation_guide())

    # Check all
    print("Overall dependency status:")
    all_results = checker.check_all_dependencies()
    print(f"  All satisfied: {all_results['all_satisfied']}")
