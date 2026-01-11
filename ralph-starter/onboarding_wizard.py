#!/usr/bin/env python3
"""
Onboarding Wizard for Ralph Mode

Guides users through setup with Ralph's personality.
Makes the technical stuff fun and accessible.
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class OnboardingWizard:
    """Handles the onboarding flow for new users."""

    # Onboarding steps
    STEP_WELCOME = "welcome"
    STEP_SETUP_TYPE = "setup_type"
    STEP_SSH_KEY = "ssh_key"
    STEP_GITHUB = "github"
    STEP_REPO = "repo"
    STEP_COMPLETE = "complete"

    # Setup types
    SETUP_GUIDED = "guided"
    SETUP_QUICK = "quick"

    def __init__(self):
        """Initialize the onboarding wizard."""
        self.logger = logging.getLogger(__name__)

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
        return InlineKeyboardMarkup(keyboard)

    def init_onboarding_state(self, user_id: int) -> Dict[str, Any]:
        """Initialize onboarding state for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Initial onboarding state dictionary
        """
        return {
            "step": self.STEP_WELCOME,
            "setup_type": None,
            "ssh_key_generated": False,
            "ssh_key_added_to_github": False,
            "repo_created": False,
            "repo_url": None,
            "started_at": None,
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

    def get_progress_message(self, state: Dict[str, Any]) -> str:
        """Get a progress message showing what's been completed.

        Args:
            state: Current onboarding state

        Returns:
            Progress message string
        """
        progress = []

        if state.get("ssh_key_generated"):
            progress.append("✅ SSH key generated")
        else:
            progress.append("⬜ SSH key not generated yet")

        if state.get("ssh_key_added_to_github"):
            progress.append("✅ SSH key added to GitHub")
        else:
            progress.append("⬜ SSH key not added to GitHub yet")

        if state.get("repo_created"):
            progress.append("✅ Repository created")
        else:
            progress.append("⬜ Repository not created yet")

        if state.get("repo_url"):
            progress.append(f"✅ Repository URL: {state['repo_url']}")
        else:
            progress.append("⬜ Repository URL not configured")

        return "*Your Progress:*\n\n" + "\n".join(progress)

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

*Need help?* Watch this video:
🎥 [How to Generate SSH Keys](https://www.youtube.com/watch?v=H5qNpRGB7Qw)
   (Skip to 1:25 for the actual command!)

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
            Success message with Ralph's personality
        """
        return """*You did it!* 🎊

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
            Help message with troubleshooting tips
        """
        return """*Ralph Help You!* 🆘

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

*Watch This Video:*
🎥 [Complete SSH Key Tutorial](https://www.youtube.com/watch?v=H5qNpRGB7Qw)

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
        return """*Adding Key to GitHub - Step by Step!* 📝

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

*Need Help?*
🎥 [How to Add SSH Key to GitHub](https://www.youtube.com/watch?v=H5qNpRGB7Qw)
   (Skip to 3:45 for adding to GitHub!)
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
        return """*Ralph Help Fix It!* 🔧

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

*Still stuck?*
🎥 [SSH Troubleshooting Video](https://www.youtube.com/watch?v=H5qNpRGB7Qw)

Try the test command again, or go back and add the key again!
"""


def get_onboarding_wizard() -> OnboardingWizard:
    """Get the onboarding wizard instance.

    Returns:
        OnboardingWizard instance
    """
    return OnboardingWizard()
