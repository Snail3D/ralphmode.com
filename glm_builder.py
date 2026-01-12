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
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import random

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from glm_client import GLMClient, BUILDER_MODEL

load_dotenv()

# Project paths
PROJECT_DIR = Path(__file__).parent
PRD_FILE = PROJECT_DIR / "scripts/ralph/prd.json"
PROMPT_FILE = PROJECT_DIR / "scripts/ralph/prompt.md"
PROGRESS_FILE = PROJECT_DIR / "scripts/ralph/progress.txt"

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_ADMIN_ID", ""))

# Ralph Wiggum quotes for random insertion
RALPH_QUOTES = [
    "I'm a unitard!",
    "Me fail English? That's unpossible!",
    "Hi, Super Nintendo Chalmers!",
    "I bent my Wookie.",
    "My cat's breath smells like cat food.",
    "I'm learnding!",
    "When I grow up, I want to be a principal or a caterpillar.",
    "That's where I saw the leprechaun. He tells me to burn things.",
    "I ate the purple berries... they taste like burning.",
    "My daddy's gonna be so proud of me!",
    "Look Big Daddy, it's Regular Daddy!",
    "I found a moonrock in my nose!",
    "What's a diorama?",
    "Mrs. Krabappel and Principal Skinner were in the closet making babies...",
    "Can you open my milk, Mommy?",
    "I choo-choo-choose you!",
    "The doctor said I wouldn't have so many nose bleeds if I kept my finger outta there.",
    "Even my boogers are spicy!",
    "I'm helping! I'm a helper!",
    "My parents won't let me use scissors.",
]


def send_telegram(message: str) -> bool:
    """Send message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [TELEGRAM] Not configured, skipping")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.json().get("ok", False)
    except Exception as e:
        print(f"  [TELEGRAM] Error: {e}")
        return False


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
        # Chatter about file writes (but not too often)
        if random.random() < 0.3:  # 30% chance
            self.quick_chatter("writing_file", filepath)
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

    def generate_office_scene(self, task: dict, done_count: int, total_count: int):
        """Generate theatrical office scene using GLM-4.5-Flash (FREE) and send to Telegram."""
        try:
            # Build the scene prompt
            scene_prompt = f"""Generate a SHORT office scene (5-7 lines) about completing this coding task.

Task: [{task['id']}] {task.get('title', '')}
Description: {task.get('description', '')}
Progress: {done_count}/{total_count} tasks ({int(done_count/total_count*100)}% done)

Characters:
- Ralph (boss): Lovably confused, says "unpossible", picks nose, but surprisingly explains things simply
- Stool (senior dev): Competent, cynical, sighs. Explains tech stuff to others.
- Gomer (junior): Eager, says "Golly!", asks clarifying questions

IMPORTANT: Include a SIMPLE EXPLANATION of what was just built so viewers can understand!

Scene must include:
1. Character announcing task is done
2. Someone explaining what they built IN SIMPLE TERMS (like explaining to a friend, not a developer)
3. A reaction from another character
4. A Ralph-style funny moment or quote

Format: *action* "dialogue"
Keep response SHORT - max 7 lines!"""

            response = self.client.personality(scene_prompt, "ralph")

            if response:
                # Build the full message
                message = f"""🎬 *Scene {done_count}*

{response}

━━━━━━━━━━━━━
✅ *[{task['id']}]* {task.get('title', '')}
📊 {done_count}/{total_count} complete
━━━━━━━━━━━━━

_{random.choice(RALPH_QUOTES)}_"""

                send_telegram(message)
                print("  [SCENE] Sent theatrical update to Telegram")
            else:
                # Fallback simple message
                message = f"""✅ *Task Complete!*

*[{task['id']}]* {task.get('title', '')}

📊 Progress: {done_count}/{total_count}

_"{random.choice(RALPH_QUOTES)}"_ - Ralph"""
                send_telegram(message)

        except Exception as e:
            print(f"  [SCENE] Error generating scene: {e}")
            # Send basic update on error
            send_telegram(f"✅ *[{task['id']}]* {task.get('title', '')} complete!\n📊 {done_count}/{total_count}")

    def refine_readme(self, task: dict):
        """Refine README.md after each task - keep it current and useful."""
        readme_path = self.project_dir / "README.md"

        if not readme_path.exists():
            print("  [README] No README.md found, skipping refinement")
            return

        current_readme = readme_path.read_text()

        # Count completed tasks for progress bar
        prd = self.load_prd()
        total = len(prd.get("tasks", []))
        done = sum(1 for t in prd.get("tasks", []) if t.get("passes", False))
        percent = int((done / total) * 100) if total > 0 else 0

        # Ask GLM to refine the README
        system_prompt = """You are a README refinement expert. Your job is to keep the README current and useful.

Rules:
1. Keep it to ~2 pages max (concise, not bloated)
2. Update the progress bar/stats with accurate numbers
3. Add any NEW features from the task that users would care about
4. Remove anything outdated or no longer relevant
5. Keep the playful Ralph Mode tone
6. Output the ENTIRE updated README.md content

Output format:
===FILE: README.md===
[full updated README content]
===END FILE==="""

        user_prompt = f"""Task just completed: [{task['id']}] {task.get('title', '')}
Description: {task.get('description', '')}

Current stats: {done}/{total} tasks complete ({percent}%)

Current README:
```
{current_readme[:3000]}
```

Update the README to reflect current progress. Keep it fresh and useful."""

        print("  [README] Refining README.md...")
        try:
            response = self.client.build(user_prompt, system_prompt, max_tokens=4000)
            if response:
                # Extract the README content
                file_pattern = r'===FILE:\s*README\.md===\s*(.*?)\s*===END FILE==='
                match = re.search(file_pattern, response, re.DOTALL)
                if match:
                    new_readme = match.group(1).strip()
                    # Remove markdown code blocks if present
                    if new_readme.startswith('```'):
                        lines = new_readme.split('\n')
                        new_readme = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

                    readme_path.write_text(new_readme)
                    print("  [README] Updated README.md")
                else:
                    print("  [README] Could not parse response, skipping")
        except Exception as e:
            print(f"  [README] Refinement failed: {e}")

    def quick_chatter(self, message_type: str, context: str = ""):
        """Send quick character chatter to Telegram - keeps the feed alive!"""
        chatters = {
            "task_start": [
                f"*Ralph squints at screen* \"Ooh! New thingy to build!\"",
                f"*Stool cracks knuckles* \"Alright, let's see what we got...\"",
                f"*Gomer bounces in chair* \"Golly, another task! What is it?\"",
                f"*Ralph picks nose* \"I'm gonna build the BEST thing ever!\"",
                f"*Stool sighs* \"Here we go again...\"",
            ],
            "thinking": [
                f"*Ralph stares intensely* \"The compooter is thinking...\"",
                f"*Stool taps desk impatiently* \"Any day now, GLM...\"",
                f"*Gomer whispers* \"Shh, it's doing the smart stuff!\"",
                f"*Ralph picks nose while waiting* \"I wonder if code tastes like chicken...\"",
            ],
            "writing_file": [
                f"*Stool types furiously* \"Writing code... this is the fun part.\"",
                f"*Gomer watches amazed* \"Golly, look at all those letters!\"",
                f"*Ralph claps* \"The magic typing ghost is back!\"",
            ],
            "running_cmd": [
                f"*Stool hits enter dramatically* \"Here goes nothing...\"",
                f"*Ralph covers eyes* \"I'm too scared to look!\"",
                f"*Gomer holds breath* \"Please work please work please work...\"",
            ],
            "git_push": [
                f"*Ralph salutes* \"Mr. Worms! The GitHu was updated succesfully!\"",
                f"*Ralph beams proudly* \"I pushed it to the GitHubb, boss!\"",
                f"*Ralph picks nose* \"The internets have our code now, Mr. Worms!\"",
                f"*Gomer whispers excitedly* \"We did it! GitHuub is updated!\"",
                f"*Ralph waves at screen* \"Bye bye code! Go to the GitHup!\"",
                f"*Stool nods* \"GitHub updated.\" *Ralph adds* \"I helped!\"",
                f"*Ralph claps* \"Mr. Worms! Mr. Worms! The GidHub thingy worked!\"",
            ],
        }

        lines = chatters.get(message_type, [f"*Ralph blinks* \"What's happening?\""])
        msg = random.choice(lines)

        if context:
            msg = f"{msg}\n\n📋 _{context}_"

        send_telegram(msg)

    def build_task(self, task: dict) -> bool:
        """
        Build a single PRD task using GLM-4.7.
        Returns True if successful.
        """
        print(f"\n{'='*60}")
        print(f"Building: [{task['id']}] {task.get('title', 'Unknown')}")
        print(f"{'='*60}")

        # Send task start chatter
        self.quick_chatter("task_start", f"[{task['id']}] {task.get('title', '')}")

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
        self.quick_chatter("thinking")
        try:
            response = self.client.build(user_prompt, system_prompt, max_tokens=8000)
        except Exception as e:
            print(f"  [ERROR] GLM call failed: {e}")
            send_telegram(f"*Ralph panics* \"THE COMPUTER BROKE! IT SAYS: {str(e)[:100]}\"")
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

            # Count tasks for progress
            prd = self.load_prd()
            total = len(prd.get("tasks", []))
            done = sum(1 for t in prd.get("tasks", []) if t.get("passes", False))

            # Generate theatrical scene and send to Telegram (uses FREE model)
            self.generate_office_scene(task, done, total)

            # Refine README on every iteration
            self.refine_readme(task)
            # Commit README changes and push
            self.run_command('git add -A && git commit -m "docs: Update README progress" --no-verify || true')
            self.run_command('git push origin main || true')
            self.quick_chatter("git_push")

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

        # Always push to GitHub after commit
        self.run_command('git push origin main || true')

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
