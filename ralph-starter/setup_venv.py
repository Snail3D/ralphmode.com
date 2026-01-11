#!/usr/bin/env python3
"""
Python Virtual Environment Setup for Ralph Mode (OB-024)

Creates and manages Python virtual environments for project isolation.
Handles venv creation, activation, and dependency installation.
"""

import logging
import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from enum import Enum


class SetupStatus(Enum):
    """Status of virtual environment setup."""
    SUCCESS = "success"
    ALREADY_EXISTS = "already_exists"
    FAILURE = "failure"
    PYTHON_TOO_OLD = "python_too_old"
    PYTHON_NOT_FOUND = "python_not_found"


class VenvSetup:
    """Manages Python virtual environment setup."""

    # Minimum required Python version
    MIN_PYTHON_VERSION = (3, 9, 0)

    def __init__(self):
        """Initialize the venv setup manager."""
        self.logger = logging.getLogger(__name__)

    def _parse_python_version(self, version_string: str) -> Tuple[int, int, int]:
        """Parse Python version string into (major, minor, patch).

        Args:
            version_string: Version string like "3.9.0" or "Python 3.9.0"

        Returns:
            Tuple of (major, minor, patch) as integers

        Raises:
            ValueError: If version string is invalid
        """
        import re

        # Remove "Python" prefix if present
        version_string = version_string.replace("Python", "").strip()

        # Extract version numbers using regex
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_string)
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def check_python_version(self) -> Tuple[SetupStatus, str, Optional[Tuple[int, int, int]]]:
        """Check if Python version meets requirements.

        Returns:
            Tuple of (status, message, version_tuple)
            - status: SetupStatus enum
            - message: Human-readable message
            - version_tuple: (major, minor, patch) if detected, None otherwise
        """
        try:
            # Get Python version
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return (
                    SetupStatus.PYTHON_NOT_FOUND,
                    "Could not determine Python version",
                    None
                )

            # Parse version
            version_output = result.stdout.strip() or result.stderr.strip()
            version_tuple = self._parse_python_version(version_output)

            # Compare with minimum version
            if version_tuple >= self.MIN_PYTHON_VERSION:
                return (
                    SetupStatus.SUCCESS,
                    f"Python {'.'.join(map(str, version_tuple))} ✅",
                    version_tuple
                )
            else:
                return (
                    SetupStatus.PYTHON_TOO_OLD,
                    f"Python {'.'.join(map(str, version_tuple))} is too old (need 3.9+)",
                    version_tuple
                )

        except FileNotFoundError:
            return (
                SetupStatus.PYTHON_NOT_FOUND,
                "Python not found",
                None
            )
        except Exception as e:
            self.logger.error(f"Python version check failed: {e}")
            return (
                SetupStatus.FAILURE,
                f"Version check failed: {str(e)}",
                None
            )

    def check_venv_exists(self, venv_path: str = "venv") -> bool:
        """Check if virtual environment already exists.

        Args:
            venv_path: Path to the virtual environment directory

        Returns:
            True if venv exists, False otherwise
        """
        venv_dir = Path(venv_path)

        # Check for common venv indicators
        if not venv_dir.exists():
            return False

        # Check for pyvenv.cfg (standard venv marker)
        pyvenv_cfg = venv_dir / "pyvenv.cfg"
        if pyvenv_cfg.exists():
            return True

        # Check for Scripts/bin directory with python
        scripts_dir = venv_dir / "Scripts" if sys.platform == "win32" else venv_dir / "bin"
        python_exe = scripts_dir / ("python.exe" if sys.platform == "win32" else "python")

        return python_exe.exists()

    def create_venv(self, venv_path: str = "venv") -> Tuple[SetupStatus, str]:
        """Create a Python virtual environment.

        Args:
            venv_path: Path where to create the virtual environment

        Returns:
            Tuple of (status, message)
            - status: SetupStatus enum
            - message: Human-readable message
        """
        try:
            # Check if venv already exists
            if self.check_venv_exists(venv_path):
                return (
                    SetupStatus.ALREADY_EXISTS,
                    f"Virtual environment already exists at {venv_path}"
                )

            self.logger.info(f"Creating virtual environment at {venv_path}...")

            # Create venv using Python's venv module
            result = subprocess.run(
                [sys.executable, "-m", "venv", venv_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.logger.info(f"Virtual environment created successfully at {venv_path}")
                return (
                    SetupStatus.SUCCESS,
                    f"Virtual environment created at {venv_path} ✅"
                )
            else:
                error_msg = result.stderr or "Unknown error"
                self.logger.error(f"venv creation failed: {error_msg}")
                return (
                    SetupStatus.FAILURE,
                    f"Failed to create venv: {error_msg}"
                )

        except subprocess.TimeoutExpired:
            return (
                SetupStatus.FAILURE,
                "venv creation timed out"
            )
        except Exception as e:
            self.logger.error(f"venv creation error: {e}")
            return (
                SetupStatus.FAILURE,
                f"venv creation error: {str(e)}"
            )

    def get_venv_python(self, venv_path: str = "venv") -> str:
        """Get the path to the Python executable in the venv.

        Args:
            venv_path: Path to the virtual environment

        Returns:
            Path to Python executable in venv
        """
        venv_dir = Path(venv_path)

        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"

        return str(python_exe)

    def get_venv_pip(self, venv_path: str = "venv") -> str:
        """Get the path to pip executable in the venv.

        Args:
            venv_path: Path to the virtual environment

        Returns:
            Path to pip executable in venv
        """
        venv_dir = Path(venv_path)

        if sys.platform == "win32":
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:
            pip_exe = venv_dir / "bin" / "pip"

        return str(pip_exe)

    def install_requirements(
        self,
        requirements_path: str,
        venv_path: str = "venv",
        progress_callback: Optional[callable] = None
    ) -> Tuple[SetupStatus, str, Optional[str]]:
        """Install requirements in the virtual environment.

        Args:
            requirements_path: Path to requirements.txt
            venv_path: Path to the virtual environment
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (status, message, error_details)
            - status: SetupStatus enum
            - message: Human-readable message
            - error_details: Error details if failed, None otherwise
        """
        try:
            # Check if requirements file exists
            if not os.path.exists(requirements_path):
                return (
                    SetupStatus.FAILURE,
                    f"Requirements file not found: {requirements_path}",
                    None
                )

            # Check if venv exists
            if not self.check_venv_exists(venv_path):
                return (
                    SetupStatus.FAILURE,
                    f"Virtual environment not found at {venv_path}",
                    None
                )

            # Get pip executable in venv
            pip_exe = self.get_venv_pip(venv_path)

            if not os.path.exists(pip_exe):
                return (
                    SetupStatus.FAILURE,
                    f"pip not found in virtual environment: {pip_exe}",
                    None
                )

            self.logger.info(f"Installing requirements from {requirements_path}...")
            if progress_callback:
                progress_callback(f"Installing from {requirements_path}...")

            # Run pip install in venv
            process = subprocess.Popen(
                [pip_exe, "install", "-r", requirements_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            stdout_lines = []
            stderr_lines = []

            # Read stdout
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        stdout_lines.append(line.strip())
                        # Show meaningful progress lines
                        if progress_callback and any(keyword in line for keyword in ["Collecting", "Installing", "Successfully"]):
                            progress_callback(line.strip())

            # Wait for process to complete
            process.wait()

            # Read stderr
            if process.stderr:
                stderr_output = process.stderr.read()
                stderr_lines = [line.strip() for line in stderr_output.split('\n') if line.strip()]

            stdout = '\n'.join(stdout_lines)
            stderr = '\n'.join(stderr_lines)

            if process.returncode == 0:
                success_msg = "All packages installed successfully ✅"
                if progress_callback:
                    progress_callback(success_msg)
                self.logger.info(success_msg)
                return (
                    SetupStatus.SUCCESS,
                    success_msg,
                    None
                )
            else:
                error_msg = stderr if stderr else "Unknown error"
                self.logger.error(f"pip install failed: {error_msg}")
                return (
                    SetupStatus.FAILURE,
                    f"Package installation failed (exit code {process.returncode})",
                    error_msg
                )

        except Exception as e:
            self.logger.error(f"Requirements installation error: {e}")
            return (
                SetupStatus.FAILURE,
                f"Installation error: {str(e)}",
                str(e)
            )

    def verify_packages(
        self,
        requirements_path: str,
        venv_path: str = "venv"
    ) -> Tuple[bool, str, Dict[str, bool]]:
        """Verify all packages from requirements are installed.

        Args:
            requirements_path: Path to requirements.txt
            venv_path: Path to the virtual environment

        Returns:
            Tuple of (all_installed, message, package_status)
            - all_installed: True if all packages are installed
            - message: Human-readable message
            - package_status: Dict mapping package names to installation status
        """
        try:
            # Read requirements file
            with open(requirements_path, 'r') as f:
                requirements = f.readlines()

            # Parse package names (simple parsing, ignores version specifiers)
            import re
            package_names = []
            for line in requirements:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Extract package name (before any version specifier)
                match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                if match:
                    package_names.append(match.group(1))

            if not package_names:
                return (True, "No packages to verify", {})

            # Get pip executable
            pip_exe = self.get_venv_pip(venv_path)

            # Check each package
            package_status = {}
            for package in package_names:
                result = subprocess.run(
                    [pip_exe, "show", package],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                package_status[package] = (result.returncode == 0)

            # Determine overall status
            all_installed = all(package_status.values())

            if all_installed:
                return (
                    True,
                    f"All {len(package_names)} packages verified ✅",
                    package_status
                )
            else:
                missing = [pkg for pkg, installed in package_status.items() if not installed]
                return (
                    False,
                    f"Missing packages: {', '.join(missing)}",
                    package_status
                )

        except Exception as e:
            self.logger.error(f"Package verification error: {e}")
            return (
                False,
                f"Verification error: {str(e)}",
                {}
            )

    def get_activation_command(self, venv_path: str = "venv") -> str:
        """Get the command to activate the virtual environment.

        Args:
            venv_path: Path to the virtual environment

        Returns:
            Activation command string
        """
        if sys.platform == "win32":
            return f"{venv_path}\\Scripts\\activate.bat"
        else:
            return f"source {venv_path}/bin/activate"


# Singleton instance
_venv_setup = None


def get_venv_setup() -> VenvSetup:
    """Get the singleton venv setup instance.

    Returns:
        VenvSetup instance
    """
    global _venv_setup
    if _venv_setup is None:
        _venv_setup = VenvSetup()
    return _venv_setup


# CLI testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== Python Virtual Environment Setup Test ===\n")

    setup = get_venv_setup()

    # Check Python version
    print("Checking Python version...")
    status, msg, version = setup.check_python_version()
    print(f"  Status: {status.value}")
    print(f"  Message: {msg}")
    print(f"  Version: {version}\n")

    if status != SetupStatus.SUCCESS:
        print("Python version check failed. Exiting.")
        sys.exit(1)

    # Check if venv exists
    print("Checking for existing venv...")
    venv_exists = setup.check_venv_exists()
    print(f"  Exists: {venv_exists}\n")

    if not venv_exists:
        print("Creating virtual environment...")
        status, msg = setup.create_venv()
        print(f"  Status: {status.value}")
        print(f"  Message: {msg}\n")

    # Show activation command
    print("Virtual environment activation:")
    print(f"  Command: {setup.get_activation_command()}\n")

    print("Setup test complete!")
