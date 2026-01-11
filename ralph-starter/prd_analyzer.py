#!/usr/bin/env python3
"""
PRD Completeness Analyzer

Analyzes PRD quality and determines if discovery is needed.
Scores PRD from 0-100 based on task completeness, acceptance criteria quality,
file hints, and overall structure.
"""

import json
from typing import Dict, List, Tuple
from pathlib import Path


class PRDAnalyzer:
    """
    Analyzes PRD quality and provides a completeness score.

    Scoring criteria:
    - Task structure (20 points): Are tasks well-formed with all required fields?
    - Acceptance criteria (30 points): Are criteria specific, testable, and comprehensive?
    - File hints (20 points): Are files_likely_modified specified?
    - Task descriptions (15 points): Are descriptions clear and detailed?
    - Category coverage (15 points): Is work organized into logical categories?
    """

    def __init__(self, prd_path: str = "scripts/ralph/prd.json"):
        """Initialize analyzer with path to PRD file."""
        self.prd_path = Path(prd_path)
        self.prd_data = None
        self.analysis_results = {}

    def load_prd(self) -> bool:
        """Load PRD from file. Returns True if successful."""
        try:
            with open(self.prd_path, 'r') as f:
                self.prd_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading PRD: {e}")
            return False

    def analyze(self) -> Dict:
        """
        Run full analysis and return results.

        Returns:
            Dict with:
                - score (int): Overall score 0-100
                - task_structure_score (float): 0-20
                - acceptance_criteria_score (float): 0-30
                - file_hints_score (float): 0-20
                - description_score (float): 0-15
                - category_score (float): 0-15
                - issues (List[str]): List of identified issues
                - recommendations (List[str]): Recommended improvements
                - needs_discovery (bool): True if score < 70
        """
        if not self.prd_data:
            if not self.load_prd():
                return {
                    "score": 0,
                    "error": "Failed to load PRD",
                    "needs_discovery": True
                }

        tasks = self.prd_data.get("tasks", [])
        if not tasks:
            return {
                "score": 0,
                "error": "No tasks found in PRD",
                "needs_discovery": True
            }

        # Run individual analyses
        task_structure_score = self._analyze_task_structure(tasks)
        acceptance_criteria_score = self._analyze_acceptance_criteria(tasks)
        file_hints_score = self._analyze_file_hints(tasks)
        description_score = self._analyze_descriptions(tasks)
        category_score = self._analyze_categories(tasks)

        # Calculate total score
        total_score = int(
            task_structure_score +
            acceptance_criteria_score +
            file_hints_score +
            description_score +
            category_score
        )

        # Gather issues and recommendations
        issues = self._identify_issues(tasks)
        recommendations = self._generate_recommendations(total_score, issues)

        results = {
            "score": total_score,
            "task_structure_score": round(task_structure_score, 2),
            "acceptance_criteria_score": round(acceptance_criteria_score, 2),
            "file_hints_score": round(file_hints_score, 2),
            "description_score": round(description_score, 2),
            "category_score": round(category_score, 2),
            "issues": issues,
            "recommendations": recommendations,
            "needs_discovery": total_score < 70,
            "total_tasks": len(tasks),
            "incomplete_tasks": len([t for t in tasks if not t.get("passes", False)])
        }

        self.analysis_results = results
        return results

    def _analyze_task_structure(self, tasks: List[Dict]) -> float:
        """
        Analyze task structure quality (0-20 points).

        Checks:
        - All tasks have required fields (id, title, description, category)
        - IDs follow naming convention
        - No duplicate IDs
        """
        max_score = 20.0
        if not tasks:
            return 0.0

        required_fields = ["id", "title", "description", "category", "acceptance_criteria"]
        score_per_task = max_score / len(tasks)
        total_score = 0.0

        seen_ids = set()

        for task in tasks:
            task_score = score_per_task

            # Check required fields
            for field in required_fields:
                if field not in task or not task[field]:
                    task_score *= 0.8  # 20% penalty for missing field

            # Check ID format (e.g., "RM-001", "SEC-015")
            task_id = task.get("id", "")
            if not task_id or "-" not in task_id:
                task_score *= 0.9

            # Check for duplicate IDs
            if task_id in seen_ids:
                task_score *= 0.5  # Major penalty for duplicates
            seen_ids.add(task_id)

            total_score += task_score

        return min(total_score, max_score)

    def _analyze_acceptance_criteria(self, tasks: List[Dict]) -> float:
        """
        Analyze acceptance criteria quality (0-30 points).

        Checks:
        - All tasks have acceptance criteria
        - Criteria are specific (not vague like "Feature implemented")
        - Multiple criteria per task (shows thoroughness)
        - Criteria are testable
        """
        max_score = 30.0
        if not tasks:
            return 0.0

        score_per_task = max_score / len(tasks)
        total_score = 0.0

        # Vague phrases that indicate poor criteria
        vague_phrases = [
            "feature implemented",
            "working correctly",
            "integrated with",
            "properly configured",
            "should work",
            "is functional"
        ]

        for task in tasks:
            criteria = task.get("acceptance_criteria", [])

            if not criteria:
                # No criteria = 0 points for this task
                continue

            task_score = score_per_task

            # Reward multiple criteria (shows thoroughness)
            if len(criteria) >= 3:
                task_score *= 1.0
            elif len(criteria) == 2:
                task_score *= 0.8
            else:
                task_score *= 0.6

            # Check for vague criteria
            vague_count = 0
            for criterion in criteria:
                criterion_lower = criterion.lower()
                if any(phrase in criterion_lower for phrase in vague_phrases):
                    vague_count += 1

            # Penalize vague criteria
            if vague_count > 0:
                vagueness_penalty = vague_count / len(criteria)
                task_score *= (1.0 - vagueness_penalty * 0.5)

            # Reward specific, testable criteria (contains numbers, file names, etc.)
            specific_count = 0
            for criterion in criteria:
                if any(char.isdigit() for char in criterion) or ".py" in criterion or "should" in criterion.lower():
                    specific_count += 1

            if specific_count > 0:
                specificity_bonus = min(specific_count / len(criteria), 1.0)
                task_score *= (1.0 + specificity_bonus * 0.2)

            total_score += task_score

        return min(total_score, max_score)

    def _analyze_file_hints(self, tasks: List[Dict]) -> float:
        """
        Analyze file hints quality (0-20 points).

        Checks:
        - Tasks have files_likely_modified field
        - File paths are specific (not just "TBD" or empty)
        """
        max_score = 20.0
        if not tasks:
            return 0.0

        score_per_task = max_score / len(tasks)
        total_score = 0.0

        for task in tasks:
            files = task.get("files_likely_modified", [])

            if not files:
                # No file hints = 0 points for this task
                continue

            task_score = score_per_task

            # Check for placeholder values
            has_real_files = False
            for file_path in files:
                if file_path and file_path.lower() not in ["tbd", "unknown", "n/a", ""]:
                    has_real_files = True
                    break

            if not has_real_files:
                task_score *= 0.3  # Major penalty for placeholder files

            # Reward multiple file hints (shows complexity understanding)
            if len(files) >= 2:
                task_score *= 1.1

            total_score += task_score

        return min(total_score, max_score)

    def _analyze_descriptions(self, tasks: List[Dict]) -> float:
        """
        Analyze task descriptions quality (0-15 points).

        Checks:
        - Descriptions are present
        - Descriptions are detailed (> 50 chars)
        - Descriptions explain the "why", not just the "what"
        """
        max_score = 15.0
        if not tasks:
            return 0.0

        score_per_task = max_score / len(tasks)
        total_score = 0.0

        for task in tasks:
            description = task.get("description", "")

            if not description:
                continue

            task_score = score_per_task

            # Check length (detailed descriptions are better)
            if len(description) >= 100:
                task_score *= 1.0
            elif len(description) >= 50:
                task_score *= 0.8
            else:
                task_score *= 0.5

            # Look for "why" indicators (shows purpose understanding)
            why_indicators = ["because", "to ensure", "to prevent", "to improve", "to enable", "so that"]
            has_why = any(indicator in description.lower() for indicator in why_indicators)

            if has_why:
                task_score *= 1.1

            total_score += task_score

        return min(total_score, max_score)

    def _analyze_categories(self, tasks: List[Dict]) -> float:
        """
        Analyze category organization (0-15 points).

        Checks:
        - Tasks are organized into categories
        - Categories are logical and consistent
        - Not too many orphaned tasks
        """
        max_score = 15.0
        if not tasks:
            return 0.0

        categories = {}
        for task in tasks:
            cat = task.get("category", "Uncategorized")
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        total_score = max_score

        # Penalty for too many uncategorized tasks
        uncategorized_count = categories.get("Uncategorized", 0) + categories.get("", 0)
        if uncategorized_count > 0:
            uncategorized_ratio = uncategorized_count / len(tasks)
            total_score *= (1.0 - uncategorized_ratio * 0.5)

        # Reward balanced categories (not all tasks in one category)
        if len(categories) >= 3:
            total_score *= 1.0
        elif len(categories) == 2:
            total_score *= 0.8
        else:
            total_score *= 0.5

        # Penalty for categories with only 1 task (suggests poor organization)
        singleton_categories = sum(1 for count in categories.values() if count == 1)
        if singleton_categories > len(categories) * 0.3:  # More than 30% singletons
            total_score *= 0.9

        return min(total_score, max_score)

    def _identify_issues(self, tasks: List[Dict]) -> List[str]:
        """Identify specific issues in the PRD."""
        issues = []

        # Check for tasks with vague acceptance criteria
        vague_tasks = []
        for task in tasks:
            criteria = task.get("acceptance_criteria", [])
            if criteria and any("feature implemented" in c.lower() or "working" in c.lower() for c in criteria):
                vague_tasks.append(task.get("id", "Unknown"))

        if vague_tasks:
            issues.append(f"{len(vague_tasks)} tasks have vague acceptance criteria: {', '.join(vague_tasks[:5])}")

        # Check for tasks without file hints
        no_files = []
        for task in tasks:
            if not task.get("files_likely_modified"):
                no_files.append(task.get("id", "Unknown"))

        if no_files:
            issues.append(f"{len(no_files)} tasks missing file hints: {', '.join(no_files[:5])}")

        # Check for short descriptions
        short_desc = []
        for task in tasks:
            desc = task.get("description", "")
            if len(desc) < 50:
                short_desc.append(task.get("id", "Unknown"))

        if short_desc:
            issues.append(f"{len(short_desc)} tasks have brief descriptions: {', '.join(short_desc[:5])}")

        return issues

    def _generate_recommendations(self, score: int, issues: List[str]) -> List[str]:
        """Generate recommendations based on score and issues."""
        recommendations = []

        if score < 50:
            recommendations.append("PRD quality is low. Consider running discovery to improve task definitions.")
            recommendations.append("Add detailed acceptance criteria for all tasks.")
            recommendations.append("Specify which files each task will modify.")
        elif score < 70:
            recommendations.append("PRD quality is moderate. Discovery recommended to clarify vague tasks.")
            recommendations.append("Improve acceptance criteria specificity.")
        else:
            recommendations.append("PRD quality is good. Discovery may not be necessary.")

        if any("vague" in issue for issue in issues):
            recommendations.append("Replace vague acceptance criteria with specific, testable requirements.")

        if any("file hints" in issue for issue in issues):
            recommendations.append("Add files_likely_modified to all tasks to guide implementation.")

        if any("brief descriptions" in issue for issue in issues):
            recommendations.append("Expand task descriptions to explain the 'why' behind each task.")

        return recommendations

    def print_report(self):
        """Print a formatted analysis report."""
        if not self.analysis_results:
            print("No analysis results available. Run analyze() first.")
            return

        results = self.analysis_results

        print("\n" + "="*60)
        print("PRD COMPLETENESS ANALYSIS REPORT")
        print("="*60)
        print(f"\nOverall Score: {results['score']}/100")
        print(f"Discovery Needed: {'YES' if results['needs_discovery'] else 'NO'}")
        print(f"\nTotal Tasks: {results['total_tasks']}")
        print(f"Incomplete Tasks: {results['incomplete_tasks']}")

        print("\n" + "-"*60)
        print("CATEGORY SCORES:")
        print("-"*60)
        print(f"Task Structure:        {results['task_structure_score']:.1f}/20")
        print(f"Acceptance Criteria:   {results['acceptance_criteria_score']:.1f}/30")
        print(f"File Hints:            {results['file_hints_score']:.1f}/20")
        print(f"Descriptions:          {results['description_score']:.1f}/15")
        print(f"Category Organization: {results['category_score']:.1f}/15")

        if results['issues']:
            print("\n" + "-"*60)
            print("ISSUES IDENTIFIED:")
            print("-"*60)
            for i, issue in enumerate(results['issues'], 1):
                print(f"{i}. {issue}")

        if results['recommendations']:
            print("\n" + "-"*60)
            print("RECOMMENDATIONS:")
            print("-"*60)
            for i, rec in enumerate(results['recommendations'], 1):
                print(f"{i}. {rec}")

        print("\n" + "="*60 + "\n")


def analyze_prd(prd_path: str = "scripts/ralph/prd.json") -> Dict:
    """
    Convenience function to analyze PRD and return results.

    Args:
        prd_path: Path to PRD JSON file

    Returns:
        Dict with analysis results
    """
    analyzer = PRDAnalyzer(prd_path)
    return analyzer.analyze()


def main():
    """CLI entry point."""
    import sys

    prd_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/ralph/prd.json"

    analyzer = PRDAnalyzer(prd_path)
    results = analyzer.analyze()
    analyzer.print_report()

    # Exit with non-zero code if discovery is needed
    sys.exit(0 if not results['needs_discovery'] else 1)


if __name__ == "__main__":
    main()
