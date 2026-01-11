#!/usr/bin/env python3
"""
Onboarding Wizard for Ralph Mode

Guides users through setup with Ralph's personality.
Makes the technical stuff fun and accessible.
"""

import logging
from typing import Dict, Any, Optional, List
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

        if state.get("git_configured"):
            progress.append(f"✅ Git configured ({state.get('git_name', 'Unknown')})")
        else:
            progress.append("⬜ Git not configured yet")

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

    # Git Configuration Setup (OB-005)

    def get_git_config_intro_message(self) -> str:
        """Get introduction message for git configuration.

        Returns:
            Git configuration introduction
        """
        return """*Time to Tell Git Who You Are!* 👤

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
        return """*Step 2: Get Your API Key!* 🔑

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

*Need a video tutorial?*
🎥 [How to Get Anthropic API Key](https://www.youtube.com/watch?v=example)
"""

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
        return """*Ralph Help With Telegram Bot!* 🆘

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

*Need a video tutorial?*
🎥 [How to Create a Telegram Bot](https://www.youtube.com/watch?v=example)

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


def get_onboarding_wizard() -> OnboardingWizard:
    """Get the onboarding wizard instance.

    Returns:
        OnboardingWizard instance
    """
    return OnboardingWizard()
