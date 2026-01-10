# Ralph Mode 🤖

**AI Dev Team in Your Telegram**

Drop code. Watch AI agents build. Ship features while you eat popcorn.

## What is Ralph Mode?

Ralph Mode is a Telegram bot that turns AI into your personal development team:

1. **Drop a zip file** of your code into Telegram
2. **AI analyzes** your codebase and generates a task list
3. **Watch the drama** as AI agents work and a middle manager reviews everything
4. **Intervene as CEO** anytime with voice or text commands
5. **Ship features** while you sleep (or watch for entertainment)

## Quick Start

### 1. Get Your API Keys

- **Telegram Bot Token**: Message [@BotFather](https://t.me/BotFather) and create a new bot
- **Groq API Key**: Sign up at [console.groq.com](https://console.groq.com) (free!)
- **Your Telegram ID**: Message [@userinfobot](https://t.me/userinfobot)

### 2. Configure

```bash
# Copy the example config
cp .env.example .env

# Edit with your keys
nano .env
```

### 3. Install & Run

```bash
# Install dependencies
pip install python-telegram-bot requests

# Run the bot
python ralph_bot.py
```

### 4. Use It

1. Open Telegram and find your bot
2. Send `/start`
3. Drop a `.zip` file of your code
4. Watch the magic happen!

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and instructions |
| `/status` | Check current session status |
| `/stop` | Stop the current session |
| `Boss: [message]` | Talk directly to the middle manager |

## The Cast

```
┌─────────────────────────────────────────┐
│                 YOU (CEO)               │
│   Give orders, watch progress, profit   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│         THE BOSS (Middle Manager)       │
│  • Nice but clueless                    │
│  • Asks dumb questions (that help!)     │
│  • Reports back to you                  │
│  • Can be convinced with good arguments │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            DEV TEAM (Workers)           │
│  • Smart and capable                    │
│  • Explain things simply to boss        │
│  • Push back when needed                │
│  • Get the actual work done             │
└─────────────────────────────────────────┘
```

## How It Works

1. You drop code into Telegram
2. AI analyzes the codebase
3. Generates a task list (PRD)
4. Boss reviews each task with the team
5. Workers implement, boss approves
6. You watch the whole thing like reality TV
7. Code ships!

## Features

- **Voice Commands**: Talk to Ralph (coming soon)
- **Screenshots**: Share visual references anytime
- **Boss Mode**: Address the manager directly with `Boss: [message]`
- **Entertainment**: Watch AI agents argue about your code

## File Structure

```
ralph-starter/
├── ralph_bot.py              # Main Telegram bot
├── scripts/ralph/
│   ├── boss_meeting.py       # Boss/Worker conversation system
│   ├── ralph.sh              # Autonomous coding loop
│   ├── prompt.md             # AI instructions
│   └── prd.json              # Task list format
├── .env.example              # Config template
└── README.md                 # This file
```

## The Ralph Pattern

Named after Ralph Wiggum from The Simpsons. The pattern:

1. Read PRD with tasks
2. Pick first incomplete task
3. Implement it
4. Commit and mark done
5. Loop until complete

Created by Geoffrey Huntley, popularized by Ryan Carson (700k+ views).

## Pro Tips

- The Boss asking "dumb" questions often leads to better solutions
- Workers can push back once, then must accept the verdict
- You (CEO) can override anything with `Boss: [command]`
- Queued orders are handled when the team has a free moment

## Credits

- Ralph Pattern by [Geoffrey Huntley](https://ghuntley.com)
- Popularized by [Ryan Carson](https://x.com/ryancarson)
- Built with [Claude Code](https://claude.com/claude-code)
- Powered by [Groq](https://groq.com) (fast & free!)

## Get It

**$10** at [ralphmode.com](https://ralphmode.com)

---

*Ship features while you sleep. 🚀*
