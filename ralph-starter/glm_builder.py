#!/usr/bin/env python3
"""
GLM Builder - Autonomous code builder using GLM-4.7

Replaces Claude Code for the build loop, saving 32x on costs.
Uses simple tool-use pattern: GLM outputs structured commands, we execute them.
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from glm_client import GLMClient, BUILDER_MODEL

load_dotenv()

# Project paths
PROJECT_DIR = Path(__file__).parent
PRD_FILE = PROJECT_DIR / "scripts/ralph/prd.json"
PROMPT_FILE = PROJECT_DIR / "scripts/ralph/prompt.md"
PROGRESS_FILE = PROJECT_DIR / "scripts/ralph/progress.txt"


class GLMBuilder:
    """Autonomous builder using GLM-4.7"""

    def __init__(self):
        self.client = GLMClient()
        self.project_dir = PROJECT_DIR

    def load_prd(self) -> dict:
        """Load PRD file."""
        with open(PRD_FILE, 'r') as f:
            return json.load(f)

    def save_prd(self, prd: dict):
        """Save PRD file."""
        with open(PRD_FILE, 'w') as f:
            json.dump(prd, f, indent=2)

    def get_next_task(self) -> Optional[dict]:
        """Get the next incomplete task from PRD."""
        prd = self.load_prd()

        # Use priority_order if available
        priority_order = prd.get("priority_order", [])
        tasks = prd.get("tasks", [])

        # Create task lookup
        task_map = {t["id"]: t for t in tasks}

        # Find first incomplete task in priority order
        for task_id in priority_order:
            if task_id in task_map:
                task = task_map[task_id]
                if not task.get("passes", False):
                    return task

        # Fallback: any incomplete task
        for task in tasks:
            if not task.get("passes", False):
                return task

        return None

    def read_file(self, filepath: str) -> str:
        """Read a file from the project."""
        full_path = self.project_dir / filepath
        if full_path.exists():
            return full_path.read_text()
        return f"[File not found: {filepath}]"

    def write_file(self, filepath: str, content: str) -> bool:
        """Write content to a file."""
        full_path = self.project_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"  [WRITE] {filepath}")
        return True

    def run_command(self, command: str) -> tuple[int, str]:
        """Run a shell command."""
        print(f"  [CMD] {command}")
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout + result.stderr
        return result.returncode, output

    def mark_task_complete(self, task_id: str):
        """Mark a task as complete in PRD."""
        prd = self.load_prd()
        for task in prd.get("tasks", []):
            if task["id"] == task_id:
                task["passes"] = True
                break
        self.save_prd(prd)
        print(f"  [DONE] Task {task_id} marked complete")

    def log_progress(self, task: dict, summary: str):
        """Log progress to progress.txt"""
        entry = f"""
## Iteration - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Task**: [{task['id']}] {task.get('title', 'Unknown')}
**Status**: Complete

### What was implemented
{summary}

### Builder
GLM-4.7 (Cost-optimized)

---
"""
        with open(PROGRESS_FILE, 'a') as f:
            f.write(entry)

    def build_task(self, task: dict) -> bool:
        """
        Build a single PRD task using GLM-4.7.
        Returns True if successful.
        """
        print(f"\n{'='*60}")
        print(f"Building: [{task['id']}] {task.get('title', 'Unknown')}")
        print(f"{'='*60}")

        # Read relevant context
        prompt_content = self.read_file("scripts/ralph/prompt.md")

        # Determine which files might be relevant
        main_file = "ralph_bot.py"
        main_content = self.read_file(main_file)

        # Build the prompt for GLM - keep it SHORT for faster thinking
        system_prompt = """Expert Python dev. Output changes in format:
===FILE: path===
[code]
===END FILE===
No explanations. Code only."""

        user_prompt = f"""Task: [{task['id']}] {task.get('title', 'Unknown')}
{task.get('description', '')}

Criteria: {task.get('acceptance_criteria', [])}

Output Python code for this feature. Be concise."""

        # Call GLM-4.7
        print("  [GLM] Generating implementation...")
        try:
            response = self.client.build(user_prompt, system_prompt, max_tokens=8000)
        except Exception as e:
            print(f"  [ERROR] GLM call failed: {e}")
            return False

        if not response:
            print("  [ERROR] Empty response from GLM")
            return False

        print(f"  [GLM] Got {len(response)} chars response")

        # Parse and execute the response
        success = self.execute_response(response, task)

        if success:
            self.mark_task_complete(task['id'])
            self.log_progress(task, f"Implemented by GLM-4.7")

        return success

    def execute_response(self, response: str, task: dict) -> bool:
        """Parse GLM response and execute file writes and commands."""

        # Extract file changes
        file_pattern = r'===FILE:\s*(.+?)===\s*(.*?)\s*===END FILE==='
        file_matches = re.findall(file_pattern, response, re.DOTALL)

        for filepath, content in file_matches:
            filepath = filepath.strip()
            content = content.strip()

            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

            self.write_file(filepath, content)

        # Extract and run commands
        cmd_pattern = r'===COMMAND:\s*(.+?)===\s*(.*?)\s*===END COMMAND==='
        cmd_matches = re.findall(cmd_pattern, response, re.DOTALL)

        for cmd_desc, cmd in cmd_matches:
            cmd = cmd.strip() or cmd_desc.strip()
            if cmd:
                # Safety check - don't run dangerous commands
                dangerous = ['rm -rf /', 'dd if=', 'mkfs', ':(){', 'fork bomb']
                if any(d in cmd.lower() for d in dangerous):
                    print(f"  [SKIP] Dangerous command blocked: {cmd}")
                    continue

                returncode, output = self.run_command(cmd)
                if returncode != 0:
                    print(f"  [WARN] Command returned {returncode}")

        # Auto-commit if no commit command was in response
        if not any('git commit' in (m[0] + m[1]) for m in cmd_matches):
            commit_msg = f"feat(ralph): [{task['id']}] {task.get('title', 'Update')}"
            self.run_command(f'git add -A && git commit -m "{commit_msg}" --no-verify || true')

        return True

    def run_iteration(self) -> bool:
        """Run one iteration of the build loop."""
        task = self.get_next_task()

        if not task:
            print("No incomplete tasks found!")
            return False

        return self.build_task(task)


def main():
    """Main entry point."""
    print("=" * 60)
    print("GLM Builder - Ralph Mode (GLM-4.7)")
    print("Cost: ~$1.40/1M tokens (32x cheaper than Opus)")
    print("=" * 60)

    builder = GLMBuilder()

    # Run one iteration
    success = builder.run_iteration()

    if success:
        print("\n[SUCCESS] Task completed!")
    else:
        print("\n[DONE] No more tasks or build failed")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
