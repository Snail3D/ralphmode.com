#!/usr/bin/env python3
"""
Quarterly Access Review Automation

Generates access review reports for SOC 2 compliance (AC-004).
Reviews user access rights across all systems and flags anomalies.

Usage:
    python quarterly_access_review.py --report          # Generate review report
    python quarterly_access_review.py --remediate       # Apply approved remediations

Example:
    python quarterly_access_review.py --report > access_review_$(date +%Y%m%d).json
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set
import pwd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent


class AccessReviewer:
    """Performs quarterly access reviews"""

    def __init__(self):
        self.today = datetime.now()
        self.quarter = f"{self.today.year}-Q{(self.today.month-1)//3 + 1}"
        self.findings = []
        self.users_reviewed = 0

    def generate_report(self) -> Dict:
        """Generate comprehensive access review report"""
        logger.info(f"Generating access review report for {self.quarter}...")

        report = {
            "report_date": self.today.isoformat(),
            "quarter": self.quarter,
            "reviewer": os.getenv("USER", "automated"),
            "scope": [
                "System user accounts",
                "SSH access",
                "Database access",
                "Application admin roles",
                "API keys and service accounts"
            ],
            "reviews": []
        }

        # Review each access category
        report["reviews"].append(self.review_system_users())
        report["reviews"].append(self.review_ssh_access())
        report["reviews"].append(self.review_database_access())
        report["reviews"].append(self.review_admin_roles())
        report["reviews"].append(self.review_api_keys())

        # Summary
        report["summary"] = {
            "users_reviewed": self.users_reviewed,
            "findings": len(self.findings),
            "critical_findings": len([f for f in self.findings if f.get("severity") == "critical"]),
            "high_findings": len([f for f in self.findings if f.get("severity") == "high"]),
            "medium_findings": len([f for f in self.findings if f.get("severity") == "medium"]),
            "low_findings": len([f for f in self.findings if f.get("severity") == "low"]),
        }

        report["findings"] = self.findings
        report["recommendations"] = self.generate_recommendations()

        return report

    def review_system_users(self) -> Dict:
        """Review system user accounts"""
        logger.info("Reviewing system user accounts...")

        review = {
            "category": "System User Accounts",
            "review_date": self.today.isoformat(),
            "users": [],
            "findings": []
        }

        try:
            # Get all users with UID >= 1000 (actual users, not system accounts)
            result = subprocess.run(
                ["awk", "-F:", "$3 >= 1000 {print $1, $3, $6, $7}", "/etc/passwd"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 4:
                            username = parts[0]
                            uid = parts[1]
                            home = parts[2]
                            shell = parts[3]

                            user_info = {
                                "username": username,
                                "uid": uid,
                                "home_directory": home,
                                "shell": shell,
                                "status": "active" if shell != "/usr/sbin/nologin" else "disabled"
                            }

                            review["users"].append(user_info)
                            self.users_reviewed += 1

                            # Check for anomalies
                            if shell not in ["/bin/bash", "/bin/sh", "/usr/sbin/nologin", "/bin/zsh"]:
                                self.add_finding(
                                    category="System Users",
                                    severity="medium",
                                    description=f"User {username} has unusual shell: {shell}",
                                    recommendation="Verify if custom shell is required",
                                    user=username
                                )

        except Exception as e:
            logger.error(f"Error reviewing system users: {e}")

        review["total_users"] = len(review["users"])
        review["active_users"] = len([u for u in review["users"] if u["status"] == "active"])

        return review

    def review_ssh_access(self) -> Dict:
        """Review SSH access configuration"""
        logger.info("Reviewing SSH access...")

        review = {
            "category": "SSH Access",
            "review_date": self.today.isoformat(),
            "authorized_keys": [],
            "findings": []
        }

        # Check for authorized_keys files
        try:
            home_dirs = Path("/home").glob("*")

            for home_dir in home_dirs:
                authorized_keys = home_dir / ".ssh" / "authorized_keys"

                if authorized_keys.exists():
                    with open(authorized_keys, 'r') as f:
                        keys = f.readlines()

                    review["authorized_keys"].append({
                        "user": home_dir.name,
                        "key_count": len([k for k in keys if k.strip() and not k.startswith('#')]),
                        "file_path": str(authorized_keys)
                    })

                    self.users_reviewed += 1

                    # Check file permissions
                    stat = authorized_keys.stat()
                    mode = oct(stat.st_mode)[-3:]

                    if mode != "600":
                        self.add_finding(
                            category="SSH Access",
                            severity="high",
                            description=f"authorized_keys for {home_dir.name} has incorrect permissions: {mode}",
                            recommendation="Change permissions to 600 (chmod 600)",
                            user=home_dir.name
                        )

        except Exception as e:
            logger.error(f"Error reviewing SSH access: {e}")

        # Check root SSH access
        root_keys = Path("/root/.ssh/authorized_keys")
        if root_keys.exists():
            review["root_ssh_enabled"] = True

            self.add_finding(
                category="SSH Access",
                severity="medium",
                description="Root SSH access is enabled",
                recommendation="Consider disabling root SSH and using sudo instead",
                user="root"
            )
        else:
            review["root_ssh_enabled"] = False

        return review

    def review_database_access(self) -> Dict:
        """Review database access rights"""
        logger.info("Reviewing database access...")

        review = {
            "category": "Database Access",
            "review_date": self.today.isoformat(),
            "users": [],
            "findings": []
        }

        # In production, this would query actual database
        # For now, document expected access

        expected_users = [
            {
                "username": "ralph_app",
                "role": "Application",
                "grants": ["SELECT", "INSERT", "UPDATE", "DELETE on ralph_db"],
                "justification": "Application database operations",
                "status": "approved"
            },
            {
                "username": "ralph_readonly",
                "role": "Analytics",
                "grants": ["SELECT on ralph_db"],
                "justification": "Read-only analytics queries",
                "status": "approved"
            },
            {
                "username": "admin",
                "role": "DBA",
                "grants": ["ALL PRIVILEGES"],
                "justification": "Database administration",
                "status": "approved"
            }
        ]

        review["users"] = expected_users
        review["total_users"] = len(expected_users)

        # Check for principle of least privilege
        for user in expected_users:
            if "ALL PRIVILEGES" in user["grants"]:
                self.add_finding(
                    category="Database Access",
                    severity="low",
                    description=f"User {user['username']} has ALL PRIVILEGES",
                    recommendation="Review if all privileges are necessary",
                    user=user["username"]
                )

        return review

    def review_admin_roles(self) -> Dict:
        """Review application admin roles"""
        logger.info("Reviewing application admin roles...")

        review = {
            "category": "Application Admin Roles",
            "review_date": self.today.isoformat(),
            "admins": [],
            "findings": []
        }

        # In production, this would query the application database
        # For now, document expected admins

        expected_admins = [
            {
                "user_id": "admin1",
                "email": "admin1@ralphmode.com",
                "role": "Super Admin",
                "permissions": ["user_management", "system_config", "analytics"],
                "last_login": "2026-01-10",
                "mfa_enabled": True,
                "status": "active"
            }
        ]

        review["admins"] = expected_admins
        review["total_admins"] = len(expected_admins)

        # Check for MFA
        for admin in expected_admins:
            if not admin.get("mfa_enabled"):
                self.add_finding(
                    category="Admin Roles",
                    severity="critical",
                    description=f"Admin {admin['user_id']} does not have MFA enabled",
                    recommendation="Require MFA for all admin accounts immediately",
                    user=admin["user_id"]
                )

        return review

    def review_api_keys(self) -> Dict:
        """Review API keys and service accounts"""
        logger.info("Reviewing API keys...")

        review = {
            "category": "API Keys & Service Accounts",
            "review_date": self.today.isoformat(),
            "keys": [],
            "findings": []
        }

        # Check .env file for API keys
        env_file = PROJECT_ROOT / ".env"

        if env_file.exists():
            # Check file permissions
            stat = env_file.stat()
            mode = oct(stat.st_mode)[-3:]

            if mode != "600":
                self.add_finding(
                    category="API Keys",
                    severity="critical",
                    description=f".env file has incorrect permissions: {mode}",
                    recommendation="Change permissions to 600 immediately (chmod 600 .env)",
                    user="system"
                )

            # Parse .env to count keys (don't log actual keys!)
            with open(env_file, 'r') as f:
                lines = f.readlines()

            api_keys = [line for line in lines if '=' in line and not line.strip().startswith('#')]

            review["keys"] = [
                {
                    "key_name": line.split('=')[0].strip(),
                    "purpose": "Application configuration",
                    "rotation_required": "Every 90 days"
                }
                for line in api_keys
            ]

            review["total_keys"] = len(api_keys)

            # Reminder to rotate keys
            self.add_finding(
                category="API Keys",
                severity="low",
                description="API keys should be rotated quarterly",
                recommendation="Schedule key rotation for next quarter",
                user="system"
            )

        else:
            review["total_keys"] = 0

        return review

    def add_finding(self, category: str, severity: str, description: str, recommendation: str, user: str):
        """Add a finding to the report"""
        self.findings.append({
            "category": category,
            "severity": severity,
            "description": description,
            "recommendation": recommendation,
            "user": user,
            "found_date": self.today.isoformat()
        })

    def generate_recommendations(self) -> List[Dict]:
        """Generate prioritized recommendations"""
        recommendations = []

        # Critical findings first
        critical = [f for f in self.findings if f["severity"] == "critical"]
        if critical:
            recommendations.append({
                "priority": "Critical",
                "action": "Immediate remediation required",
                "findings_count": len(critical),
                "deadline": (self.today + timedelta(days=1)).strftime("%Y-%m-%d")
            })

        # High findings
        high = [f for f in self.findings if f["severity"] == "high"]
        if high:
            recommendations.append({
                "priority": "High",
                "action": "Remediate within 7 days",
                "findings_count": len(high),
                "deadline": (self.today + timedelta(days=7)).strftime("%Y-%m-%d")
            })

        # Medium findings
        medium = [f for f in self.findings if f["severity"] == "medium"]
        if medium:
            recommendations.append({
                "priority": "Medium",
                "action": "Remediate within 30 days",
                "findings_count": len(medium),
                "deadline": (self.today + timedelta(days=30)).strftime("%Y-%m-%d")
            })

        # Low findings
        low = [f for f in self.findings if f["severity"] == "low"]
        if low:
            recommendations.append({
                "priority": "Low",
                "action": "Remediate within next quarter",
                "findings_count": len(low),
                "deadline": f"{self.today.year}-Q{((self.today.month-1)//3 + 2) % 4}"
            })

        return recommendations


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Quarterly Access Review")
    parser.add_argument("--report", action="store_true", help="Generate access review report")
    parser.add_argument("--remediate", action="store_true", help="Apply approved remediations")

    args = parser.parse_args()

    reviewer = AccessReviewer()

    if args.report:
        report = reviewer.generate_report()
        print(json.dumps(report, indent=2))

    elif args.remediate:
        logger.info("Remediation functionality not yet implemented")
        logger.info("Remediations should be reviewed and applied manually for safety")
        sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
