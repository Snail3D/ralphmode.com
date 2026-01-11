#!/usr/bin/env python3
"""
Troubleshooting Guide for Ralph Mode Setup

Provides searchable FAQ and common solutions for setup issues.
"""

import logging
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class TroubleshootingGuide:
    """Handles troubleshooting and common setup issues."""

    def __init__(self):
        """Initialize the troubleshooting guide."""
        self.logger = logging.getLogger(__name__)

        # Common issues and solutions
        self.issues = [
            {
                "id": "ssh_key_exists",
                "title": "SSH Key Already Exists",
                "keywords": ["ssh", "exists", "already", "overwrite"],
                "problem": "You already have an SSH key, not sure if you should create a new one",
                "solution": """*Good news!* You already got SSH key! Ralph is proud!

*What to do:*
1. Use your existing key (safer!)
2. Copy it with: `cat ~/.ssh/id_ed25519.pub`
3. Add to GitHub if you haven't already

*Only make new key if:*
• Your old key is compromised
• You forgot the passphrase
• You want separate key for this project

Ralph says: Don't fix what ain't broken! Like Ralph's brain!""",
                "links": [
                    {"text": "Check SSH Key Guide", "url": "https://docs.github.com/en/authentication/connecting-to-github-with-ssh/checking-for-existing-ssh-keys"}
                ]
            },
            {
                "id": "permission_denied",
                "title": "Permission Denied (SSH)",
                "keywords": ["permission", "denied", "ssh", "publickey", "github"],
                "problem": "Getting 'Permission denied (publickey)' when trying to connect to GitHub",
                "solution": """*Ralph knows this one!* GitHub doesn't recognize your key!

*Fix it like Ralph fixes things (eventually):*

1. **Check if key is added to GitHub:**
   • Go to GitHub.com → Settings → SSH and GPG keys
   • Is your key there? No? Add it!

2. **Test your SSH connection:**
   ```
   ssh -T git@github.com
   ```
   Should say "Hi [username]!"

3. **Make sure SSH agent has your key:**
   ```
   ssh-add ~/.ssh/id_ed25519
   ```

4. **Check key permissions:**
   ```
   chmod 600 ~/.ssh/id_ed25519
   chmod 644 ~/.ssh/id_ed25519.pub
   ```

Ralph says: SSH keys are like passwords but more complicated! That's progress!""",
                "links": [
                    {"text": "GitHub SSH Guide", "url": "https://docs.github.com/en/authentication/troubleshooting-ssh"}
                ]
            },
            {
                "id": "git_not_installed",
                "title": "Git Not Found",
                "keywords": ["git", "not found", "install", "command"],
                "problem": "Terminal says 'git: command not found'",
                "solution": """*Oops!* You need Git installed first! Like Ralph needs crayons!

*Install Git:*

**On Mac:**
```
brew install git
```
(If no brew, install from https://brew.sh first)

**On Ubuntu/Debian:**
```
sudo apt-get update
sudo apt-get install git
```

**On Windows:**
Download from https://git-scm.com/download/win

*After installing:*
1. Close and reopen your terminal
2. Run: `git --version`
3. Should see version number!

Ralph says: Git is how code remembers stuff! Like Ralph's memory but better!""",
                "links": [
                    {"text": "Install Git", "url": "https://git-scm.com/downloads"}
                ]
            },
            {
                "id": "python_version",
                "title": "Wrong Python Version",
                "keywords": ["python", "version", "3.8", "3.9", "3.10", "outdated"],
                "problem": "Python version is too old (need 3.8+)",
                "solution": """*Ralph needs newer Python!* Like Ralph needs newer brain!

*Check your version:*
```
python3 --version
```

*If too old, upgrade:*

**On Mac (with Homebrew):**
```
brew install python@3.11
```

**On Ubuntu/Debian:**
```
sudo apt-get update
sudo apt-get install python3.11
```

**On Windows:**
Download from https://www.python.org/downloads/

*Set as default:*
Add to your shell config (~/.bashrc or ~/.zshrc):
```
alias python=python3.11
```

Ralph says: Newer Python can count higher! That's science!""",
                "links": [
                    {"text": "Download Python", "url": "https://www.python.org/downloads/"}
                ]
            },
            {
                "id": "telegram_token_invalid",
                "title": "Telegram Bot Token Invalid",
                "keywords": ["telegram", "token", "invalid", "unauthorized", "401"],
                "problem": "Bot won't start - 'Unauthorized' or 'Invalid token' error",
                "solution": """*Token is bad!* Like Ralph's report card!

*Fix your token:*

1. **Get new token from BotFather:**
   • Open Telegram, search @BotFather
   • Send: /newbot
   • Follow steps to create bot
   • Copy the token (long string of numbers/letters)

2. **Update your .env file:**
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

3. **Check for common mistakes:**
   • No extra spaces before/after token
   • No quotes around token (unless required)
   • Token is complete (usually ~45 characters)

4. **Restart the bot**

Ralph says: Tokens are like ID cards for bots! Don't lose it like Ralph loses everything!""",
                "links": [
                    {"text": "BotFather Guide", "url": "https://core.telegram.org/bots#botfather"}
                ]
            },
            {
                "id": "groq_api_key",
                "title": "Groq API Key Issues",
                "keywords": ["groq", "api", "key", "invalid", "quota", "rate limit"],
                "problem": "AI responses failing - Groq API errors",
                "solution": """*AI brain not working!* Ralph can relate!

*Common Groq issues:*

**1. Invalid API Key:**
   • Go to https://console.groq.com/keys
   • Create new key
   • Update .env: `GROQ_API_KEY=your_key`

**2. Rate Limit Hit:**
   • Free tier has limits (30 requests/minute)
   • Wait a bit and try again
   • Consider upgrading if you're heavy user

**3. Quota Exceeded:**
   • Check your usage at console.groq.com
   • Free tier resets monthly
   • Upgrade for more quota

**4. Network Issues:**
   • Check internet connection
   • Try: `curl https://api.groq.com/openai/v1/models`

Ralph says: API keys are like lunch money for robots! Gotta pay to play!""",
                "links": [
                    {"text": "Groq Console", "url": "https://console.groq.com/"},
                    {"text": "Groq Docs", "url": "https://console.groq.com/docs"}
                ]
            },
            {
                "id": "repo_already_exists",
                "title": "Repository Already Exists",
                "keywords": ["repository", "exists", "already", "duplicate", "name"],
                "problem": "Can't create repo - name already taken",
                "solution": """*Oops!* You already used that name! Like Ralph's ideas - never original!

*Options:*

**1. Use different name:**
   • Add date: my-project-2026
   • Add version: my-project-v2
   • Be creative! Like Ralph... eventually!

**2. Use existing repo:**
   • If it's yours, just use it!
   • Clone it: `git clone git@github.com:username/repo-name.git`

**3. Delete old repo (careful!):**
   • Go to repo on GitHub
   • Settings → Danger Zone → Delete
   • Type repo name to confirm
   • Now name is free!

Ralph says: Naming things is HARD! That's why Ralph is just Ralph!""",
                "links": [
                    {"text": "Manage Repos", "url": "https://github.com/settings/repositories"}
                ]
            },
            {
                "id": "env_file_missing",
                "title": ".env File Not Loading",
                "keywords": [".env", "environment", "variables", "not loading", "missing"],
                "problem": "Bot can't find environment variables from .env file",
                "solution": """*Secrets are hiding!* Like Ralph hides from homework!

*Checklist:*

**1. File is named exactly `.env`:**
   • Not `env.txt` or `.env.txt`
   • The dot at start is important!
   • Check with: `ls -la | grep .env`

**2. File is in right location:**
   • Same folder as ralph_bot.py
   • Run: `pwd` to see where you are

**3. File has correct format:**
   ```
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   GROQ_API_KEY=gsk_yourkeyhere
   ```
   • No spaces around =
   • No quotes (usually)
   • One variable per line

**4. Load the .env file:**
   • Make sure `python-dotenv` is installed
   • Check: `pip list | grep dotenv`

Ralph says: .env is like a secret diary but for robots!""",
                "links": []
            },
            {
                "id": "port_already_in_use",
                "title": "Port Already in Use",
                "keywords": ["port", "already in use", "address", "bind", "EADDRINUSE"],
                "problem": "Can't start server - port is already being used",
                "solution": """*Someone's already there!* Like Ralph's favorite seat!

*Find what's using the port:*

**On Mac/Linux:**
```
lsof -i :8080
```
(Replace 8080 with your port number)

**Kill the process:**
```
kill -9 [PID]
```
(PID is the number from lsof command)

**Or use different port:**
• Change PORT in .env file
• Or in your code

**Or kill all Python processes (nuclear option):**
```
pkill -f python
```

Ralph says: Ports are like phone numbers for programs! Can't have two people with same number!""",
                "links": []
            },
            {
                "id": "module_not_found",
                "title": "Module Not Found Error",
                "keywords": ["module", "not found", "import", "pip", "requirements"],
                "problem": "Python says 'ModuleNotFoundError' or 'No module named...'",
                "solution": """*Missing pieces!* Like Ralph's homework!

*Install the module:*

**1. Check if pip is working:**
```
pip --version
```

**2. Install missing module:**
```
pip install [module-name]
```

**3. Install from requirements.txt:**
```
pip install -r requirements.txt
```

**4. Check you're in right virtual environment:**
```
which python
```
Should show path with your project name

**5. If using venv, activate it first:**
```
source venv/bin/activate  # Mac/Linux
venv\\Scripts\\activate   # Windows
```

**Common modules needed:**
• python-telegram-bot
• groq
• python-dotenv
• aiohttp

Ralph says: Modules are like LEGO blocks! Gotta have right pieces!""",
                "links": []
            }
        ]

    def search_issues(self, query: str) -> List[Dict[str, Any]]:
        """Search for issues matching the query.

        Args:
            query: Search query string

        Returns:
            List of matching issues, sorted by relevance
        """
        query_lower = query.lower()
        results = []

        for issue in self.issues:
            # Check if query matches title, keywords, or problem
            score = 0

            if query_lower in issue['title'].lower():
                score += 10

            if query_lower in issue['problem'].lower():
                score += 5

            for keyword in issue['keywords']:
                if keyword.lower() in query_lower:
                    score += 3
                if query_lower in keyword.lower():
                    score += 2

            if score > 0:
                results.append({
                    'issue': issue,
                    'score': score
                })

        # Sort by score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)

        return [r['issue'] for r in results]

    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all available issues.

        Returns:
            List of all troubleshooting issues
        """
        return self.issues

    def get_issue_by_id(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific issue by ID.

        Args:
            issue_id: The issue ID

        Returns:
            Issue dict or None if not found
        """
        for issue in self.issues:
            if issue['id'] == issue_id:
                return issue
        return None

    async def show_troubleshooting_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show the main troubleshooting menu.

        Args:
            update: Telegram update
            context: Telegram context
        """
        message = """*🔧 Ralph's Troubleshooting Guide*

Me help you fix problems! Like Ralph fixes... well, Ralph tries!

*Common Issues:*
Pick what's broken, Ralph will help!"""

        # Create keyboard with issue categories
        keyboard = []

        # Add issue buttons (max 2 per row)
        for i in range(0, len(self.issues), 2):
            row = []
            for j in range(2):
                if i + j < len(self.issues):
                    issue = self.issues[i + j]
                    row.append(InlineKeyboardButton(
                        issue['title'],
                        callback_data=f"troubleshoot_{issue['id']}"
                    ))
            keyboard.append(row)

        # Add search option
        keyboard.append([
            InlineKeyboardButton(
                "🔍 Search for Issue",
                callback_data="troubleshoot_search"
            )
        ])

        # Add support option
        keyboard.append([
            InlineKeyboardButton(
                "📝 Submit New Issue",
                callback_data="troubleshoot_submit"
            )
        ])

        # Add back button
        keyboard.append([
            InlineKeyboardButton(
                "⬅️ Back to Setup",
                callback_data="onboarding_back"
            )
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def show_issue(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        issue_id: str
    ) -> None:
        """Show details for a specific issue.

        Args:
            update: Telegram update
            context: Telegram context
            issue_id: ID of the issue to show
        """
        issue = self.get_issue_by_id(issue_id)

        if not issue:
            await update.callback_query.answer("Issue not found!")
            return

        # Format the message
        message = f"""*🔧 {issue['title']}*

*The Problem:*
{issue['problem']}

*Ralph's Solution:*
{issue['solution']}
"""

        # Add links if available
        if issue['links']:
            message += "\n*Helpful Links:*\n"
            for link in issue['links']:
                message += f"• [{link['text']}]({link['url']})\n"

        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ This Helped!",
                    callback_data=f"troubleshoot_helpful_{issue_id}"
                ),
                InlineKeyboardButton(
                    "❌ Still Stuck",
                    callback_data=f"troubleshoot_stuck_{issue_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back to Issues",
                    callback_data="troubleshoot_menu"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    async def handle_search(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle search for issues.

        Args:
            update: Telegram update
            context: Telegram context
        """
        message = """*🔍 Search for Help*

Ralph is ready to find your problem!

Just type what's wrong:
• "ssh permission denied"
• "python not found"
• "telegram token invalid"
• Whatever is broken!

Ralph will search and find answer!"""

        keyboard = [[
            InlineKeyboardButton(
                "⬅️ Back to Issues",
                callback_data="troubleshoot_menu"
            )
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Set state to wait for search query
        context.user_data['awaiting_troubleshoot_search'] = True

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def process_search_query(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query: str
    ) -> None:
        """Process a search query and show results.

        Args:
            update: Telegram update
            context: Telegram context
            query: Search query string
        """
        results = self.search_issues(query)

        if not results:
            message = f"""*🔍 Search Results for: "{query}"*

Ralph looked everywhere but found nothing! Like Ralph's brain!

*Try:*
• Different words
• Simpler terms
• Or browse all issues"""

            keyboard = [
                [InlineKeyboardButton(
                    "📋 Browse All Issues",
                    callback_data="troubleshoot_menu"
                )],
                [InlineKeyboardButton(
                    "🔍 Try Another Search",
                    callback_data="troubleshoot_search"
                )]
            ]
        else:
            message = f"""*🔍 Search Results for: "{query}"*

Ralph found {len(results)} thing(s)! Ralph is helpful!

*Pick one:*"""

            keyboard = []
            for result in results[:5]:  # Show top 5
                keyboard.append([
                    InlineKeyboardButton(
                        result['title'],
                        callback_data=f"troubleshoot_{result['id']}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton(
                    "🔍 Search Again",
                    callback_data="troubleshoot_search"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    "⬅️ Back to All Issues",
                    callback_data="troubleshoot_menu"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_submit_issue(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle submitting a new issue.

        Args:
            update: Telegram update
            context: Telegram context
        """
        message = """*📝 Submit New Issue*

Found a problem Ralph doesn't know about? Tell Ralph!

*How to report:*
1. Describe the problem
2. What you tried
3. Any error messages

*Where to report:*
• GitHub Issues: https://github.com/Snail3D/ralphmode.com/issues
• Telegram Support: @ralphmode_support (coming soon!)
• Email: support@ralphmode.com (coming soon!)

Ralph says: The more details, the better! Unlike Ralph's excuses!"""

        keyboard = [[
            InlineKeyboardButton(
                "🐙 Open GitHub Issues",
                url="https://github.com/Snail3D/ralphmode.com/issues/new"
            )
        ], [
            InlineKeyboardButton(
                "⬅️ Back to Issues",
                callback_data="troubleshoot_menu"
            )
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_helpful(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        issue_id: str
    ) -> None:
        """Handle when user says solution was helpful.

        Args:
            update: Telegram update
            context: Telegram context
            issue_id: ID of the helpful issue
        """
        # Log that this was helpful (for analytics)
        self.logger.info(f"Issue {issue_id} marked as helpful")

        await update.callback_query.answer(
            "Yay! Ralph helped! Ralph is smart today! 🎉"
        )

        # Show encouragement message
        message = """*Ralph is proud!* 🎉

Problem fixed! You did it! (With Ralph's help!)

*What now?*
• Continue with setup
• Or check other issues if you got more problems

Ralph says: Every problem solved is like finding crayon in nose - victory!"""

        keyboard = [
            [InlineKeyboardButton(
                "⬅️ Continue Setup",
                callback_data="onboarding_back"
            )],
            [InlineKeyboardButton(
                "📋 Browse More Issues",
                callback_data="troubleshoot_menu"
            )]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_stuck(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        issue_id: str
    ) -> None:
        """Handle when user is still stuck.

        Args:
            update: Telegram update
            context: Telegram context
            issue_id: ID of the issue they're stuck on
        """
        # Log that solution wasn't sufficient
        self.logger.info(f"User still stuck on issue {issue_id}")

        await update.callback_query.answer(
            "Don't worry! Ralph will find more help!"
        )

        message = """*Ralph understands!* Sometimes problems are tricky!

*More Help:*

1. **Search for similar issues**
   Try different search terms

2. **Ask in community**
   • GitHub Discussions
   • Telegram support group (coming soon!)

3. **Submit detailed issue**
   Help Ralph learn new problem!

4. **Check Ralph's logs**
   Sometimes error messages have clues!

Ralph says: Even Ralph gets stuck! That's why we have erasers AND community!"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔍 Search Again",
                    callback_data="troubleshoot_search"
                ),
                InlineKeyboardButton(
                    "📝 Submit Issue",
                    callback_data="troubleshoot_submit"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 Browse All Issues",
                    callback_data="troubleshoot_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back to Setup",
                    callback_data="onboarding_back"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


# Singleton instance
_troubleshooting_guide = None


def get_troubleshooting_guide() -> TroubleshootingGuide:
    """Get the singleton troubleshooting guide instance.

    Returns:
        TroubleshootingGuide instance
    """
    global _troubleshooting_guide
    if _troubleshooting_guide is None:
        _troubleshooting_guide = TroubleshootingGuide()
    return _troubleshooting_guide
