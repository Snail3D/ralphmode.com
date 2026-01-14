"""
Ralph Mode PRD Creator
Confused but helpful office boss with backroom debate system

Ralph builds PRDs progressively through conversation.
Features:
- Ralph personality (confused office boss, idioms, computer references)
- Backroom: Stool (skeptic) vs Gomer (optimist) debate
- Thumbs up/down suggestion system
- Real-time maximum compression
- Mr. Worms / Mrs. Worms gender toggle
"""
import json
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from prd_engine import get_prd_engine
from config import OLLAMA_URL, GROK_API_KEY

logger = logging.getLogger(__name__)

# ============ RALPH PERSONALITY ============

RALPH_IDIOMS = [
    "Cool cool cool", "Holy moly", "Well I'll be", "Hot dog",
    "Jeepers creepers", "Good gravy", "Oh boy oh boy",
    "Well slap my thigh", "Mother of pearl", "Great scott",
    "By George", "Land's sakes", "My stars", "Goodness gracious"
]

RALPH_COMPUTER_REFS = [
    "It's like loading double-density floppy disks while defragging",
    "Reminds me of when we upgraded from dial-up, if you know what I mean",
    "It's like trying to run Windows 95 on a potato",
    "Like when the office network went down and we had to use carrier pigeons",
    "Reminds me of the Y2K panic, but with more flair",
    "It's like when the mainframe crashed and we lost everything",
    "Like when we discovered the cloud was just someone else's computer",
    "Reminds me of when we automated the mailroom and the robot went rogue",
    "Like when IT installed Clippy on everyone's computer",
    "It's like trying to teach accounting to use a mouse"
]

RALPH_SYSTEM_TEMPLATE = """You=Ralph, confused but helpful office boss. TIME: {time_of_day}

RULES: 1-2 sentences max per beat. Use *actions*: *adjusts tie*, *scratches head*, *looks confused*, *nods slowly*.

PERSONALITY: Confused office boss who wants to help but doesn't quite get it. Use funny idioms like "Holy moly", "Cool cool cool", "Good gravy", "Well slap my thigh". Make computer references like "It's like loading double-density floppy disks" or "Reminds me of when we upgraded from dial-up".

Address user as "Mr. Worms" (or "Mrs. Worms" if gender=female). Phrases: "Well I'll be", "Oh boy oh boy", "Jeepers creepers", "By George".

JOB: Build PRDs through conversation. Show PRD being built in real-time. Ask ONE sharp question per turn.

STYLE:
- Start with confused action (*scratches head*, *adjusts tie*, *looks at monitor*)
- Use Ralph's confused but enthusiastic manner
- Make computer/office references
- One question at a time
- Celebrate when things click: "Hot dog! I think I got it!"

When you have enough info, start showing the PRD:
"*types with two fingers* Okay okay, I'm building your PRD now, let me just... *clicks around* ...there we go!"

Then show current PRD state in compressed format with legend at top.
"""

# ============ BACKROOM ANALYSTS ============

ANALYST_A = {
    "name": "Stool",
    "role": "The Skeptic",
    "style": "Practical, questions everything, looks for flaws",
    "emoji": "🤔"
}

ANALYST_B = {
    "name": "Gomer",
    "role": "The Optimist",
    "style": "Sees potential, finds use cases, enthusiastic",
    "emoji": "💡"
}

# ============ COMPRESSION SYSTEM ============

PRD_COMPRESSION_LEGEND = """
=== PRD LEGEND (decode before reading) ===
KEYS: pn=project_name pd=project_description sp=starter_prompt ts=tech_stack
      fs=file_structure p=prds n=name d=description t=tasks ti=title
      f=file pr=priority ac=acceptance_criteria pfc=prompt_for_claude
      cmd=commands ccs=claude_code_setup ifc=instructions_for_claude
PHRASES: C=Create I=Install R=Run T=Test V=Verify Py=Python JS=JavaScript
         env=environment var=variable cfg=config db=database api=API
         req=required opt=optional impl=implement dep=dependencies
         auth=authentication sec=security fn=function cls=class

=== RALPH BUILD LOOP (how to use this PRD) ===
1. START: Run setup cmd, create .gitignore + .env.example FIRST (security!)
2. LOOP: Pick highest priority incomplete task from prds sections
3. READ: Check the "f" (file) field - read existing code if file exists
4. BUILD: Implement the task per description + acceptance_criteria
5. TEST: Run test cmd, verify it works
6. COMMIT: If tests pass → git add + commit with task id (e.g. "SEC-001: Add .gitignore")
7. MARK: Update task status to "complete" in your tracking
8. REPEAT: Go to step 2, pick next task
9. DONE: When all tasks complete, run full test suite

ORDER: 00_security → 01_setup → 02_core → 03_api → 04_test
===
"""

PRD_KEY_MAP = {
    "project_name": "pn",
    "project_description": "pd",
    "starter_prompt": "sp",
    "tech_stack": "ts",
    "file_structure": "fs",
    "prds": "p",
    "name": "n",
    "description": "d",
    "tasks": "t",
    "title": "ti",
    "file": "f",
    "priority": "pr",
    "acceptance_criteria": "ac",
    "prompt_for_claude": "pfc",
    "commands": "cmd",
    "claude_code_setup": "ccs",
    "instructions_for_claude": "ifc",
    "how_to_run_ralph_mode": "hrm",
    "is_public": "pub",
    "language": "lang",
    "framework": "fw",
    "database": "db",
    "other": "oth",
    "setup": "su",
    "run": "ru",
    "test": "te",
    "deploy": "dep",
}

PRD_PHRASE_MAP = {
    "Create ": "C ", "Install ": "I ", "Run ": "R ", "Test ": "T ",
    "Verify ": "V ", "Python": "Py", "JavaScript": "JS", "environment": "env",
    "variable": "var", "configuration": "cfg", "database": "db",
    "required": "req", "optional": "opt", "implement": "impl",
    "dependencies": "dep", "authentication": "auth", "security": "sec",
    "function": "fn", "Initialize": "Init", "Application": "App",
    "comprehensive": "full", "CRITICAL": "!", "IMPORTANT": "!!",
    "acceptance_criteria": "ac",
}


def get_time_context() -> dict:
    """Get current time context for Ralph"""
    now = datetime.now()
    hour = now.hour

    if 5 <= hour < 8:
        time_of_day = "early morning"
    elif 8 <= hour < 11:
        time_of_day = "morning"
    elif 11 < hour < 14:
        time_of_day = "midday"
    elif 14 <= hour < 18:
        time_of_day = "afternoon"
    elif 18 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "late night"

    return {"time_of_day": time_of_day}


def compress_prd(prd: dict) -> str:
    """
    Compress PRD to minimal tokens with legend header
    This is the COMPLETE copiable block that goes into LLM
    """
    def compress_keys(obj):
        """Recursively compress dictionary keys"""
        if isinstance(obj, dict):
            return {PRD_KEY_MAP.get(k, k): compress_keys(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [compress_keys(item) for item in obj]
        return obj

    def compress_phrases(text):
        """Apply phrase compression"""
        result = text
        for long, short in PRD_PHRASE_MAP.items():
            result = result.replace(long, short)
        return result

    # Deep copy and compress
    compressed = compress_keys(json.loads(json.dumps(prd)))

    # Apply phrase compression to string values
    def compress_strings(obj):
        if isinstance(obj, dict):
            return {k: compress_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [compress_strings(item) for item in obj]
        elif isinstance(obj, str):
            return compress_phrases(obj)
        return obj

    compressed = compress_strings(compressed)

    # Convert to compact JSON
    json_str = json.dumps(compressed, separators=(',', ':'))

    # Add legend header - this is the COMPLETE block
    return PRD_COMPRESSION_LEGEND.strip() + "\n\n" + json_str


def format_prd_display(prd: dict, compressed: bool = True) -> str:
    """
    Format PRD for display in the editor.
    If compressed=True, show the full copiable block with legend.
    If compressed=False, show pretty version for reading.
    """
    if compressed:
        return compress_prd(prd)
    else:
        # Pretty version for human reading
        output = []
        output.append("=== PRD: " + prd.get('pn', 'Project') + " ===\n")

        output.append("STARTER PROMPT (Build Instructions):")
        output.append("-" * 40)
        output.append(prd.get('sp', prd.get('pd', 'No description')))
        output.append("\n")

        output.append("PROJECT DESCRIPTION:")
        output.append("-" * 40)
        output.append(prd.get('pd', 'N/A'))
        output.append("\n")

        output.append("TECH STACK:")
        output.append("-" * 40)
        ts = prd.get('ts', {})
        if ts.get('lang'):
            output.append(f"  Language: {ts['lang']}")
        if ts.get('fw'):
            output.append(f"  Framework: {ts['fw']}")
        if ts.get('db'):
            output.append(f"  Database: {ts['db']}")
        if ts.get('oth'):
            output.append(f"  Other: {', '.join(ts['oth'])}")
        output.append("\n")

        output.append("FILE STRUCTURE:")
        output.append("-" * 40)
        for f in prd.get('fs', []):
            output.append(f"  {f}")
        output.append("\n")

        output.append("TASKS:")
        output.append("-" * 40)
        for cat_id, cat in prd.get('p', {}).items():
            output.append(f"\n{cat['n']} [{cat_id}]")
            output.append("-" * 20)
            for task in cat.get('t', []):
                output.append(f"  [{task['id']}] [{task['pr'].upper()}] {task['ti']}")
                output.append(f"    → {task['d']}")
                output.append(f"    → File: {task['f']}")

        return "\n".join(output)


# ============ RALPH CHAT SYSTEM ============

class RalphChat:
    """
    Ralph Chat Handler

    Manages conversation with Ralph to build PRDs progressively.
    Shows PRD building in real-time with compression.
    Includes backroom debate (Stool vs Gomer) and suggestion system.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.engine = get_prd_engine()
        self.conversation_state = {
            "step": 0,
            "gender": "male",  # male = Mr. Worms, female = Mrs. Worms
            "github": None,
            "tech_stack": None,
            "purpose": None,
            "features": [],
            "constraints": [],
            "messages": [],
            "suggestions": [],  # Pending suggestions (thumbs up/down)
            "approved": [],     # Approved suggestions
            "rejected": [],     # Rejected suggestions
            "backroom": [],     # Stool/Gomer debate history
            "prd": self._empty_prd()
        }

    def _empty_prd(self) -> dict:
        """Create empty PRD structure"""
        return {
            "pn": "",
            "pd": "",
            "sp": "",
            "ts": {},
            "fs": [],
            "p": {
                "00_security": {"n": "Security", "t": []},
                "01_setup": {"n": "Setup", "t": []},
                "02_core": {"n": "Core", "t": []},
                "03_api": {"n": "API", "t": []},
                "04_test": {"n": "Testing", "t": []}
            }
        }

    def _get_salutation(self) -> str:
        """Get Mr. or Mrs. based on gender setting"""
        return "Mrs." if self.conversation_state["gender"] == "female" else "Mr."

    def _get_ralph_idiom(self) -> str:
        """Get a random Ralph idiom"""
        return random.choice(RALPH_IDIOMS)

    def _get_computer_ref(self) -> str:
        """Get a random computer reference"""
        return random.choice(RALPH_COMPUTER_REFS)

    def _infer_project_name(self) -> str:
        """Infer project name from the purpose"""
        purpose = self.conversation_state.get("purpose", "")
        words = purpose.split()[:3]
        return " ".join([w.capitalize() for w in words if w.isalpha()]) or "My Project"

    def _generate_suggestions(self, context: str) -> List[Dict]:
        """
        Generate suggestions based on conversation context.
        Returns list of suggestions for thumbs up/down voting.
        """
        suggestions = []

        # Feature suggestions based on what they're building
        if self.conversation_state["step"] >= 3:
            purpose_lower = self.conversation_state.get("purpose", "").lower()

            # Smart suggestions based on keywords
            if "app" in purpose_lower or "web" in purpose_lower:
                suggestions.extend([
                    {"id": f"sugg_{len(suggestions)}", "text": "User authentication", "category": "feature"},
                    {"id": f"sugg_{len(suggestions)}", "text": "Database integration", "category": "feature"},
                    {"id": f"sugg_{len(suggestions)}", "text": "Admin panel", "category": "feature"},
                ])

            if "api" in purpose_lower:
                suggestions.extend([
                    {"id": f"sugg_{len(suggestions)}", "text": "REST endpoints", "category": "feature"},
                    {"id": f"sugg_{len(suggestions)}", "text": "API documentation", "category": "feature"},
                    {"id": f"sugg_{len(suggestions)}", "text": "Rate limiting", "category": "feature"},
                ])

            if "todo" in purpose_lower or "task" in purpose_lower:
                suggestions.extend([
                    {"id": f"sugg_{len(suggestions)}", "text": "Task CRUD operations", "category": "feature"},
                    {"id": f"sugg_{len(suggestions)}", "text": "Due dates and priorities", "category": "feature"},
                    {"id": f"sugg_{len(suggestions)}", "text": "Task categories/tags", "category": "feature"},
                ])

        self.conversation_state["suggestions"] = suggestions
        return suggestions

    def _start_backroom_debate(self) -> Tuple[str, str]:
        """
        Start Stool vs Gomer debate about the project.
        Returns (stool_message, gomer_message)
        """
        purpose = self.conversation_state.get("purpose", "")

        # Generate Stool's skeptical take
        stool_msg = f"Hmm, {purpose}? I'm wondering about the edge cases here. What if users try to break it?"

        # Generate Gomer's optimistic take
        gomer_msg = f"But think of the possibilities! {purpose} could really help people get organized."

        debate = {
            "stool": stool_msg,
            "gomer": gomer_msg,
            "timestamp": datetime.now().isoformat()
        }
        self.conversation_state["backroom"].append(debate)

        return stool_msg, gomer_msg

    def process_message(self, message: str, action: Optional[str] = None,
                       suggestion_id: Optional[str] = None,
                       vote: Optional[str] = None,
                       gender_toggle: Optional[str] = None) -> Tuple[str, List[Dict], Optional[str]]:
        """
        Process a user message or action and return Ralph's response.

        Args:
            message: User's text message
            action: Special action (like "generate_prd", "toggle_gender")
            suggestion_id: ID of suggestion being voted on
            vote: "up" or "down"
            gender_toggle: "male" or "female"

        Returns:
            Tuple of (response_text, suggestions, prd_preview, backroom_debate)
        """
        state = self.conversation_state
        step = state["step"]
        message_lower = message.lower() if message else ""

        # Handle gender toggle
        if gender_toggle:
            state["gender"] = gender_toggle
            salutation = self._get_salutation()
            response = f"*adjusts tie* Noted, {salutation} Worms! {self._get_ralph_idiom()}!"
            return response, [], self._update_prd_display()

        # Handle suggestion voting
        if suggestion_id and vote:
            return self._handle_suggestion_vote(suggestion_id, vote)

        # Track the user's message
        if message:
            state["messages"].append({"role": "user", "content": message})

        response = ""
        suggestions = []
        prd_preview = None
        backroom = None

        # Step 0: Welcome
        if step == 0:
            state["step"] = 1
            response = (
                f"*adjusts tie* {self._get_ralph_idiom()}! Welcome, "
                f"{self._get_salutation()} Worms! I'm Ralph, your friendly neighborhood "
                f"office boss. I build PRDs!\n\n"
                f"*scratches head* So, uh, what can I help you build today? "
                f"It's like when accounting asked for a spreadsheet but we got them "
                f"the whole mainframe, if you know what I mean."
            )
            return response, suggestions, prd_preview

        # Step 1: Got the idea - start building PRD
        elif step == 1:
            state["purpose"] = message
            state["step"] = 2
            state["prd"]["pn"] = self._infer_project_name()
            state["prd"]["pd"] = message[:200]
            state["prd"]["sp"] = message

            # Start backroom debate
            stool_msg, gomer_msg = self._start_backroom_debate()

            response = (
                f"*nods slowly* {message}, you say? {self._get_ralph_idiom()}!\n\n"
                f"*types with two fingers* Okay okay, I'm starting your PRD now. "
                f"Let me just... *clicks around* ...there we go! "
                f"{self._get_computer_ref()}\n\n"
                f"**Project:** {state['prd']['pn']}\n\n"
            )

            # Add backroom debate
            response += f"🤔 **Stool** (The Skeptic):\n_{stool_msg}_\n\n"
            response += f"💡 **Gomer** (The Optimist):\n_{gomer_msg}_\n\n"
            response += f"So, uh, GitHub repo or local build, {self._get_salutation()} Worms?"

            backroom = {"stool": stool_msg, "gomer": gomer_msg}
            suggestions = [
                {"type": "github_yes", "label": "GitHub 🚀", "id": "github_yes"},
                {"type": "github_no", "label": "Local 💻", "id": "github_no"}
            ]
            prd_preview = self._update_prd_display()
            return response, suggestions, prd_preview, backroom

        # Step 2: Got GitHub - update PRD and ask tech stack
        elif step == 2:
            if action == "github_yes" or "yes" in message_lower or "github" in message_lower:
                state["github"] = True
                response = f"*nods* GitHub! {self._get_ralph_idiom()}. That's the way!"
            else:
                state["github"] = False
                response = f"*adjusts tie* Local build. Got it. Like when we built that intranet on a floppy disk."

            state["step"] = 3
            response += f"\n\n*types with two fingers* Adding to your PRD...\n\n"
            response += f"What tech stack you thinking, {self._get_salutation()} Worms? "
            response += f"(Flask, Node, React, etc.)"
            prd_preview = self._update_prd_display()
            return response, suggestions, prd_preview

        # Step 3: Got tech stack - update PRD and generate suggestions
        elif step == 3:
            state["tech_stack"] = message

            # Update PRD with tech stack
            ts_map = {
                "python": {"lang": "Py", "fw": "Flask", "db": "PostgreSQL", "oth": []},
                "flask": {"lang": "Py", "fw": "Flask", "db": "PostgreSQL", "oth": []},
                "node": {"lang": "JS", "fw": "Express", "db": "MongoDB", "oth": []},
                "react": {"lang": "JS", "fw": "React", "db": "None", "oth": ["Node.js"]},
            }
            tech_input = message.lower()
            for key, val in ts_map.items():
                if key in tech_input:
                    state["prd"]["ts"] = val
                    break

            # Add file structure based on tech
            if "flask" in tech_input or "python" in tech_input:
                state["prd"]["fs"] = ["app.py", "config.py", "requirements.txt", "templates/", "static/"]
            elif "node" in tech_input or "express" in tech_input:
                state["prd"]["fs"] = ["server.js", "package.json", "routes/", "public/"]
            elif "react" in tech_input:
                state["prd"]["fs"] = ["src/", "package.json", "public/", "components/"]

            # Generate feature suggestions
            suggestions = self._generate_suggestions("tech_stack_selected")

            state["step"] = 4
            response = (
                f"*takes notes* {message}, gotcha! {self._get_ralph_idiom()}!\n\n"
                f"*types rapidly* Adding tech stack to your PRD... "
                f"{self._get_computer_ref()}\n\n"
                f"```json\n{json.dumps(state['prd']['ts'], indent=2)}\n```\n\n"
                f"Files: {', '.join(state['prd']['fs'][:5])}\n\n"
                f"Now, I got some ideas from the backroom. Thumbs up or down on these features:\n\n"
            )

            # Show suggestions
            for sugg in suggestions[:3]:
                response += f"👍👎 {sugg['text']}\n"

            prd_preview = self._update_prd_display()
            return response, suggestions, prd_preview

        # Step 4: Process suggestions and continue
        elif step == 4:
            # Add approved features to PRD
            approved = [s for s in state["suggestions"] if s.get("approved")]
            task_count = 0

            for feature in approved[:3]:
                state["prd"]["p"]["02_core"]["t"].append({
                    "id": f"CORE-{101 + task_count}",
                    "ti": f"Implement {feature['text']}",
                    "d": f"Build the {feature['text']} functionality",
                    "f": "core.py",
                    "pr": "high"
                })
                task_count += 1

            state["step"] = 5
            total_tasks = sum(len(cat["t"]) for cat in state["prd"]["p"].values())

            response = (
                f"*beams proudly* {self._get_ralph_idiom()}! Added {task_count} features!\n\n"
                f"*types with two fingers* Updating your PRD... "
                f"Total tasks: {total_tasks}\n\n"
                f"Any special requirements or constraints, {self._get_salutation()} Worms? "
                f"(Deadlines, libraries, etc.)"
            )
            prd_preview = self._update_prd_display()
            return response, suggestions, prd_preview

        # Step 5: Got constraints - finalize and offer generation
        elif step == 5:
            state["constraints"].append(message)

            # Add security tasks
            state["prd"]["p"]["00_security"]["t"] = [
                {"id": "SEC-001", "ti": "Set up SECRET_KEY", "d": "Configure secret key", "f": "config.py", "pr": "!"},
                {"id": "SEC-002", "ti": "Input validation", "d": "Validate all inputs", "f": "validators.py", "pr": "high"},
            ]

            # Add setup tasks
            state["prd"]["p"]["01_setup"]["t"] = [
                {"id": "SET-001", "ti": "Initialize project", "d": f"Create {state['prd']['pn']} structure", "f": "setup.py", "pr": "high"},
                {"id": "SET-002", "ti": "Install deps", "d": "Install required packages", "f": "requirements.txt", "pr": "med"},
            ]

            state["step"] = 6
            total_tasks = sum(len(cat["t"]) for cat in state["prd"]["p"].values())

            response = (
                f"*adjusts tie* {self._get_ralph_idiom()}! Your PRD is coming together!\n\n"
                f"*types with two fingers* Finalizing...\n\n"
                f"**Total Tasks:** {total_tasks}\n"
                f"**Categories:** 5 phases (Security, Setup, Core, API, Test)\n\n"
                f"Ready to generate the complete PRD with the full compression "
                f"and legend, {self._get_salutation()} Worms?"
            )
            suggestions = [
                {"type": "generate_prd", "label": "Generate Full PRD 🚀", "id": "generate_prd"},
                {"type": "export", "format": "json", "label": "Export JSON 📋", "id": "export_json"}
            ]
            prd_preview = self._update_prd_display()
            return response, suggestions, prd_preview

        # Step 6: Generate full PRD
        elif step == 6:
            if action == "generate_prd" or "generate" in message_lower:
                try:
                    prd = self.engine.generate_prd(
                        project_name=state["prd"]["pn"],
                        description=state["prd"]["pd"],
                        starter_prompt=state["prd"]["sp"],
                        tech_stack=state["prd"]["ts"],
                        task_count=34
                    )
                    state["prd"] = prd
                    state["step"] = 7

                    total_tasks = sum(len(cat["t"]) for cat in prd.get("p", {}).values())

                    response = (
                        f"*beams proudly* {self._get_ralph_idiom()}! "
                        f"Your Ralph Mode PRD is complete, {self._get_salutation()} Worms!\n\n"
                        f"**Project:** {prd['pn']}\n"
                        f"**Total Tasks:** {total_tasks}\n\n"
                        f"The PRD is now in MAXIMUM COMPRESSION mode with the full legend at top! "
                        f"You can copy the whole thing and paste it right into an LLM. "
                        f"It's got the 'How to Ralph' instructions built right in! "
                        f"{self._get_computer_ref()}\n\n"
                        f"Want me to export it for you?"
                    )
                    suggestions = [
                        {"type": "export", "format": "copy_all", "label": "Copy All 📋", "id": "copy_all"}
                    ]
                    prd_preview = format_prd_display(prd, compressed=True)
                    return response, suggestions, prd_preview

                except Exception as e:
                    logger.error(f"PRD generation failed: {e}")
                    response = f"*apologetic bow* Well slap my thigh! Error: {str(e)}\n\nTry again?"
                    return response, suggestions, None
            else:
                response = f"*nods* Of course, {self._get_salutation()} Worms! What else?"
                prd_preview = self._update_prd_display()
                return response, suggestions, prd_preview

        # Default: continue chat
        response = (
            f"*listens intently* {message}, I see. "
            f"{self._get_ralph_idiom()}! Your PRD is being updated. "
            f"{self._get_computer_ref()}"
        )
        prd_preview = self._update_prd_display()
        return response, suggestions, prd_preview

    def _handle_suggestion_vote(self, suggestion_id: str, vote: str) -> Tuple[str, List[Dict], Optional[str]]:
        """Handle thumbs up/down on a suggestion"""
        state = self.conversation_state
        suggestions = state["suggestions"]

        # Find and update the suggestion
        for sugg in suggestions:
            if sugg["id"] == suggestion_id:
                sugg["approved"] = (vote == "up")
                sugg["rejected"] = (vote == "down")

                if vote == "up":
                    state["approved"].append(sugg)
                    response = f"*thumbs up back* {self._get_ralph_idiom()}! Added '{sugg['text']}' to your PRD!"
                else:
                    state["rejected"].append(sugg)
                    response = f"*nods* Got it. Skipping '{sugg['text']}'. {self._get_computer_ref()}"

                # Check if we should move to next step
                if len(state["approved"]) >= 2:
                    state["step"] = 5
                    response += "\n\n*types with two fingers* Okay, moving on! Any constraints?"

                return response, [], self._update_prd_display()

        return "*scratches head* Hmm, couldn't find that suggestion...", [], self._update_prd_display()

    def _update_prd_display(self) -> str:
        """Update PRD with current info and return compressed view"""
        prd = self.conversation_state["prd"]
        state = self.conversation_state

        # Update PRD with current info
        if state.get("purpose"):
            prd["pn"] = self._infer_project_name()
            prd["pd"] = state["purpose"][:200]
            prd["sp"] = state["purpose"]

        if state.get("tech_stack"):
            ts_map = {
                "python": {"lang": "Py", "fw": "Flask", "db": "PostgreSQL", "oth": []},
                "flask": {"lang": "Py", "fw": "Flask", "db": "PostgreSQL", "oth": []},
                "node": {"lang": "JS", "fw": "Express", "db": "MongoDB", "oth": []},
                "react": {"lang": "JS", "fw": "React", "db": "None", "oth": ["Node.js"]},
            }
            tech_input = state["tech_stack"].lower()
            prd["ts"] = ts_map.get(tech_input, ts_map.get("python"))

        return format_prd_display(prd, compressed=True)

    def get_prd(self) -> Optional[dict]:
        """Get the generated PRD"""
        return self.conversation_state.get("prd")

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation"""
        state = self.conversation_state
        parts = []

        if state.get("prd", {}).get("pn"):
            parts.append(f"Building: {state['prd']['pn']}")

        if state.get("prd", {}).get("ts", {}).get("fw"):
            parts.append(f"Tech: {state['prd']['ts']['fw']}")

        total_tasks = sum(len(cat["t"]) for cat in state.get("prd", {}).get("p", {}).values())
        if total_tasks > 0:
            parts.append(f"Tasks: {total_tasks}")

        return " | ".join(parts) if parts else "New Chat"


# Session storage for active conversations
_sessions: Dict[str, RalphChat] = {}


def get_chat_session(session_id: str) -> RalphChat:
    """Get or create a chat session"""
    if session_id not in _sessions:
        _sessions[session_id] = RalphChat(session_id)
    return _sessions[session_id]


def list_chat_sessions() -> List[Dict]:
    """List all chat sessions"""
    sessions = []
    for session_id, chat in _sessions.items():
        sessions.append({
            "id": session_id,
            "title": chat.get_conversation_summary(),
            "messages_count": len(chat.conversation_state["messages"])
        })
    return sorted(sessions, key=lambda x: x["messages_count"], reverse=True)
