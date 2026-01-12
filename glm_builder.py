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
            self.office_chatter("writing", filepath)
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

    def office_chatter(self, situation: str, task_title: str = ""):
        """Generate natural office conversation - no formal notifications!"""

        # Simplify task title for conversation
        simple_task = task_title.lower().replace("_", " ").replace("-", " ")

        convos = {
            "task_start": [
                f"*Ralph squints at monitor* \"Ooh what's this one?\"\n*Stool glances over* \"Looks like we're working on {simple_task}.\"\n*Ralph* \"Sounds importent!\"",
                f"*Gomer* \"Hey guys, what are we doing now?\"\n*Stool* \"Something about {simple_task}.\"\n*Ralph picks nose* \"I'm helping!\"",
                f"*Ralph* \"Stool! STOOL! What's happening?\"\n*Stool sighs* \"We're building {simple_task}, Ralph.\"\n*Ralph* \"Oh boy oh boy!\"",
                f"*Stool stretches* \"Alright, next up...\"\n*Gomer* \"What is it?\"\n*Stool* \"{simple_task}.\"\n*Ralph* \"That's my favrite!\"",
                f"*Ralph spins in chair* \"Wheee! What are we making?\"\n*Stool* \"Focus, Ralph. {simple_task}.\"\n*Gomer* \"Sounds neat!\"",
            ],
            "thinking": [
                f"*Ralph stares at screen* \"Why is it just... sitting there?\"\n*Stool* \"It's thinking, Ralph.\"\n*Ralph* \"Compooters can THINK?!\"",
                f"*Gomer* \"Is it broken?\"\n*Stool* \"No, it's processing.\"\n*Ralph* \"I process stuff too! Like chicken nuggets!\"",
                f"*Ralph pokes monitor* \"Hello? Helloooo?\"\n*Stool* \"Don't touch that.\"\n*Ralph* \"But it's being slow...\"",
                f"*Gomer whispers* \"Should we do something?\"\n*Stool* \"Just wait.\"\n*Ralph* \"Waiting is my second best skill!\"",
                f"*Ralph* \"Maybe it fell asleep?\"\n*Stool* \"Computers don't sleep, Ralph.\"\n*Ralph* \"That's sad. Everyone needs sleepy time.\"",
            ],
            "writing": [
                f"*Stool types* \"And... there we go.\"\n*Ralph watches amazed* \"So many letters!\"\n*Gomer* \"Golly, that's a lot of code!\"",
                f"*Ralph* \"Are those words?\"\n*Stool* \"It's code.\"\n*Ralph* \"Code words! Like spies use!\"",
                f"*Gomer* \"Wow, look at it go!\"\n*Ralph claps* \"The typing ghost is back!\"\n*Stool* \"That's... that's me typing, Ralph.\"",
                f"*Ralph* \"Can I type something?\"\n*Stool* \"No.\"\n*Ralph* \"Please?\"\n*Stool* \"...no.\"",
            ],
            "git_push": [
                f"*Ralph jumps up* \"Mr. Worms! MR. WORMS! The GitHu thingy worked!\"\n*Stool* \"Yes, it's uploaded.\"\n*Ralph* \"I did it!\"",
                f"*Ralph salutes* \"Reporting for duty! The code went to the internets!\"\n*Gomer* \"We're on GitHubb now!\"\n*Ralph* \"Hi internet people!\"",
                f"*Stool* \"Pushed.\"\n*Ralph* \"Did someone fall?\"\n*Stool* \"No, I pushed the code to GitHub.\"\n*Ralph* \"Oh! I knew that.\"",
                f"*Gomer* \"Did it work?\"\n*Stool* \"Yep, it's live.\"\n*Ralph waves at screen* \"Bye bye code! Say hi to the GitHup for me!\"",
                f"*Ralph* \"Stool! The GidHub ate our code!\"\n*Stool* \"That's... that's what it's supposed to do.\"\n*Ralph* \"Oh good! I was worried.\"",
            ],
            "success": [
                f"*Gomer* \"Hey, it worked!\"\n*Ralph* \"YAYYY!\"\n*Stool* \"Don't get too excited, there's more to do.\"\n*Ralph* \"Too late! Already excited!\"",
                f"*Ralph does a little dance* \"We did it we did it!\"\n*Stool* \"Calm down.\"\n*Gomer* \"Let him have this one, Stool.\"",
                f"*Stool leans back* \"Another one done.\"\n*Ralph* \"Can we have a pizza party?\"\n*Stool* \"No.\"\n*Ralph* \"...cake party?\"",
                f"*Gomer high-fives Ralph* \"Nice work team!\"\n*Ralph misses the high-five* \"Ow my face!\"\n*Stool sighs*",
            ],
            "random": [
                f"*Ralph* \"Hey Stool, guess what?\"\n*Stool* \"What?\"\n*Ralph* \"...I forgot.\"",
                f"*Gomer* \"Anyone want coffee?\"\n*Stool* \"Sure.\"\n*Ralph* \"I want chocolate milk!\"\n*Gomer* \"We don't have that.\"\n*Ralph* \"Aw...\"",
                f"*Ralph* \"My chair squeaks.\"\n*Stool* \"So?\"\n*Ralph* \"It's singing to me.\"\n*Stool* \"Please focus.\"",
                f"*Ralph stares at ceiling* \"Do you think clouds have feelings?\"\n*Stool* \"Ralph. Work.\"\n*Ralph* \"But what if they're SAD clouds?\"",
                f"*Gomer* \"How much longer?\"\n*Stool* \"A while.\"\n*Ralph* \"A while is my favorite time!\"",
                f"*Ralph* \"I'm hungry.\"\n*Stool* \"You just ate.\"\n*Ralph* \"That was FOREVER ago!\"\n*Gomer* \"It was ten minutes.\"",
                f"*Ralph picks nose* \"Found something!\"\n*Stool* \"Please don't share.\"\n*Ralph* \"It's green!\"\n*Gomer* \"RALPH!\"",
                f"*Ralph spins in chair* \"Wheeeee!\"\n*Stool* \"Stop that.\"\n*Ralph spins faster*",
                f"*Gomer* \"What's that smell?\"\n*Stool* \"Ralph, did you bring tuna again?\"\n*Ralph* \"It's my emotional support fish!\"",
                f"*Ralph* \"I made a new friend!\"\n*Stool* \"Who?\"\n*Ralph points at plant* \"Gerald.\"\n*Stool* \"That's a fern.\"",
                f"*Ralph waves at monitor* \"Hi computer!\"\n*Gomer* \"It can't hear you.\"\n*Ralph* \"You don't know that.\"",
                f"*Stool stretches* \"My back is killing me.\"\n*Ralph* \"I can fix it!\"\n*Stool* \"Please don't.\"",
            ],
            "error": [
                f"*Ralph* \"Uh oh.\"\n*Stool* \"What now?\"\n*Ralph* \"The screen is angry...\"\n*Gomer* \"That's just an error message.\"",
                f"*Ralph panics* \"STOOL! THE COMPUTER IS YELLING!\"\n*Stool* \"Calm down, it's just a bug.\"\n*Ralph* \"A BUG?! WHERE?!\"",
                f"*Gomer* \"Something broke.\"\n*Stool sighs* \"Of course it did.\"\n*Ralph* \"Was it me? Please say it wasn't me.\"",
            ],
        }

        lines = convos.get(situation, convos["random"])
        msg = random.choice(lines)
        send_telegram(msg)

    def maybe_random_chatter(self):
        """40% chance to send random office chatter - keeps feed alive!"""
        if random.random() < 0.4:
            self.office_chatter("random")

    def build_task(self, task: dict) -> bool:
        """
        Build a single PRD task using GLM-4.7.
        Returns True if successful.
        """
        print(f"\n{'='*60}")
        print(f"Building: [{task['id']}] {task.get('title', 'Unknown')}")
        print(f"{'='*60}")

        # Office conversation about starting new task
        self.office_chatter("task_start", task.get('title', 'something'))

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
        self.office_chatter("thinking")
        try:
            response = self.client.build(user_prompt, system_prompt, max_tokens=8000)
        except Exception as e:
            print(f"  [ERROR] GLM call failed: {e}")
            self.office_chatter("error")
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

            # Office celebrates completion - no formal notifications!
            self.office_chatter("success", task.get('title', ''))

            # Maybe some random chatter too
            self.maybe_random_chatter()

            # Refine README on every iteration
            self.refine_readme(task)

            # More chatter while working
            self.maybe_random_chatter()

            # Commit README changes and push
            self.run_command('git add -A && git commit -m "docs: Update README progress" --no-verify || true')
            self.run_command('git push origin main || true')
            self.office_chatter("git_push")

            # Maybe one more chatter at the end
            self.maybe_random_chatter()

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
        # Random office chatter as iteration starts
        self.maybe_random_chatter()

        task = self.get_next_task()

        if not task:
            print("No incomplete tasks found!")
            send_telegram("*Ralph looks around* \"Are we... done?\"\n*Stool* \"Looks like it.\"\n*Ralph* \"YAY! Pizza time?\"")
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
