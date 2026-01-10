#!/usr/bin/env python3
"""
SF-001: Circuit Breaker for Ralph Mode Bot

This module implements a circuit breaker pattern to prevent cascading failures
in the build orchestrator. When too many consecutive builds fail, the circuit
breaker trips and pauses the build loop until manually reset.

Features:
- Track consecutive build failures
- Trip circuit after 5+ consecutive failures
- Send admin alerts via Telegram
- Require manual /resume command to restart
- Log all failures for review
- Persist state across restarts

Usage:
    from circuit_breaker import CircuitBreaker, get_circuit_breaker

    cb = get_circuit_breaker()

    # Before starting a build
    if cb.is_tripped():
        print("Circuit breaker is tripped! Build loop paused.")
        return

    # After build failure
    cb.record_failure(feedback_id=123, reason="Build timeout")

    # After build success
    cb.record_success()

    # To resume after trip
    cb.reset()
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Tripped - rejecting all requests
    HALF_OPEN = "half_open"  # Testing if system recovered (future enhancement)


@dataclass
class CircuitBreakerState:
    """Persistent state of the circuit breaker."""
    state: str  # CircuitState value
    consecutive_failures: int
    total_failures: int
    total_successes: int
    last_failure_time: Optional[str] = None
    last_success_time: Optional[str] = None
    trip_time: Optional[str] = None
    trip_reason: Optional[str] = None
    failure_history: list = None  # Last N failures

    def __post_init__(self):
        if self.failure_history is None:
            self.failure_history = []


class CircuitBreaker:
    """
    SF-001: Circuit Breaker

    Prevents cascading failures by pausing the build loop after too many
    consecutive failures. Requires manual intervention to resume.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        state_file: Optional[str] = None
    ):
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before tripping (default: 5)
            state_file: Path to state persistence file (default: /tmp/ralph_circuit_breaker.json)
        """
        self.failure_threshold = failure_threshold

        # State file for persistence
        if state_file:
            self.state_file = Path(state_file)
        else:
            self.state_file = Path('/tmp/ralph_circuit_breaker.json')

        # Load or initialize state
        self.state = self._load_state()

        logger.info(
            f"CircuitBreaker initialized: threshold={failure_threshold}, "
            f"state={self.state.state}, consecutive_failures={self.state.consecutive_failures}"
        )

    def _load_state(self) -> CircuitBreakerState:
        """
        Load circuit breaker state from disk.

        Returns:
            CircuitBreakerState
        """
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    state = CircuitBreakerState(**data)
                    logger.info(f"Loaded circuit breaker state from {self.state_file}")
                    return state
        except Exception as e:
            logger.error(f"Error loading circuit breaker state: {e}", exc_info=True)

        # Return default state
        return CircuitBreakerState(
            state=CircuitState.CLOSED.value,
            consecutive_failures=0,
            total_failures=0,
            total_successes=0,
            failure_history=[]
        )

    def _save_state(self):
        """Save circuit breaker state to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
            logger.debug(f"Saved circuit breaker state to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving circuit breaker state: {e}", exc_info=True)

    def is_tripped(self) -> bool:
        """
        Check if circuit breaker is tripped (OPEN state).

        Returns:
            True if tripped, False otherwise
        """
        return self.state.state == CircuitState.OPEN.value

    def record_failure(self, feedback_id: Optional[int] = None, reason: str = "Unknown"):
        """
        Record a build failure.

        If consecutive failures exceed threshold, trip the circuit breaker.

        Args:
            feedback_id: Optional feedback ID that failed
            reason: Failure reason
        """
        # Increment counters
        self.state.consecutive_failures += 1
        self.state.total_failures += 1
        self.state.last_failure_time = datetime.utcnow().isoformat()

        # Add to failure history (keep last 20)
        failure_entry = {
            'timestamp': self.state.last_failure_time,
            'feedback_id': feedback_id,
            'reason': reason
        }
        self.state.failure_history.append(failure_entry)
        if len(self.state.failure_history) > 20:
            self.state.failure_history = self.state.failure_history[-20:]

        logger.warning(
            f"CircuitBreaker: Failure recorded (consecutive: {self.state.consecutive_failures}/"
            f"{self.failure_threshold}): feedback_id={feedback_id}, reason={reason}"
        )

        # Check if we should trip
        if self.state.consecutive_failures >= self.failure_threshold:
            self._trip(reason)

        self._save_state()

    def _trip(self, reason: str):
        """
        Trip the circuit breaker (transition to OPEN state).

        Args:
            reason: Reason for tripping
        """
        if self.state.state == CircuitState.OPEN.value:
            logger.warning("CircuitBreaker: Already tripped, skipping trip action")
            return

        self.state.state = CircuitState.OPEN.value
        self.state.trip_time = datetime.utcnow().isoformat()
        self.state.trip_reason = reason

        logger.error(
            f"🚨 CIRCUIT BREAKER TRIPPED! "
            f"Consecutive failures: {self.state.consecutive_failures}, "
            f"Reason: {reason}"
        )

        # Alert admin
        self._alert_admin()

        self._save_state()

    def _alert_admin(self):
        """
        SF-001: Alert admin via Telegram when circuit breaker trips.

        Sends a message to admin notifying them that the build loop is paused
        and requires manual intervention.
        """
        try:
            # Import notification service
            from notification_service import get_notification_service
            import asyncio

            # Get admin Telegram ID from environment
            admin_telegram_id = os.getenv('ADMIN_TELEGRAM_ID')

            if not admin_telegram_id:
                logger.warning("ADMIN_TELEGRAM_ID not set, cannot send alert")
                # Try webhook as fallback
                self._alert_webhook()
                return

            admin_id = int(admin_telegram_id)

            # Build alert message
            message = (
                f"🚨 *CIRCUIT BREAKER TRIPPED*\n\n"
                f"The Ralph build loop has been paused due to too many consecutive failures.\n\n"
                f"📊 *Stats:*\n"
                f"  • Consecutive failures: {self.state.consecutive_failures}\n"
                f"  • Threshold: {self.failure_threshold}\n"
                f"  • Last failure: {self.state.trip_reason}\n"
                f"  • Trip time: {self.state.trip_time}\n\n"
                f"📝 *Recent failures:*\n"
            )

            # Add last 5 failures
            recent_failures = self.state.failure_history[-5:]
            for i, failure in enumerate(reversed(recent_failures), 1):
                fb_id = failure.get('feedback_id', 'N/A')
                reason = failure.get('reason', 'Unknown')[:50]
                message += f"  {i}. FB-{fb_id}: {reason}...\n"

            message += (
                f"\n"
                f"⚠️ *Action Required:*\n"
                f"Use `/resume` command to restart the build loop after investigating.\n\n"
                f"— Ralph Circuit Breaker 🔌"
            )

            # Send notification
            ns = get_notification_service()

            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Send message
            loop.run_until_complete(
                ns.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode="Markdown"
                )
            )

            logger.info(f"Circuit breaker alert sent to admin {admin_id}")

        except Exception as e:
            logger.error(f"Error sending admin alert: {e}", exc_info=True)
            # Try webhook as fallback
            self._alert_webhook()

    def _alert_webhook(self):
        """Send alert via webhook if Telegram fails."""
        try:
            import requests

            webhook_url = os.getenv('ADMIN_ALERT_WEBHOOK')
            if not webhook_url:
                logger.warning("ADMIN_ALERT_WEBHOOK not set, cannot send webhook alert")
                return

            payload = {
                'text': (
                    f"🚨 CIRCUIT BREAKER TRIPPED\n"
                    f"Consecutive failures: {self.state.consecutive_failures}\n"
                    f"Threshold: {self.failure_threshold}\n"
                    f"Reason: {self.state.trip_reason}\n"
                    f"Time: {self.state.trip_time}"
                ),
                'state': asdict(self.state)
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Circuit breaker alert sent to webhook")

        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}", exc_info=True)

    def record_success(self):
        """
        Record a build success.

        Resets consecutive failure counter (but keeps circuit in OPEN state
        if already tripped - requires manual reset).
        """
        self.state.consecutive_failures = 0
        self.state.total_successes += 1
        self.state.last_success_time = datetime.utcnow().isoformat()

        logger.info(
            f"CircuitBreaker: Success recorded, consecutive failures reset to 0"
        )

        self._save_state()

    def reset(self, admin_id: Optional[int] = None) -> bool:
        """
        SF-001: Reset circuit breaker (transition from OPEN to CLOSED).

        This requires manual intervention and should only be called after
        investigating and fixing the root cause of failures.

        Args:
            admin_id: Optional admin user ID who performed the reset

        Returns:
            True if reset successful, False if already closed
        """
        if self.state.state != CircuitState.OPEN.value:
            logger.warning("CircuitBreaker: Cannot reset - not in OPEN state")
            return False

        logger.warning(
            f"CircuitBreaker: Manual reset by admin_id={admin_id}. "
            f"Transitioning from OPEN to CLOSED."
        )

        # Reset state
        self.state.state = CircuitState.CLOSED.value
        self.state.consecutive_failures = 0
        self.state.trip_time = None
        self.state.trip_reason = None

        self._save_state()

        # Notify admin of successful reset
        if admin_id:
            self._notify_reset(admin_id)

        return True

    def _notify_reset(self, admin_id: int):
        """
        Notify admin that circuit breaker was successfully reset.

        Args:
            admin_id: Admin Telegram ID
        """
        try:
            from notification_service import get_notification_service
            import asyncio

            message = (
                f"✅ *Circuit Breaker Reset*\n\n"
                f"The Ralph build loop has been resumed.\n\n"
                f"📊 *Previous Stats:*\n"
                f"  • Total failures: {self.state.total_failures}\n"
                f"  • Total successes: {self.state.total_successes}\n\n"
                f"The consecutive failure counter has been reset.\n"
                f"Monitoring will continue.\n\n"
                f"— Ralph Circuit Breaker 🔌"
            )

            ns = get_notification_service()

            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Send message
            loop.run_until_complete(
                ns.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode="Markdown"
                )
            )

            logger.info(f"Circuit breaker reset notification sent to admin {admin_id}")

        except Exception as e:
            logger.error(f"Error sending reset notification: {e}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current circuit breaker status.

        Returns:
            Dict with status information
        """
        return {
            'state': self.state.state,
            'is_tripped': self.is_tripped(),
            'consecutive_failures': self.state.consecutive_failures,
            'failure_threshold': self.failure_threshold,
            'total_failures': self.state.total_failures,
            'total_successes': self.state.total_successes,
            'last_failure_time': self.state.last_failure_time,
            'last_success_time': self.state.last_success_time,
            'trip_time': self.state.trip_time,
            'trip_reason': self.state.trip_reason,
            'recent_failures': self.state.failure_history[-5:] if self.state.failure_history else []
        }


# Global instance
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get or create the global circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        # Get threshold from environment or use default
        threshold = int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '5'))
        _circuit_breaker = CircuitBreaker(failure_threshold=threshold)
    return _circuit_breaker


def main():
    """Main entry point for CLI testing."""
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Mode Circuit Breaker (SF-001)')
    parser.add_argument(
        'action',
        choices=['status', 'reset', 'test-trip'],
        help='Action to perform'
    )
    parser.add_argument(
        '--admin-id',
        type=int,
        help='Admin Telegram ID (for reset)'
    )

    args = parser.parse_args()

    cb = get_circuit_breaker()

    if args.action == 'status':
        status = cb.get_status()
        print(f"\n{'='*60}")
        print(f"Circuit Breaker Status")
        print(f"{'='*60}")
        print(f"State: {status['state'].upper()}")
        print(f"Tripped: {'YES' if status['is_tripped'] else 'NO'}")
        print(f"Consecutive Failures: {status['consecutive_failures']}/{status['failure_threshold']}")
        print(f"Total Failures: {status['total_failures']}")
        print(f"Total Successes: {status['total_successes']}")

        if status['last_failure_time']:
            print(f"Last Failure: {status['last_failure_time']}")

        if status['trip_time']:
            print(f"\nTripped At: {status['trip_time']}")
            print(f"Trip Reason: {status['trip_reason']}")

        if status['recent_failures']:
            print(f"\nRecent Failures:")
            for i, failure in enumerate(reversed(status['recent_failures']), 1):
                print(f"  {i}. FB-{failure.get('feedback_id', 'N/A')}: {failure.get('reason', 'Unknown')}")

    elif args.action == 'reset':
        if cb.reset(admin_id=args.admin_id):
            print("✅ Circuit breaker reset successfully")
        else:
            print("⚠️  Circuit breaker is not tripped, nothing to reset")

    elif args.action == 'test-trip':
        print("Testing circuit breaker by simulating failures...")
        for i in range(cb.failure_threshold + 1):
            cb.record_failure(feedback_id=999, reason=f"Test failure {i+1}")
            print(f"Recorded failure {i+1}/{cb.failure_threshold}")

            if cb.is_tripped():
                print("🚨 Circuit breaker TRIPPED!")
                break


if __name__ == '__main__':
    main()
