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
