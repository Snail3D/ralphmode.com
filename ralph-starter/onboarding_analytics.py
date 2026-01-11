#!/usr/bin/env python3
"""
Onboarding Analytics - OB-048

Track where users get stuck during onboarding. Improve based on data.
Privacy-respecting (anonymized) analytics for admin review.

Features:
- Track time spent on each step
- Record abandonment points
- Log errors encountered
- Admin dashboard for review
- Privacy-respecting (hashed user IDs)
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class OnboardingAnalytics:
    """Track onboarding progress and issues for improvement."""

    def __init__(self, data_dir: str = "data/analytics"):
        """Initialize analytics tracker.

        Args:
            data_dir: Directory to store analytics data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.sessions_file = self.data_dir / "onboarding_sessions.jsonl"
        self.events_file = self.data_dir / "onboarding_events.jsonl"
        self.errors_file = self.data_dir / "onboarding_errors.jsonl"

        # Ensure files exist
        for file in [self.sessions_file, self.events_file, self.errors_file]:
            if not file.exists():
                file.touch()

    def _hash_user_id(self, user_id: int) -> str:
        """Hash user ID for privacy.

        Args:
            user_id: Telegram user ID

        Returns:
            Hashed user ID (first 12 chars of SHA256)
        """
        hash_obj = hashlib.sha256(str(user_id).encode())
        return hash_obj.hexdigest()[:12]

    def start_session(self, user_id: int, setup_type: str = "guided") -> str:
        """Start tracking a new onboarding session.

        Args:
            user_id: Telegram user ID
            setup_type: Type of setup (guided or quick)

        Returns:
            Session ID
        """
        hashed_id = self._hash_user_id(user_id)
        session_id = f"{hashed_id}_{int(datetime.now().timestamp())}"

        session_data = {
            "session_id": session_id,
            "user_id_hash": hashed_id,
            "setup_type": setup_type,
            "start_time": datetime.now().isoformat(),
            "status": "active"
        }

        self._append_to_file(self.sessions_file, session_data)
        logger.info(f"Started onboarding session: {session_id}")
        return session_id

    def track_step_start(self, session_id: str, step_name: str, step_data: Optional[Dict] = None):
        """Track when a user starts a step.

        Args:
            session_id: Session identifier
            step_name: Name of the step (e.g., "ssh_key_generation")
            step_data: Optional additional data about the step
        """
        event_data = {
            "session_id": session_id,
            "event_type": "step_start",
            "step_name": step_name,
            "timestamp": datetime.now().isoformat(),
            "step_data": step_data or {}
        }

        self._append_to_file(self.events_file, event_data)
        logger.debug(f"Step started: {step_name} in session {session_id}")

    def track_step_complete(self, session_id: str, step_name: str, duration_seconds: Optional[float] = None):
        """Track when a user completes a step.

        Args:
            session_id: Session identifier
            step_name: Name of the step
            duration_seconds: Optional time spent on step
        """
        event_data = {
            "session_id": session_id,
            "event_type": "step_complete",
            "step_name": step_name,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration_seconds
        }

        self._append_to_file(self.events_file, event_data)
        logger.debug(f"Step completed: {step_name} in session {session_id}")

    def track_error(self, session_id: str, step_name: str, error_type: str, error_message: str,
                   error_data: Optional[Dict] = None):
        """Track an error encountered during onboarding.

        Args:
            session_id: Session identifier
            step_name: Step where error occurred
            error_type: Type of error (e.g., "api_validation", "git_error")
            error_message: Human-readable error message
            error_data: Optional additional error context
        """
        error_data_entry = {
            "session_id": session_id,
            "step_name": step_name,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            "error_data": error_data or {}
        }

        self._append_to_file(self.errors_file, error_data_entry)
        logger.warning(f"Error in session {session_id} at {step_name}: {error_type} - {error_message}")

    def track_abandonment(self, session_id: str, last_step: str):
        """Track when a user abandons the onboarding process.

        Args:
            session_id: Session identifier
            last_step: Last step the user was on
        """
        event_data = {
            "session_id": session_id,
            "event_type": "abandoned",
            "last_step": last_step,
            "timestamp": datetime.now().isoformat()
        }

        self._append_to_file(self.events_file, event_data)
        logger.info(f"Session abandoned at {last_step}: {session_id}")

    def complete_session(self, session_id: str, success: bool = True):
        """Mark a session as complete.

        Args:
            session_id: Session identifier
            success: Whether onboarding completed successfully
        """
        event_data = {
            "session_id": session_id,
            "event_type": "session_complete",
            "success": success,
            "timestamp": datetime.now().isoformat()
        }

        self._append_to_file(self.events_file, event_data)
        logger.info(f"Session {'completed' if success else 'failed'}: {session_id}")

    def get_analytics_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary analytics for the admin dashboard.

        Args:
            days: Number of days to include in summary

        Returns:
            Dictionary with analytics summary
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Load all data
        sessions = self._load_recent_data(self.sessions_file, cutoff_date)
        events = self._load_recent_data(self.events_file, cutoff_date)
        errors = self._load_recent_data(self.errors_file, cutoff_date)

        # Calculate metrics
        total_sessions = len(sessions)
        completed_sessions = len([e for e in events if e.get("event_type") == "session_complete" and e.get("success")])
        abandoned_sessions = len([e for e in events if e.get("event_type") == "abandoned"])

        # Calculate step metrics
        step_stats = self._calculate_step_stats(events)

        # Calculate error stats
        error_stats = self._calculate_error_stats(errors)

        # Calculate abandonment points
        abandonment_points = self._calculate_abandonment_points(events)

        summary = {
            "period_days": days,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "abandoned_sessions": abandoned_sessions,
            "completion_rate": round(completed_sessions / total_sessions * 100, 1) if total_sessions > 0 else 0,
            "step_statistics": step_stats,
            "error_statistics": error_stats,
            "abandonment_points": abandonment_points,
            "generated_at": datetime.now().isoformat()
        }

        return summary

    def get_step_funnel(self) -> List[Dict[str, Any]]:
        """Get funnel visualization data showing drop-off at each step.

        Returns:
            List of step funnel data
        """
        events = self._load_all_data(self.events_file)

        # Count users at each step
        step_counts = {}
        for event in events:
            if event.get("event_type") == "step_start":
                step_name = event.get("step_name")
                step_counts[step_name] = step_counts.get(step_name, 0) + 1

        # Sort by typical onboarding order
        step_order = [
            "welcome",
            "ssh_key_generation",
            "ssh_key_addition",
            "repo_creation",
            "git_config",
            "anthropic_api_key",
            "telegram_bot_creation",
            "env_file_creation",
            "groq_api_key",
            "weather_api_key",
            "verification"
        ]

        funnel = []
        for step in step_order:
            if step in step_counts:
                funnel.append({
                    "step": step,
                    "count": step_counts[step]
                })

        return funnel

    def get_dashboard_html(self) -> str:
        """Generate HTML dashboard for admin review.

        Returns:
            HTML string with analytics dashboard
        """
        summary = self.get_analytics_summary(days=30)
        funnel = self.get_step_funnel()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Onboarding Analytics Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #2196F3;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f5f5f5;
            font-weight: 600;
        }}
        .progress-bar {{
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Onboarding Analytics Dashboard</h1>
            <p>Generated: {summary['generated_at']}</p>
            <p>Period: Last {summary['period_days']} days</p>
        </div>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{summary['total_sessions']}</div>
                <div class="metric-label">Total Sessions</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary['completed_sessions']}</div>
                <div class="metric-label">Completed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary['abandoned_sessions']}</div>
                <div class="metric-label">Abandoned</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary['completion_rate']}%</div>
                <div class="metric-label">Completion Rate</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📉 Conversion Funnel</div>
            <table>
                <thead>
                    <tr>
                        <th>Step</th>
                        <th>Users</th>
                        <th>Progress</th>
                    </tr>
                </thead>
                <tbody>
        """

        max_count = max([s['count'] for s in funnel]) if funnel else 1
        for step_data in funnel:
            step_name = step_data['step'].replace('_', ' ').title()
            count = step_data['count']
            percentage = (count / max_count * 100) if max_count > 0 else 0

            html += f"""
                    <tr>
                        <td>{step_name}</td>
                        <td>{count}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {percentage}%"></div>
                            </div>
                        </td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="section-title">⚠️ Common Abandonment Points</div>
            <table>
                <thead>
                    <tr>
                        <th>Step</th>
                        <th>Abandonments</th>
                    </tr>
                </thead>
                <tbody>
        """

        for step, count in sorted(summary['abandonment_points'].items(), key=lambda x: x[1], reverse=True)[:10]:
            step_name = step.replace('_', ' ').title()
            html += f"""
                    <tr>
                        <td>{step_name}</td>
                        <td>{count}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="section-title">🐛 Error Statistics</div>
            <table>
                <thead>
                    <tr>
                        <th>Error Type</th>
                        <th>Count</th>
                        <th>Affected Steps</th>
                    </tr>
                </thead>
                <tbody>
        """

        for error_type, data in sorted(summary['error_statistics'].items(), key=lambda x: x[1]['count'], reverse=True):
            html += f"""
                    <tr>
                        <td>{error_type}</td>
                        <td>{data['count']}</td>
                        <td>{', '.join(data.get('steps', []))}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
        """

        return html

    def _append_to_file(self, file_path: Path, data: Dict):
        """Append JSON data to a JSONL file.

        Args:
            file_path: Path to JSONL file
            data: Data to append
        """
        try:
            with open(file_path, 'a') as f:
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            logger.error(f"Failed to append to {file_path}: {e}")

    def _load_recent_data(self, file_path: Path, cutoff_date: datetime) -> List[Dict]:
        """Load data from JSONL file after cutoff date.

        Args:
            file_path: Path to JSONL file
            cutoff_date: Only load data after this date

        Returns:
            List of data entries
        """
        data = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(entry.get('timestamp', entry.get('start_time', '')))
                        if timestamp >= cutoff_date:
                            data.append(entry)
        except Exception as e:
            logger.error(f"Failed to load data from {file_path}: {e}")

        return data

    def _load_all_data(self, file_path: Path) -> List[Dict]:
        """Load all data from JSONL file.

        Args:
            file_path: Path to JSONL file

        Returns:
            List of all data entries
        """
        data = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to load all data from {file_path}: {e}")

        return data

    def _calculate_step_stats(self, events: List[Dict]) -> Dict[str, Dict]:
        """Calculate statistics per step.

        Args:
            events: List of event entries

        Returns:
            Dictionary of step statistics
        """
        stats = {}

        for event in events:
            if event.get('event_type') in ['step_start', 'step_complete']:
                step_name = event.get('step_name')
                if step_name not in stats:
                    stats[step_name] = {
                        'starts': 0,
                        'completions': 0,
                        'total_duration': 0,
                        'count_with_duration': 0
                    }

                if event.get('event_type') == 'step_start':
                    stats[step_name]['starts'] += 1
                elif event.get('event_type') == 'step_complete':
                    stats[step_name]['completions'] += 1
                    if event.get('duration_seconds'):
                        stats[step_name]['total_duration'] += event['duration_seconds']
                        stats[step_name]['count_with_duration'] += 1

        # Calculate averages
        for step_name in stats:
            if stats[step_name]['count_with_duration'] > 0:
                stats[step_name]['avg_duration'] = round(
                    stats[step_name]['total_duration'] / stats[step_name]['count_with_duration'],
                    1
                )
            stats[step_name]['completion_rate'] = round(
                stats[step_name]['completions'] / stats[step_name]['starts'] * 100,
                1
            ) if stats[step_name]['starts'] > 0 else 0

        return stats

    def _calculate_error_stats(self, errors: List[Dict]) -> Dict[str, Dict]:
        """Calculate error statistics.

        Args:
            errors: List of error entries

        Returns:
            Dictionary of error statistics
        """
        stats = {}

        for error in errors:
            error_type = error.get('error_type', 'unknown')
            step_name = error.get('step_name', 'unknown')

            if error_type not in stats:
                stats[error_type] = {
                    'count': 0,
                    'steps': set()
                }

            stats[error_type]['count'] += 1
            stats[error_type]['steps'].add(step_name)

        # Convert sets to lists for JSON serialization
        for error_type in stats:
            stats[error_type]['steps'] = list(stats[error_type]['steps'])

        return stats

    def _calculate_abandonment_points(self, events: List[Dict]) -> Dict[str, int]:
        """Calculate where users abandon onboarding.

        Args:
            events: List of event entries

        Returns:
            Dictionary mapping step names to abandonment counts
        """
        abandonments = {}

        for event in events:
            if event.get('event_type') == 'abandoned':
                last_step = event.get('last_step', 'unknown')
                abandonments[last_step] = abandonments.get(last_step, 0) + 1

        return abandonments


# Singleton instance
_analytics_instance = None


def get_analytics() -> OnboardingAnalytics:
    """Get singleton analytics instance.

    Returns:
        OnboardingAnalytics instance
    """
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = OnboardingAnalytics()
    return _analytics_instance


if __name__ == "__main__":
    # Demo usage
    analytics = get_analytics()

    # Simulate a session
    session_id = analytics.start_session(user_id=12345, setup_type="guided")
    analytics.track_step_start(session_id, "ssh_key_generation")
    analytics.track_step_complete(session_id, "ssh_key_generation", duration_seconds=45.2)
    analytics.track_step_start(session_id, "ssh_key_addition")
    analytics.track_error(session_id, "ssh_key_addition", "connection_error", "Failed to connect to GitHub")
    analytics.track_abandonment(session_id, "ssh_key_addition")

    # Get summary
    summary = analytics.get_analytics_summary(days=7)
    print(json.dumps(summary, indent=2))

    # Generate dashboard
    dashboard_html = analytics.get_dashboard_html()
    output_path = Path("data/analytics/dashboard.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(dashboard_html)
    print(f"\nDashboard saved to: {output_path}")
