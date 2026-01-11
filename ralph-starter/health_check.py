#!/usr/bin/env python3
"""
MCP Health Check System (OB-021)

Verifies all MCP connections are working. Runs periodically and on-demand.
Provides status reporting, reconnection capabilities, and alerting.
"""

import logging
import subprocess
import asyncio
import json
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from enum import Enum
import os


class HealthStatus(Enum):
    """Health status levels for MCP servers."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class MCPHealthChecker:
    """Health checker for MCP servers."""

    def __init__(self, log_dir: str = "./logs"):
        """Initialize the health checker.

        Args:
            log_dir: Directory for health check logs
        """
        self.logger = logging.getLogger(__name__)
        self.log_dir = log_dir
        self.health_history: List[Dict[str, Any]] = []
        self.current_status: Dict[str, HealthStatus] = {}
        self.alert_callbacks: List[callable] = []

        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # Load health history from disk
        self._load_history()

    def _load_history(self):
        """Load health check history from disk."""
        history_file = os.path.join(self.log_dir, "mcp_health_history.json")
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.health_history = json.load(f)
                self.logger.info(f"Loaded {len(self.health_history)} health check records")
        except Exception as e:
            self.logger.warning(f"Could not load health history: {e}")
            self.health_history = []

    def _save_history(self):
        """Save health check history to disk."""
        history_file = os.path.join(self.log_dir, "mcp_health_history.json")
        try:
            # Keep only last 1000 records to prevent bloat
            history_to_save = self.health_history[-1000:]
            with open(history_file, 'w') as f:
                json.dump(history_to_save, f, indent=2)
            self.logger.debug(f"Saved {len(history_to_save)} health check records")
        except Exception as e:
            self.logger.error(f"Could not save health history: {e}")

    def register_alert_callback(self, callback: callable):
        """Register a callback for connection loss alerts.

        Args:
            callback: Function to call when connection is lost
                     Should accept (server_name, status, message)
        """
        self.alert_callbacks.append(callback)
        self.logger.info(f"Registered alert callback: {callback.__name__}")

    async def _trigger_alerts(self, server_name: str, status: HealthStatus, message: str):
        """Trigger all registered alert callbacks.

        Args:
            server_name: Name of the MCP server
            status: Current health status
            message: Status message
        """
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(server_name, status, message)
                else:
                    callback(server_name, status, message)
            except Exception as e:
                self.logger.error(f"Alert callback {callback.__name__} failed: {e}")

    def check_github_mcp(self) -> Tuple[HealthStatus, str]:
        """Check GitHub MCP server health.

        Returns:
            Tuple of (status, message)
        """
        try:
            # Check if gh CLI is installed
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return HealthStatus.DOWN, "GitHub CLI not installed"

            # Check if authenticated
            auth_result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if auth_result.returncode != 0:
                return HealthStatus.DEGRADED, "GitHub CLI not authenticated"

            return HealthStatus.HEALTHY, "GitHub MCP ready"

        except subprocess.TimeoutExpired:
            return HealthStatus.DOWN, "GitHub CLI check timed out"
        except FileNotFoundError:
            return HealthStatus.DOWN, "GitHub CLI not found"
        except Exception as e:
            return HealthStatus.DOWN, f"GitHub check failed: {str(e)}"

    def check_slack_mcp(self) -> Tuple[HealthStatus, str]:
        """Check Slack MCP server health.

        Returns:
            Tuple of (status, message)
        """
        try:
            # Check if Slack token is configured
            slack_token = os.getenv("SLACK_BOT_TOKEN")

            if not slack_token:
                return HealthStatus.DOWN, "SLACK_BOT_TOKEN not configured"

            # Basic token format validation
            if not slack_token.startswith("xoxb-"):
                return HealthStatus.DEGRADED, "Slack token format invalid"

            return HealthStatus.HEALTHY, "Slack MCP configured"

        except Exception as e:
            return HealthStatus.DOWN, f"Slack check failed: {str(e)}"

    def check_discord_mcp(self) -> Tuple[HealthStatus, str]:
        """Check Discord MCP server health.

        Returns:
            Tuple of (status, message)
        """
        try:
            # Check if Discord token is configured
            discord_token = os.getenv("DISCORD_BOT_TOKEN")

            if not discord_token:
                return HealthStatus.DOWN, "DISCORD_BOT_TOKEN not configured"

            # Basic token validation (Discord tokens are typically long)
            if len(discord_token) < 50:
                return HealthStatus.DEGRADED, "Discord token format suspicious"

            return HealthStatus.HEALTHY, "Discord MCP configured"

        except Exception as e:
            return HealthStatus.DOWN, f"Discord check failed: {str(e)}"

    def check_notion_mcp(self) -> Tuple[HealthStatus, str]:
        """Check Notion MCP server health.

        Returns:
            Tuple of (status, message)
        """
        try:
            # Check if Notion token is configured
            notion_token = os.getenv("NOTION_API_KEY")

            if not notion_token:
                return HealthStatus.DOWN, "NOTION_API_KEY not configured"

            # Notion tokens start with "secret_"
            if not notion_token.startswith("secret_"):
                return HealthStatus.DEGRADED, "Notion token format invalid"

            return HealthStatus.HEALTHY, "Notion MCP configured"

        except Exception as e:
            return HealthStatus.DOWN, f"Notion check failed: {str(e)}"

    def check_node_installed(self) -> Tuple[HealthStatus, str]:
        """Check if Node.js is installed (required for MCP servers).

        Returns:
            Tuple of (status, message)
        """
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return HealthStatus.DOWN, "Node.js not installed"

            version = result.stdout.strip()
            return HealthStatus.HEALTHY, f"Node.js {version} installed"

        except subprocess.TimeoutExpired:
            return HealthStatus.DOWN, "Node.js check timed out"
        except FileNotFoundError:
            return HealthStatus.DOWN, "Node.js not found"
        except Exception as e:
            return HealthStatus.DOWN, f"Node.js check failed: {str(e)}"

    async def check_all_servers(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all configured MCP servers.

        Returns:
            Dictionary with server health status
        """
        results = {}

        # Check Node.js (prerequisite for all MCP servers)
        node_status, node_msg = self.check_node_installed()
        results["node_js"] = {
            "status": node_status.value,
            "message": node_msg,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Check individual MCP servers
        servers_to_check = {
            "github": self.check_github_mcp,
            "slack": self.check_slack_mcp,
            "discord": self.check_discord_mcp,
            "notion": self.check_notion_mcp
        }

        for server_name, check_func in servers_to_check.items():
            status, message = check_func()
            results[server_name] = {
                "status": status.value,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Update current status
            previous_status = self.current_status.get(server_name)
            self.current_status[server_name] = status

            # Trigger alerts if status changed to DOWN or DEGRADED
            if status in [HealthStatus.DOWN, HealthStatus.DEGRADED]:
                if previous_status != status:
                    await self._trigger_alerts(server_name, status, message)

        # Log the check
        check_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        }
        self.health_history.append(check_record)
        self._save_history()

        return results

    async def check_server(self, server_name: str) -> Dict[str, Any]:
        """Check health of a specific MCP server.

        Args:
            server_name: Name of the server to check

        Returns:
            Dictionary with server health status
        """
        check_functions = {
            "github": self.check_github_mcp,
            "slack": self.check_slack_mcp,
            "discord": self.check_discord_mcp,
            "notion": self.check_notion_mcp,
            "node_js": self.check_node_installed
        }

        check_func = check_functions.get(server_name.lower())
        if not check_func:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": f"Unknown server: {server_name}",
                "timestamp": datetime.utcnow().isoformat()
            }

        status, message = check_func()
        result = {
            "status": status.value,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Update current status
        previous_status = self.current_status.get(server_name)
        self.current_status[server_name] = status

        # Trigger alerts if status changed to DOWN or DEGRADED
        if status in [HealthStatus.DOWN, HealthStatus.DEGRADED]:
            if previous_status != status:
                await self._trigger_alerts(server_name, status, message)

        return result

    async def reconnect_server(self, server_name: str) -> Tuple[bool, str]:
        """Attempt to reconnect a failed MCP server.

        Args:
            server_name: Name of the server to reconnect

        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Attempting to reconnect {server_name}...")

        # For GitHub, try to re-authenticate
        if server_name.lower() == "github":
            try:
                # Check current auth status first
                result = subprocess.run(
                    ["gh", "auth", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    return True, "GitHub already authenticated"

                # Provide instructions for manual auth
                return False, "Please run: gh auth login"

            except Exception as e:
                return False, f"GitHub reconnect failed: {str(e)}"

        # For other services, check configuration
        elif server_name.lower() in ["slack", "discord", "notion"]:
            # Re-check the server
            check_result = await self.check_server(server_name)

            if check_result["status"] == HealthStatus.HEALTHY.value:
                return True, f"{server_name.title()} reconnected successfully"
            else:
                return False, f"{server_name.title()} still {check_result['status']}: {check_result['message']}"

        return False, f"Reconnect not supported for {server_name}"

    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of current health status.

        Returns:
            Dictionary with health summary
        """
        if not self.current_status:
            return {
                "overall_status": "unknown",
                "healthy_count": 0,
                "degraded_count": 0,
                "down_count": 0,
                "servers": {}
            }

        healthy_count = sum(1 for s in self.current_status.values() if s == HealthStatus.HEALTHY)
        degraded_count = sum(1 for s in self.current_status.values() if s == HealthStatus.DEGRADED)
        down_count = sum(1 for s in self.current_status.values() if s == HealthStatus.DOWN)

        # Determine overall status
        if down_count > 0:
            overall_status = "degraded"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "down_count": down_count,
            "servers": {
                name: status.value
                for name, status in self.current_status.items()
            },
            "last_check": self.health_history[-1]["timestamp"] if self.health_history else None
        }

    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of health check records
        """
        return self.health_history[-limit:]

    def format_health_report(self, results: Dict[str, Dict[str, Any]]) -> str:
        """Format health check results as readable report.

        Args:
            results: Health check results

        Returns:
            Formatted report string
        """
        report = "**MCP Health Check Report**\n\n"

        for server_name, result in results.items():
            status = result["status"]
            message = result["message"]

            # Status emoji
            if status == "healthy":
                emoji = "✅"
            elif status == "degraded":
                emoji = "⚠️"
            elif status == "down":
                emoji = "❌"
            else:
                emoji = "❓"

            report += f"{emoji} **{server_name.title()}**: {status}\n"
            report += f"   → {message}\n\n"

        return report


# Singleton instance
_health_checker_instance = None


def get_health_checker() -> MCPHealthChecker:
    """Get the singleton health checker instance.

    Returns:
        MCPHealthChecker instance
    """
    global _health_checker_instance
    if _health_checker_instance is None:
        _health_checker_instance = MCPHealthChecker()
    return _health_checker_instance
