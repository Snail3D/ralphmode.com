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
            "git_configured": False,
            "git_name": None,
            "git_email": None,
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


def get_onboarding_wizard() -> OnboardingWizard:
    """Get the onboarding wizard instance.

    Returns:
        OnboardingWizard instance
    """
    return OnboardingWizard()
