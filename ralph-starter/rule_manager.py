"""
Rule Change Deliberation Process (HR-002)

This module enforces the rule change process outlined in FOUNDATION/HARDCORE_RULES.md.
Before any rule can be changed, it must go through a deliberate process:
1. Review git history
2. Foundational check
3. Impact analysis
4. Deliberation

Only Mr. Worms (the user) can approve rule changes.
"""

import subprocess
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class RuleChangeDeliberationProcess:
    """
    Enforces the deliberation process for changing HARDCORE_RULES.

    This is a SAFETY mechanism. Rules define WHO WE ARE.
    Changes require deep thought, not quick edits.
    """

    def __init__(self, rules_file_path: str = "FOUNDATION/HARDCORE_RULES.md"):
        self.rules_file = Path(rules_file_path)
        if not self.rules_file.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_file_path}")

    def review_git_history(self) -> Dict[str, any]:
        """
        Step 1: Review Git History

        - When was this rule established?
        - What led to it?
        - What problems did it solve?

        Returns dict with git history information.
        """
        history = {
            "file_path": str(self.rules_file),
            "creation_date": None,
            "last_modified": None,
            "total_commits": 0,
            "recent_commits": [],
            "original_commit": None,
            "errors": []
        }

        try:
            # Get file creation date (first commit)
            result = subprocess.run(
                ["git", "log", "--reverse", "--format=%H|%ai|%an|%s", "--", str(self.rules_file)],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                history["total_commits"] = len(commits)

                # First commit (creation)
                if commits:
                    first = commits[0].split('|')
                    if len(first) >= 4:
                        history["original_commit"] = {
                            "hash": first[0][:8],
                            "date": first[1],
                            "author": first[2],
                            "message": first[3]
                        }
                        history["creation_date"] = first[1]

                # Last 5 commits
                for commit_line in commits[-5:]:
                    parts = commit_line.split('|')
                    if len(parts) >= 4:
                        history["recent_commits"].append({
                            "hash": parts[0][:8],
                            "date": parts[1],
                            "author": parts[2],
                            "message": parts[3]
                        })

                # Last modified date
                if commits:
                    last = commits[-1].split('|')
                    if len(last) >= 2:
                        history["last_modified"] = last[1]
            else:
                history["errors"].append("File not tracked in git or no commits found")

        except subprocess.TimeoutExpired:
            history["errors"].append("Git command timed out")
        except FileNotFoundError:
            history["errors"].append("Git not found in system PATH")
        except Exception as e:
            history["errors"].append(f"Error reviewing git history: {str(e)}")

        return history

    def foundational_check(self, proposed_change: str) -> Dict[str, any]:
        """
        Step 2: Foundational Check

        - Does this change align with our core identity?
        - Would the original creators recognize us after this change?
        - Are we improving the rule or abandoning a principle?

        Returns dict with foundational analysis.
        """
        check = {
            "proposed_change": proposed_change,
            "timestamp": datetime.now().isoformat(),
            "core_identity_questions": {
                "aligns_with_identity": None,  # Mr. Worms must answer
                "creators_would_recognize": None,
                "improving_not_abandoning": None
            },
            "red_flags": [],
            "considerations": []
        }

        # Analyze proposed change for red flags
        red_flag_keywords = [
            "remove", "delete", "disable", "ignore", "skip",
            "bypass", "override", "exception", "edge case"
        ]

        proposed_lower = proposed_change.lower()
        for keyword in red_flag_keywords:
            if keyword in proposed_lower:
                check["red_flags"].append(
                    f"Change mentions '{keyword}' - suggests weakening a principle"
                )

        # Add considerations
        check["considerations"].append(
            "The Ten Rules define who Ralph Mode is at its core"
        )
        check["considerations"].append(
            "Changes should strengthen principles, not weaken them"
        )
        check["considerations"].append(
            "If unsure, default to KEEPING THE RULE"
        )

        return check

    def impact_analysis(self, rule_number: int, proposed_change: str) -> Dict[str, any]:
        """
        Step 3: Impact Analysis

        - What breaks if we change this?
        - What do we lose?
        - Is the gain worth the loss?

        Returns dict with impact analysis.
        """
        analysis = {
            "rule_number": rule_number,
            "proposed_change": proposed_change,
            "timestamp": datetime.now().isoformat(),
            "potential_breaks": [],
            "potential_losses": [],
            "affected_systems": [],
            "requires_code_changes": False,
            "risk_level": "UNKNOWN"
        }

        # Map rules to affected systems
        rule_impacts = {
            1: {
                "systems": ["content_filter.py", "sanitizer.py", "personality_manager.py"],
                "breaks": ["Family-safe content filtering may need adjustment"],
                "losses": ["Clear moral boundary that guides all responses"]
            },
            2: {
                "systems": ["ralph_personality.py", "character responses"],
                "breaks": ["Ralph's core personality trait"],
                "losses": ["The innocence that makes Ralph unique"]
            },
            3: {
                "systems": ["permission_system", "command handlers", "feedback loop"],
                "breaks": ["User authority structure"],
                "losses": ["Clear hierarchy and respect for user decisions"]
            },
            4: {
                "systems": ["all features", "entertainment layer", "work validation"],
                "breaks": ["Balance between fun and function"],
                "losses": ["Core value proposition: real work, fun wrapper"]
            },
            5: {
                "systems": ["feedback responses", "personality engine", "quality checks"],
                "breaks": ["Honest communication"],
                "losses": ["Trust and authenticity"]
            },
            6: {
                "systems": ["testing", "validation", "deployment checks"],
                "breaks": ["Quality standards"],
                "losses": ["Reliability and user trust"]
            },
            7: {
                "systems": ["content_filter.py", "response generation"],
                "breaks": ["Respectful content boundaries"],
                "losses": ["Inclusive environment for all users"]
            },
            8: {
                "systems": ["reward_system", "celebration messages", "motivation"],
                "breaks": ["Authentic joy from real achievement"],
                "losses": ["Meaningful accomplishment vs empty dopamine"]
            },
            9: {
                "systems": ["session_management", "completion handlers", "retention"],
                "breaks": ["Ethical user relationship"],
                "losses": ["Trust and goodwill - users know we respect them"]
            },
            10: {
                "systems": ["tone", "messaging", "positioning"],
                "breaks": ["Humble positioning"],
                "losses": ["User autonomy and tool-service relationship"]
            }
        }

        if rule_number in rule_impacts:
            impact = rule_impacts[rule_number]
            analysis["affected_systems"] = impact["systems"]
            analysis["potential_breaks"] = impact["breaks"]
            analysis["potential_losses"] = impact["losses"]
            analysis["requires_code_changes"] = True
            analysis["risk_level"] = "HIGH"
        else:
            analysis["affected_systems"] = ["Unknown - requires manual review"]
            analysis["potential_breaks"] = ["Unknown - rule not mapped"]
            analysis["risk_level"] = "CRITICAL"

        return analysis

    def generate_deliberation_report(
        self,
        rule_number: int,
        proposed_change: str,
        requester: str = "Unknown"
    ) -> str:
        """
        Generate a comprehensive deliberation report for Mr. Worms to review.

        This report contains all information needed to make an informed decision
        about changing a HARDCORE_RULE.
        """
        # Gather all information
        git_history = self.review_git_history()
        foundational = self.foundational_check(proposed_change)
        impact = self.impact_analysis(rule_number, proposed_change)

        # Generate report
        report = []
        report.append("=" * 80)
        report.append("HARDCORE RULE CHANGE DELIBERATION REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Requested by: {requester}")
        report.append(f"Rule Number: #{rule_number}")
        report.append("")
        report.append("PROPOSED CHANGE:")
        report.append("-" * 80)
        report.append(proposed_change)
        report.append("")

        # Step 1: Git History Review
        report.append("STEP 1: GIT HISTORY REVIEW")
        report.append("-" * 80)
        if git_history["errors"]:
            report.append("⚠️  Errors during git history review:")
            for error in git_history["errors"]:
                report.append(f"  - {error}")
        else:
            if git_history["original_commit"]:
                orig = git_history["original_commit"]
                report.append(f"File created: {orig['date']}")
                report.append(f"First commit: {orig['hash']} - {orig['message']}")
                report.append(f"Author: {orig['author']}")
            report.append(f"Total commits: {git_history['total_commits']}")
            report.append(f"Last modified: {git_history['last_modified']}")
            if git_history["recent_commits"]:
                report.append("\nRecent changes:")
                for commit in git_history["recent_commits"]:
                    report.append(f"  {commit['hash']} ({commit['date'][:10]}) - {commit['message']}")
        report.append("")

        # Step 2: Foundational Check
        report.append("STEP 2: FOUNDATIONAL CHECK")
        report.append("-" * 80)
        if foundational["red_flags"]:
            report.append("🚨 RED FLAGS DETECTED:")
            for flag in foundational["red_flags"]:
                report.append(f"  - {flag}")
            report.append("")
        report.append("Questions to answer before proceeding:")
        report.append("  1. Does this change align with our core identity?")
        report.append("  2. Would the original creators recognize us after this change?")
        report.append("  3. Are we improving the rule or abandoning a principle?")
        report.append("")
        report.append("Considerations:")
        for consideration in foundational["considerations"]:
            report.append(f"  • {consideration}")
        report.append("")

        # Step 3: Impact Analysis
        report.append("STEP 3: IMPACT ANALYSIS")
        report.append("-" * 80)
        report.append(f"Risk Level: {impact['risk_level']}")
        report.append(f"Requires Code Changes: {'Yes' if impact['requires_code_changes'] else 'No'}")
        report.append("")
        report.append("Affected Systems:")
        for system in impact["affected_systems"]:
            report.append(f"  • {system}")
        report.append("")
        report.append("What Breaks:")
        for break_item in impact["potential_breaks"]:
            report.append(f"  ⚠️  {break_item}")
        report.append("")
        report.append("What We Lose:")
        for loss in impact["potential_losses"]:
            report.append(f"  💔 {loss}")
        report.append("")

        # Step 4: Deliberation Guidelines
        report.append("STEP 4: DELIBERATION GUIDELINES")
        report.append("-" * 80)
        report.append("This is NOT a quick decision.")
        report.append("")
        report.append("Process:")
        report.append("  1. Read this report carefully")
        report.append("  2. Sleep on it (minimum 24 hours)")
        report.append("  3. Discuss with team if applicable")
        report.append("  4. If still unsure: KEEP THE RULE")
        report.append("")
        report.append("Remember:")
        report.append("  • These rules define WHO WE ARE")
        report.append("  • Without them, we're just another AI wrapper")
        report.append("  • Crack the foundation, the building falls")
        report.append("")

        # Decision Section
        report.append("=" * 80)
        report.append("DECISION (To be filled out by Mr. Worms)")
        report.append("=" * 80)
        report.append("")
        report.append("[ ] APPROVED - Change the rule")
        report.append("[ ] REJECTED - Keep the rule as-is")
        report.append("[ ] REVISED - Modify the proposed change (describe below)")
        report.append("")
        report.append("Reasoning:")
        report.append("")
        report.append("")
        report.append("")
        report.append("Signature: ___________________ Date: ___________")
        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def save_deliberation_report(self, report: str, rule_number: int) -> Path:
        """
        Save the deliberation report to a file for review.

        Returns the path to the saved report.
        """
        # Create deliberations directory if it doesn't exist
        delib_dir = Path("FOUNDATION/deliberations")
        delib_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rule_{rule_number}_deliberation_{timestamp}.txt"
        filepath = delib_dir / filename

        # Save report
        with open(filepath, 'w') as f:
            f.write(report)

        return filepath

    def initiate_rule_change_process(
        self,
        rule_number: int,
        proposed_change: str,
        requester: str = "Unknown"
    ) -> Tuple[str, Path]:
        """
        Initiate the full rule change deliberation process.

        Returns:
            - The deliberation report as a string
            - The path to the saved report file
        """
        # Generate report
        report = self.generate_deliberation_report(
            rule_number,
            proposed_change,
            requester
        )

        # Save report
        filepath = self.save_deliberation_report(report, rule_number)

        return report, filepath


# Singleton instance
_rule_manager: Optional[RuleChangeDeliberationProcess] = None


def get_rule_manager() -> RuleChangeDeliberationProcess:
    """Get the singleton RuleChangeDeliberationProcess instance."""
    global _rule_manager
    if _rule_manager is None:
        _rule_manager = RuleChangeDeliberationProcess()
    return _rule_manager


# CLI interface for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python rule_manager.py <rule_number> <proposed_change>")
        print('Example: python rule_manager.py 1 "Allow edge cases for content filtering"')
        sys.exit(1)

    rule_num = int(sys.argv[1])
    proposed = sys.argv[2]
    requester = sys.argv[3] if len(sys.argv) > 3 else "CLI User"

    manager = get_rule_manager()
    report, filepath = manager.initiate_rule_change_process(rule_num, proposed, requester)

    print(report)
    print()
    print(f"📄 Report saved to: {filepath}")
    print()
    print("⚠️  This report requires Mr. Worms' review and approval.")
    print("    No changes will be made until the decision section is completed.")
