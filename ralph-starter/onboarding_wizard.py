#!/usr/bin/env python3
"""
Onboarding Wizard for Ralph Mode

Guides users through setup with Ralph's personality.
Makes the technical stuff fun and accessible.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import git helper for first commit assistant (OB-030)
try:
    from git_helper import get_git_helper
    GIT_HELPER_AVAILABLE = True
except ImportError:
    GIT_HELPER_AVAILABLE = False
    logging.warning("Git helper not available for first commit assistant")

# Import Ralph personality module for narration
try:
    from ralph_personality import get_ralph_narrator
    RALPH_NARRATOR_AVAILABLE = True
except ImportError:
    RALPH_NARRATOR_AVAILABLE = False

# Import bot tester for OB-039
try:
    from bot_tester import get_bot_tester
    BOT_TESTER_AVAILABLE = True
except ImportError:
    BOT_TESTER_AVAILABLE = False
    logging.warning("Bot tester not available")


class OnboardingWizard:
    """Handles the onboarding flow for new users."""

    # Onboarding steps
    STEP_WELCOME = "welcome"
    STEP_SETUP_TYPE = "setup_type"
    STEP_SSH_KEY = "ssh_key"
    STEP_GITHUB = "github"
    STEP_REPO = "repo"
    STEP_CHARACTER = "character"  # OB-041: Character avatar selection
    STEP_THEME = "theme"  # OB-040: Visual theme selection
    STEP_BOT_TEST = "bot_test"  # OB-039: Bot testing walkthrough
    STEP_COMPLETE = "complete"

    # Setup types
    SETUP_GUIDED = "guided"
    SETUP_QUICK = "quick"

    def __init__(self):
        """Initialize the onboarding wizard."""
        self.logger = logging.getLogger(__name__)

        # Initialize Ralph narrator (OB-032: Story Mode Narration)
        if RALPH_NARRATOR_AVAILABLE:
            self.narrator = get_ralph_narrator()
        else:
            self.narrator = None
            self.logger.warning("Ralph narrator not available")

        # Import setup state manager
        try:
            from setup_state import get_setup_state_manager
            self.state_manager = get_setup_state_manager()
            self.state_persistence_available = True
        except ImportError:
            self.state_manager = None
            self.state_persistence_available = False
            self.logger.warning("Setup state persistence not available")

        # Import rollback manager
        try:
            from rollback_manager import get_rollback_manager
            self.rollback_manager = get_rollback_manager()
            self.rollback_available = True
        except ImportError:
            self.rollback_manager = None
            self.rollback_available = False
            self.logger.warning("Rollback functionality not available")

        # Import setup verifier
        try:
            from setup_verifier import get_setup_verifier
            self.verifier = get_setup_verifier()
            self.verifier_available = True
        except ImportError:
            self.verifier = None

        # Import tutorial library
        try:
            from tutorial_library import get_tutorial_library
            self.tutorials = get_tutorial_library()
            self.tutorials_available = True
        except ImportError:
            self.tutorials = None
            self.tutorials_available = False
            self.logger.warning("Tutorial library not available")
            self.verifier_available = False
            self.logger.warning("Setup verification not available")

        # Import troubleshooting guide
        try:
            from troubleshooting import get_troubleshooting_guide
            self.troubleshooting = get_troubleshooting_guide()
            self.troubleshooting_available = True
        except ImportError:
            self.troubleshooting = None
            self.troubleshooting_available = False
            self.logger.warning("Troubleshooting guide not available")

        # Import environment file manager (OB-008)
        try:
            from env_manager import EnvManager
            self.env_manager = EnvManager()
            self.env_manager_available = True
        except ImportError:
            self.env_manager = None
            self.env_manager_available = False
            self.logger.warning("Environment file manager not available")

        # Import API key manager (OB-009)
        try:
            from api_key_manager import get_api_key_manager
            self.api_key_manager = get_api_key_manager()
            self.api_key_validation_available = True
        except ImportError:
            self.api_key_manager = None
            self.api_key_validation_available = False
            self.logger.warning("API key validation not available")

        # Import git helper (OB-030: First Commit Assistant)
        if GIT_HELPER_AVAILABLE:
            self.git_helper = get_git_helper()
        else:
            self.git_helper = None
            self.logger.warning("Git helper not available for first commit assistant")

        # Import progress tracker (OB-013: Progress Tracker UI)
        try:
            from progress_tracker import get_progress_tracker
            self.progress_tracker = get_progress_tracker()
            self.progress_tracker_available = True
        except ImportError:
            self.progress_tracker = None
            self.progress_tracker_available = False
            self.logger.warning("Progress tracker not available")

        # Import bot tester (OB-039: Bot Testing Walkthrough)
        if BOT_TESTER_AVAILABLE:
            self.bot_tester = get_bot_tester()
        else:
            self.bot_tester = None
            self.logger.warning("Bot tester not available")

        # Import theme manager (OB-040: Visual Theme Selector)
        try:
            from theme_manager import get_theme_manager
            self.theme_manager = get_theme_manager()
            self.theme_manager_available = True
        except ImportError:
            self.theme_manager = None
            self.theme_manager_available = False
            self.logger.warning("Theme manager not available")

        # Import user preferences (OB-041: Character Avatar Selection)
        try:
            from user_preferences import get_user_preferences
            self.user_prefs = get_user_preferences()
            self.user_prefs_available = True
        except ImportError:
            self.user_prefs = None
            self.user_prefs_available = False
            self.logger.warning("User preferences not available")

        # Import doc generator (OB-050: Onboarding Documentation Generator)
        try:
            from doc_generator import get_doc_generator
            self.doc_generator = get_doc_generator()
            self.doc_generator_available = True
        except ImportError:
            self.doc_generator = None
            self.doc_generator_available = False
            self.logger.warning("Documentation generator not available")

        # Import PRD generator (OB-028: PRD Template Generator)
        try:
            from prd_generator import get_prd_generator
            self.prd_generator = get_prd_generator()
            self.prd_generator_available = True
        except ImportError:
            self.prd_generator = None
            self.prd_generator_available = False
            self.logger.warning("PRD generator not available")

    def get_welcome_message(self) -> str:
        """Get Ralph's welcoming onboarding message.

        Returns:
            Welcome message with Ralph's personality
        """
        return """*Welcome to Ralph Mode Setup!* 🍩

Me Ralph! Me help you set up AI team!

*What we gonna do:*
• Get your computer talking to GitHub (that's where code lives!)
• Make a special house for your code (called "repository")
• Connect Ralph's brain to your computer
• Make sure everything works good!

Don't worry! Ralph make it super easy! Like eating paste... but PRODUCTIVE!

*Two ways to do this:*

🎯 *Guided Setup* - Ralph walks you through every step
   Perfect if this is your first time!
   Ralph explains EVERYTHING!

⚡ *Quick Setup* - For smarty-pants who did this before
   Just the important stuff!

*Which one you want?*
"""

    def get_welcome_keyboard(self) -> InlineKeyboardMarkup:
        """Get the welcome screen keyboard with setup type options.

        Returns:
            Keyboard markup with Guided/Quick setup buttons
        """
        keyboard = [
            [
                InlineKeyboardButton("🎯 Guided Setup (Recommended)", callback_data="setup_guided"),
            ],
            [
                InlineKeyboardButton("⚡ Quick Setup", callback_data="setup_quick"),
            ],
        ]

        # Add troubleshooting option if available
        if self.troubleshooting_available:
            keyboard.append([
                InlineKeyboardButton("🔧 Troubleshooting Guide", callback_data="troubleshoot_menu")
            ])

        return InlineKeyboardMarkup(keyboard)

    def get_setup_overview(self, setup_type: str) -> str:
        """Get the setup overview based on chosen type.

        Args:
            setup_type: Either 'guided' or 'quick'

        Returns:
            Overview message for the selected setup type
        """
        if setup_type == self.SETUP_GUIDED:
            return """*Okay! Ralph do Guided Setup!* 👍

Me gonna help you with:

**Step 1:** Make special key for GitHub 🔑
   (Like a super secret password but fancier!)

**Step 2:** Tell GitHub about your key 🎫
   (So GitHub knows it's really you!)

**Step 3:** Make a code house (repository) 🏠
   (Where your code lives!)

**Step 4:** Connect Ralph to everything 🔌
   (The magic part!)

Ralph take it slow! No rush! We do together!

*Ready to start?*
"""
        else:  # Quick setup
            return """*Quick Setup Mode Activated!* ⚡

Ralph assume you know the drill!

**Quick checklist:**
✅ SSH key for GitHub
✅ GitHub repository created
✅ Repository URL configured
✅ Claude Code installed

Ralph help you check each one super fast!

*Let's go!*
"""

    def get_overview_keyboard(self) -> InlineKeyboardMarkup:
        """Get the keyboard for the overview screen.

        Returns:
            Keyboard markup with Continue button
        """
        keyboard = [
            [InlineKeyboardButton("▶️ Let's Go!", callback_data="setup_continue")],
            [InlineKeyboardButton("◀️ Back", callback_data="setup_back_welcome")],
        ]

        # Add troubleshooting option if available
        if self.troubleshooting_available:
            keyboard.append([
                InlineKeyboardButton("🔧 Need Help?", callback_data="troubleshoot_menu")
            ])

        return InlineKeyboardMarkup(keyboard)

    def init_onboarding_state(self, user_id: int) -> Dict[str, Any]:
        """Initialize onboarding state for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Initial onboarding state dictionary
        """
        from datetime import datetime

        return {
            "step": self.STEP_WELCOME,
            "setup_type": None,
            "ssh_key_generated": False,
            "ssh_key_added_to_github": False,
            "repo_created": False,
            "repo_url": None,
            "git_configured": False,
            "git_name": None,
            "git_email": None,
            "first_commit": False,  # OB-013: Progress Tracker UI
            "environment_setup": False,  # OB-013: Progress Tracker UI
            "bot_tested": False,  # OB-039: Bot Testing Walkthrough
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }

    def update_step(self, state: Dict[str, Any], new_step: str) -> Dict[str, Any]:
        """Update the current step in onboarding state.

        Args:
            state: Current onboarding state
            new_step: New step to move to

        Returns:
            Updated state dictionary
        """
        state["step"] = new_step
        return state

    def set_setup_type(self, state: Dict[str, Any], setup_type: str) -> Dict[str, Any]:
        """Set the setup type in onboarding state.

        Args:
            state: Current onboarding state
            setup_type: Either 'guided' or 'quick'

        Returns:
            Updated state dictionary
        """
        state["setup_type"] = setup_type
        return state

    def is_onboarding_complete(self, state: Dict[str, Any]) -> bool:
        """Check if onboarding is complete.

        Args:
            state: Current onboarding state

        Returns:
            True if onboarding is complete, False otherwise
        """
        return (
            state.get("ssh_key_generated", False) and
            state.get("ssh_key_added_to_github", False) and
            state.get("repo_created", False) and
            state.get("repo_url") is not None
        )

    def get_progress_message(self, state: Dict[str, Any], current_step: str = None) -> str:
        """Get a progress message showing what's been completed.

        Args:
            state: Current onboarding state
            current_step: ID of the current step being worked on (optional)

        Returns:
            Progress message string with Ralph's encouragement (OB-032, OB-013)
        """
        # Use new progress tracker if available (OB-013)
        if self.progress_tracker_available:
            base_message = self.progress_tracker.get_progress_message(state, current_step)

            # Add Ralph's encouragement based on progress (OB-032)
            encouragement = ""
            if self.narrator:
                if self.progress_tracker.is_setup_complete(state):
                    encouragement = f"\n\n{self.narrator.get_encouragement('milestone')}"
                else:
                    # Count completed steps
                    completed_count = sum([
                        state.get(step["id"], False)
                        for step in self.progress_tracker.SETUP_STEPS
                    ])
                    if completed_count > 0:
                        encouragement = f"\n\n{self.narrator.get_encouragement('progress')}"

            return base_message + encouragement

        # Fallback to old implementation if progress tracker not available
        progress = []
        completed_count = 0
        total_steps = 5

        if state.get("ssh_key_generated"):
            progress.append("✅ SSH key generated")
            completed_count += 1
        else:
            progress.append("⬜ SSH key not generated yet")

        if state.get("ssh_key_added_to_github"):
            progress.append("✅ SSH key added to GitHub")
            completed_count += 1
        else:
            progress.append("⬜ SSH key not added to GitHub yet")

        if state.get("repo_created"):
            progress.append("✅ Repository created")
            completed_count += 1
        else:
            progress.append("⬜ Repository not created yet")

        if state.get("repo_url"):
            progress.append(f"✅ Repository URL: {state['repo_url']}")
            completed_count += 1
        else:
            progress.append("⬜ Repository URL not configured")

        if state.get("git_configured"):
            progress.append(f"✅ Git configured ({state.get('git_name', 'Unknown')})")
            completed_count += 1
        else:
            progress.append("⬜ Git not configured yet")

        # Add Ralph's encouragement based on progress (OB-032)
        encouragement = ""
        if self.narrator:
            if completed_count == total_steps:
                encouragement = f"\n\n{self.narrator.get_encouragement('milestone')}"
            elif completed_count > 0:
                encouragement = f"\n\n{self.narrator.get_encouragement('progress')}"

        return "*Your Progress:*\n\n" + "\n".join(progress) + encouragement

    def get_visual_progress_with_current_step(self, state: Dict[str, Any], current_step_id: str = None) -> str:
        """Get visual progress display highlighting the current step.

        Args:
            state: Current onboarding state
            current_step_id: ID of the step being worked on (e.g., 'ssh_key_generated')

        Returns:
            Visual progress message with current step highlighted (OB-013)
        """
        if self.progress_tracker_available:
            return self.progress_tracker.get_progress_message(state, current_step_id)
        else:
            # Fallback to regular progress message
            return self.get_progress_message(state)

    def get_celebration_message_with_checklist(self, state: Dict[str, Any]) -> str:
        """Get celebration message when setup is complete with full checklist.

        Args:
            state: Completed onboarding state

        Returns:
            Celebration message with visual checklist (OB-013)
        """
        if self.progress_tracker_available and self.progress_tracker.is_setup_complete(state):
            return self.progress_tracker.get_celebration_message(state)
        else:
            # Fallback to basic message
            return "*🎉 Setup Complete! 🎉*\n\nGreat job! You're all set to start using Ralph Mode!"

    # SSH Key Generation Wizard (OB-002)

    def get_ssh_key_intro_message(self) -> str:
        """Get Ralph's introduction to SSH keys.

        Returns:
            SSH key explanation message with Ralph's personality
        """
        return """*Step 1: Make Your Special Key!* 🔑

Okay! Ralph explain what SSH key is!

Think of it like this: GitHub is a big building with code inside. But they don't let just ANYBODY in! You need a special key!

*SSH key is like:*
• A super secret handshake 🤝
• A magic password that never gets typed 🎩
• Your special badge that says "This is ME!" 👤

The cool part? You make TWO keys:
• **Private key** - stays on YOUR computer FOREVER (never share!)
• **Public key** - you give this to GitHub (it's safe!)

It's like having a lock (GitHub) and a key (your computer). GitHub keeps the lock, you keep the key!

Ralph check if you already got one...
"""

    def get_ssh_check_command(self) -> str:
        """Get the command to check if SSH key exists.

        Returns:
            Shell command string
        """
        return "ls -la ~/.ssh/id_*.pub"

    def get_ssh_keygen_command(self, email: Optional[str] = None) -> str:
        """Get the SSH key generation command.

        Args:
            email: User's email address for the key (optional)

        Returns:
            ssh-keygen command string
        """
        if email:
            return f'ssh-keygen -t ed25519 -C "{email}" -f ~/.ssh/id_ed25519 -N ""'
        return 'ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""'

    def get_ssh_keygen_message(self, has_existing_key: bool = False, email: Optional[str] = None) -> str:
        """Get the message for SSH key generation step.

        Args:
            has_existing_key: Whether user already has an SSH key
            email: User's email address for the key (optional)

        Returns:
            SSH key generation message
        """
        if has_existing_key:
            return """*Ralph found SSH key!* 🎉

You already got a key! Look at you being all prepared!

*What you wanna do?*

**Option 1:** Use the key you already got (easier!)
**Option 2:** Make a brand new key (start fresh!)

Ralph think Option 1 is good unless old key is broken or lost!
"""

        keygen_cmd = self.get_ssh_keygen_command(email)

        # Get tutorial link
        tutorial_section = ""
        if self.tutorials_available and self.tutorials:
            ssh_tutorial = self.tutorials.get_tutorial("ssh_keys", 0)
            if ssh_tutorial:
                tutorial_section = f"""
*Need help?* Watch this video:
🎥 [{ssh_tutorial.title}]({ssh_tutorial.url})
   ⏱️ {ssh_tutorial.duration} | Skip to 2:30 for the command!
"""
            else:
                tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"
        else:
            tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"

        return f"""*Time to Make Your Key!* 🔨

Ralph give you magic command! Just copy and paste into your terminal!

*Copy this command:*
```bash
{keygen_cmd}
```

*What this does:*
• `-t ed25519` - Makes super secure key (fancy math!)
• `-C "{email or 'your-email'}"` - Puts your name on it
• `-f ~/.ssh/id_ed25519` - Where to save it
• `-N ""` - No extra password (makes it easier!)

*Steps:*
1. Open your Terminal (or Command Prompt on Windows)
2. Copy the command above
3. Paste it in and press Enter
4. Wait a few seconds... DONE!

Ralph make it so the key has no passphrase so it's easier to use! If you want extra security, you can remove the `-N ""` part and it will ask you for a passphrase!
{tutorial_section}
*Did you run the command?*
"""

    def get_ssh_keygen_keyboard(self, has_existing_key: bool = False) -> InlineKeyboardMarkup:
        """Get the keyboard for SSH key generation step.

        Args:
            has_existing_key: Whether user already has an SSH key

        Returns:
            Keyboard markup with relevant buttons
        """
        if has_existing_key:
            keyboard = [
                [InlineKeyboardButton("✅ Use Existing Key", callback_data="ssh_use_existing")],
                [InlineKeyboardButton("🔄 Generate New Key", callback_data="ssh_generate_new")],
                [InlineKeyboardButton("❓ Check Again", callback_data="ssh_check_again")],
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("✅ I ran the command!", callback_data="ssh_key_generated")],
                [InlineKeyboardButton("📋 Copy Command Again", callback_data="ssh_copy_command")],
                [InlineKeyboardButton("❓ Need Help", callback_data="ssh_help")],
                [InlineKeyboardButton("◀️ Back", callback_data="setup_back_overview")],
            ]
        return InlineKeyboardMarkup(keyboard)

    def get_ssh_success_message(self) -> str:
        """Get the success message after SSH key generation.

        Returns:
            Success message with Ralph's personality and celebration (OB-032)
        """
        # Add celebration message (OB-032)
        celebration = ""
        if self.narrator:
            celebration = self.narrator.get_celebration("SSH key created") + "\n\n"

        return f"""{celebration}*You did it!* 🎊

Ralph so proud! You made a SSH key!

Your computer now has a special badge! The key is saved in a secret folder on your computer (called `.ssh`).

*What we got now:*
✅ Private key (stays on your computer)
✅ Public key (we give this to GitHub next!)

The files are called:
• `id_ed25519` - Your private key (NEVER share!)
• `id_ed25519.pub` - Your public key (this one is safe to share!)

*Next step:* We gonna tell GitHub about your public key!

Ready?
"""

    def get_ssh_help_message(self) -> str:
        """Get help message for SSH key generation issues.

        Returns:
            Help message with troubleshooting tips and Ralph's humor (OB-032)
        """
        # Add humorous error intro (OB-032)
        error_intro = ""
        if self.narrator:
            error_intro = self.narrator.get_error_message("general") + "\n\n"

        # Get tutorial links
        tutorial_section = ""
        if self.tutorials_available and self.tutorials:
            ssh_tutorial = self.tutorials.get_tutorial("ssh_keys", 0)
            if ssh_tutorial:
                tutorial_section = f"""
*Watch This Video:*
🎥 [{ssh_tutorial.title}]({ssh_tutorial.url})
   ⏱️ {ssh_tutorial.duration}
   Key sections: 1:15 for checking keys, 2:30 for generation
"""
            else:
                tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"
        else:
            tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"

        return f"""{error_intro}*Ralph Help You!* 🆘

**Common Problems:**

**Problem 1:** "Command not found"
→ Make sure you in Terminal (Mac/Linux) or Git Bash (Windows)
→ Windows users might need to install Git first!

**Problem 2:** "File already exists"
→ You already got a key! Use the "Check Again" button
→ Ralph can help you use that one instead!

**Problem 3:** "Permission denied"
→ Try adding `sudo` at the start (but usually not needed!)
→ Make sure you can write to your home folder

**Problem 4:** "I don't know what terminal is!"
→ Mac: Search for "Terminal" in Spotlight
→ Windows: Search for "Command Prompt" or install Git Bash
→ Linux: You probably know already! 😉
{tutorial_section}
Still stuck? Tell Ralph what error message you seeing!
"""

    # GitHub SSH Key Addition Guide (OB-003)

    def get_public_key_command(self) -> str:
        """Get the command to read the public key.

        Returns:
            Command to display public key content
        """
        return "cat ~/.ssh/id_ed25519.pub"

    def get_github_ssh_guide_message(self) -> str:
        """Get the message for adding SSH key to GitHub.

        Returns:
            GitHub SSH addition guide message
        """
        return """*Step 2: Tell GitHub About Your Key!* 🎫

Okay! Now GitHub needs to know your public key!

Remember: public key is SAFE to share! (The other one stays secret!)

*Here's what we gonna do:*

**Step 1:** Copy your public key
**Step 2:** Go to GitHub settings
**Step 3:** Paste the key
**Step 4:** Test it works!

Ralph walk you through each step!

*First, let's get your public key...*

Run this command in Terminal:
```bash
cat ~/.ssh/id_ed25519.pub
```

This will show your public key! It looks like random letters and numbers!

*Ready to copy your key?*
"""

    def get_github_ssh_instructions_message(self) -> str:
        """Get detailed instructions for adding SSH key to GitHub.

        Returns:
            Detailed step-by-step instructions
        """
        # Get tutorial link
        tutorial_section = ""
        if self.tutorials_available and self.tutorials:
            github_tutorial = self.tutorials.get_tutorial("ssh_keys", 0)
            if github_tutorial:
                tutorial_section = f"""
*Need Help?*
🎥 [{github_tutorial.title}]({github_tutorial.url})
   ⏱️ {github_tutorial.duration} | Skip to 4:45 for adding to GitHub!
"""
            else:
                tutorial_section = "\n*Need Help?* Check Ralph Mode documentation!"
        else:
            tutorial_section = "\n*Need Help?* Check Ralph Mode documentation!"

        return f"""*Adding Key to GitHub - Step by Step!* 📝

Okay! Follow these steps EXACTLY!

**Step 1: Copy Your Public Key**
Run this command:
```bash
cat ~/.ssh/id_ed25519.pub
```
Copy EVERYTHING it shows (starts with `ssh-ed25519`)

**Step 2: Go to GitHub**
Click this link: [GitHub SSH Settings](https://github.com/settings/keys)

**Step 3: Add New SSH Key**
• Click the green "New SSH key" button
• Title: Put "My Computer" (or whatever you want!)
• Key type: Choose "Authentication Key"
• Key: Paste what you copied from Step 1
• Click "Add SSH key"

**Step 4: You might need to enter your GitHub password**
That's normal! GitHub making sure it's really you!

*Done?* Click the button below when you added the key!
{tutorial_section}
"""

    def get_github_ssh_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for GitHub SSH addition step.

        Returns:
            Keyboard with relevant action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🔗 Open GitHub SSH Settings", url="https://github.com/settings/keys")],
            [InlineKeyboardButton("✅ I Added the Key!", callback_data="github_ssh_added")],
            [InlineKeyboardButton("📋 Show Command Again", callback_data="github_show_key_command")],
            [InlineKeyboardButton("❓ Need Help", callback_data="github_ssh_help")],
            [InlineKeyboardButton("◀️ Back", callback_data="setup_back_ssh")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_ssh_test_command(self) -> str:
        """Get the command to test SSH connection to GitHub.

        Returns:
            SSH test command
        """
        return "ssh -T git@github.com"

    def get_github_ssh_test_message(self) -> str:
        """Get message for testing GitHub SSH connection.

        Returns:
            SSH connection test instructions
        """
        return """*Let's Test It!* 🧪

Ralph wanna make sure it works!

Run this command to test your connection:
```bash
ssh -T git@github.com
```

*What you'll see:*

If it WORKS, you'll see:
```
Hi [your-username]! You've successfully authenticated...
```

If it asks "Are you sure you want to continue connecting?", type `yes` and press Enter!

Don't worry if it says "You've successfully authenticated, but GitHub does not provide shell access" - that's GOOD! It means it works!

If you see an error, click "Help" below!

*Did you run the test?*
"""

    def get_github_ssh_test_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for SSH connection test.

        Returns:
            Keyboard with test result options
        """
        keyboard = [
            [InlineKeyboardButton("✅ It Works!", callback_data="github_ssh_success")],
            [InlineKeyboardButton("❌ Got an Error", callback_data="github_ssh_error")],
            [InlineKeyboardButton("📋 Show Command Again", callback_data="github_show_test_command")],
            [InlineKeyboardButton("❓ Help", callback_data="github_ssh_test_help")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_github_ssh_success_message(self) -> str:
        """Get success message after GitHub SSH is working.

        Returns:
            Success celebration message
        """
        return """*IT WORKS!* 🎉🎊🎈

Ralph SO PROUD of you!

Your computer can now talk to GitHub! No more typing passwords!

*What we did:*
✅ Made a special key on your computer
✅ Told GitHub about your key
✅ Tested the connection
✅ EVERYTHING WORKS!

You're like a REAL developer now! 👨‍💻👩‍💻

*Next step:* Make a code house (repository) for your projects!

Ready to keep going?
"""

    def get_github_ssh_error_help(self) -> str:
        """Get help message for SSH connection errors.

        Returns:
            Troubleshooting help for SSH errors
        """
        # Get troubleshooting tutorial
        tutorial_section = ""
        if self.tutorials_available and self.tutorials:
            troubleshoot_tutorial = self.tutorials.get_tutorial("troubleshooting", 0)
            if troubleshoot_tutorial:
                tutorial_section = f"""
*Still stuck?*
🎥 [{troubleshoot_tutorial.title}]({troubleshoot_tutorial.url})
   ⏱️ {troubleshoot_tutorial.duration} | See 0:45 for permission errors
"""
            else:
                tutorial_section = "\n*Still stuck?* Check Ralph Mode documentation!"
        else:
            tutorial_section = "\n*Still stuck?* Check Ralph Mode documentation!"

        return f"""*Ralph Help Fix It!* 🔧

**Common Errors and Fixes:**

**Error: "Permission denied (publickey)"**
→ Your key isn't added to GitHub or you added the PRIVATE key by mistake
→ Make sure you copied the PUBLIC key (ends with .pub)
→ Try adding the key to GitHub again

**Error: "Could not resolve hostname github.com"**
→ Check your internet connection!
→ Make sure you spelled github.com correctly

**Error: "Host key verification failed"**
→ Type `yes` when it asks "Are you sure you want to continue?"
→ This is normal the first time!

**Error: "No such file or directory"**
→ Your SSH key might not exist
→ Go back and generate the key first

**Wrong key copied?**
→ Make sure you ran: `cat ~/.ssh/id_ed25519.pub`
→ Copy EVERYTHING from ssh-ed25519 to the end
→ Don't copy the PRIVATE key (without .pub)!
{tutorial_section}
Try the test command again, or go back and add the key again!
"""

    # Git Configuration Setup (OB-005)

    def get_git_config_intro_message(self) -> str:
        """Get introduction message for git configuration.

        Returns:
            Git configuration introduction with Ralph's narration (OB-032)
        """
        # Add step introduction narration (OB-032)
        step_intro = ""
        if self.narrator:
            step_intro = self.narrator.get_step_intro("Git Configuration") + "\n\n"

        return f"""{step_intro}*Time to Tell Git Who You Are!* 👤

Okay! Before you start making code, Git needs to know YOUR name!

*What's Git?*
Git is like a time machine for your code! It remembers every change you make!

But Git is kinda forgetful about WHO made the changes... so we gotta tell it!

Think of it like:
• Writing your name in your school notebook 📓
• Putting a name tag on your art project 🎨
• Signing your homework before you turn it in ✍️

Every time you save code (called a "commit"), Git writes your name on it! That way everyone knows YOU did the awesome work!

*What Ralph needs:*
• Your name (like "John Smith" or whatever you wanna be called!)
• Your email (the one you used for GitHub)

This shows up in the history! Other developers see it! Make it good!

*Ready to set it up?*
"""

    def get_git_config_name_request_message(self) -> str:
        """Get message asking for user's name.

        Returns:
            Name request message
        """
        return """*What's Your Name?* 📝

Ralph need your name for Git!

This can be:
• Your real name: "Sarah Johnson"
• Your nickname: "CodeMaster3000"
• Your username: "sarahjdev"
• Whatever you want people to see in commit history!

*Examples of good names:*
✅ John Smith
✅ Jane Developer
✅ CoolCoder99
✅ j.smith

*Examples of bad names:*
❌ asdfgh
❌ user
❌ me

Remember: This shows up FOREVER in your code history! Choose something you proud of!

*Type your name:*
"""

    def get_git_config_email_request_message(self) -> str:
        """Get message asking for user's email.

        Returns:
            Email request message
        """
        return """*What's Your Email?* 📧

Ralph need your email for Git!

**IMPORTANT:** Use the SAME email you used when you signed up for GitHub!

Why? Because GitHub uses the email to link your commits to your account! If you use a different email, your commits won't show up on your profile!

*Where to find your GitHub email:*
Go to: https://github.com/settings/emails
Look for your PRIMARY email!

*Type your email:*
(Don't worry, Ralph only saves it on YOUR computer! Nobody else sees it unless you make your repo public!)
"""

    def get_git_config_commands(self, name: str, email: str) -> tuple:
        """Get the git config commands for setting name and email.

        Args:
            name: User's name
            email: User's email

        Returns:
            Tuple of (name_command, email_command)
        """
        name_cmd = f'git config --global user.name "{name}"'
        email_cmd = f'git config --global user.email "{email}"'
        return name_cmd, email_cmd

    def get_git_config_command_message(self, name: str, email: str) -> str:
        """Get message with git config commands.

        Args:
            name: User's name
            email: User's email

        Returns:
            Message with copy-paste commands
        """
        name_cmd, email_cmd = self.get_git_config_commands(name, email)

        return f"""*Perfect! Let's Save Your Info!* 💾

Okay {name}! Ralph give you TWO magic commands!

**Command 1: Set Your Name**
```bash
{name_cmd}
```

**Command 2: Set Your Email**
```bash
{email_cmd}
```

*What these do:*
• `git config` - Changes Git settings
• `--global` - Makes it work for ALL your projects (not just one!)
• `user.name` - Your name setting
• `user.email` - Your email setting

*Steps:*
1. Open Terminal (or Command Prompt)
2. Copy the FIRST command and press Enter
3. Copy the SECOND command and press Enter
4. That's it!

You won't see any output if it works! No news is GOOD news!

*Did you run both commands?*
"""

    def get_git_config_verify_command(self) -> str:
        """Get command to verify git configuration.

        Returns:
            Git config verification command
        """
        return "git config --list | grep user"

    def get_git_config_verify_message(self) -> str:
        """Get message for verifying git configuration.

        Returns:
            Verification instructions
        """
        return """*Let's Check If It Worked!* 🔍

Ralph wanna make sure Git knows who you are!

Run this command to check:
```bash
git config --list | grep user
```

*What you should see:*
```
user.name=Your Name
user.email=your.email@example.com
```

If you see that, IT WORKED! 🎉

If you see nothing, or wrong info, we can fix it! Just click "Need Help" below!

*What did you see?*
"""

    def get_git_config_verify_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for git config verification.

        Returns:
            Keyboard with verification options
        """
        keyboard = [
            [InlineKeyboardButton("✅ It Worked!", callback_data="git_config_success")],
            [InlineKeyboardButton("❌ Didn't Work", callback_data="git_config_error")],
            [InlineKeyboardButton("📋 Show Commands Again", callback_data="git_show_config_commands")],
            [InlineKeyboardButton("❓ Need Help", callback_data="git_config_help")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_git_config_success_message(self) -> str:
        """Get success message after git configuration.

        Returns:
            Success celebration message
        """
        return """*Git Knows Who You Are!* 🎊

Ralph SO PROUD! You configured Git!

Now every time you save your code, Git writes YOUR name on it!

*What this means:*
✅ Your commits show YOUR name
✅ GitHub knows it's you
✅ Your profile shows your contributions
✅ You're officially a Git user now!

*Fun fact:*
This is saved FOREVER in commit history! In 10 years, people can see who wrote the code! That's pretty cool!

*What's a commit?*
A "commit" is like taking a snapshot of your code! Git saves it with:
• The code changes you made
• YOUR name (that we just set up!)
• The date and time
• A message about what you changed

It's like a diary entry for your code! 📔

*Next up:*
Ralph can help you make your first commit! Or we keep setting up other stuff!

What you wanna do?
"""

    def get_git_config_help_message(self) -> str:
        """Get help message for git configuration issues.

        Returns:
            Git config troubleshooting help
        """
        return """*Ralph Help Fix Git Config!* 🔧

**Common Problems:**

**Problem 1: "git command not found"**
→ You need to install Git first!
→ Mac: Download from https://git-scm.com/download/mac
→ Windows: Download from https://git-scm.com/download/windows
→ Linux: `sudo apt install git` (Ubuntu) or `sudo yum install git` (Fedora)

**Problem 2: "Nothing shows when I check"**
→ Commands might have failed silently
→ Try running them again one at a time
→ Make sure you using the right Terminal/Command Prompt

**Problem 3: "Shows different name/email"**
→ You already configured Git before!
→ Just run the commands again with the NEW info
→ It will overwrite the old settings!

**Problem 4: "I don't know if it worked"**
→ Run: `git config user.name` to see your name
→ Run: `git config user.email` to see your email
→ If they show up, it worked!

**Problem 5: "I made a typo in my name/email!"**
→ No problem! Just run the commands again with the CORRECT info!
→ Git will update it!

*Why --global?*
The `--global` flag means this works for ALL your projects!
Without it, you'd have to set it up for EACH project separately!
Ralph recommend always use --global for your personal computer!

*Still stuck?*
Tell Ralph exactly what error message you seeing!
Or what shows when you run `git config --list`
"""

    def get_git_config_explanation_message(self) -> str:
        """Get kid-friendly explanation of version control.

        Returns:
            Version control explanation
        """
        return """*What's Version Control? Ralph Explains!* 📚

Okay! Ralph make this SUPER simple!

*Imagine you writing a story...*

**WITHOUT version control:**
• You write: "The cat sat on the mat"
• Next day you change it to: "The dog sat on the mat"
• But now you forget what it was before!
• If you mess up, you can't go back!
• You have to save "story_v1.txt", "story_v2.txt", "story_FINAL.txt", "story_FINAL_REAL.txt"... CHAOS!

**WITH version control (Git):**
• You write: "The cat sat on the mat" → Save it! (commit)
• Next day: "The dog sat on the mat" → Save it! (commit)
• Git remembers BOTH versions!
• You can see what changed!
• You can go back to "cat" if you want!
• Only one file! Git handles all the versions!

*For code, it's even better:*
• You try adding a feature → Commit
• Feature breaks everything → No problem! Go back!
• You wanna see what you changed last week → Git shows you!
• Working with friends → Git merges everyone's code!

Think of Git like:
• 💾 A save system in a video game (but for code!)
• 📸 A photo album of your code over time
• ⏰ A time machine you can use to go back
• 📖 A history book that never forgets

*Why developers LOVE Git:*
✅ Never lose code
✅ Try new things without fear
✅ Work with other people without chaos
✅ See who changed what and when
✅ Go back if something breaks

Ralph uses Git EVERY DAY! All the professionals do!

*Cool right?* Now you know why we set up your name! 🎉
"""

    # Anthropic API Key Setup (OB-006)

    def get_anthropic_api_intro_message(self) -> str:
        """Get introduction message for Anthropic API key setup.

        Returns:
            Anthropic API key introduction
        """
        return """*Time to Connect Ralph's Brain!* 🧠

Okay! This is the IMPORTANT part!

Ralph needs a special key to talk to Claude AI! That's what makes Ralph smart!

*What's an API key?*
Think of it like:
• A library card for using Claude's brain 📚
• A ticket to ride the AI train 🎫
• Your permission slip to use super smart AI 📝

This key connects Ralph to Anthropic's servers, where Claude lives!

*Why you need this:*
• Ralph uses Claude to understand your code
• Claude writes the actual code changes
• Without this key, Ralph just a regular bot!

*Important:*
⚠️ API keys are SECRETS! Never share them!
⚠️ Don't put them in your code or GitHub!
⚠️ Only put them in the `.env` file (which stays on YOUR computer!)

*Ready to get your key?*
"""

    def get_anthropic_signup_message(self) -> str:
        """Get message with signup instructions for Anthropic.

        Returns:
            Signup instructions message
        """
        return """*Step 1: Sign Up for Anthropic!* 📝

First, you need an Anthropic account!

*Follow these steps:*

**Step 1:** Click the link below to go to Anthropic
**Step 2:** Click "Sign Up" or "Get Started"
**Step 3:** Create your account (use email or Google)
**Step 4:** Verify your email if needed

*The link:*
🔗 [Anthropic Console](https://console.anthropic.com)

*After you sign up:*
You might need to add a payment method! Don't worry - Anthropic gives you FREE credits to start!

**Pricing (as of 2024):**
• You get some free credits when you sign up
• After that, it's pay-as-you-go
• Claude is VERY affordable (pennies per request!)
• You can set spending limits!

Ralph recommend starting with free credits to test everything!

*Need help understanding pricing?*
🎥 [Anthropic Pricing Guide](https://www.anthropic.com/pricing)

*Did you create your account?*
"""

    def get_anthropic_signup_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for Anthropic signup step.

        Returns:
            Keyboard with signup action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🔗 Open Anthropic Console", url="https://console.anthropic.com")],
            [InlineKeyboardButton("✅ I Have an Account!", callback_data="anthropic_has_account")],
            [InlineKeyboardButton("💰 Learn About Pricing", url="https://www.anthropic.com/pricing")],
            [InlineKeyboardButton("❓ Need Help", callback_data="anthropic_signup_help")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_anthropic_api_key_message(self) -> str:
        """Get instructions for getting the API key.

        Returns:
            API key retrieval instructions
        """
        # Get API tutorial
        tutorial_section = ""
        if self.tutorials_available and self.tutorials:
            api_tutorial = self.tutorials.get_tutorial("api_keys", 1)  # Anthropic-specific tutorial
            if api_tutorial:
                tutorial_section = f"""
*Need a video tutorial?*
🎥 [{api_tutorial.title}]({api_tutorial.url})
   ⏱️ {api_tutorial.duration} | See 2:10 for key generation
"""
            else:
                tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"
        else:
            tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"

        return f"""*Step 2: Get Your API Key!* 🔑

Perfect! Now let's get your API key!

*Follow these steps EXACTLY:*

**Step 1:** Go to the Anthropic Console
**Step 2:** Click on "API Keys" in the left menu
**Step 3:** Click "Create Key" or "+ Create Key"
**Step 4:** Give it a name like "Ralph Mode Bot"
**Step 5:** Copy the key! (It only shows ONCE!)

*IMPORTANT:*
⚠️ The key starts with `sk-ant-`
⚠️ Copy the WHOLE thing (it's long!)
⚠️ Save it somewhere safe for now
⚠️ You can't see it again after you close the page!

*What your key looks like:*
```
sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

*Security Reminders:*
🔒 NEVER share this key with anyone
🔒 NEVER post it on GitHub, Twitter, Discord, etc.
🔒 NEVER put it directly in your code
🔒 Ralph will help you save it SAFELY in the `.env` file

*Got your key copied?*

🔗 [Get API Key](https://console.anthropic.com/settings/keys)
{tutorial_section}"""

    def get_anthropic_api_key_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for API key retrieval step.

        Returns:
            Keyboard with API key action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🔗 Open API Keys Page", url="https://console.anthropic.com/settings/keys")],
            [InlineKeyboardButton("✅ I Copied My Key!", callback_data="anthropic_key_copied")],
            [InlineKeyboardButton("📋 Show Instructions Again", callback_data="anthropic_show_key_instructions")],
            [InlineKeyboardButton("❓ Need Help", callback_data="anthropic_key_help")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_anthropic_key_entry_message(self) -> str:
        """Get message for entering the API key.

        Returns:
            Key entry request message
        """
        return """*Step 3: Send Ralph Your Key!* 📨

Okay! Now Ralph needs you to send the API key!

*How to do this:*
1. Just paste your API key in the chat
2. Ralph will save it SAFELY in your `.env` file
3. Nobody else will see it!

*What to paste:*
The WHOLE key that starts with `sk-ant-`

*Example:*
```
sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**SECURITY NOTE:**
Ralph will validate the key format before saving!
If it doesn't look right, Ralph will warn you!

*Ready? Paste your API key now:*
"""

    def validate_anthropic_key_format(self, key: str) -> bool:
        """Validate that the API key has the correct format.

        Args:
            key: The API key to validate

        Returns:
            True if format is valid, False otherwise
        """
        # Anthropic keys start with sk-ant- and are typically 100+ characters
        if not key:
            return False

        key = key.strip()

        # Check if it starts with the correct prefix
        if not key.startswith("sk-ant-"):
            return False

        # Check minimum length (Anthropic keys are usually 100+ chars)
        if len(key) < 50:
            return False

        # Check that it only contains valid characters (alphanumeric, hyphens, underscores)
        import re
        if not re.match(r'^sk-ant-[a-zA-Z0-9_-]+$', key):
            return False

        return True

    def get_anthropic_key_invalid_message(self, key: str) -> str:
        """Get message for invalid API key format.

        Args:
            key: The invalid key that was provided

        Returns:
            Error message explaining what's wrong
        """
        issues = []

        if not key or not key.strip():
            issues.append("❌ The key is empty!")
        elif not key.startswith("sk-ant-"):
            issues.append("❌ API key should start with `sk-ant-`")
        elif len(key) < 50:
            issues.append("❌ API key is too short! Real keys are 100+ characters!")
        else:
            issues.append("❌ API key has invalid characters!")

        return f"""*Hmm... That Key Doesn't Look Right!* 🤔

Ralph found some problems:

{chr(10).join(issues)}

*What Anthropic API keys look like:*
✅ Starts with: `sk-ant-`
✅ Length: Usually 100+ characters
✅ Contains: Letters, numbers, hyphens, underscores
✅ Example: `sk-ant-api03-xxxxxxxxxxxxxxxxxxxx...`

*Common mistakes:*
• Copied only part of the key (copy ALL of it!)
• Added extra spaces (Ralph can fix this!)
• Copied the wrong thing (make sure it's from Anthropic Console!)
• Confused it with another API key (Groq? OpenAI? Wrong key!)

*Try again!*
Go back to: https://console.anthropic.com/settings/keys
Copy the WHOLE key and send it again!
"""

    def get_anthropic_key_success_message(self) -> str:
        """Get success message after API key is saved.

        Returns:
            Success celebration message
        """
        return """*API Key Saved!* 🎉🔐

Ralph SO EXCITED! You did it!

*What Ralph just did:*
✅ Validated your API key format
✅ Saved it to your `.env` file
✅ Made sure it's secure (only on YOUR computer!)

*Where is it saved?*
The key is in: `.env` (this file is in `.gitignore`, so it NEVER goes to GitHub!)

*What this means:*
🧠 Ralph can now use Claude's brain!
💡 You can build AI-powered features!
🚀 Your bot is ready to be SUPER SMART!

*Security reminder:*
Your `.env` file is LOCAL only! If you push to GitHub, the key won't be included!
That's GOOD! It keeps your key safe!

*Next steps:*
Ralph can help you:
• Test the API key with a quick request
• Set up other API keys (Telegram, Groq, etc.)
• Start using Ralph Mode!

*Want to test the key real quick?*
"""

    def get_anthropic_key_security_reminder(self) -> str:
        """Get security reminder message about API keys.

        Returns:
            Security education message
        """
        return """*Ralph's Security Lesson!* 🔒📚

Ralph wants to make sure you understand API key security!

*Why API keys are secret:*
• Anyone with your key can use YOUR account
• They can spend YOUR money on API calls
• They can see YOUR data
• You're responsible for what they do!

*Good practices:*
✅ Only put keys in `.env` (never in code!)
✅ Add `.env` to `.gitignore` (it's already there!)
✅ Never post keys in Discord, Twitter, etc.
✅ Rotate keys if you think they're compromised
✅ Set spending limits in Anthropic Console

*Bad practices:*
❌ Putting keys directly in code files
❌ Committing `.env` to GitHub
❌ Sharing keys with friends ("just for testing")
❌ Posting keys in screenshots
❌ Emailing keys to yourself

*What if your key gets leaked?*
1. Go to Anthropic Console IMMEDIATELY
2. Delete the leaked key
3. Create a new one
4. Update your `.env` file

*Remember:*
Your API key = Your money = Your responsibility!
Ralph helps you keep it safe! 🛡️
"""

    def get_anthropic_test_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for API key testing options.

        Returns:
            Keyboard with testing action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🧪 Test the Key!", callback_data="anthropic_test_key")],
            [InlineKeyboardButton("📚 Security Reminder", callback_data="anthropic_security_reminder")],
            [InlineKeyboardButton("▶️ Continue Setup", callback_data="setup_continue_next")],
        ]
        return InlineKeyboardMarkup(keyboard)

    # OB-009: API Key Validation Service

    async def test_anthropic_key(self, api_key: str) -> Tuple[bool, str]:
        """Test if an Anthropic API key works by making a real API call.

        Args:
            api_key: The API key to test

        Returns:
            Tuple of (success, message)
        """
        if not self.api_key_validation_available or not self.api_key_manager:
            return False, "⚠️ API key testing not available (missing api_key_manager module)"

        # First validate format
        is_valid, error_msg = self.api_key_manager.validate_anthropic_key(api_key)
        if not is_valid:
            return False, f"❌ Invalid format: {error_msg}"

        # Then test with real API call
        self.logger.info("Testing Anthropic API key...")
        success, message = self.api_key_manager.test_anthropic_key(api_key)

        return success, message

    async def test_telegram_token(self, token: str) -> Tuple[bool, str]:
        """Test if a Telegram bot token works by making a real API call.

        Args:
            token: The bot token to test

        Returns:
            Tuple of (success, message)
        """
        if not self.api_key_validation_available or not self.api_key_manager:
            return False, "⚠️ Token testing not available (missing api_key_manager module)"

        # First validate format
        is_valid, error_msg = self.api_key_manager.validate_telegram_token(token)
        if not is_valid:
            return False, f"❌ Invalid format: {error_msg}"

        # Then test with real API call
        self.logger.info("Testing Telegram bot token...")
        success, message = self.api_key_manager.test_telegram_token(token)

        return success, message

    async def test_groq_key(self, api_key: str) -> Tuple[bool, str]:
        """Test if a Groq API key works by making a real API call.

        Args:
            api_key: The API key to test

        Returns:
            Tuple of (success, message)
        """
        if not self.api_key_validation_available or not self.api_key_manager:
            return False, "⚠️ API key testing not available (missing api_key_manager module)"

        # First validate format
        is_valid, error_msg = self.api_key_manager.validate_groq_key(api_key)
        if not is_valid:
            return False, f"❌ Invalid format: {error_msg}"

        # Then test with real API call
        self.logger.info("Testing Groq API key...")
        success, message = self.api_key_manager.test_groq_key(api_key)

        return success, message

    def get_api_test_progress_message(self, key_type: str) -> str:
        """Get message shown while testing an API key.

        Args:
            key_type: Type of key being tested (anthropic, telegram, groq)

        Returns:
            Progress message
        """
        messages = {
            "anthropic": """*Testing Anthropic API Key...* 🧪

Ralph is making a tiny test request to Claude!

This usually takes just a few seconds...

⏳ *Please wait...*""",

            "telegram": """*Testing Telegram Bot Token...* 🧪

Ralph is trying to connect to your bot!

This should be super quick...

⏳ *Please wait...*""",

            "groq": """*Testing Groq API Key...* 🧪

Ralph is making a quick test call to Groq!

Should only take a moment...

⏳ *Please wait...*"""
        }

        return messages.get(key_type, "*Testing your key...* 🧪\n\n⏳ *Please wait...*")

    def get_api_test_result_message(self, success: bool, key_type: str, result_msg: str) -> str:
        """Get message showing API key test results.

        Args:
            success: Whether the test was successful
            key_type: Type of key tested (anthropic, telegram, groq)
            result_msg: The result message from the test

        Returns:
            Formatted result message
        """
        if success:
            celebrations = {
                "anthropic": """*🎉 ANTHROPIC KEY WORKS! 🎉*

Ralph just talked to Claude and it worked PERFECTLY!

{result_msg}

*What this means:*
✅ Your API key is valid
✅ You have access to Claude
✅ API calls will work
✅ You're all set for AI coding!

*Ready to continue?*""",

                "telegram": """*🎊 TELEGRAM BOT IS ALIVE! 🎊*

Ralph successfully connected to your bot!

{result_msg}

*What this means:*
✅ Your bot token is valid
✅ The bot is active
✅ Ralph can use this bot
✅ You can start chatting!

*Ready to continue?*""",

                "groq": """*⚡ GROQ KEY WORKS! ⚡*

Ralph just tested Groq and it's BLAZING FAST!

{result_msg}

*What this means:*
✅ Your API key is valid
✅ You have access to Groq
✅ Fast AI responses enabled
✅ You're good to go!

*Ready to continue?*"""
            }

            template = celebrations.get(key_type, "*✅ Success!*\n\n{result_msg}\n\n*Ready to continue?*")
            return template.format(result_msg=result_msg)

        else:
            # Failed test
            return f"""*❌ Test Failed*

{result_msg}

*What to do:*
1. Double-check you copied the ENTIRE key
2. Make sure you didn't include extra spaces
3. Verify the key wasn't deleted or expired
4. Try getting a fresh key if nothing works

*Want to try again?*"""

    def get_api_test_result_keyboard(self, success: bool) -> InlineKeyboardMarkup:
        """Get keyboard for API key test results.

        Args:
            success: Whether the test was successful

        Returns:
            Keyboard with appropriate next steps
        """
        if success:
            keyboard = [
                [InlineKeyboardButton("▶️ Continue Setup", callback_data="setup_continue_next")],
                [InlineKeyboardButton("🔄 Test Again", callback_data="retry_api_test")],
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Enter Different Key", callback_data="retry_api_key")],
                [InlineKeyboardButton("❓ Get Help", callback_data="api_key_help")],
                [InlineKeyboardButton("⏭️ Skip for Now", callback_data="skip_api_key")],
            ]

        return InlineKeyboardMarkup(keyboard)

    # Groq API Key Setup (OB-010) - Optional

    def get_groq_api_intro_message(self) -> str:
        """Get introduction message for Groq API key setup (optional).

        Returns:
            Groq API key introduction
        """
        return """*Want to Make Ralph SUPER FAST? ⚡*

This part is OPTIONAL! But Ralph thinks it's pretty cool!

*What's Groq?*
Groq is like Claude's super-speedy cousin! It's:
• Lightning fast AI responses ⚡
• Great for quick tasks and conversations 💨
• FREE tier available! 🎉

*Why add Groq?*
• Makes Ralph's responses MUCH faster
• Reduces costs for simple tasks
• Still uses Claude for the hard stuff
• Best of both worlds! 🌍

*Important:*
⚠️ This is 100% optional!
⚠️ Ralph works great with just Claude!
⚠️ You can always add this later!

*What do you want to do?*
"""

    def get_groq_intro_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for Groq intro with setup or skip options.

        Returns:
            Keyboard with Groq setup options
        """
        keyboard = [
            [InlineKeyboardButton("⚡ Set Up Groq (Recommended)", callback_data="groq_setup_start")],
            [InlineKeyboardButton("⏭️ Skip for Now", callback_data="groq_skip")],
            [InlineKeyboardButton("📚 Learn More About Groq", url="https://groq.com")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_groq_signup_message(self) -> str:
        """Get message with signup instructions for Groq.

        Returns:
            Signup instructions message
        """
        return """*Step 1: Sign Up for Groq!* 🚀

Let's get you set up with BLAZING fast AI!

*Follow these steps:*

**Step 1:** Click the link below to go to Groq
**Step 2:** Click "Sign Up" or "Get Started"
**Step 3:** Create your account (use email or Google)
**Step 4:** Verify your email if needed

*The link:*
🔗 [Groq Console](https://console.groq.com)

*About Groq pricing:*
• FREE tier with generous limits! 🎉
• Perfect for testing and personal projects
• Much faster than traditional AI
• Pay-as-you-go after free tier

Ralph says: "Groq is like putting rocket fuel in Ralph's car! Vroom vroom! 🏎️"

*Benefits of Groq:*
✅ Responses in milliseconds (not seconds!)
✅ Great for conversations and quick tasks
✅ Free tier is very generous
✅ Works alongside Claude perfectly

*Did you create your account?*
"""

    def get_groq_signup_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for Groq signup step.

        Returns:
            Keyboard with signup action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🔗 Open Groq Console", url="https://console.groq.com")],
            [InlineKeyboardButton("✅ I Have an Account!", callback_data="groq_has_account")],
            [InlineKeyboardButton("📊 Learn About Pricing", url="https://groq.com/pricing")],
            [InlineKeyboardButton("⏭️ Skip Groq Setup", callback_data="groq_skip")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_groq_api_key_message(self) -> str:
        """Get instructions for getting the Groq API key.

        Returns:
            API key retrieval instructions
        """
        return """*Step 2: Get Your Groq API Key!* 🔑

Almost there! Let's grab that API key!

*Follow these steps EXACTLY:*

**Step 1:** Go to the Groq Console
**Step 2:** Click on "API Keys" in the navigation
**Step 3:** Click "Create API Key" or "+ New API Key"
**Step 4:** Give it a name like "Ralph Mode Bot"
**Step 5:** Copy the key! (Save it somewhere safe!)

*IMPORTANT:*
⚠️ The key starts with `gsk_`
⚠️ Copy the WHOLE thing (it's long!)
⚠️ Save it somewhere safe
⚠️ You might not see it again after closing!

*What your key looks like:*
```
gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

*Security Reminders:*
🔒 NEVER share this key with anyone
🔒 NEVER post it on GitHub, Twitter, Discord, etc.
🔒 NEVER put it directly in your code
🔒 Ralph will save it SAFELY in the `.env` file

*Got your key copied?*

🔗 [Get API Key](https://console.groq.com/keys)

*Need help?*
Ralph is here if you get stuck!
"""

    def get_groq_api_key_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for Groq API key retrieval step.

        Returns:
            Keyboard with API key action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🔗 Open API Keys Page", url="https://console.groq.com/keys")],
            [InlineKeyboardButton("✅ I Copied My Key!", callback_data="groq_key_copied")],
            [InlineKeyboardButton("📋 Show Instructions Again", callback_data="groq_show_key_instructions")],
            [InlineKeyboardButton("⏭️ Skip for Now", callback_data="groq_skip")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_groq_key_entry_message(self) -> str:
        """Get message for entering the Groq API key.

        Returns:
            Key entry request message
        """
        return """*Step 3: Send Ralph Your Groq Key!* 📨

Okay! Now Ralph needs you to send the API key!

*Just send it as a message right here!*

Ralph will:
✅ Check if the format is correct
✅ Test it with a real API call
✅ Save it securely in your `.env` file
✅ Make sure it works!

*Security note:*
Don't worry! Ralph will delete your message after saving the key! 🗑️
(But Telegram servers might keep it, so be careful!)

*Paste your Groq API key below:*
👇 (It should start with `gsk_`)
"""

    def get_groq_key_invalid_message(self, key: str) -> str:
        """Get error message for invalid Groq API key format.

        Args:
            key: The invalid key that was provided

        Returns:
            Error message with troubleshooting tips
        """
        key_preview = f"{key[:10]}..." if len(key) > 10 else key

        return f"""*Oops! That doesn't look like a Groq API key!* ❌

Ralph got: `{key_preview}`

*Common problems:*
• Copied only part of the key (copy ALL of it!)
• Added extra spaces (Ralph can fix this!)
• Copied the wrong thing (make sure it's from Groq Console!)
• Confused it with another API key (Anthropic? OpenAI? Wrong key!)

*Try again!*
Go back to: https://console.groq.com/keys

Make sure to copy the ENTIRE key! It should:
• Start with `gsk_`
• Be pretty long (40-50 characters)
• Have letters and numbers

*Send Ralph the key when you're ready!*
"""

    def get_groq_key_success_message(self) -> str:
        """Get success message after Groq API key is saved.

        Returns:
            Success message with next steps
        """
        return """*Ralph Saved Your Groq Key! ⚡*

Woohoo! Ralph tested it and it works GREAT!

*What Ralph did:*
✅ Validated the key format
✅ Tested it with Groq's API
✅ Saved it to your `.env` file
✅ Made sure it's working perfectly

*What this means for you:*
⚡ SUPER FAST AI responses
⚡ Lower costs for simple tasks
⚡ Best of both worlds (Claude + Groq)
⚡ Ralph is turbocharged! 🏎️

*Next steps:*
Ralph can help you:
• Set up other API keys (OpenWeather, etc.)
• Continue with the setup wizard
• Start using Ralph Mode!

*Ready to continue?*
"""

    def get_groq_test_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for Groq API key testing options.

        Returns:
            Keyboard with testing action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🧪 Test the Key!", callback_data="groq_test_key")],
            [InlineKeyboardButton("▶️ Continue Setup", callback_data="setup_continue_next")],
            [InlineKeyboardButton("⏭️ Skip Groq", callback_data="groq_skip")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_groq_skip_confirmation_message(self) -> str:
        """Get confirmation message when user skips Groq setup.

        Returns:
            Skip confirmation message with Ralph's personality (OB-032)
        """
        # Add skip message with Ralph's understanding (OB-032)
        skip_msg = ""
        if self.narrator:
            skip_msg = self.narrator.get_skip_message() + "\n\n"

        return f"""{skip_msg}*No Problem! Skipping Groq Setup!* ⏭️

Ralph totally understands! Groq is optional!

*What this means:*
• Ralph will use only Claude for AI
• Everything still works perfectly
• You can add Groq later anytime
• Just run `/setup` again when ready!

*To add Groq later:*
1. Run `/setup` command
2. Select "Configure API Keys"
3. Choose "Groq API Key"
4. Follow the setup steps

Ralph says: "That's okay! Ralph works great with just Claude too! Me still smart! 🧠"

*Ready to continue with setup?*
"""

    # OpenWeather API Setup (OB-011)

    def get_openweather_intro_message(self) -> str:
        """Get introduction message for OpenWeather API setup.

        Returns:
            OpenWeather introduction message
        """
        return """*OpenWeather API - Make Ralph's Office Real! 🌤️*

Hey! Want Ralph's office to feel REAL?

*What is OpenWeather?*
OpenWeather gives Ralph REAL weather data for your city!
When it's raining outside, Ralph's office is rainy too! ☔

*Why is this cool?*
🌧️ Real weather in scene descriptions
🌤️ Ralph might say "Look at that sunshine!"
❄️ Seasonal atmosphere (snow, heat, storms)
🌍 Grounded in YOUR reality

*Example:*
Instead of: _"The office is quiet"_
You get: _"Rain taps against the window. Gus sips his coffee, watching the storm roll in."_

*Is this required?*
**NOPE!** Totally optional!
Ralph works great without it too!

*How much does it cost?*
🎉 **FREE!** (Up to 1,000 calls/day)
That's WAY more than Ralph needs!

*Want to set it up?*
Ralph will help you get an API key! It's easy!
"""

    def get_openweather_intro_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for OpenWeather introduction.

        Returns:
            Keyboard with setup options
        """
        keyboard = [
            [InlineKeyboardButton("🌤️ Yes! Set Up Weather!", callback_data="openweather_start")],
            [InlineKeyboardButton("📚 Learn More", url="https://openweathermap.org/")],
            [InlineKeyboardButton("⏭️ Skip Weather Setup", callback_data="openweather_skip")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_openweather_signup_message(self) -> str:
        """Get message for OpenWeather account signup.

        Returns:
            Signup instructions
        """
        return """*Step 1: Create Your Free OpenWeather Account!* 🌍

Let's get you signed up! It's super quick!

*Follow these steps:*

**Step 1:** Go to OpenWeather
**Step 2:** Click "Sign Up" in the top right
**Step 3:** Fill in the form (email, username, password)
**Step 4:** Verify your email (check spam folder!)
**Step 5:** Come back here when you're signed in!

*What to use:*
📧 **Email:** Use a real email (you'll need to verify it!)
👤 **Username:** Anything you want
🔒 **Password:** Make it secure!

*After signing up:*
You'll get an email to verify your account!
Click the link in the email, then come back here!

🔗 [Sign Up for OpenWeather](https://home.openweathermap.org/users/sign_up)

*Already have an account?*
Great! Click "I Have an Account!" below!
"""

    def get_openweather_signup_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for OpenWeather signup step.

        Returns:
            Keyboard with signup options
        """
        keyboard = [
            [InlineKeyboardButton("🌍 Go to Sign Up Page", url="https://home.openweathermap.org/users/sign_up")],
            [InlineKeyboardButton("✅ I Have an Account!", callback_data="openweather_has_account")],
            [InlineKeyboardButton("⏭️ Skip Weather Setup", callback_data="openweather_skip")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_openweather_api_key_message(self) -> str:
        """Get instructions for getting the OpenWeather API key.

        Returns:
            API key retrieval instructions
        """
        return """*Step 2: Get Your OpenWeather API Key!* 🔑

Almost there! Let's grab that API key!

*Follow these steps EXACTLY:*

**Step 1:** Log into OpenWeather
**Step 2:** Click on your username (top right)
**Step 3:** Click "My API Keys"
**Step 4:** You'll see a default key already created!
**Step 5:** Copy that key! (Or create a new one!)

*IMPORTANT:*
⚠️ The key is 32 characters long
⚠️ Contains only letters (a-f) and numbers (0-9)
⚠️ Copy the WHOLE thing!
⚠️ It might take 10 minutes to activate (be patient!)

*What your key looks like:*
```
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

*Security Reminders:*
🔒 NEVER share this key with anyone
🔒 NEVER post it publicly
🔒 NEVER put it directly in your code
🔒 Ralph will save it SAFELY in the `.env` file

*Got your key copied?*

🔗 [Get API Key](https://home.openweathermap.org/api_keys)

*Need help?*
Ralph is here if you get stuck!

*Note:* New API keys can take up to 10 minutes to activate. Don't worry if the test fails at first!
"""

    def get_openweather_api_key_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for OpenWeather API key retrieval step.

        Returns:
            Keyboard with API key action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🔗 Open API Keys Page", url="https://home.openweathermap.org/api_keys")],
            [InlineKeyboardButton("✅ I Copied My Key!", callback_data="openweather_key_copied")],
            [InlineKeyboardButton("📋 Show Instructions Again", callback_data="openweather_show_key_instructions")],
            [InlineKeyboardButton("⏭️ Skip for Now", callback_data="openweather_skip")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_openweather_key_entry_message(self) -> str:
        """Get message for entering the OpenWeather API key.

        Returns:
            Key entry request message
        """
        return """*Step 3: Send Ralph Your OpenWeather Key!* 📨

Okay! Now Ralph needs you to send the API key!

*Just send it as a message right here!*

Ralph will:
✅ Check if the format is correct
✅ Test it with a real API call
✅ Save it securely in your `.env` file
✅ Make sure it works!

*Security note:*
Don't worry! Ralph will delete your message after saving the key! 🗑️
(But Telegram servers might keep it, so be careful!)

*Paste your OpenWeather API key below:*
👇 (It should be 32 characters: letters a-f and numbers 0-9)

*Note:* If your key is brand new (created in the last 10 minutes), it might not work yet. OpenWeather takes a few minutes to activate new keys!
"""

    def get_openweather_location_message(self) -> str:
        """Get message for asking user's location.

        Returns:
            Location request message
        """
        return """*Step 4: What's Your City?* 🌍

Ralph needs to know where you are for the weather!

*Just send your city name!*

Examples:
• `London`
• `New York`
• `Tokyo`
• `San Francisco`
• `Paris`

*Privacy note:*
🔒 Ralph only stores your CITY, not exact address
🔒 This is ONLY used for weather (nothing else!)
🔒 You can change this anytime in settings

*Send your city name as a message:*
👇
"""

    def get_openweather_key_invalid_message(self, key: str) -> str:
        """Get error message for invalid OpenWeather API key format.

        Args:
            key: The invalid key that was provided

        Returns:
            Error message with troubleshooting tips
        """
        key_preview = f"{key[:10]}..." if len(key) > 10 else key

        return f"""*Oops! That doesn't look like an OpenWeather API key!* ❌

Ralph got: `{key_preview}`

*Common problems:*
• Copied only part of the key (copy ALL 32 characters!)
• Added extra spaces or line breaks (Ralph can try to fix this!)
• Copied the wrong thing (make sure it's from "My API Keys" page!)
• Key has special characters (OpenWeather keys are hex: 0-9, a-f only!)

*OpenWeather API keys should:*
• Be exactly 32 characters long
• Contain only: 0-9 and a-f
• Look like: `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`

*Try again!*
Go back to: https://home.openweathermap.org/api_keys

Make sure to copy the ENTIRE key!

*Send Ralph the key when you're ready!*
"""

    def get_openweather_key_success_message(self, location: str = None) -> str:
        """Get success message after OpenWeather API key is saved.

        Args:
            location: The configured location (if any)

        Returns:
            Success message with next steps
        """
        location_text = f"for {location}" if location else ""

        return f"""*Ralph Saved Your OpenWeather Key! 🌤️*

Woohoo! Ralph tested it and it works GREAT!

*What Ralph did:*
✅ Validated the key format
✅ Tested it with OpenWeather's API {location_text}
✅ Saved it to your `.env` file
✅ Made sure it's working perfectly

*What this means for you:*
🌧️ REAL weather in Ralph's office scenes!
🌤️ Grounded, immersive atmosphere
🌍 Your city's weather affects the mood
⛈️ Ralph might comment on storms or sunshine!

*Next steps:*
Ralph can help you:
• Continue with the setup wizard
• Configure other optional features
• Start using Ralph Mode!

*Ready to continue?*
"""

    def get_openweather_test_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for OpenWeather API key testing options.

        Returns:
            Keyboard with testing action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🧪 Test the Key!", callback_data="openweather_test_key")],
            [InlineKeyboardButton("▶️ Continue Setup", callback_data="setup_continue_next")],
            [InlineKeyboardButton("⏭️ Skip Weather", callback_data="openweather_skip")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_openweather_skip_confirmation_message(self) -> str:
        """Get confirmation message when user skips OpenWeather setup.

        Returns:
            Skip confirmation message
        """
        return """*No Problem! Skipping Weather Setup!* ⏭️

Ralph totally understands! Weather is optional!

*What this means:*
• Ralph's office will have generated atmospheric weather
• Everything still works perfectly
• You can add weather later anytime
• Just run `/setup` again when ready!

*To add weather later:*
1. Run `/setup` command
2. Select "Configure API Keys"
3. Choose "OpenWeather API"
4. Follow the setup steps

Ralph says: "That's okay! Ralph can make up weather too! Me good at pretending! 🎭"

*Ready to continue with setup?*
"""

    # Telegram Bot Creation Wizard (OB-007)

    def get_telegram_bot_intro_message(self) -> str:
        """Get introduction message for Telegram bot creation.

        Returns:
            Telegram bot creation introduction
        """
        return """*Time to Make Your Telegram Bot!* 🤖

Ralph help you make a Telegram bot! This is how you talk to Ralph!

*What's a Telegram bot?*
Think of it like:
• A phone number for your AI 📱
• A way to chat with your code 💬
• Your personal assistant that lives in Telegram 🤖

*What you need:*
1. Telegram app (download from telegram.org if you don't have it!)
2. A name for your bot
3. 2 minutes of your time!

*How we gonna do this:*
Ralph introduce you to **@BotFather** - he's the bot that makes bots!
(Ralph know, it sounds confusing... a bot that makes bots! But it works!)

*Ready to meet the BotFather?*
"""

    def get_telegram_bot_intro_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for Telegram bot introduction.

        Returns:
            Keyboard with BotFather link
        """
        keyboard = [
            [InlineKeyboardButton("👨‍💼 Talk to BotFather", url="https://t.me/BotFather")],
            [InlineKeyboardButton("✅ I'm Ready!", callback_data="telegram_bot_ready")],
            [InlineKeyboardButton("❓ What's Telegram?", callback_data="telegram_what_is")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_what_is_telegram_message(self) -> str:
        """Get explanation of what Telegram is.

        Returns:
            Telegram explanation message
        """
        return """*What's Telegram? Ralph Explains!* 📱

Telegram is a messaging app! Like WhatsApp or iMessage!

*Why use Telegram for this?*
• Free to use!
• Works on phone AND computer! 📱💻
• Has AMAZING bot support! 🤖
• Super fast and reliable! ⚡
• Works everywhere in the world! 🌍

*How to get Telegram:*
**On Phone:**
• iPhone: App Store - search "Telegram"
• Android: Play Store - search "Telegram"

**On Computer:**
• Go to: https://telegram.org/apps
• Download for Windows/Mac/Linux
• Or use the web version!

*What Ralph needs:*
You just need to create an account! Use your phone number!

After you got Telegram, come back here and Ralph help you make a bot!

*Got Telegram now?*
"""

    def get_what_is_telegram_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for Telegram explanation.

        Returns:
            Keyboard with download links
        """
        keyboard = [
            [InlineKeyboardButton("📥 Download Telegram", url="https://telegram.org/apps")],
            [InlineKeyboardButton("✅ I Have Telegram!", callback_data="telegram_bot_ready")],
            [InlineKeyboardButton("◀️ Back", callback_data="telegram_bot_intro")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_botfather_walkthrough_message(self) -> str:
        """Get step-by-step walkthrough for using BotFather.

        Returns:
            BotFather walkthrough instructions
        """
        return """*Let's Make Your Bot!* 🏭

Okay! Follow these steps EXACTLY!

**Step 1: Open BotFather**
Click the link below or search "@BotFather" in Telegram
(Look for the official one - blue checkmark!)

**Step 2: Start the conversation**
Click "START" or send: `/start`
BotFather will say hello!

**Step 3: Create new bot**
Send this command: `/newbot`
BotFather will ask you some questions!

**Step 4: Choose a name** (what people see)
Examples:
• "My Ralph Bot"
• "Code Assistant Bot"
• "Super Cool Helper"
Whatever you want! This is the DISPLAY name!

**Step 5: Choose a username** (must be unique!)
Must end with "bot"!
Examples:
• `my_ralph_bot`
• `code_helper_2024_bot`
• `supercool_bot`

Try a few names - some might be taken!

**Step 6: Get your token!** 🔑
BotFather will give you a TOKEN!
It looks like: `1234567890:ABCdefGHIjklMNOpqrSTUvwxyz`

⚠️ **IMPORTANT:** This token is SECRET!
Copy it and save it somewhere safe!

*Ready to start?*
"""

    def get_botfather_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for BotFather walkthrough.

        Returns:
            Keyboard with BotFather link and actions
        """
        keyboard = [
            [InlineKeyboardButton("👨‍💼 Open BotFather", url="https://t.me/BotFather")],
            [InlineKeyboardButton("✅ I Got My Token!", callback_data="telegram_token_received")],
            [InlineKeyboardButton("📋 Show Steps Again", callback_data="telegram_show_steps")],
            [InlineKeyboardButton("❓ Need Help", callback_data="telegram_bot_help")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_token_entry_message(self) -> str:
        """Get message for entering the bot token.

        Returns:
            Token entry request message
        """
        return """*Send Ralph Your Bot Token!* 🔑

Perfect! Now Ralph needs your bot token!

*What to send:*
Paste the WHOLE token that BotFather gave you!

*What it looks like:*
```
1234567890:ABCdefGHIjklMNOpqrSTUvwxyz-abcdefgh
```

*Where to find it:*
1. Look at your chat with BotFather
2. Find the message that says "Use this token to access the HTTP API"
3. Copy the ENTIRE token
4. Paste it here!

**SECURITY NOTE:**
• This token is a SECRET!
• Ralph will save it safely in your `.env` file
• Never share it with anyone!
• Anyone with this token can control your bot!

*Ready? Paste your token now:*
"""

    def validate_telegram_token_format(self, token: str) -> bool:
        """Validate that the Telegram bot token has the correct format.

        Args:
            token: The bot token to validate

        Returns:
            True if format is valid, False otherwise
        """
        import re

        if not token:
            return False

        token = token.strip()

        # Telegram tokens are in format: 123456789:ABCdefGHIjklMNOpqrSTUvwxyz
        # Bot ID (numbers) : Auth token (alphanumeric and special chars)
        pattern = r'^\d{8,10}:[A-Za-z0-9_-]{35,}$'

        return bool(re.match(pattern, token))

    def get_telegram_token_invalid_message(self, token: str) -> str:
        """Get message for invalid bot token format.

        Args:
            token: The invalid token that was provided

        Returns:
            Error message explaining what's wrong
        """
        issues = []

        if not token or not token.strip():
            issues.append("❌ The token is empty!")
        elif ':' not in token:
            issues.append("❌ Token should have a colon `:` in the middle!")
            issues.append("   Format: `123456789:ABCdefGHIjklMNOpqr`")
        else:
            parts = token.split(':')
            if len(parts) != 2:
                issues.append("❌ Token should have exactly ONE colon!")
            else:
                bot_id, auth_token = parts
                if not bot_id.isdigit():
                    issues.append("❌ First part (before `:`) should be only numbers!")
                if len(bot_id) < 8:
                    issues.append("❌ Bot ID is too short!")
                if len(auth_token) < 30:
                    issues.append("❌ Auth token (after `:`) is too short!")

        return f"""*Hmm... That Token Doesn't Look Right!* 🤔

Ralph found some problems:

{chr(10).join(issues)}

*What Telegram tokens look like:*
✅ Format: `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`
✅ Two parts separated by a colon `:`
✅ First part: 8-10 digits (your bot's ID)
✅ Second part: 35+ characters (letters, numbers, - and _)

*Common mistakes:*
• Didn't copy the whole token (copy ALL of it!)
• Added extra spaces at the beginning or end
• Copied the wrong message from BotFather
• Token got split across two lines (make sure it's one line!)

*Try again!*
1. Go back to your chat with @BotFather
2. Find the token (the long string after "Use this token")
3. Copy THE WHOLE THING (including the colon!)
4. Paste it here!

*Example from BotFather:*
```
Done! Congratulations on your new bot.
...
Use this token to access the HTTP API:
1234567890:ABCdefGHI-jklMNOpqrSTUvwxyz123
```
Copy that ENTIRE bottom line!
"""

    def get_telegram_token_success_message(self) -> str:
        """Get success message after bot token is saved.

        Returns:
            Success celebration message
        """
        return """*Bot Token Saved!* 🎉🤖

Ralph GOT IT! Your bot token is safe!

*What Ralph just did:*
✅ Validated your token format
✅ Saved it to your `.env` file
✅ Made sure it's secure (only on YOUR computer!)

*What this means:*
🤖 Your bot is ready to come to life!
💬 Ralph can now control your bot!
🔐 The token is stored safely (never goes to GitHub!)

*Next, let's test if it works!*

Ralph gonna try to connect to your bot...
This usually takes just a second!

*Testing the connection...*
"""

    def get_telegram_test_message(self, success: bool, bot_info: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> str:
        """Get message after testing bot connection.

        Args:
            success: Whether the test was successful
            bot_info: Bot information if successful
            error: Error message if failed

        Returns:
            Test result message
        """
        if success and bot_info:
            bot_name = bot_info.get('first_name', 'Unknown')
            bot_username = bot_info.get('username', 'Unknown')

            return f"""*🎊 BOT IS ALIVE! 🎊*

Ralph connected to your bot!

*Your Bot Info:*
👤 Name: **{bot_name}**
🔗 Username: @{bot_username}
✅ Status: Active and Ready!

*What this means:*
• Your bot token works!
• The bot is online!
• Ralph can send messages through it!

*Next steps:*
• Ralph can help you configure the bot
• Set up commands and features
• Start chatting with your bot!

Try talking to your bot! Search for @{bot_username} in Telegram and click START!

*Ready to continue setup?*
"""
        else:
            error_msg = error or "Unknown error"
            return f"""*❌ Connection Failed* 😔

Ralph tried to connect to your bot but something went wrong!

*Error:*
{error_msg}

*Why this might happen:*
• Token might be wrong (typo when copying?)
• Token might be revoked (did you delete the bot?)
• Internet connection issue
• Telegram might be having problems (rare!)

*What to do:*
1. Check if you copied the ENTIRE token
2. Make sure you didn't delete the bot in BotFather
3. Try the token again
4. If nothing works, create a NEW bot and get a new token!

*Want to try again?*
"""

    def get_telegram_test_keyboard(self, success: bool) -> InlineKeyboardMarkup:
        """Get keyboard after bot connection test.

        Args:
            success: Whether the test was successful

        Returns:
            Keyboard with next steps
        """
        if success:
            keyboard = [
                [InlineKeyboardButton("✅ Continue Setup", callback_data="setup_continue_next")],
                [InlineKeyboardButton("🔄 Test Again", callback_data="telegram_test_again")],
                [InlineKeyboardButton("📚 Bot Configuration Tips", callback_data="telegram_config_tips")],
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Try Different Token", callback_data="telegram_retry_token")],
                [InlineKeyboardButton("🆕 Create New Bot", callback_data="telegram_new_bot")],
                [InlineKeyboardButton("❓ Get Help", callback_data="telegram_test_help")],
                [InlineKeyboardButton("⏭️ Skip for Now", callback_data="setup_skip_telegram")],
            ]

        return InlineKeyboardMarkup(keyboard)

    def get_telegram_bot_help_message(self) -> str:
        """Get help message for Telegram bot creation issues.

        Returns:
            Troubleshooting help
        """
        # Get Telegram bot tutorial
        tutorial_section = ""
        if self.tutorials_available and self.tutorials:
            telegram_tutorial = self.tutorials.get_tutorial("telegram_bots", 0)
            if telegram_tutorial:
                tutorial_section = f"""
*Need a video tutorial?*
🎥 [{telegram_tutorial.title}]({telegram_tutorial.url})
   ⏱️ {telegram_tutorial.duration} | See 0:45 for finding BotFather
"""
            else:
                tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"
        else:
            tutorial_section = "\n*Need help?* Check Ralph Mode documentation!"

        return f"""*Ralph Help With Telegram Bot!* 🆘

**Common Problems:**

**Problem 1: "Can't find BotFather"**
→ Search EXACTLY: `@BotFather` in Telegram
→ Look for the one with a BLUE CHECKMARK ✅
→ Don't talk to fake BotFathers!

**Problem 2: "Username already taken"**
→ Try adding numbers: `my_bot_2024_bot`
→ Try underscores: `my_cool_bot`
→ Remember: must end with `bot`!

**Problem 3: "BotFather not responding"**
→ Click START in the chat
→ Make sure you have internet connection
→ Wait a few seconds - he's busy!

**Problem 4: "Lost my token!"**
→ Go back to BotFather
→ Send: `/mybots`
→ Select your bot
→ Click "API Token"
→ BotFather will show it again!

**Problem 5: "Token doesn't work"**
→ Make sure you copied ALL of it
→ Check for spaces at the ends
→ Make sure it's ONE line (not split across two)
→ Try regenerating the token in BotFather

**Problem 6: "I deleted my bot by accident!"**
→ No problem! Just make a new one!
→ Use `/newbot` again
→ Pick a different username
{tutorial_section}
*Still stuck?*
Tell Ralph exactly what error you seeing!
"""

    def get_telegram_config_tips_message(self) -> str:
        """Get bot configuration tips message.

        Returns:
            Configuration tips and best practices
        """
        return """*Bot Configuration Tips!* ⚙️

Now that your bot is working, here are some tips!

**1. Set a Profile Picture** 🖼️
• Go to BotFather → `/mybots`
• Select your bot → Edit Bot → Edit Botpic
• Upload a cool image!
• Makes your bot look professional!

**2. Set a Description** 📝
• BotFather → `/mybots` → Edit Bot → Edit Description
• Write what your bot does!
• Shows up when people first talk to your bot!

**3. Set an About Text** ℹ️
• BotFather → `/mybots` → Edit Bot → Edit About
• Short description (max 120 characters)
• Shows on bot's profile page!

**4. Set Commands** ⌨️
• BotFather → `/mybots` → Edit Bot → Edit Commands
• List what commands your bot responds to!
• Example: `start - Start the bot`

**5. Privacy Settings** 🔒
• BotFather → `/mybots` → Bot Settings → Group Privacy
• Turn OFF if you want bot to see all group messages
• Turn ON if bot should only see commands

**6. Inline Mode** (Optional) 🔍
• BotFather → `/mybots` → Bot Settings → Inline Mode
• Allows using bot inline: `@yourbotname query`
• Cool feature but not required!

*Ralph's Advice:*
You don't NEED to do all this now! Your bot works!
But these make it look MORE professional! ✨

*Ready to continue?*
"""

    # OB-036: Telegram Bot Permissions Guide

    def get_bot_permissions_guide_message(self) -> str:
        """Get comprehensive guide for Telegram bot permissions.

        Returns:
            Bot permissions guide with explanations
        """
        return """*Telegram Bot Permissions Guide!* 🔐

Ralph gonna help you set up your bot's permissions!

*What are permissions?*
They control what your bot can see and do in Telegram!

**Here's what we gonna configure:**

**1. Privacy Mode** 🕵️
• Controls if bot sees ALL messages or just commands
• **DISABLED** = Bot sees everything in groups
• **ENABLED** = Bot only sees messages that start with /

*Ralph's Recommendation:*
**DISABLE** privacy mode for Ralph to work right!
Ralph needs to see your messages to help you!

**2. Group Mode** 👥
• Let your bot work in group chats
• Ralph works great in groups or private chats!

*Ralph's Recommendation:*
**ENABLE** groups if you want to work with team!

**3. Inline Mode** 🔍
• Lets people use bot like: `@yourbot search term`
• Cool feature but not needed for Ralph!

*Ralph's Recommendation:*
**OPTIONAL** - only if you want this feature!

*Ready to configure these settings?*
"""

    def get_bot_permissions_instructions_message(self) -> str:
        """Get step-by-step instructions for setting bot permissions via BotFather.

        Returns:
            Detailed permission configuration steps
        """
        return """*Setting Bot Permissions - Step by Step!* 📝

Follow these steps in BotFather!

**Step 1: Open BotFather**
Search `@BotFather` in Telegram and start chat

**Step 2: Access Your Bot Settings**
Send this command:
```
/mybots
```
Then select your bot from the list!

**Step 3: Go to Bot Settings**
Click "Bot Settings" button

**Step 4: Configure Privacy Mode** 🔒

Send to BotFather:
```
/setprivacy
```

BotFather will ask: "Enable privacy mode?"

**For Ralph, choose: DISABLE**
• Type: `Disable`
• This lets Ralph see all messages
• Needed for Ralph to help you properly!

✅ Success message: "Privacy mode is disabled for [your bot]"

**Step 5: Configure Group Settings** 👥

Click "Allow Groups" in Bot Settings

**For Ralph, choose: ENABLE**
• This lets you add Ralph to group chats
• Great for team projects!

**Step 6: Configure Inline Mode** (Optional) 🔍

Send to BotFather:
```
/setinline
```

**For Ralph:**
• You can skip this!
• Or enable if you want inline features later
• Not required for basic Ralph functionality

*That's it!* Your bot permissions are configured!

Click below when you're done!
"""

    def get_bot_permissions_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for bot permissions guide.

        Returns:
            Keyboard with BotFather link and action buttons
        """
        keyboard = [
            [InlineKeyboardButton("👨‍💼 Open BotFather", url="https://t.me/BotFather")],
            [InlineKeyboardButton("📋 Show Commands", callback_data="show_permission_commands")],
            [InlineKeyboardButton("✅ I Configured Permissions!", callback_data="bot_permissions_done")],
            [InlineKeyboardButton("❓ Help", callback_data="bot_permissions_help")],
            [InlineKeyboardButton("◀️ Back", callback_data="setup_back_permissions")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_bot_permissions_commands_message(self) -> str:
        """Get quick reference of BotFather commands for permissions.

        Returns:
            Commands reference
        """
        return """*Quick Commands Reference!* 📋

Copy and paste these into BotFather:

**Access your bot settings:**
```
/mybots
```

**Disable Privacy Mode (Recommended):**
```
/setprivacy
```
Then choose: `Disable`

**Enable Inline Mode (Optional):**
```
/setinline
```

**View all settings:**
Select your bot → "Bot Settings"

*Ralph says:*
"Just copy these! Paste in BotFather! Easy peasy!" 👃

[Official Telegram Bot Docs](https://core.telegram.org/bots#privacy-mode)
"""

    def get_bot_permissions_help_message(self) -> str:
        """Get troubleshooting help for bot permissions.

        Returns:
            Common problems and solutions
        """
        return """*Bot Permissions Help!* 🆘

**Common Problems:**

**Problem 1: "BotFather doesn't respond to /setprivacy"**
→ Make sure you typed it exactly: `/setprivacy`
→ Try `/mybots` first, select bot, then Bot Settings
→ Look for "Group Privacy" option there!

**Problem 2: "I don't see the Disable option"**
→ BotFather shows "Enable" or "Disable"
→ Current setting is shown first
→ Choose the OPPOSITE of current setting!

**Problem 3: "Privacy mode keeps turning back on"**
→ Check you selected the RIGHT bot in BotFather
→ Try setting it again
→ Restart your bot after changing

**Problem 4: "Not sure if settings applied"**
→ BotFather shows confirmation message
→ You can check anytime: `/mybots` → your bot → Bot Settings
→ Current settings are shown!

**Problem 5: "Bot still doesn't see group messages"**
→ Remove bot from group and add again
→ Check privacy mode is DISABLED
→ Make sure bot is admin (if group requires it)

*What Privacy Mode should be:*
**DISABLED** = Bot sees all messages (Ralph needs this!)
**ENABLED** = Bot only sees commands (don't use this!)

*Still confused?*
Check the official docs or tell Ralph what's wrong!

[Telegram Bot Privacy Mode](https://core.telegram.org/bots/features#privacy-mode)
"""

    def get_bot_permissions_verification_message(self) -> str:
        """Get message to verify permissions are set correctly.

        Returns:
            Verification checklist
        """
        return """*Let's Verify Your Settings!* ✅

Ralph gonna check if everything's configured right!

**Checklist:**

□ Privacy Mode: **DISABLED**
  → Bot can see all messages
  → Required for Ralph to work!

□ Groups: **ENABLED**
  → Bot can join group chats
  → Good for team projects!

□ Inline Mode: **Your choice!**
  → Optional feature
  → Not needed for basic Ralph!

*How to verify:*

1. Go to @BotFather
2. Send `/mybots`
3. Select your bot
4. Click "Bot Settings"
5. Check each setting!

**Privacy Mode should say:**
"Privacy mode is **disabled** for YourBot"

*Everything look good?*
Click "Done" below if settings are correct!

*Need to change something?*
No problem! Just go back to BotFather and adjust!

Ralph says: "Take your time! Getting settings right is important!" 👃
"""

    # Repository Creation Wizard (OB-004)

    def get_repo_creation_intro_message(self) -> str:
        """Get introduction message for repository creation.

        Returns:
            Repository creation introduction
        """
        return """*Step 3: Make Your Code House!* 🏠

Time to make a repository! (Ralph call it "repo" for short!)

*What's a repository?*
It's like a house for your code! Everything lives there!

Think of it like:
• A folder on GitHub where your code lives
• A history book of all changes you make
• A backup in case your computer breaks!

GitHub keeps it safe in the cloud! ☁️

*Two ways to make a repo:*

**Option 1:** Use the website (easier, Ralph recommend!)
**Option 2:** Use the command line (for fancy developers!)

Ralph help with both!

*First, what you wanna call your project?*
"""

    def get_repo_creation_method_message(self, project_name: str) -> str:
        """Get message for choosing repository creation method.

        Args:
            project_name: Name of the project

        Returns:
            Method selection message
        """
        return f"""*Great! Your project is called "{project_name}"!*

Now, how you wanna make the repo?

**Option 1: Use GitHub Website** (Easier!)
• Click a button
• Fill in a form
• Done!
Ralph guide you through it!

**Option 2: Use Command Line** (Faster if you know what you doing!)
• One command
• All done!
Needs `gh` CLI tool installed!

*Which way you wanna do it?*
"""

    def get_repo_creation_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for repository creation method selection.

        Returns:
            Keyboard with method options
        """
        keyboard = [
            [InlineKeyboardButton("🌐 Use GitHub Website (Easier)", callback_data="repo_method_web")],
            [InlineKeyboardButton("⌨️ Use Command Line", callback_data="repo_method_cli")],
            [InlineKeyboardButton("◀️ Back", callback_data="setup_back_github")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_repo_web_creation_message(self, project_name: str) -> str:
        """Get instructions for creating repository via web.

        Args:
            project_name: Name of the project

        Returns:
            Web creation instructions
        """
        return f"""*Creating "{project_name}" on GitHub!* 🌐

Okay! Follow these steps!

**Step 1:** Click the link below to go to GitHub
**Step 2:** Click the green "New" button (or the "+" in top right)
**Step 3:** Fill in the form:
• *Repository name:* `{project_name}`
• *Description:* "My awesome project!" (or whatever you want!)
• *Public or Private?*

**Public** = Everyone can see it (good for learning!)
**Private** = Only you can see it (good for secrets!)

Ralph recommend Public for learning!

**Step 4:** Check "Add a README file" box
**Step 5:** Click "Create repository"

*Done?* Click below when you made it!

🌐 [Create New Repository](https://github.com/new)
"""

    def get_repo_cli_creation_message(self, project_name: str) -> str:
        """Get instructions for creating repository via CLI.

        Args:
            project_name: Name of the project

        Returns:
            CLI creation instructions
        """
        return f"""*Creating "{project_name}" with Command Line!* ⌨️

You using the fancy way! Ralph impressed!

**First, you need the `gh` tool!**

Check if you got it:
```bash
gh --version
```

If you see a version number, you got it! If not, install it:
• Mac: `brew install gh`
• Linux: Check your package manager
• Windows: Download from https://cli.github.com

**Then, create your repo!**

*For a PUBLIC repo:* (everyone can see)
```bash
gh repo create {project_name} --public --clone
```

*For a PRIVATE repo:* (only you can see)
```bash
gh repo create {project_name} --private --clone
```

*What this does:*
• `gh repo create` - Makes a new repo
• `{project_name}` - The name
• `--public` or `--private` - Who can see it
• `--clone` - Downloads it to your computer too!

Ralph recommend public for learning!

*Did you run the command?*
"""

    def get_repo_creation_cli_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for CLI repository creation.

        Returns:
            Keyboard with CLI action buttons
        """
        keyboard = [
            [InlineKeyboardButton("✅ I Created It!", callback_data="repo_created")],
            [InlineKeyboardButton("📋 Show Command Again", callback_data="repo_show_command")],
            [InlineKeyboardButton("🌐 Use Website Instead", callback_data="repo_method_web")],
            [InlineKeyboardButton("❓ Need Help", callback_data="repo_help")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_repo_web_creation_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for web repository creation.

        Returns:
            Keyboard with web action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🔗 Open GitHub", url="https://github.com/new")],
            [InlineKeyboardButton("✅ I Created It!", callback_data="repo_created")],
            [InlineKeyboardButton("⌨️ Use Command Line Instead", callback_data="repo_method_cli")],
            [InlineKeyboardButton("❓ Need Help", callback_data="repo_help")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_repo_public_vs_private_message(self) -> str:
        """Get explanation of public vs private repositories.

        Returns:
            Public vs private explanation
        """
        return """*Public vs Private - What's the Difference?* 🤔

**PUBLIC Repository** 🌍
• Anyone on the internet can see it
• Good for: Learning projects, open source, portfolios
• Free forever!
• Other developers can learn from your code
• Shows up on your GitHub profile

**PRIVATE Repository** 🔒
• Only YOU can see it (unless you invite someone)
• Good for: Secret projects, work stuff, personal code
• Also free! (GitHub lets you have private repos now!)
• Nobody can see your code without permission
• Doesn't show on your public profile

*Ralph's Advice:*
If you learning to code → Use PUBLIC!
Other people can help you and see your progress!

If it's got passwords or secrets → Use PRIVATE!
Keep the secret stuff secret!

You can always change it later in settings!
"""

    def get_repo_success_message(self, project_name: str) -> str:
        """Get success message after repository creation.

        Args:
            project_name: Name of the created project

        Returns:
            Success celebration message
        """
        return f"""*Repository Created!* 🎊🏠

Ralph SO HAPPY! You made your first repo!

Your project "{project_name}" now has a home on GitHub!

*What you got now:*
✅ SSH key to talk to GitHub
✅ GitHub knows your computer
✅ A repository (code house) ready for code!

*Next Steps:*
Ralph can help you:
• Set up your git name and email
• Clone the repo to your computer
• Make your first commit!

This is SO EXCITING! You basically a GitHub expert now!

*Ready to keep going?*
"""

    def get_repo_help_message(self) -> str:
        """Get help message for repository creation issues.

        Returns:
            Repository creation help
        """
        return """*Ralph Help With Repos!* 🆘

**Common Problems:**

**Problem: "Repository name already exists"**
→ Someone already using that name (maybe you!)
→ Try a different name
→ Or check if you already made it: github.com/your-username

**Problem: "gh command not found"**
→ You need to install GitHub CLI first
→ Mac: `brew install gh`
→ Or use the website method instead!

**Problem: "Not logged in to GitHub"**
→ Run: `gh auth login`
→ Follow the prompts to log in
→ Then try creating the repo again

**Problem: "Permission denied"**
→ Make sure you logged into GitHub
→ Run `gh auth status` to check
→ Might need to run `gh auth login` again

**Using the website:**
• Go to: https://github.com/new
• Fill in the form
• Click "Create repository"
• That's it!

*Still stuck?*
Tell Ralph what error you seeing!
"""

    # Setup Resume Functionality (OB-035)

    def check_for_incomplete_setup(
        self,
        user_id: int,
        telegram_id: int
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check if user has an incomplete setup to resume.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            Tuple of (has_incomplete, state_dict)
        """
        if not self.state_persistence_available or not self.state_manager:
            return False, None

        try:
            return self.state_manager.has_incomplete_setup(user_id, telegram_id)
        except Exception as e:
            self.logger.error(f"Error checking for incomplete setup: {e}")
            return False, None

    def get_resume_setup_message(self, state: Dict[str, Any]) -> str:
        """Get message offering to resume incomplete setup.

        Args:
            state: The saved setup state

        Returns:
            Resume offer message with progress
        """
        if not self.state_manager:
            return ""

        return self.state_manager.get_resume_message(state)

    def get_resume_setup_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for resume/restart choice.

        Returns:
            Keyboard with Resume and Restart buttons
        """
        keyboard = [
            [InlineKeyboardButton("▶️ Resume Setup (Recommended)", callback_data="setup_resume")],
            [InlineKeyboardButton("🔄 Start Fresh", callback_data="setup_restart")],
            [InlineKeyboardButton("📊 Show My Progress", callback_data="setup_show_progress")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def save_state(
        self,
        user_id: int,
        telegram_id: int,
        state: Dict[str, Any]
    ) -> bool:
        """Save the current setup state.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID
            state: Current state dictionary

        Returns:
            True if saved successfully
        """
        if not self.state_persistence_available or not self.state_manager:
            return False

        try:
            return self.state_manager.save_setup_state(user_id, telegram_id, state)
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
            return False

    def load_state(
        self,
        user_id: int,
        telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        """Load saved setup state.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            Saved state dictionary or None
        """
        if not self.state_persistence_available or not self.state_manager:
            return None

        try:
            return self.state_manager.load_setup_state(user_id, telegram_id)
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
            return None

    def clear_state(self, user_id: int, telegram_id: int) -> bool:
        """Clear saved setup state (for restart).

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            True if cleared successfully
        """
        if not self.state_persistence_available or not self.state_manager:
            return False

        try:
            return self.state_manager.clear_setup_state(user_id, telegram_id)
        except Exception as e:
            self.logger.error(f"Error clearing state: {e}")
            return False

    def mark_complete(self, user_id: int, telegram_id: int) -> bool:
        """Mark setup as completed.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            True if marked successfully
        """
        if not self.state_persistence_available or not self.state_manager:
            return False

        try:
            return self.state_manager.mark_setup_complete(user_id, telegram_id)
        except Exception as e:
            self.logger.error(f"Error marking complete: {e}")
            return False

    def get_restart_confirmation_message(self) -> str:
        """Get message confirming user wants to restart.

        Returns:
            Confirmation message
        """
        return """*Start Fresh?* 🔄

Ralph can start over from the beginning!

**Warning:** This will erase your current progress!

If you already did some steps (like making SSH keys), you can still use them! Ralph will just ask you about them again!

*Are you sure you wanna restart?*
"""

    def get_restart_confirmation_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for restart confirmation.

        Returns:
            Keyboard with confirm/cancel options
        """
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Start Fresh", callback_data="setup_restart_confirm")],
            [InlineKeyboardButton("❌ No, Keep My Progress", callback_data="setup_resume")],
            [InlineKeyboardButton("◀️ Back to Options", callback_data="setup_back_resume_choice")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_stale_setup_message(self, state: Dict[str, Any]) -> str:
        """Get message for stale/expired setups.

        Args:
            state: The expired state

        Returns:
            Stale setup message
        """
        if not self.state_manager:
            age = "a while"
        else:
            age = self.state_manager.get_setup_age_message(state)

        return f"""*Ralph found an old setup!* ⏰

You started setting up {age}!

That's pretty old! The setup might not work anymore!

**Ralph recommends:** Start fresh!

But if you wanna try resuming anyway, Ralph won't stop you! Maybe you almost done!

*What you wanna do?*
"""

    def get_stale_setup_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for stale setup choice.

        Returns:
            Keyboard with resume/restart options emphasizing restart
        """
        keyboard = [
            [InlineKeyboardButton("🔄 Start Fresh (Recommended)", callback_data="setup_restart")],
            [InlineKeyboardButton("▶️ Try to Resume Anyway", callback_data="setup_resume")],
        ]
        return InlineKeyboardMarkup(keyboard)

    # Rollback Functionality (OB-031)

    def track_change(
        self,
        user_id: int,
        step_name: str,
        change_type: str,
        details: Dict[str, Any]
    ) -> Optional[str]:
        """Track a setup change for potential rollback.

        Args:
            user_id: User ID
            step_name: Setup step name
            change_type: Type of change
            details: Change details

        Returns:
            Change ID or None
        """
        if not self.rollback_available or not self.rollback_manager:
            return None

        return self.rollback_manager.track_change(
            user_id=user_id,
            step_name=step_name,
            change_type=change_type,
            details=details
        )

    def track_env_update(
        self,
        user_id: int,
        step_name: str,
        variable_name: str,
        old_value: Optional[str] = None
    ) -> Optional[str]:
        """Track an environment variable update.

        Args:
            user_id: User ID
            step_name: Setup step name
            variable_name: Environment variable name
            old_value: Previous value (None if new)

        Returns:
            Change ID or None
        """
        if not self.rollback_available or not self.rollback_manager:
            return None

        return self.rollback_manager.track_env_variable(
            user_id=user_id,
            step_name=step_name,
            variable_name=variable_name,
            old_value=old_value
        )

    def track_file_change(
        self,
        user_id: int,
        step_name: str,
        file_path: str,
        is_new: bool = True,
        backup_content: Optional[str] = None
    ) -> Optional[str]:
        """Track a file creation or modification.

        Args:
            user_id: User ID
            step_name: Setup step name
            file_path: Path to the file
            is_new: True if file is newly created
            backup_content: Original content if modified

        Returns:
            Change ID or None
        """
        if not self.rollback_available or not self.rollback_manager:
            return None

        if is_new:
            return self.rollback_manager.track_file_creation(
                user_id=user_id,
                step_name=step_name,
                file_path=file_path
            )
        else:
            return self.rollback_manager.track_file_modification(
                user_id=user_id,
                step_name=step_name,
                file_path=file_path,
                backup_content=backup_content
            )

    def get_recent_changes(
        self,
        user_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent setup changes for undo.

        Args:
            user_id: User ID
            limit: Max changes to return

        Returns:
            List of recent changes
        """
        if not self.rollback_available or not self.rollback_manager:
            return []

        return self.rollback_manager.get_recent_changes(user_id, limit)

    def get_rollback_ui_message(self, user_id: int) -> str:
        """Get the rollback UI message showing recent changes.

        Args:
            user_id: User ID

        Returns:
            Formatted message with recent changes
        """
        if not self.rollback_available or not self.rollback_manager:
            return "*Undo Not Available* 😔\n\nRalph can't undo changes right now!"

        return self.rollback_manager.get_rollback_summary(user_id)

    def get_rollback_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Get keyboard with undo options.

        Args:
            user_id: User ID

        Returns:
            Keyboard with undo buttons
        """
        changes = self.get_recent_changes(user_id, limit=5)

        keyboard = []

        # Add undo buttons for each recent change
        for i, change in enumerate(changes[:3], 1):  # Show top 3
            step = change["step_name"].replace("_", " ").title()
            button_text = f"↩️ Undo: {step}"
            callback_data = f"undo_{change['change_id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        # Add "View All Changes" option if there are more
        if len(changes) > 3:
            keyboard.append([
                InlineKeyboardButton("📋 View All Changes", callback_data="rollback_view_all")
            ])

        # Add back button
        keyboard.append([
            InlineKeyboardButton("◀️ Back to Setup", callback_data="setup_continue")
        ])

        return InlineKeyboardMarkup(keyboard)

    def rollback_change(
        self,
        change_id: str
    ) -> tuple[bool, str]:
        """Rollback a specific change.

        Args:
            change_id: ID of the change to undo

        Returns:
            Tuple of (success, message)
        """
        if not self.rollback_available or not self.rollback_manager:
            return False, "Rollback not available"

        return self.rollback_manager.rollback_change(change_id)

    def rollback_step(
        self,
        user_id: int,
        step_name: str
    ) -> tuple[bool, str, List[str]]:
        """Rollback all changes from a specific step.

        Args:
            user_id: User ID
            step_name: Name of the step to rollback

        Returns:
            Tuple of (success, summary, details)
        """
        if not self.rollback_available or not self.rollback_manager:
            return False, "Rollback not available", []

        return self.rollback_manager.rollback_step(user_id, step_name)

    def get_undo_success_message(self, details: str) -> str:
        """Get success message after undoing a change.

        Args:
            details: Details of what was undone

        Returns:
            Success message with Ralph's personality
        """
        return f"""*Change Undone!* ↩️✅

Ralph rolled back the change!

*What was undone:*
{details}

Your setup is now like before! Ralph kept everything safe!

If something still looks wrong, you can:
• Undo more changes
• Start the step over
• Tell Ralph what's wrong!

*What you wanna do next?*
"""

    def get_undo_failed_message(self, error: str) -> str:
        """Get error message when undo fails.

        Args:
            error: Error details

        Returns:
            Error message with Ralph's personality
        """
        return f"""*Undo Failed!* ❌😔

Ralph tried to undo the change but something went wrong!

*Error:*
{error}

*Why this might happen:*
• File was already changed or deleted
• Backup file is missing
• Permission issues

*What you can do:*
• Try undoing a different change
• Manually fix the issue
• Start fresh with /setup

Ralph sorry this didn't work! 😔
"""

    def get_rollback_explanation_message(self) -> str:
        """Get explanation of rollback functionality.

        Returns:
            Educational message about rollback
        """
        return """*What's Rollback?* ↩️

Ralph tracks every change during setup! If something goes wrong, you can UNDO it!

*What Ralph tracks:*
📄 Files created (like .env, config files)
🔧 Settings changed (git config, environment variables)
🗂️ Folders created for your project

*How it works:*
1. Ralph saves a copy before changing stuff
2. If something breaks, click "Undo"
3. Ralph restores everything!
4. Try the step again!

*Why this is helpful:*
✅ No fear of messing up!
✅ Easy to fix mistakes
✅ Can restart individual steps
✅ Your computer stays clean

Think of it like:
• Ctrl+Z for your entire setup! ⌨️
• A time machine for configuration! ⏰
• A safety net for beginners! 🎪

Ralph got your back! Never worry about breaking stuff!
"""

    def get_rollback_help_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for rollback help screen.

        Returns:
            Keyboard with rollback action options
        """
        keyboard = [
            [InlineKeyboardButton("📋 View Recent Changes", callback_data="rollback_view_recent")],
            [InlineKeyboardButton("📚 Learn About Rollback", callback_data="rollback_explain")],
            [InlineKeyboardButton("◀️ Back to Setup", callback_data="setup_continue")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_rollback_step_message(self, step_name: str) -> str:
        """Get message for rolling back an entire step.

        Args:
            step_name: Name of the step to rollback

        Returns:
            Confirmation message
        """
        step_display = step_name.replace("_", " ").title()

        return f"""*Undo Entire Step?* 🔄

You want to undo ALL changes from: **{step_display}**

**Warning:** This will reverse EVERYTHING Ralph did in this step!

*What will happen:*
• All files created in this step will be removed
• All settings will be restored to before
• You'll start this step fresh

This is helpful if the step went wrong and you wanna try again!

*Are you sure?*
"""

    def get_rollback_step_keyboard(self, step_name: str) -> InlineKeyboardMarkup:
        """Get keyboard for step rollback confirmation.

        Args:
            step_name: Name of the step

        Returns:
            Confirmation keyboard
        """
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Undo This Step", callback_data=f"rollback_step_confirm_{step_name}")],
            [InlineKeyboardButton("❌ No, Keep Changes", callback_data="rollback_cancel")],
            [InlineKeyboardButton("📋 Show What Will Be Undone", callback_data=f"rollback_preview_{step_name}")],
        ]
        return InlineKeyboardMarkup(keyboard)


    # Setup Verification Suite (OB-047)

    def run_verification(self, include_optional: bool = True) -> Dict[str, Any]:
        """Run the setup verification suite.

        Args:
            include_optional: Whether to check optional configurations

        Returns:
            Verification results dictionary
        """
        if not self.verifier_available or not self.verifier:
            return {
                "overall_status": "unavailable",
                "overall_message": "Setup verification is not available",
                "counts": {"total": 0, "pass": 0, "fail": 0, "warning": 0, "info": 0},
                "results": [],
                "by_category": {}
            }

        return self.verifier.verify_all(include_optional=include_optional)

    def get_verification_message(self, include_optional: bool = True) -> str:
        """Get the verification dashboard message.

        Args:
            include_optional: Whether to check optional configurations

        Returns:
            Formatted verification message with Ralph's personality
        """
        if not self.verifier_available or not self.verifier:
            return """*Ralph Can't Check Setup* 😔

Setup verifier is not available right now!

But don't worry! Ralph can still help you set things up manually!

*What you need:*
• .env file with your API keys
• Git configured with your name and email
• SSH key added to GitHub
• Telegram bot token from @BotFather

*Want help with any of these?*
"""

        # Run verification
        self.verifier.verify_all(include_optional=include_optional)

        # Get dashboard message
        return self.verifier.get_dashboard_message()

    def get_verification_keyboard(self, has_issues: bool = False) -> InlineKeyboardMarkup:
        """Get keyboard for verification results.

        Args:
            has_issues: Whether verification found issues

        Returns:
            Keyboard with relevant action buttons
        """
        keyboard = []

        if has_issues:
            keyboard.append([
                InlineKeyboardButton("🔧 Fix Issues", callback_data="setup_fix_issues")
            ])

        keyboard.extend([
            [InlineKeyboardButton("🔄 Re-run Verification", callback_data="setup_verify_again")],
            [InlineKeyboardButton("📄 Export Report", callback_data="setup_export_report")],
            [InlineKeyboardButton("✅ Continue Anyway", callback_data="setup_continue_after_verify")],
            [InlineKeyboardButton("◀️ Back to Setup", callback_data="setup_continue")],
        ])

        return InlineKeyboardMarkup(keyboard)

    def get_verification_intro_message(self) -> str:
        """Get introduction message for verification.

        Returns:
            Verification introduction with Ralph's personality
        """
        return """*Ralph Gonna Check Your Setup!* 🔍

Before we finish, Ralph wants to make sure EVERYTHING is working!

Ralph will check:
• Your system (Python, Git, etc.)
• Your API keys (Telegram, Groq, etc.)
• Your Git configuration
• Your SSH keys
• Your project files

*Why check?*
• Make sure you won't get errors later!
• Find problems BEFORE they cause trouble!
• Ralph gives you fix suggestions!

This only takes a few seconds!

*Ready?*
"""

    def get_verification_intro_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for verification introduction.

        Returns:
            Keyboard with verification options
        """
        keyboard = [
            [InlineKeyboardButton("✅ Check Everything!", callback_data="verify_full")],
            [InlineKeyboardButton("⚡ Check Required Only", callback_data="verify_required")],
            [InlineKeyboardButton("⏭️ Skip Verification", callback_data="setup_skip_verify")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def export_verification_report(self, filename: str = "setup_verification_report.txt") -> Optional[str]:
        """Export verification results to a file.

        Args:
            filename: Name of the report file

        Returns:
            Path to the report or None if unavailable
        """
        if not self.verifier_available or not self.verifier:
            return None

        if not self.verifier.results:
            # Run verification first
            self.verifier.verify_all(include_optional=True)

        return self.verifier.export_report(filename)

    def get_verification_complete_message(self, summary: Dict[str, Any]) -> str:
        """Get completion message after verification.

        Args:
            summary: Verification summary dictionary

        Returns:
            Completion message with Ralph's personality
        """
        if summary["overall_status"] == "complete":
            return """*🎉 EVERYTHING PERFECT! 🎉*

Ralph checked EVERYTHING and it all works!

You're ready to start using Ralph Mode!

*What's working:*
✅ Your system is set up correctly
✅ All required API keys are configured
✅ Git is ready to go
✅ SSH keys are working
✅ Project files are all there!

*Next steps:*
• Start the bot: `python ralph_bot.py`
• Talk to Ralph on Telegram!
• Drop some code and watch the magic happen!

Ralph SO PROUD of you! You did it! 🎊
"""
        elif summary["overall_status"] == "warnings":
            return f"""*⚠️ Almost There! ⚠️*

Ralph found {summary['counts']['warning']} warnings!

*What this means:*
• Most things are working!
• Some stuff might not be perfect
• Ralph gave you suggestions to fix them!

*You can either:*
• Fix the warnings now (recommended!)
• Continue and fix them later (risky!)

The bot MIGHT work with warnings, but Ralph recommend fixing them!

*What you wanna do?*
"""
        elif summary["overall_status"] == "incomplete":
            return f"""*❌ Setup Incomplete! ❌*

Ralph found {summary['counts']['fail']} problems!

*What this means:*
• Some required stuff is missing!
• The bot WON'T work without these!
• Ralph gave you steps to fix them!

*Don't worry!* Ralph helps you fix everything!

Look at the dashboard above to see what needs fixing!

*Ready to fix these issues?*
"""
        else:
            return """*Ralph Not Sure What Happened* 🤔

Verification couldn't run properly!

But don't worry! We can try again or set things up manually!

*What you wanna do?*
"""

    def get_verification_complete_keyboard(self, overall_status: str) -> InlineKeyboardMarkup:
        """Get keyboard for verification complete screen.

        Args:
            overall_status: Overall verification status

        Returns:
            Keyboard with appropriate next steps
        """
        keyboard = []

        if overall_status == "complete":
            keyboard.extend([
                [InlineKeyboardButton("🚀 Start Using Ralph!", callback_data="setup_start_bot")],
                [InlineKeyboardButton("📄 Export Report", callback_data="setup_export_report")],
                [InlineKeyboardButton("✅ Finish Setup", callback_data="setup_finish")],
            ])
        elif overall_status == "warnings":
            keyboard.extend([
                [InlineKeyboardButton("🔧 Fix Warnings First", callback_data="setup_fix_warnings")],
                [InlineKeyboardButton("✅ Continue Anyway", callback_data="setup_continue_warnings")],
                [InlineKeyboardButton("🔄 Re-run Verification", callback_data="setup_verify_again")],
            ])
        elif overall_status == "incomplete":
            keyboard.extend([
                [InlineKeyboardButton("🔧 Fix Issues Now!", callback_data="setup_fix_issues")],
                [InlineKeyboardButton("📋 Show Issue Details", callback_data="setup_show_issues")],
                [InlineKeyboardButton("🔄 Re-run Verification", callback_data="setup_verify_again")],
            ])
        else:
            keyboard.extend([
                [InlineKeyboardButton("🔄 Try Again", callback_data="setup_verify_again")],
                [InlineKeyboardButton("◀️ Back to Setup", callback_data="setup_continue")],
            ])

        return InlineKeyboardMarkup(keyboard)

    def get_fix_suggestions_message(self, summary: Dict[str, Any]) -> str:
        """Get detailed fix suggestions for failed/warning items.

        Args:
            summary: Verification summary dictionary

        Returns:
            Formatted fix suggestions message
        """
        lines = ["*🔧 How to Fix Issues*\n"]

        # Get failed and warning results
        issues = [r for r in summary["results"] if r.status.name in ["FAIL", "WARNING"]]

        if not issues:
            return "*No issues to fix!* ✅\n\nEverything looks good!"

        for i, result in enumerate(issues, 1):
            status_emoji = result.status.value
            lines.append(f"{i}. {status_emoji} *{result.name}*")
            lines.append(f"   Problem: {result.message}")

            if result.fix_suggestion:
                lines.append(f"   Fix: {result.fix_suggestion}")

            if result.details:
                lines.append(f"   Details: {result.details}")

            lines.append("")

        lines.append("*After fixing, re-run verification to check!*")

        return "\n".join(lines)

    # Webhook vs Polling Explainer (OB-038)

    def get_webhook_vs_polling_intro_message(self) -> str:
        """Get introduction message explaining webhook vs polling.

        Returns:
            Webhook vs polling introduction with Ralph's personality
        """
        return """*How Should Your Bot Get Messages?* 📨

Ralph needs to explain something important about bots!

Your bot needs to CHECK for messages from Telegram! But there's TWO ways to do it!

Think of it like checking for mail:

**📪 Polling** (Like checking your mailbox)
You walk to the mailbox every few seconds to see if there's new mail!

**📫 Webhook** (Like a mail person knocking)
The mail person brings mail RIGHT to your door when it arrives!

Let Ralph explain both ways so you can pick the best one!

*Ready to learn?*
"""

    def get_webhook_vs_polling_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for webhook vs polling introduction.

        Returns:
            Keyboard with learn/skip options
        """
        keyboard = [
            [InlineKeyboardButton("📚 Explain Both Methods!", callback_data="webhook_explain_both")],
            [InlineKeyboardButton("🤔 Help Me Choose", callback_data="webhook_help_choose")],
            [InlineKeyboardButton("⏭️ I Already Know!", callback_data="webhook_skip_explanation")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_webhook_polling_explanation_message(self) -> str:
        """Get detailed explanation of webhook and polling.

        Returns:
            Detailed comparison message
        """
        return """*Webhook vs Polling - The Full Story!* 📖

**🔄 POLLING (Checking the Mailbox)**

*How it works:*
Your bot asks Telegram "Got any messages?" every second or two!

*Pros:*
✅ SUPER EASY to set up! (Just run the bot!)
✅ Works ANYWHERE (even on your laptop!)
✅ No domain name needed!
✅ No SSL certificate needed!
✅ Perfect for testing!

*Cons:*
❌ Slower (checks every 1-2 seconds)
❌ Uses more internet (constantly asking)
❌ Less efficient for busy bots

*Best for:*
• Running on your computer
• Testing and development
• Small personal bots
• No server/domain available

**🔗 WEBHOOK (Doorbell Ring)**

*How it works:*
Telegram sends messages DIRECTLY to your server the instant they arrive!

*Pros:*
✅ INSTANT delivery! (no delay!)
✅ More efficient (only when messages arrive)
✅ Better for busy bots
✅ Professional setup

*Cons:*
❌ Needs a public server (not your laptop!)
❌ Needs a domain name (like yourbot.com)
❌ Needs SSL certificate (HTTPS)
❌ More complex setup

*Best for:*
• Production bots (real users!)
• High-traffic bots
• Professional deployments
• When you have a server

*Ralph's Recommendation:*
🎯 Start with POLLING (easier!)
🎯 Switch to WEBHOOK later when you deploy!

Most developers use POLLING during development and WEBHOOK in production!

*What you wanna use?*
"""

    def get_webhook_polling_comparison_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard after comparison explanation.

        Returns:
            Keyboard with method selection options
        """
        keyboard = [
            [InlineKeyboardButton("📪 Use Polling (Easier)", callback_data="method_choose_polling")],
            [InlineKeyboardButton("📫 Use Webhook (Advanced)", callback_data="method_choose_webhook")],
            [InlineKeyboardButton("🤔 Still Not Sure?", callback_data="webhook_help_decide")],
            [InlineKeyboardButton("◀️ Back", callback_data="webhook_intro")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_webhook_help_choose_message(self) -> str:
        """Get message to help user choose between methods.

        Returns:
            Decision guide message
        """
        return """*Let Ralph Help You Choose!* 🤔

Answer these questions and Ralph will tell you what to use!

**Question 1: Where will your bot run?**

A. On my laptop or home computer
B. On a server or cloud (like AWS, Linode, etc.)

**Question 2: Do you have a domain name?**

A. No, I don't have a domain
B. Yes, I have a domain (like mybot.com)

**Question 3: What's your bot for?**

A. Learning, testing, personal use
B. Real users, production, business

**Ralph's Simple Guide:**

*If you answered mostly A's:*
👉 **USE POLLING!** It's perfect for you!

*If you answered mostly B's:*
👉 **USE WEBHOOK!** You're ready for the pro setup!

*Still not sure?*
👉 **START WITH POLLING!** You can always switch later!

Ralph recommend EVERYONE starts with polling! It's easier and works great!

*What you wanna do?*
"""

    def get_help_choose_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for choosing method after guidance.

        Returns:
            Keyboard with method options
        """
        keyboard = [
            [InlineKeyboardButton("📪 I'll Use Polling!", callback_data="method_choose_polling")],
            [InlineKeyboardButton("📫 I'll Try Webhook!", callback_data="method_choose_webhook")],
            [InlineKeyboardButton("📚 Read Comparison Again", callback_data="webhook_explain_both")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_polling_setup_guide_message(self) -> str:
        """Get setup guide for polling method.

        Returns:
            Polling setup instructions
        """
        return """*Setting Up Polling!* 📪

Great choice! Polling is EASY!

Ralph already set this up for you! Your bot uses polling by default!

*How it works in the code:*
```python
# In ralph_bot.py, Ralph uses:
application.run_polling()
```

That's it! When you run your bot, it automatically starts polling Telegram for messages!

*To start your bot:*
```bash
python ralph_bot.py
```

The bot will:
1. Connect to Telegram
2. Start checking for messages
3. Respond when messages arrive!

*Testing it:*
1. Start your bot with the command above
2. Open Telegram
3. Find your bot (@your_bot_username)
4. Send a message!
5. Bot should respond instantly!

*What you'll see:*
```
Starting bot in polling mode...
Bot is polling for updates...
```

If you see that, IT'S WORKING! 🎉

*Pros of this setup:*
✅ Works on your laptop
✅ No configuration needed
✅ Just works!
✅ Perfect for development

*Want to test your bot now?*
"""

    def get_polling_setup_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for polling setup.

        Returns:
            Keyboard with next steps for polling
        """
        keyboard = [
            [InlineKeyboardButton("✅ Got It! I'll Try It!", callback_data="polling_understood")],
            [InlineKeyboardButton("🧪 How Do I Test?", callback_data="polling_test_guide")],
            [InlineKeyboardButton("🔧 Troubleshooting", callback_data="polling_troubleshoot")],
            [InlineKeyboardButton("◀️ Back to Comparison", callback_data="webhook_explain_both")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_webhook_setup_guide_message(self) -> str:
        """Get setup guide for webhook method.

        Returns:
            Webhook setup instructions
        """
        return """*Setting Up Webhook!* 📫

Okay! Webhook is more advanced but VERY powerful!

*What you need:*
1. ✅ A public server (not your laptop!)
2. ✅ A domain name (like mybot.example.com)
3. ✅ SSL certificate (for HTTPS)
4. ✅ Your bot needs to be accessible from the internet

*Step 1: Get Your Server Ready*

Make sure your bot is running on a server with a public IP!

*Step 2: Set Up Domain + SSL*

Point your domain to your server's IP
Get an SSL certificate (use Let's Encrypt - it's FREE!)

*Step 3: Configure Webhook in Code*

```python
# In ralph_bot.py, use:
application.run_webhook(
    listen="0.0.0.0",
    port=8443,
    url_path="webhook",
    webhook_url="https://yourbot.com/webhook"
)
```

*Step 4: Tell Telegram About Your Webhook*

Run this once:
```python
await application.bot.set_webhook(
    url="https://yourbot.com/webhook"
)
```

*Step 5: Test It!*

Send a message to your bot - should respond instantly!

*Common Issues:*

**"Webhook failed"**
→ Check your SSL certificate is valid
→ Make sure HTTPS is working
→ Check firewall allows port 8443

**"Connection refused"**
→ Bot not running?
→ Wrong port?
→ Firewall blocking?

*Advanced Options:*

You can use services like:
• **Nginx** as a reverse proxy
• **Certbot** for SSL certificates
• **Systemd** to keep bot running

Ralph recommend reading Telegram's webhook guide:
🔗 [Telegram Webhook Guide](https://core.telegram.org/bots/webhooks)

*This is complex! Want to stick with polling?*
"""

    def get_webhook_setup_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for webhook setup.

        Returns:
            Keyboard with webhook setup options
        """
        keyboard = [
            [InlineKeyboardButton("✅ I Set It Up!", callback_data="webhook_test")],
            [InlineKeyboardButton("📚 More Details", url="https://core.telegram.org/bots/webhooks")],
            [InlineKeyboardButton("😅 Too Hard! Use Polling", callback_data="method_choose_polling")],
            [InlineKeyboardButton("🔧 Troubleshooting", callback_data="webhook_troubleshoot")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_polling_test_guide_message(self) -> str:
        """Get guide for testing polling setup.

        Returns:
            Polling test guide message
        """
        return """*Testing Your Polling Bot!* 🧪

Follow these steps to test if it works!

**Step 1: Start the bot**
```bash
python ralph_bot.py
```

**Step 2: Watch the output**
You should see:
```
Starting bot...
Bot is polling for updates...
Logged in as: YourBotName
```

**Step 3: Open Telegram**
• Open Telegram on your phone or computer
• Search for your bot: @your_bot_username
• Click START (or tap the start button)

**Step 4: Send a test message**
Type: `/start`

**Step 5: Check if bot responds**
Your bot should send a welcome message back!

*What you'll see in terminal:*
```
Received message from User: /start
Sending response...
```

*If it works:* 🎉 YOU DID IT!

*If it doesn't work:*
1. Check bot token is correct in .env
2. Make sure bot is running (no errors in terminal)
3. Check internet connection
4. Try clicking "Help" below!

*Ready to test?*
"""

    def get_polling_test_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for polling test guide.

        Returns:
            Keyboard with test-related options
        """
        keyboard = [
            [InlineKeyboardButton("✅ It Works!", callback_data="polling_test_success")],
            [InlineKeyboardButton("❌ It's Not Working", callback_data="polling_troubleshoot")],
            [InlineKeyboardButton("📋 Show Steps Again", callback_data="polling_test_guide")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_webhook_test_guide_message(self) -> str:
        """Get guide for testing webhook setup.

        Returns:
            Webhook test guide message
        """
        return """*Testing Your Webhook!* 🧪

Let's make sure webhook is working!

**Step 1: Check Webhook Status**
```python
python -c "
import asyncio
from telegram import Bot

async def check():
    bot = Bot('YOUR_BOT_TOKEN')
    info = await bot.get_webhook_info()
    print(f'Webhook URL: {info.url}')
    print(f'Pending updates: {info.pending_update_count}')
    if info.last_error_message:
        print(f'Error: {info.last_error_message}')
    else:
        print('No errors!')

asyncio.run(check())
"
```

**Step 2: Send Test Message**
• Open Telegram
• Find your bot
• Send: `/start`

**Step 3: Check Server Logs**
Your server should show:
```
Received webhook POST request
Processing update...
Sending response...
```

**Step 4: Verify Response**
Bot should respond instantly (faster than polling!)

*If webhook is NOT set:*
Run this:
```python
python -c "
import asyncio
from telegram import Bot

async def set_hook():
    bot = Bot('YOUR_BOT_TOKEN')
    await bot.set_webhook('https://yourbot.com/webhook')
    print('Webhook set!')

asyncio.run(set_hook())
"
```

*Common Problems:*

**"Failed to resolve host"**
→ Domain DNS not set up correctly

**"SSL certificate verify failed"**
→ SSL certificate is invalid or expired

**"Connection refused"**
→ Bot not listening on correct port

*Need help debugging?*
"""

    def get_webhook_test_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for webhook test guide.

        Returns:
            Keyboard with webhook test options
        """
        keyboard = [
            [InlineKeyboardButton("✅ Webhook Works!", callback_data="webhook_test_success")],
            [InlineKeyboardButton("❌ Having Issues", callback_data="webhook_troubleshoot")],
            [InlineKeyboardButton("📋 Show Check Command", callback_data="webhook_show_check")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_polling_troubleshoot_message(self) -> str:
        """Get troubleshooting guide for polling issues.

        Returns:
            Polling troubleshooting message
        """
        return """*Polling Troubleshooting!* 🔧

Ralph help you fix polling problems!

**Problem 1: "Bot doesn't respond to messages"**
→ Check: Is bot running? Look at terminal
→ Check: Bot token correct in .env file?
→ Check: Internet connection working?
→ Try: Restart the bot

**Problem 2: "Connection error"**
→ Check: Can you access telegram.org?
→ Check: Firewall blocking Python?
→ Try: Different network (mobile hotspot?)

**Problem 3: "Bot is offline in Telegram"**
→ Check: Is ralph_bot.py actually running?
→ Check: No errors in terminal?
→ Try: Send /start to wake it up

**Problem 4: "Timeout errors"**
→ This is normal occasionally!
→ Bot will automatically retry!
→ If happens often, check internet

**Problem 5: "'NoneType' errors"**
→ Check .env has TELEGRAM_BOT_TOKEN set
→ Make sure token is not empty
→ Verify token format (numbers:letters)

**Problem 6: "Webhook already set"**
→ Previous bot had webhook configured!
→ Delete webhook:
```python
python -c "
import asyncio
from telegram import Bot

async def del_hook():
    bot = Bot('YOUR_TOKEN')
    await bot.delete_webhook()
    print('Deleted!')

asyncio.run(del_hook())
"
```

*Still stuck?*
Tell Ralph EXACTLY what error you seeing!
"""

    def get_troubleshoot_keyboard(self, method: str = "polling") -> InlineKeyboardMarkup:
        """Get keyboard for troubleshooting.

        Args:
            method: "polling" or "webhook"

        Returns:
            Keyboard with troubleshooting options
        """
        callback_prefix = method
        keyboard = [
            [InlineKeyboardButton("🔄 I Fixed It!", callback_data=f"{callback_prefix}_test_again")],
            [InlineKeyboardButton("📋 Show Guide Again", callback_data=f"{callback_prefix}_setup_guide")],
            [InlineKeyboardButton("❓ Ask for Help", callback_data=f"{callback_prefix}_ask_help")],
        ]

        if method == "webhook":
            keyboard.append([
                InlineKeyboardButton("😅 Switch to Polling", callback_data="method_choose_polling")
            ])

        return InlineKeyboardMarkup(keyboard)

    def get_webhook_troubleshoot_message(self) -> str:
        """Get troubleshooting guide for webhook issues.

        Returns:
            Webhook troubleshooting message
        """
        return """*Webhook Troubleshooting!* 🔧

Ralph help you fix webhook problems!

**Problem 1: "SSL certificate verify failed"**
→ Your certificate expired or invalid
→ Get new one: `sudo certbot renew`
→ Or use: https://letsencrypt.org

**Problem 2: "Webhook failed: Failed to resolve host"**
→ Domain not pointing to your server
→ Check DNS: `dig yourdomain.com`
→ Wait for DNS to propagate (can take hours!)

**Problem 3: "Connection refused"**
→ Bot not running OR not listening
→ Check bot is started
→ Check port is correct (usually 8443 or 443)
→ Check firewall allows that port

**Problem 4: "Bad webhook: HTTPS required"**
→ Webhook MUST use HTTPS (not HTTP!)
→ Get SSL certificate from Let's Encrypt
→ Make sure URL starts with `https://`

**Problem 5: "Webhook replies timed out"**
→ Your bot takes too long to respond
→ Must respond within 60 seconds!
→ Use async properly
→ Send long tasks to background

**Problem 6: "Wrong response from webhook"**
→ Bot returning wrong status code
→ Must return 200 OK
→ Check your webhook handler code

**Problem 7: "Can't delete webhook"**
→ Run: `await bot.delete_webhook(drop_pending_updates=True)`
→ Then wait a minute before setting new one

*Check webhook status:*
```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
```

*Need more help?*
→ Telegram Webhook Guide: https://core.telegram.org/bots/webhooks
→ Or switch to polling (it's easier!)

*What you wanna do?*
"""

    def get_method_success_message(self, method: str = "polling") -> str:
        """Get success message after method setup.

        Args:
            method: "polling" or "webhook"

        Returns:
            Success celebration message
        """
        if method == "polling":
            return """*Polling Setup Complete!* 🎉📪

Ralph SO PROUD! Your bot is using polling!

*What this means:*
✅ Bot checks for messages automatically
✅ Works on your computer
✅ Easy to test and develop
✅ Just run `python ralph_bot.py` and go!

*Next time you start the bot:*
```bash
python ralph_bot.py
```

And it just WORKS! No extra setup needed!

*When to switch to webhook:*
• When you deploy to a real server
• When you get a domain name
• When you want INSTANT message delivery

But for now, polling is PERFECT!

Ralph recommend keeping this for development! ✨

*Ready to move on?*
"""
        else:  # webhook
            return """*Webhook Setup Complete!* 🎉📫

WOW! You set up webhook! That's ADVANCED!

*What this means:*
✅ INSTANT message delivery
✅ More efficient for busy bots
✅ Professional production setup
✅ Your bot is using HTTPS!

*When you start the bot:*
```bash
python ralph_bot.py
```

It will run in webhook mode! Telegram sends messages DIRECTLY to your server!

*Things to remember:*
• Keep your SSL certificate valid
• Monitor your server logs
• Bot must respond within 60 seconds
• Use a process manager (systemd, pm2) to keep it running

*You're basically a pro now!* 🌟

Ralph SO IMPRESSED!

*Ready to continue setup?*
"""

    def get_method_success_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard after successful method setup.

        Returns:
            Keyboard with next steps
        """
        keyboard = [
            [InlineKeyboardButton("✅ Continue Setup", callback_data="setup_continue_next")],
            [InlineKeyboardButton("📚 Learn More", callback_data="method_learn_more")],
            [InlineKeyboardButton("🔄 Change Method", callback_data="webhook_intro")],
        ]
        return InlineKeyboardMarkup(keyboard)

    # Environment File Creator (OB-008)

    def create_env_file_if_needed(self) -> Tuple[bool, str]:
        """Create .env file if it doesn't exist.

        Returns:
            Tuple of (created, message)
        """
        if not self.env_manager_available:
            return False, "Environment manager not available"

        if self.env_manager.env_exists():
            return False, ".env file already exists"

        try:
            self.env_manager.create_env_file()
            self.env_manager.add_to_gitignore()
            return True, ".env file created successfully"
        except Exception as e:
            self.logger.error(f"Failed to create .env file: {e}")
            return False, f"Error creating .env file: {str(e)}"

    def save_api_key_to_env(self, var_name: str, value: str) -> Tuple[bool, str]:
        """Save an API key to the .env file.

        Args:
            var_name: Environment variable name
            value: API key value

        Returns:
            Tuple of (success, message)
        """
        if not self.env_manager_available:
            return False, "Environment manager not available"

        try:
            # Ensure .env exists
            if not self.env_manager.env_exists():
                self.env_manager.create_env_file()

            # Ensure .gitignore is safe
            self.env_manager.add_to_gitignore()

            # Save the variable
            self.env_manager.set_variable(var_name, value)

            return True, f"{var_name} saved successfully to .env"
        except Exception as e:
            self.logger.error(f"Failed to save {var_name}: {e}")
            return False, f"Error saving {var_name}: {str(e)}"

    def get_env_status_message(self) -> str:
        """Get current .env file status message.

        Returns:
            Formatted status message with Ralph's personality
        """
        if not self.env_manager_available:
            return """*Ralph Can't Check .env* 😔

Environment manager not available right now!

But don't worry! Ralph can still guide you through setup manually!

*What you need to do:*
1. Create a file called `.env` in your project folder
2. Add your API keys there
3. Make sure `.env` is in `.gitignore`

*Need help with this?*
"""

        summary = self.env_manager.get_setup_summary()

        return f"""*Environment File Status* 📄

{summary}

*Ralph's Tips:*
• Never commit .env to GitHub!
• Add all your secret keys here
• This file stays LOCAL only!
• Check it's in .gitignore!

*Need to update something?*
"""

    def get_env_creation_message(self) -> str:
        """Get message explaining .env file creation.

        Returns:
            Educational message about .env files
        """
        return """*Creating Your .env File!* 📄✨

Ralph gonna make a special file for your secrets!

*What is .env?*
• A file that stores your API keys and passwords
• Lives ONLY on YOUR computer
• NEVER goes to GitHub (it's in .gitignore!)
• Keeps your secrets SAFE!

*Why you need this:*
• API keys must stay secret
• Putting them in code = BAD! Anyone on GitHub can see!
• `.env` file = SAFE! Only you can see!

*What Ralph will put in it:*
• Your Telegram bot token
• Your API keys (Anthropic, Groq, etc.)
• Secret keys for security
• Configuration settings

*How it works:*
1. Ralph creates `.env` file
2. Ralph adds it to `.gitignore` (so Git ignores it!)
3. You add your API keys when Ralph asks
4. Ralph saves them safely!

Think of it like a locked diary for your computer! 🔐📖

*Ready for Ralph to create it?*
"""

    def get_env_creation_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for .env file creation.

        Returns:
            Keyboard with creation options
        """
        keyboard = [
            [InlineKeyboardButton("✅ Create .env File", callback_data="env_create_file")],
            [InlineKeyboardButton("📚 Learn More About .env", callback_data="env_learn_more")],
            [InlineKeyboardButton("🔍 Check Current Status", callback_data="env_check_status")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_env_variable_prompt(self, var_name: str) -> str:
        """Get prompt message for entering an environment variable.

        Args:
            var_name: Variable name to prompt for

        Returns:
            Formatted prompt message
        """
        description = self.env_manager.get_variable_description(var_name) if self.env_manager_available else var_name

        return f"""*Setting: {var_name}* 🔑

{description}

*How to do this:*
1. Copy your {var_name.replace('_', ' ').lower()}
2. Paste it in the chat
3. Ralph will save it to `.env` safely!

*Security reminder:*
🔒 This value is SECRET!
🔒 Ralph will store it safely in `.env`
🔒 It will NEVER go to GitHub!

*Ready? Paste your {var_name.replace('_', ' ').lower()} now:*
"""

    def get_env_saved_message(self, var_name: str) -> str:
        """Get success message after saving an environment variable.

        Args:
            var_name: Variable name that was saved

        Returns:
            Success celebration message
        """
        return f"""*{var_name} Saved!* 🎉🔐

Ralph GOT IT! Your {var_name.replace('_', ' ').lower()} is safe!

*What Ralph just did:*
✅ Saved {var_name} to `.env` file
✅ Made sure it's secure (only on YOUR computer!)
✅ Verified `.env` is in `.gitignore`!

*Where is it?*
The value is in: `.env` (this file NEVER goes to GitHub!)

*What this means:*
🔐 Your secret is safe!
✨ Your app can now use this configuration!
🚀 One step closer to being ready!

*Next step?*
"""

    def verify_gitignore_safety(self) -> Tuple[bool, str]:
        """Verify that .env is safely in .gitignore.

        Returns:
            Tuple of (is_safe, message)
        """
        if not self.env_manager_available:
            return False, "Environment manager not available"

        is_safe, message = self.env_manager.verify_gitignore()
        return is_safe, message

    def ensure_env_safety(self) -> Tuple[bool, str]:
        """Ensure .env file is created and safely in .gitignore.

        Returns:
            Tuple of (success, message)
        """
        if not self.env_manager_available:
            return False, "Environment manager not available"

        try:
            # Create .env if needed
            if not self.env_manager.env_exists():
                self.env_manager.create_env_file()

            # Ensure .gitignore is safe
            added = self.env_manager.add_to_gitignore()

            if added:
                return True, ".env file created and added to .gitignore!"
            else:
                return True, ".env file is already safely configured!"

        except Exception as e:
            self.logger.error(f"Failed to ensure .env safety: {e}")
            return False, f"Error: {str(e)}"

    def detect_existing_config(self) -> Dict[str, bool]:
        """Detect what's already configured for quick setup.

        Returns:
            Dictionary of configuration items and their status
        """
        config_status = {
            "python": False,
            "git": False,
            "git_config": False,
            "ssh_key": False,
            "env_file": False,
            "telegram_token": False,
            "groq_api_key": False,
            "admin_id": False,
        }

        if not self.verifier_available:
            return config_status

        # Run verification to check existing config
        results = self.verifier.verify_all(include_optional=False)

        # Map verifier results to config status
        for check in results.get("checks", []):
            name = check.get("name", "")
            status = check.get("status", "")

            if name == "Python Version" and status == "✅":
                config_status["python"] = True
            elif name == "Git Installation" and status == "✅":
                config_status["git"] = True
            elif name == "Git Configuration" and status == "✅":
                config_status["git_config"] = True
            elif name == "SSH Key" and status == "✅":
                config_status["ssh_key"] = True
            elif name == "Environment File" and status == "✅":
                config_status["env_file"] = True
            elif name == "Telegram Bot Token" and status == "✅":
                config_status["telegram_token"] = True
            elif name == "Groq API Key" and status == "✅":
                config_status["groq_api_key"] = True
            elif name == "Telegram Admin ID" and status == "✅":
                config_status["admin_id"] = True

        return config_status

    def get_quick_setup_checklist(self, config_status: Dict[str, bool]) -> str:
        """Generate quick setup checklist based on what's missing.

        Args:
            config_status: Dictionary of config items and their status

        Returns:
            Formatted checklist message
        """
        checklist = "*Quick Setup Checklist* ⚡\n\n"

        # Count what's done
        total = len(config_status)
        done = sum(1 for v in config_status.values() if v)

        checklist += f"*Progress: {done}/{total} configured*\n\n"

        # Show what's needed
        if not config_status["ssh_key"]:
            checklist += "❌ SSH key for GitHub\n"
        else:
            checklist += "✅ SSH key for GitHub\n"

        if not config_status["telegram_token"]:
            checklist += "❌ Telegram bot token\n"
        else:
            checklist += "✅ Telegram bot token\n"

        if not config_status["groq_api_key"]:
            checklist += "❌ Groq API key\n"
        else:
            checklist += "✅ Groq API key\n"

        if not config_status["admin_id"]:
            checklist += "❌ Telegram admin ID\n"
        else:
            checklist += "✅ Telegram admin ID\n"

        # Optional items
        if not config_status["git_config"]:
            checklist += "⚠️ Git user config (optional but recommended)\n"

        return checklist

    def get_next_quick_setup_step(self, config_status: Dict[str, bool]) -> Optional[str]:
        """Determine the next step needed in quick setup.

        Args:
            config_status: Dictionary of config items and their status

        Returns:
            Next step identifier, or None if setup is complete
        """
        # Check in order of importance
        if not config_status["ssh_key"]:
            return "ssh_key"
        elif not config_status["telegram_token"]:
            return "telegram_token"
        elif not config_status["groq_api_key"]:
            return "groq_api_key"
        elif not config_status["admin_id"]:
            return "admin_id"
        elif not config_status["git_config"]:
            return "git_config"

        return None  # All done!

    def get_quick_setup_prompt(self, step: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Get minimal prompt for a quick setup step.

        Args:
            step: The setup step identifier

        Returns:
            Tuple of (message, keyboard)
        """
        if step == "ssh_key":
            message = """*SSH Key Setup* 🔑

Ralph needs your SSH key for GitHub!

**Already have one?**
`cat ~/.ssh/id_ed25519.pub`

**Need to generate?**
`ssh-keygen -t ed25519 -C "your@email.com"`

*Reply with your public key when ready!*"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 How to find my key?", callback_data="quick_help_ssh")],
                [InlineKeyboardButton("⏭️ Skip for now", callback_data="quick_skip_ssh")]
            ])

        elif step == "telegram_token":
            message = """*Telegram Bot Token* 🤖

Ralph needs your bot token!

**Get it from:**
1. Message @BotFather on Telegram
2. Use /newbot or /token
3. Copy the token

*Reply with token:*
`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Open @BotFather", url="https://t.me/BotFather")],
                [InlineKeyboardButton("⏭️ Skip for now", callback_data="quick_skip_telegram")]
            ])

        elif step == "groq_api_key":
            message = """*Groq API Key* ⚡

Ralph needs Groq for AI magic!

**Get it from:**
https://console.groq.com/keys

*Reply with your API key:*
`gsk_...`"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Get Groq Key", url="https://console.groq.com/keys")],
                [InlineKeyboardButton("⏭️ Skip for now", callback_data="quick_skip_groq")]
            ])

        elif step == "admin_id":
            message = """*Telegram Admin ID* 👤

Ralph needs to know who the boss is!

**Get your ID:**
Message @userinfobot on Telegram

*Reply with your numeric ID:*
`123456789`"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Open @userinfobot", url="https://t.me/userinfobot")],
                [InlineKeyboardButton("⏭️ Skip for now", callback_data="quick_skip_admin")]
            ])

        elif step == "git_config":
            message = """*Git Configuration* 🔧

Ralph recommends setting your Git identity!

**Commands:**
`git config --global user.name "Your Name"`
`git config --global user.email "you@example.com"`

*Press Continue when done!*"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done", callback_data="quick_continue")],
                [InlineKeyboardButton("⏭️ Skip", callback_data="quick_skip_git")]
            ])

        else:
            message = "Unknown step!"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="setup_quick")]
            ])

        return message, keyboard

    def get_quick_setup_complete_message(self) -> str:
        """Get completion message for quick setup.

        Returns:
            Completion message
        """
        return """*Quick Setup Complete!* 🎉⚡

Ralph got everything configured!

**What's ready:**
✅ SSH key for GitHub
✅ Telegram bot token
✅ Groq API key
✅ Admin permissions

**Ready to roll!**
Your bot is ready to start working!

*Start using Ralph:*
/start - Wake up the team
/help - See what Ralph can do
/status - Check the bot status

Ralph mode: ACTIVATED! 🚀"""

    def get_setup_completion_celebration(self, configured_items: List[str]) -> str:
        """Get celebration message when setup is complete.

        Args:
            configured_items: List of what was configured during setup

        Returns:
            Celebration message with next steps and Ralph's celebration (OB-032)
        """
        # Add Ralph's big celebration (OB-032)
        celebration = ""
        goodbye = ""
        if self.narrator:
            celebration = self.narrator.get_celebration("Setup complete") + "\n\n"
            goodbye = "\n\n" + self.narrator.get_goodbye_message()

        # Build configured items list
        items_text = "\n".join([f"✅ {item}" for item in configured_items]) if configured_items else "✅ Everything Ralph needed!"

        return f"""{celebration}*🎉 CONGRATULATIONS! 🎉*

Ralph is SO PROUD of you!

You did the WHOLE setup! That's unpossible for most people, but you DID IT!

**What you configured:**
{items_text}

**What's now possible:**
🤖 Your AI dev team is ready to work
💬 Talk to Ralph and the workers in Telegram
🚀 Ship features while you sleep
📦 Download code packages anytime
🎯 Track progress in real-time

**Next steps:**
1️⃣ Start the bot: /start
2️⃣ See what Ralph can do: /help
3️⃣ Give Ralph a task and watch the magic!

**Learn more:**
📚 Read the docs: https://ralphmode.com/docs
🎥 Watch tutorials: https://ralphmode.com/tutorials
💡 See examples: https://ralphmode.com/examples
🐛 Get help: https://ralphmode.com/support

**Share your achievement:**
Tell your friends! Ralph Mode makes coding fun!
Tweet: "I just set up Ralph Mode! AI dev team in Telegram 🤖🎉 #RalphMode"

Ralph says: "Me proud of you! You did unpossible thing!" 👃
{goodbye}
*Ready to start building?*"""

    # ==================== OB-050: ONBOARDING DOCUMENTATION GENERATOR ====================

    def generate_project_documentation(
        self,
        state: Dict[str, Any],
        project_name: str = "Ralph Mode Project",
        save_to_file: bool = True
    ) -> Optional[str]:
        """Generate customized README.md based on user's setup configuration.

        Args:
            state: Onboarding state dictionary with user's configuration
            project_name: Name of the user's project
            save_to_file: If True, save README to file

        Returns:
            Generated README content, or None if doc generator not available
        """
        if not self.doc_generator_available:
            self.logger.warning("OB-050: Doc generator not available")
            return None

        try:
            # Generate README content
            readme_content = self.doc_generator.generate_readme(state, project_name)

            # Optionally save to file
            if save_to_file:
                success = self.doc_generator.save_readme(readme_content, "README.md")
                if success:
                    self.logger.info("OB-050: Generated and saved README.md")
                else:
                    self.logger.error("OB-050: Failed to save README.md")

            return readme_content

        except Exception as e:
            self.logger.error(f"OB-050: Error generating documentation: {e}")
            return None

    def generate_getting_started_guide(self, state: Dict[str, Any]) -> Optional[str]:
        """Generate a getting started guide for new users.

        Args:
            state: Onboarding state dictionary

        Returns:
            Getting started guide content, or None if not available
        """
        if not self.doc_generator_available:
            return None

        try:
            return self.doc_generator.generate_getting_started_guide(state)
        except Exception as e:
            self.logger.error(f"OB-050: Error generating getting started guide: {e}")
            return None

    def get_documentation_generated_message(self, project_name: str = "Ralph Mode Project") -> str:
        """Get message confirming documentation was generated.

        Args:
            project_name: Name of the project

        Returns:
            Confirmation message
        """
        return f"""📚 *Documentation Generated!*

Ralph made you some helpful docs!

**What was created:**
✅ README.md - Your project overview
✅ Configuration summary
✅ Custom commands for your setup
✅ Getting started guide
✅ Troubleshooting tips

**Where to find it:**
Your project folder now has a fresh README.md with:
• Quick start instructions tailored to YOUR setup
• All the commands YOU need
• Troubleshooting for YOUR configuration

Ralph says: "I put the instructions in the README thingy! It knows what you did!" 📝

*Check it out - it's got everything about {project_name}!*"""

    # ==================== OB-049: RE-ONBOARDING FLOW ====================

    def get_reconfigure_welcome_message(self) -> str:
        """Get welcome message for reconfiguration.

        Returns:
            Welcome message for /reconfigure
        """
        return """*Welcome to Setup Reconfiguration!* 🔧

Ralph here! Need to change something in your setup?

No problem! I'll help you update:
• 🔑 API keys (Telegram, Groq, etc.)
• 👤 Admin settings
• 🌐 Environment variables
• 🔐 SSH keys
• 📝 Git configuration

**What would you like to do?**"""

    def get_current_configuration(self) -> Dict[str, Any]:
        """Get current configuration status for all settings.

        Returns:
            Dictionary with configuration details (values masked for security)
        """
        config = {}

        # Check environment variables if env_manager available
        if self.env_manager_available:
            all_vars = self.env_manager.get_all_variables()

            # Import EnvManager for access to constants
            from env_manager import EnvManager as EnvMgr

            # Mask sensitive values
            for key in EnvMgr.REQUIRED_VARS + EnvMgr.OPTIONAL_VARS:
                value = all_vars.get(key, "")
                if value:
                    # Mask all but last 4 characters
                    if len(value) > 4:
                        config[key] = f"{'*' * (len(value) - 4)}{value[-4:]}"
                    else:
                        config[key] = "****"
                else:
                    config[key] = "(not set)"

        # Check verification status
        if self.verifier_available:
            detected_config = self.detect_existing_config()
            config["verification_status"] = detected_config

        return config

    def format_configuration_display(self, config: Dict[str, Any]) -> str:
        """Format configuration for display.

        Args:
            config: Configuration dictionary from get_current_configuration()

        Returns:
            Formatted string for Telegram message
        """
        from env_manager import EnvManager as EnvMgr

        lines = ["*Your Current Configuration:* ⚙️\n"]

        # Required settings
        lines.append("**Required Settings:**")
        for var in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_OWNER_ID", "GROQ_API_KEY"]:
            value = config.get(var, "(not set)")
            status = "✅" if value != "(not set)" else "❌"
            desc = EnvMgr.VAR_DESCRIPTIONS.get(var, var)
            lines.append(f"{status} {desc}")
            lines.append(f"   `{var} = {value}`\n")

        # Optional settings
        lines.append("\n**Optional Settings:**")
        for var in EnvMgr.OPTIONAL_VARS:
            value = config.get(var, "(not set)")
            if value != "(not set)":
                status = "✅"
                desc = EnvMgr.VAR_DESCRIPTIONS.get(var, var)
                lines.append(f"{status} {desc}")
                lines.append(f"   `{var} = {value}`\n")

        # Verification status
        if "verification_status" in config:
            lines.append("\n**System Checks:**")
            verification = config["verification_status"]
            for key, status in verification.items():
                icon = "✅" if status else "❌"
                label = key.replace("_", " ").title()
                lines.append(f"{icon} {label}")

        return "\n".join(lines)

    def get_reconfigure_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for reconfigure menu.

        Returns:
            InlineKeyboardMarkup with reconfigure options
        """
        buttons = [
            [InlineKeyboardButton("🔑 Update API Keys", callback_data="reconfig_api_keys")],
            [InlineKeyboardButton("👤 Update Admin Settings", callback_data="reconfig_admin")],
            [InlineKeyboardButton("🔐 Update SSH Key", callback_data="reconfig_ssh")],
            [InlineKeyboardButton("📝 Update Git Config", callback_data="reconfig_git")],
            [InlineKeyboardButton("📜 View Change History", callback_data="reconfig_history")],
            [InlineKeyboardButton("❌ Cancel", callback_data="reconfig_cancel")]
        ]
        return InlineKeyboardMarkup(buttons)

    def get_api_keys_reconfigure_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for API key reconfiguration.

        Returns:
            InlineKeyboardMarkup with API key options
        """
        buttons = [
            [InlineKeyboardButton("🤖 Telegram Bot Token", callback_data="reconfig_telegram_token")],
            [InlineKeyboardButton("⚡ Groq API Key", callback_data="reconfig_groq_key")],
            [InlineKeyboardButton("🧠 Claude API Key (Optional)", callback_data="reconfig_claude_key")],
            [InlineKeyboardButton("🌤️ OpenWeather API Key (Optional)", callback_data="reconfig_weather_key")],
            [InlineKeyboardButton("◀️ Back to Menu", callback_data="reconfig_menu")]
        ]
        return InlineKeyboardMarkup(buttons)

    def get_destructive_change_warning(self, setting_name: str, current_value: str) -> str:
        """Get warning message for destructive changes.

        Args:
            setting_name: Name of setting being changed
            current_value: Current value (masked)

        Returns:
            Warning message
        """
        return f"""*⚠️ WARNING: Destructive Change*

You're about to change a critical setting!

**Setting:** `{setting_name}`
**Current value:** `{current_value}`

**This will:**
• Immediately update your configuration
• May disconnect active sessions
• Could break the bot if incorrect

**Ralph says:** "Be careful! Make sure you got the right value! My dad once changed something and the whole town's power went out!" 😰

**Are you SURE you want to continue?**"""

    def get_destructive_change_keyboard(self, setting_name: str) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for destructive changes.

        Args:
            setting_name: Name of setting being changed

        Returns:
            InlineKeyboardMarkup with confirmation buttons
        """
        buttons = [
            [InlineKeyboardButton("✅ Yes, I'm Sure", callback_data=f"reconfig_confirm_{setting_name}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="reconfig_menu")]
        ]
        return InlineKeyboardMarkup(buttons)

    def save_configuration_change(
        self,
        user_id: int,
        setting_name: str,
        old_value: str,
        new_value: str
    ) -> bool:
        """Save a configuration change to history.

        Args:
            user_id: Telegram user ID who made the change
            setting_name: Name of setting changed
            old_value: Previous value (masked)
            new_value: New value (masked)

        Returns:
            True if saved successfully
        """
        if not self.state_persistence_available:
            return False

        import datetime

        change_record = {
            "user_id": user_id,
            "setting": setting_name,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Store in setup state under "config_history"
        # Get existing history
        history = self.state_manager.get_config_history(user_id) if hasattr(self.state_manager, 'get_config_history') else []
        history.append(change_record)

        # Keep only last 50 changes
        if len(history) > 50:
            history = history[-50:]

        # Save back
        if hasattr(self.state_manager, 'save_config_history'):
            return self.state_manager.save_config_history(user_id, history)

        return True

    def get_configuration_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get configuration change history for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            List of change records
        """
        if not self.state_persistence_available:
            return []

        if hasattr(self.state_manager, 'get_config_history'):
            return self.state_manager.get_config_history(user_id)

        return []

    def format_configuration_history(self, history: List[Dict[str, Any]]) -> str:
        """Format configuration history for display.

        Args:
            history: List of change records

        Returns:
            Formatted string
        """
        if not history:
            return """*Configuration Change History* 📜

No changes recorded yet!

Ralph says: "Nothing's been changed! You set it up perfect the first time!" 👃"""

        lines = ["*Configuration Change History* 📜\n"]
        lines.append(f"Last {len(history)} changes:\n")

        # Show most recent first
        for change in reversed(history[-10:]):  # Last 10 changes
            timestamp = change.get("timestamp", "Unknown")
            setting = change.get("setting", "Unknown")
            old_val = change.get("old_value", "Unknown")
            new_val = change.get("new_value", "Unknown")

            # Parse timestamp for better display
            try:
                import datetime
                dt = datetime.datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = timestamp

            lines.append(f"**{time_str}**")
            lines.append(f"Changed: `{setting}`")
            lines.append(f"From: `{old_val}`")
            lines.append(f"To: `{new_val}`\n")

        return "\n".join(lines)

    def get_reconfigure_success_message(self, setting_name: str) -> str:
        """Get success message after reconfiguring a setting.

        Args:
            setting_name: Name of setting that was changed

        Returns:
            Success message
        """
        return f"""*✅ Configuration Updated!*

`{setting_name}` has been successfully updated!

Ralph says: "I did it! I changed the thingy without breaking everything!" 🎉

**What's next?**
• Your bot will use the new setting immediately
• You can verify it works with /status
• Change more settings or go back to the menu

*Everything's working great!*"""

    # OB-037: Group Chat Setup Guide

    def get_group_chat_setup_guide_message(self) -> str:
        """Get comprehensive guide for adding bot to group chats.

        Returns:
            Group chat setup guide with explanations
        """
        return """*Adding Ralph to Group Chats!* 👥

Ralph can work with your whole team in groups!

*Why use groups?*
• Work on projects together with friends
• Everyone can see Ralph's progress
• Great for team collaboration!
• More fun with more people watching! 🎉

**What you'll need:**
✅ Your bot must be created (from BotFather)
✅ Privacy mode should be DISABLED
✅ Groups should be ENABLED in bot settings

**What we'll do:**
1. Add your bot to a group
2. Make it an admin (gives it permission to work)
3. Test if it can read and write messages
4. Fix any privacy mode issues

*Ready to add Ralph to a group?*"""

    def get_group_chat_add_bot_instructions_message(self) -> str:
        """Get step-by-step instructions for adding bot to group.

        Returns:
            Detailed instructions for adding bot to group
        """
        return """*How to Add Bot to Group - Step by Step!* 📝

**Step 1: Create or Open Group** 👥
• Open Telegram and go to an existing group
• OR create new group: Menu → "New Group"
• Name it something fun like "Ralph's Workshop" 🛠️

**Step 2: Add Your Bot to Group** 🤖
1. In group chat, tap the group name at top
2. Tap "Add Members" or "Add Participants"
3. Search for your bot by username
   (Example: `@your_bot_name`)
4. Select your bot from results
5. Tap "Add" or checkmark ✓

✅ Success: You'll see message "[Bot Name] joined the group"

**Step 3: Make Bot an Admin** 👑

*Why admin?*
Ralph needs admin rights to:
• See all messages in the group
• Send messages and media
• Manage work sessions properly

*How to make admin:*
1. Tap group name at top
2. Tap "Administrators" or "Edit"
3. Tap "Add Admin"
4. Select your bot
5. Choose these permissions:
   ✓ Delete Messages
   ✓ Ban Users (optional)
   ✓ Pin Messages (optional)
   ✓ Manage Topics (if group has topics)
6. Tap "Done" or checkmark ✓

✅ Success: Bot shows up in Administrators list!

*Ralph says:*
"Now I'm the boss! Well, still under Mr. Worms tho..." 👃

Click below when you've added your bot!"""

    def get_group_chat_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for group chat setup guide.

        Returns:
            Keyboard with helpful links and action buttons
        """
        keyboard = [
            [InlineKeyboardButton("📋 Show Test Commands", callback_data="group_test_commands")],
            [InlineKeyboardButton("🔧 Fix Privacy Mode", callback_data="group_privacy_help")],
            [InlineKeyboardButton("✅ Bot Works in Group!", callback_data="group_setup_done")],
            [InlineKeyboardButton("❓ Troubleshooting", callback_data="group_setup_help")],
            [InlineKeyboardButton("◀️ Back", callback_data="setup_back_group")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_group_chat_test_commands_message(self) -> str:
        """Get test commands to verify bot works in group.

        Returns:
            Test commands with expected results
        """
        return """*Testing Your Bot in Group!* 🧪

Go to your group and try these tests!

**Test 1: Basic Command** ⚡
Send in group:
```
/start
```

✅ **Expected:** Bot responds with welcome message
❌ **If nothing:** Bot isn't seeing messages (check privacy mode!)

**Test 2: Chat Message** 💬
Send regular message (no slash):
```
Hello Ralph!
```

✅ **Expected:** Bot can see it and might respond
❌ **If ignored:** Privacy mode is ON (need to disable!)

**Test 3: Check Bot Status** 📊
Send in group:
```
/status
```

✅ **Expected:** Bot shows current configuration
❌ **If nothing:** Bot not running or can't see commands

**If all tests pass:**
🎉 Your bot is working perfectly in groups!

**If tests fail:**
Click "Troubleshooting" below for help!

*Ralph says:*
"Try the tests! If I don't answer, something's wrong!" 👃"""

    def get_group_chat_privacy_help_message(self) -> str:
        """Get help for fixing privacy mode issues in groups.

        Returns:
            Privacy mode troubleshooting guide
        """
        return """*Fixing Privacy Mode for Groups!* 🔒

**The Problem:**
If privacy mode is ENABLED, your bot can't see regular messages in groups!

**How to check current setting:**
1. Go to @BotFather
2. Send `/mybots`
3. Select your bot
4. Tap "Bot Settings"
5. Look at "Group Privacy"

**What it should say:**
✅ "Privacy mode is **DISABLED**" = Good! Bot sees everything
❌ "Privacy mode is **ENABLED**" = Bad! Bot only sees commands

**How to disable privacy mode:**

**Step 1:** Open @BotFather
**Step 2:** Send this command:
```
/setprivacy
```

**Step 3:** BotFather asks "Enable privacy mode?"
Choose: `Disable`

**Step 4:** BotFather confirms:
"Privacy mode is disabled for [your bot]"

**Step 5:** IMPORTANT - Refresh the group!
• Remove bot from group
• Add bot back to group
• Make it admin again

*Why refresh?*
Privacy changes only apply when bot joins!
Old session keeps old settings!

**After refreshing:**
Test again with regular message in group!

*Ralph says:*
"Privacy mode is like wearing earplugs! Turn it OFF so I can hear you!" 👂"""

    def get_group_chat_troubleshooting_message(self) -> str:
        """Get comprehensive troubleshooting for group chat issues.

        Returns:
            Common problems and solutions
        """
        return """*Group Chat Troubleshooting!* 🆘

**Problem 1: "Bot doesn't respond in group"**

Possible causes:
→ Privacy mode is ENABLED (disable it!)
→ Bot isn't admin (make it admin!)
→ Bot isn't running (check your server!)
→ Wrong bot token in .env file

*How to fix:*
1. Check privacy mode in BotFather
2. Make bot admin with all permissions
3. Remove and re-add bot to group
4. Restart your bot application

**Problem 2: "Bot only responds to commands (/start) but not regular messages"**

*This is privacy mode!*
→ Privacy mode: ENABLED (wrong!)
→ Need: DISABLED

*How to fix:*
1. Go to @BotFather
2. `/setprivacy` → Disable
3. Remove bot from group
4. Add bot back
5. Make admin again

**Problem 3: "Can't make bot admin"**

→ You must be group admin yourself!
→ Group owner needs to make you admin first
→ Or ask group owner to make bot admin

*How to fix:*
1. Ask group owner for admin rights
2. Then you can make bot admin
3. Or have owner make bot admin directly

**Problem 4: "Bot joined but disappeared from members"**

→ Bot was kicked automatically
→ Group has bot restrictions
→ Anti-spam settings kicked it

*How to fix:*
1. Check group settings for bot restrictions
2. Disable anti-bot features temporarily
3. Add bot again as admin immediately

**Problem 5: "Error: 'Bot was blocked by user'"**

→ Someone blocked the bot in private chat
→ This doesn't affect group functionality!

*How to fix:*
Nothing! Bot still works in group!
That person just can't use bot privately!

**Problem 6: "Bot responds twice"**

→ Bot is in group AND privacy chat
→ Sees message in both places

*How to fix:*
Check your code - should handle group vs private logic!

*Still stuck?*
Check these:
1. Bot token is correct in .env
2. Bot is running (check logs)
3. Privacy mode = DISABLED
4. Bot is admin in group
5. Try creating new test group

*Ralph says:*
"Groups are tricky! But we'll figure it out!" 🧩

[Telegram Groups Documentation](https://core.telegram.org/bots/features#group-privacy)"""

    def get_group_chat_success_message(self) -> str:
        """Get success message after bot is working in group.

        Returns:
            Success celebration message
        """
        return """*🎉 Bot Works in Groups!*

Awesome! Your bot is all set up for group chats!

**What you can do now:**
✅ Work on projects with your team
✅ Everyone can watch Ralph work
✅ Collaborate in real-time
✅ Share the coding fun! 🚀

**Admin Permissions Verified:**
Your bot can:
• See all messages in group
• Send messages and updates
• Manage work sessions
• Be the star of the show! ⭐

**Next Steps:**
• Add more team members to group
• Start a coding session with /start
• Try some commands together
• Watch Ralph impress everyone!

*Ralph says:*
"Look at me! I'm working with the WHOLE TEAM now! This is so cool!" 👃✨

**Pro Tips:**
💡 Pin important messages Ralph sends
💡 Use /status to check what's happening
💡 Each team member can give Ralph instructions
💡 Great for pair programming and code reviews!

*Your bot is ready for teamwork!* 👥🤖"""

    def get_group_chat_admin_rights_explainer_message(self) -> str:
        """Get detailed explanation of why admin rights are needed.

        Returns:
            Admin rights explanation
        """
        return """*Why Does Bot Need Admin Rights?* 👑

Good question! Let Ralph explain!

**What Ralph Needs to Do:**
1. **See ALL messages** 📬
   → Not just commands
   → Regular chat messages too
   → Understand context of conversation

2. **Send messages freely** 💬
   → Update you on progress
   → Ask questions when stuck
   → Celebrate when features ship!

3. **Send media and files** 📎
   → Code screenshots
   → GIFs for entertainment
   → Progress bars and visuals

4. **Delete old messages** (optional) 🗑️
   → Clean up clutter
   → Remove outdated status messages
   → Keep chat organized

**Permissions Breakdown:**

*Delete Messages:*
✅ Recommended - keeps chat clean
❌ Optional - but helpful!

*Ban Users:*
❌ Not needed for Ralph
⚠️ Ralph won't ban anyone! (He's too nice!)

*Pin Messages:*
✅ Useful - can pin important updates
❌ Optional - your choice!

*Invite Users:*
❌ Not needed for Ralph
⚠️ You control who joins!

*Manage Topics:*
✅ Needed if group has topics/forums
❌ Not needed for simple groups

**Minimum Required:**
Just admin status itself!
The extra permissions make Ralph more useful!

**Security:**
Your bot only does what you coded it to do!
Admin rights don't change bot behavior!
You're still in control! 🔐

*Ralph says:*
"I'm admin but I promise not to go crazy with power!" 😊

[More about Bot Permissions](https://core.telegram.org/bots/features#group-admin-bots)"""


    # First Commit Assistant (OB-030)

    def get_first_commit_intro_message(self) -> str:
        """Get introduction message for first git commit.

        Returns:
            Intro message with Ralph's personality
        """
        return """*🎉 Time for Your First Commit!*

This is SO EXCITING! Ralph gonna help you make your FIRST GIT COMMIT!

**What's a commit?**
Think of it like saving your game!
→ You made some changes to your code
→ Git takes a SNAPSHOT of everything
→ You can go back to this point ANYTIME!

**Why commits are cool:**
✨ You can undo mistakes!
✨ You can see what changed!
✨ You can work with other people!
✨ It's like a time machine for code!

**What Ralph gonna do:**
1. 📋 Show you what files changed
2. ✅ Help you pick what to save (stage them)
3. 📝 Help you write a good commit message
4. 💾 Save the snapshot (commit!)
5. 🚀 Send it to GitHub (push!)

*Ralph says:*
"This is like making history! YOUR code history!" 📜✨

*Ready to make your mark?*
"""

    def get_first_commit_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for first commit intro.

        Returns:
            InlineKeyboardMarkup with action buttons
        """
        keyboard = [
            [InlineKeyboardButton("📋 Show Me What Changed", callback_data="first_commit_status")],
            [InlineKeyboardButton("⏭️ Skip (I'll do it later)", callback_data="first_commit_skip")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_git_status_explanation_message(self, untracked: List[str], modified: List[str]) -> str:
        """Get message explaining git status with file lists.

        Args:
            untracked: List of untracked files
            modified: List of modified files

        Returns:
            Formatted status explanation
        """
        total_changes = len(untracked) + len(modified)

        if total_changes == 0:
            return """*✅ Everything's Clean!*

Good news! Your working directory is clean!

**What this means:**
→ All changes are already committed
→ No new files to add
→ Nothing to commit right now!

*Ralph says:*
"Your code is all saved up! Good job!" 🎉

*What now?*
When you make changes to files or add new files, come back and we'll commit them!
"""

        message = f"""*📋 Here's What Changed!*

Ralph found **{total_changes} file(s)** with changes!

"""

        if untracked:
            message += f"""**🆕 New Files ({len(untracked)}):**
These files are brand new - Git hasn't seen them before!
"""
            for file in untracked[:10]:  # Show first 10
                message += f"  • `{file}`\n"
            if len(untracked) > 10:
                message += f"  ... and {len(untracked) - 10} more!\n"
            message += "\n"

        if modified:
            message += f"""**✏️ Modified Files ({len(modified)}):**
These files were changed since your last commit!
"""
            for file in modified[:10]:  # Show first 10
                message += f"  • `{file}`\n"
            if len(modified) > 10:
                message += f"  ... and {len(modified) - 10} more!\n"
            message += "\n"

        message += """*What Ralph gonna do:*
Ralph will add ALL these files to your commit!
Like putting them all in a box before wrapping it up!

*Ready to continue?*
"""
        return message

    def get_git_status_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for git status view.

        Returns:
            InlineKeyboardMarkup with action buttons
        """
        keyboard = [
            [InlineKeyboardButton("✅ Add All & Continue", callback_data="first_commit_add_all")],
            [InlineKeyboardButton("⏭️ Skip This Step", callback_data="first_commit_skip")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_commit_message_guide_message(self) -> str:
        """Get guide for writing a good commit message.

        Returns:
            Commit message best practices guide
        """
        return """*📝 Time to Write Your Commit Message!*

This is the DESCRIPTION of what you did!
Think of it like a label on a box!

**Good Commit Messages:**
✅ "Add initial project setup"
✅ "Fix login button styling"
✅ "Update README with installation steps"
✅ "Add user authentication system"

**Bad Commit Messages:**
❌ "stuff"
❌ "fixed it"
❌ "asdf"
❌ "changes"

**Ralph's Tips:**
1. **Start with a verb** (Add, Fix, Update, Remove)
2. **Be specific** (What did you change?)
3. **Keep it short** (50-72 characters)
4. **Start with capital letter**
5. **Don't end with period**

*Examples:*
→ "Add initial Python files and setup"
→ "Fix environment variable configuration"
→ "Update onboarding wizard with git helper"

*What Ralph wants to know:*
**What did you do in this commit?**

*Type your commit message now:*
(Ralph will check if it's good!)
"""

    def get_commit_message_feedback_message(self, is_valid: bool, feedback: str, user_message: str) -> str:
        """Get feedback on commit message quality.

        Args:
            is_valid: Whether message passes validation
            feedback: Validation feedback message
            user_message: The user's proposed message

        Returns:
            Formatted feedback message
        """
        if is_valid:
            return f"""*✅ Great Commit Message!*

Your message: `{user_message}`

{feedback}

**Why Ralph likes it:**
→ Clear and descriptive!
→ Follows best practices!
→ Future you will understand it!

*Ready to commit with this message?*
"""
        else:
            return f"""*⚠️ Let's Make It Better!*

Your message: `{user_message}`

**Ralph says:** {feedback}

*Try again!*
Type a better commit message:

*Remember:*
→ Be descriptive
→ Start with a verb (Add, Fix, Update)
→ Keep it clear and short
→ Start with capital letter

*You got this!*
"""

    def get_commit_message_keyboard(self, is_valid: bool) -> InlineKeyboardMarkup:
        """Get keyboard for commit message feedback.

        Args:
            is_valid: Whether message is valid

        Returns:
            InlineKeyboardMarkup with appropriate buttons
        """
        if is_valid:
            keyboard = [
                [InlineKeyboardButton("💾 Commit with This Message", callback_data="first_commit_execute")],
                [InlineKeyboardButton("✏️ Try Different Message", callback_data="first_commit_retry_message")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("💡 Suggest a Message", callback_data="first_commit_suggest")],
                [InlineKeyboardButton("⏭️ Skip This Step", callback_data="first_commit_skip")]
            ]
        return InlineKeyboardMarkup(keyboard)

    def get_commit_executing_message(self, commit_message: str) -> str:
        """Get message shown while commit is being created.

        Args:
            commit_message: The commit message being used

        Returns:
            Execution progress message
        """
        return f"""*💾 Creating Your Commit!*

Ralph is working on it!

**Commit message:** `{commit_message}`

**What Ralph doing:**
1. ✅ Added files to staging area
2. 🔄 Creating commit...
3. ⏳ Almost done...

*Ralph says:*
"Me making history! YOUR code history!" 📜✨
"""

    def get_commit_success_message(self, commit_message: str, is_first: bool = False) -> str:
        """Get success message after commit is created.

        Args:
            commit_message: The commit message used
            is_first: Whether this is the user's first ever commit

        Returns:
            Success celebration message
        """
        celebration = "🎉🎊🚀✨🎈" if is_first else "✅"

        message = f"""*{celebration} COMMIT SUCCESSFUL! {celebration}*

"""

        if is_first:
            message += """**🎉 CONGRATULATIONS! 🎉**
This was your FIRST GIT COMMIT EVER!

You're now officially a developer who knows version control!
Ralph is SO PROUD! 👏👏👏

"""

        message += f"""**Your commit:** `{commit_message}`

**What just happened:**
✅ Git took a snapshot of your code
✅ Changes are now saved in history
✅ You can go back to this point anytime
✅ Your code is safe!

**Next: Push to GitHub**
Right now your commit is ONLY on your computer!
Let's send it to GitHub so it's backed up in the cloud!

*Ralph says:*
"Now let's put it in the cloud where everyone can see your awesome work!" ☁️

*Ready to push?*
"""
        return message

    def get_commit_success_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard after successful commit.

        Returns:
            InlineKeyboardMarkup with next action buttons
        """
        keyboard = [
            [InlineKeyboardButton("🚀 Push to GitHub", callback_data="first_commit_push")],
            [InlineKeyboardButton("✅ Done (I'll push later)", callback_data="first_commit_complete")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_push_explanation_message(self, branch: str = "main") -> str:
        """Get explanation of what git push does.

        Args:
            branch: Branch name to push to

        Returns:
            Push explanation message
        """
        return f"""*🚀 Time to Push to GitHub!*

**What's "pushing"?**
Think of it like uploading your save file to the cloud!

**Right now:**
→ Your commit is on YOUR computer only
→ If computer breaks, it's GONE!
→ Nobody else can see it

**After pushing:**
→ Commit is on GitHub (in the cloud!)
→ It's backed up safely
→ Other people can see it
→ You can access it from anywhere!

**What Ralph gonna do:**
1. Connect to GitHub (using your SSH key!)
2. Upload your commit to the cloud
3. Set up tracking (so future pushes are easier!)

**The command:**
`git push -u origin {branch}`

**Breakdown:**
→ `push` = send commits to GitHub
→ `-u` = set up tracking (only needed first time!)
→ `origin` = GitHub (the remote server)
→ `{branch}` = your branch name

*Ralph says:*
"Let's back up your work before your cat walks on the keyboard!" 🐱

*Ready?*
"""

    def get_push_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for push action.

        Returns:
            InlineKeyboardMarkup with push buttons
        """
        keyboard = [
            [InlineKeyboardButton("🚀 Push Now!", callback_data="first_commit_push_execute")],
            [InlineKeyboardButton("⏭️ I'll Push Later", callback_data="first_commit_complete")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_push_executing_message(self, branch: str = "main") -> str:
        """Get message shown while push is in progress.

        Args:
            branch: Branch being pushed

        Returns:
            Push progress message
        """
        return f"""*🚀 Pushing to GitHub!*

Ralph is sending your code to the cloud!

**Branch:** `{branch}`
**Remote:** `origin` (GitHub)

**What happening:**
1. 🔐 Authenticating with GitHub...
2. 📤 Uploading your commit...
3. ☁️ Syncing with cloud...
4. ⏳ Almost there...

*This might take a few seconds!*
"""

    def get_push_success_message(self, branch: str = "main") -> str:
        """Get success message after push completes.

        Args:
            branch: Branch that was pushed

        Returns:
            Success celebration message
        """
        return f"""*🎉 PUSHED SUCCESSFULLY! 🎉*

Your code is now on GitHub! ☁️✨

**What just happened:**
✅ Commit uploaded to GitHub
✅ Code is backed up in the cloud
✅ Tracking is set up for future pushes
✅ Your code is SAFE!

**Check it out:**
Go to your GitHub repository and you'll see:
→ Your commit message
→ All the files you added
→ Timestamp of when you committed
→ Your contribution graph got a green square! 🟩

**Future pushes:**
Now you can just type `git push` and it works!
No need for the extra flags anymore!

*Ralph says:*
"Look at you! Making commits and pushing like a PRO! Me so proud!" 🏆

**🎊 First Commit Mission: COMPLETE! 🎊**

You now know:
✅ How to check git status
✅ How to add files
✅ How to write commit messages
✅ How to create commits
✅ How to push to GitHub

*You're a Git master now!* 🎓
"""

    def get_push_error_message(self, error: str) -> str:
        """Get error message if push fails.

        Args:
            error: Error message from git

        Returns:
            Helpful error explanation
        """
        return f"""*⚠️ Push Had a Problem*

Don't worry! This happens! Let's fix it!

**Error:** {error}

**Common causes:**
1. **No internet connection**
   → Check your WiFi!

2. **SSH key not added to GitHub**
   → Did you add your SSH key?
   → Try the SSH test: `ssh -T git@github.com`

3. **No remote set up**
   → Need to connect your repo to GitHub first
   → Run: `git remote add origin <your-repo-url>`

4. **Wrong branch name**
   → Your branch might be called 'master' not 'main'
   → Try: `git push -u origin master`

5. **First push to new repo**
   → Sometimes takes a moment
   → Try again in a few seconds

*What to do:*
1. Check the error message above
2. Try the suggested fix
3. Or skip for now and push later!

*Ralph says:*
"Git is tricky sometimes! But we'll figure it out!" 💪

*What do you want to do?*
"""

    def get_push_error_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for push error recovery.

        Returns:
            InlineKeyboardMarkup with retry options
        """
        keyboard = [
            [InlineKeyboardButton("🔄 Try Again", callback_data="first_commit_push_execute")],
            [InlineKeyboardButton("📚 Show Troubleshooting", callback_data="first_commit_push_help")],
            [InlineKeyboardButton("✅ I'll Fix It Later", callback_data="first_commit_complete")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_suggested_commit_message_display(self, suggestion: str) -> str:
        """Get message showing suggested commit message.

        Args:
            suggestion: Auto-generated suggestion

        Returns:
            Formatted suggestion message
        """
        return f"""*💡 Ralph's Suggestion!*

Based on your changes, Ralph thinks this would be good:

**Suggested message:** `{suggestion}`

**Why this suggestion:**
→ Describes what you added/changed
→ Follows commit message best practices
→ Clear and professional

*What do you want to do:*
→ Use this message as-is
→ Edit it to make it better
→ Write your own from scratch

*Type your choice or a new message:*
"""

    def get_suggested_commit_keyboard(self, suggestion: str) -> InlineKeyboardMarkup:
        """Get keyboard for suggested commit message.

        Args:
            suggestion: The suggested message

        Returns:
            InlineKeyboardMarkup with suggestion actions
        """
        keyboard = [
            [InlineKeyboardButton("✅ Use This Message", callback_data=f"first_commit_use_suggestion:{suggestion}")],
            [InlineKeyboardButton("✏️ Write My Own", callback_data="first_commit_custom_message")]
        ]
        return InlineKeyboardMarkup(keyboard)

    # ==================== OB-040: VISUAL THEME SELECTOR ====================

    def get_theme_selection_message(self) -> str:
        """Get message for theme selection step.

        Returns:
            Theme selection message with Ralph's personality
        """
        return """*Time to make Ralph Mode look good!* 🎨

I got different themes for how messages look. Pick one that feels right to ya!

*Here's what we got:*

**🌞 Light Mode** - Clean and bright, easy on the eyes
**🌙 Dark Mode** - Sleek for late-night coding
**🎨 Colorful** - Full emoji action, vibrant vibes (default)
**⚪ Minimal** - No frills, just the content

*Wanna see 'em in action?* Hit a button below to preview!"""

    def get_theme_selection_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for theme selection.

        Returns:
            InlineKeyboardMarkup with theme options
        """
        if not self.theme_manager_available:
            # Fallback if theme manager not available
            keyboard = [
                [InlineKeyboardButton("Continue with Default", callback_data="theme_select:colorful")]
            ]
            return InlineKeyboardMarkup(keyboard)

        keyboard = [
            [InlineKeyboardButton("🌞 Light Mode", callback_data="theme_preview:light")],
            [InlineKeyboardButton("🌙 Dark Mode", callback_data="theme_preview:dark")],
            [InlineKeyboardButton("🎨 Colorful", callback_data="theme_preview:colorful")],
            [InlineKeyboardButton("⚪ Minimal", callback_data="theme_preview:minimal")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_theme_preview_message(self, theme_id: str) -> str:
        """Get preview of a theme.

        Args:
            theme_id: Theme identifier (light, dark, colorful, minimal)

        Returns:
            Preview message showing theme in action
        """
        if not self.theme_manager_available:
            return "Theme preview not available. Using default theme."

        theme = self.theme_manager.get_theme(theme_id)
        if not theme:
            return "Invalid theme selected."

        preview_text = f"""*{theme['name']}*
_{theme['description']}_

*Here's a preview:*

{theme['preview']}

*Like what you see?*"""

        return preview_text

    def get_theme_preview_keyboard(self, theme_id: str) -> InlineKeyboardMarkup:
        """Get keyboard for theme preview with select option.

        Args:
            theme_id: Theme identifier

        Returns:
            InlineKeyboardMarkup with select/back buttons
        """
        keyboard = [
            [InlineKeyboardButton("✅ Choose This Theme", callback_data=f"theme_select:{theme_id}")],
            [InlineKeyboardButton("⬅️ Back to Themes", callback_data="theme_back")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def save_theme_preference(
        self,
        user_id: int,
        telegram_id: int,
        theme_id: str
    ) -> bool:
        """Save user's theme preference to database.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID
            theme_id: Selected theme ID

        Returns:
            True if saved successfully
        """
        try:
            from database import get_db, User

            with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()

                if user:
                    user.theme_preference = theme_id
                    db.commit()
                    self.logger.info(f"OB-040: Saved theme '{theme_id}' for user {telegram_id}")
                    return True
                else:
                    self.logger.error(f"OB-040: User {user_id} not found")
                    return False

        except Exception as e:
            self.logger.error(f"OB-040: Error saving theme preference: {e}")
            return False

    def get_theme_confirmation_message(self, theme_id: str) -> str:
        """Get confirmation message after theme is selected.

        Args:
            theme_id: Selected theme ID

        Returns:
            Confirmation message
        """
        theme_name = {
            "light": "Light Mode",
            "dark": "Dark Mode",
            "colorful": "Colorful",
            "minimal": "Minimal"
        }.get(theme_id, "Unknown")

        return f"""*Sweet choice!* ✨

Your theme is set to **{theme_name}**!

All my messages will use this style from now on. You can change it later if you want!

*Ready to keep going?*"""

    # ==================== OB-041: CHARACTER AVATAR SELECTION ====================

    def get_character_selection_message(self) -> str:
        """Get message for character avatar selection step.

        Returns:
            Character selection message with Ralph's personality
        """
        return """*Who's gonna be your guide?* 🎭

Before we get started, pick someone from the team to show ya the ropes! They'll help you set things up and be your main contact.

*Here's who we got:*

**👦 Ralph (Me!)** - Your lovable boss who makes things happen (somehow)
**👨‍💻 Stool** - Chill frontend dev with coffee and good vibes
**🍩 Gomer** - Backend genius hiding behind donut jokes
**🎷 Mona** - The smartest person in the room (she'll tell you)
**☕ Gus** - 25-year veteran who's seen it all

*Tap a button to meet 'em!*"""

    def get_character_selection_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for character selection.

        Returns:
            InlineKeyboardMarkup with character options
        """
        if not self.user_prefs_available:
            # Fallback if user preferences not available
            keyboard = [
                [InlineKeyboardButton("Continue with Ralph", callback_data="character_select:Ralph")]
            ]
            return InlineKeyboardMarkup(keyboard)

        from user_preferences import UserPreferences

        keyboard = [
            [InlineKeyboardButton("👦 Ralph (Me!)", callback_data="character_preview:Ralph")],
            [InlineKeyboardButton("👨‍💻 Stool", callback_data="character_preview:Stool")],
            [InlineKeyboardButton("🍩 Gomer", callback_data="character_preview:Gomer")],
            [InlineKeyboardButton("🎷 Mona", callback_data="character_preview:Mona")],
            [InlineKeyboardButton("☕ Gus", callback_data="character_preview:Gus")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_character_preview_message(self, character: str) -> str:
        """Get preview of a character.

        Args:
            character: Character name (Ralph, Stool, Gomer, Mona, or Gus)

        Returns:
            Preview message showing character personality
        """
        if not self.user_prefs_available:
            return "Character preview not available. Using Ralph as default."

        from user_preferences import UserPreferences

        char_info = UserPreferences.AVAILABLE_CHARACTERS.get(character)
        if not char_info:
            return "Invalid character selected."

        preview_text = f"""*{character} - {char_info['title']}*
_{char_info['description']}_

*Sample:*
"{char_info['personality_preview']}"

*Wanna go with {character}?*"""

        return preview_text

    def get_character_preview_keyboard(self, character: str) -> InlineKeyboardMarkup:
        """Get keyboard for character preview with select option.

        Args:
            character: Character name

        Returns:
            InlineKeyboardMarkup with select/back buttons
        """
        keyboard = [
            [InlineKeyboardButton(f"✅ Choose {character}", callback_data=f"character_select:{character}")],
            [InlineKeyboardButton("⬅️ Back to Characters", callback_data="character_back")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def save_character_preference(
        self,
        user_id: int,
        character: str
    ) -> bool:
        """Save user's character preference.

        Args:
            user_id: Telegram user ID
            character: Selected character name

        Returns:
            True if saved successfully
        """
        if not self.user_prefs_available:
            self.logger.warning("OB-041: User preferences not available")
            return False

        try:
            success = self.user_prefs.set_guide_character(user_id, character)
            if success:
                self.logger.info(f"OB-041: Saved character '{character}' for user {user_id}")
            else:
                self.logger.error(f"OB-041: Failed to save character for user {user_id}")
            return success

        except Exception as e:
            self.logger.error(f"OB-041: Error saving character preference: {e}")
            return False

    def get_character_confirmation_message(self, character: str) -> str:
        """Get confirmation message after character is selected.

        Args:
            character: Selected character name

        Returns:
            Confirmation message
        """
        messages = {
            "Ralph": "*Me?! You picked me?!* 😊\n\nAww shucks! I'm gonna be the bestest guide ever! Let's get you all set up!",
            "Stool": "*Yo, that's what's up!* ☕\n\nLowkey honored you chose me. Let's build something that slaps!",
            "Gomer": "*Woohoo!* 🍩\n\nYou picked the donut guy! D'oh, I mean... I'm gonna help you real good!",
            "Mona": "*Excellent choice.* 🎷\n\nActually, statistically speaking, I was the optimal selection. Let's proceed logically.",
            "Gus": "*Hmph. Good choice, kid.* ☕\n\nI've onboarded more devs than you've had hot dinners. Let's get this done right."
        }

        return messages.get(character, f"*Great choice!*\n\n{character} will be your guide! Let's keep going.")

    # OB-028: PRD Template Generator Methods

    def get_project_type_selection_message(self) -> str:
        """Get message asking user to select project type for PRD generation.

        Returns:
            Message explaining project type selection
        """
        return """*Time to make your task list!* 📋

Ralph needs to know what kind of project you're building so we can give you a good starting point!

*What are you making?*

Pick the one that sounds most like your project. Don't worry, you can change the tasks later!"""

    def get_project_type_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard with project type options.

        Returns:
            Inline keyboard with all project types
        """
        if not self.prd_generator_available:
            self.logger.warning("OB-028: PRD generator not available")
            keyboard = [[InlineKeyboardButton("Skip PRD Setup", callback_data="prd_skip")]]
            return InlineKeyboardMarkup(keyboard)

        project_types = self.prd_generator.get_project_types()
        keyboard = []

        # Add project types (2 per row)
        for i in range(0, len(project_types), 2):
            row = []
            for j in range(2):
                if i + j < len(project_types):
                    pt = project_types[i + j]
                    button_text = f"{pt['emoji']} {pt['name']}"
                    callback_data = f"prd_type_{pt['id']}"
                    row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            keyboard.append(row)

        # Add skip option
        keyboard.append([InlineKeyboardButton("⏩ Skip for now", callback_data="prd_skip")])

        return InlineKeyboardMarkup(keyboard)

    def get_project_type_description(self, project_type_id: str) -> str:
        """Get description for a specific project type.

        Args:
            project_type_id: ID of the project type

        Returns:
            Description string
        """
        if not self.prd_generator_available:
            return "PRD generator not available"

        project_types = self.prd_generator.get_project_types()
        for pt in project_types:
            if pt['id'] == project_type_id:
                return f"{pt['emoji']} *{pt['name']}*\n\n{pt['description']}"

        return "Unknown project type"

    async def generate_prd_for_project(
        self,
        project_type: str,
        project_name: str,
        output_path: str = "scripts/ralph/prd.json"
    ) -> bool:
        """Generate PRD file for the selected project type.

        Args:
            project_type: Type of project (telegram_bot, web_app, etc.)
            project_name: Name of the project
            output_path: Where to save the PRD file

        Returns:
            True if successful, False otherwise
        """
        if not self.prd_generator_available:
            self.logger.error("OB-028: PRD generator not available")
            return False

        try:
            # Generate PRD
            prd = self.prd_generator.generate_prd(project_type, project_name)

            # Save to file
            success = self.prd_generator.save_prd(prd, output_path)

            if success:
                self.logger.info(f"OB-028: Generated PRD for {project_name} ({project_type})")
                self.logger.info(f"OB-028: Saved to {output_path}")
                self.logger.info(f"OB-028: Created {len(prd['tasks'])} initial tasks")
            else:
                self.logger.error("OB-028: Failed to save PRD file")

            return success

        except Exception as e:
            self.logger.error(f"OB-028: Error generating PRD: {e}")
            return False

    def get_prd_generation_success_message(self, project_type: str, num_tasks: int) -> str:
        """Get success message after PRD is generated.

        Args:
            project_type: Type of project selected
            num_tasks: Number of tasks created

        Returns:
            Success message with details
        """
        return f"""*Yay! Ralph made your task list!* 🎉

Created **{num_tasks} tasks** for your project!

*What's in it:*
• Setup tasks to get started
• Core features to implement
• Testing and documentation
• Everything organized in priority order!

*Where is it?*
Your PRD is saved at `scripts/ralph/prd.json`

*What now?*
You can edit the file to:
• Add more tasks
• Change priorities
• Update acceptance criteria
• Remove tasks you don't need

Ralph will work through these tasks one by one! Each task has clear acceptance criteria so Ralph knows when it's done!

Want to see what Ralph does? Check out the PRD file!"""

    def get_prd_explanation_message(self) -> str:
        """Get explanation of what a PRD is and how it works.

        Returns:
            Educational message about PRDs
        """
        if not self.prd_generator_available:
            return "PRD generator not available"

        return self.prd_generator.get_prd_explanation()

    def get_prd_skip_message(self) -> str:
        """Get message when user skips PRD generation.

        Returns:
            Message explaining they can create PRD later
        """
        return """*No problem!* 👍

You can always create a PRD later!

*Ways to make one:*
• Use `/prd_template` command
• Manually edit `scripts/ralph/prd.json`
• Copy from another project

*For now*, Ralph can still work on your project! Just tell Ralph what to do and Ralph will do it!

Ralph works great with OR without a PRD! The PRD just helps Ralph know what to build when you're sleeping! 😴"""

    # OB-039: Bot Testing Walkthrough
    def get_bot_test_intro_message(self) -> str:
        """Get the introduction message for bot testing.

        Returns:
            Message introducing bot testing phase
        """
        if self.bot_tester:
            return self.bot_tester.get_intro_message()

        # Fallback if bot_tester not available
        return """*🧪 Time to Test Your Bot!*

Let's make sure everything works before we finish setup.

Send me any message to test that I'm responding correctly!"""

    def get_bot_test_acknowledgment(self, message_text: str) -> str:
        """Get acknowledgment message for user's test message.

        Args:
            message_text: The message the user sent

        Returns:
            Acknowledgment message
        """
        if self.bot_tester:
            return self.bot_tester.get_message_acknowledgment(message_text)

        # Fallback
        return f"""*🎯 Got it!*

I received your message: "{message_text}"

This means I'm working correctly!"""

    def get_bot_test_command_prompt(self) -> str:
        """Get message prompting user to test a command.

        Returns:
            Command test prompt
        """
        if self.bot_tester:
            return self.bot_tester.get_basic_command_test_message()

        # Fallback
        return """*Great! Now let's test commands.*

Try sending:
```
/help
```

This will test my command handlers."""

    def get_bot_test_completion_message(self) -> str:
        """Get message when bot testing is complete.

        Returns:
            Completion message
        """
        if self.bot_tester:
            return self.bot_tester.get_completion_message()

        # Fallback
        return """*🎉 All Tests Passed!*

Your bot is working perfectly!

✅ Message handling works
✅ Commands work
✅ Bot is responding quickly

You're all set!"""

    def get_bot_test_keyboard(self, tests_complete: bool = False) -> InlineKeyboardMarkup:
        """Get keyboard for bot testing step.

        Args:
            tests_complete: Whether all tests are complete

        Returns:
            Keyboard with test options
        """
        buttons = []

        if tests_complete:
            buttons.append([
                InlineKeyboardButton("✅ Finish Testing", callback_data="bot_test_complete")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("⏭ Skip Testing", callback_data="bot_test_skip")
            ])

        return InlineKeyboardMarkup(buttons)


def get_onboarding_wizard() -> OnboardingWizard:
    """Get the onboarding wizard instance.

    Returns:
        OnboardingWizard instance
    """
    return OnboardingWizard()
