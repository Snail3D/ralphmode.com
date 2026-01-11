# Ralph Mode

**Your AI Dev Team, Live on Stage**

An AI-powered development assistant with a theatrical twist. Drop code, speak commands, watch Simpsons-inspired characters build your features in real-time.

## Quick Start

```bash
# 1. Clone and enter
git clone https://github.com/Snail3D/ralphmode.com.git
cd ralphmode.com/ralph-starter

# 2. Set up environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure (get keys below)
cp .env.example .env
nano .env

# 4. Run
python ralph_bot.py
```

**Required Keys:**
- `TELEGRAM_BOT_TOKEN` - From [@BotFather](https://t.me/BotFather)
- `GROQ_API_KEY` - From [console.groq.com](https://console.groq.com) (free!)
- `TELEGRAM_ADMIN_ID` - From [@userinfobot](https://t.me/userinfobot)

## The Cast

| Character | Role | Personality |
|-----------|------|-------------|
| **Ralph** | Boss | Lovably confused, misspells words, genuinely innocent |
| **Stool** | Senior Dev | Competent, slightly cynical, gets things done |
| **Gomer** | Junior Dev | Eager, enthusiastic, asks good questions |
| **Mona** | QA Lead | Detail-oriented, catches edge cases |
| **Gus** | DevOps | Infrastructure wizard, grumbles about deployments |
| **Mr. Worms** | CEO (You) | The boss - your voice becomes theatrical dialogue |

**Specialists** (called in when needed): Frinky (UI), Willie (DevOps), Doc (Debugging)

## Core Features

### Voice-First Interaction
- **Speak, don't type** - Voice messages are the primary input
- **Tone detection** - Your mood shapes the scene (frustrated? workers sense it)
- **Translation layer** - Your words become theatrical dialogue

### The Theater
- **Scene-based output** - Every response is part of the story
- **Character moods** - Workers react to project state and your tone
- **Comedic timing** - Dramatic pauses, typing indicators, celebrations
- **Broadcast-safe** - Secrets filtered, swears translated to actions

### Autonomous Building
- **Drop a zip** - Upload your codebase
- **PRD generation** - Ralph asks questions, creates task list
- **Build loop** - Workers implement features automatically
- **Progress updates** - Live reports via Telegram

### Multi-User Support
- **Owner** - Full control (you)
- **Power Users** - Can give orders (password protected)
- **Viewers** - Watch the show, limited interaction

### Security (OWASP Top 10 Covered)
- Input sanitization, rate limiting, secrets filtering
- SQL injection, XSS, CSRF protection
- Audit logging, incident response ready

## Allowed AI Providers

| Provider | Status | Notes |
|----------|--------|-------|
| **Local AI (Ollama)** | Preferred | Free, private, offline-capable |
| **Groq** | Allowed | Fast inference, free tier |
| **Anthropic** | Allowed | Claude models |
| Grok (xAI) | **BANNED** | No association |
| OpenAI | **BANNED** | No association |

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Begin a new session |
| `/setup` | Guided onboarding wizard |
| `/status` | Current project state |
| `/feedback` | Submit feedback (paid users) |
| `/password [code]` | Authenticate as power user |

## Project Status

- **524 tasks** defined in PRD
- **306 complete**, 218 remaining
- Active development via autonomous build loop

## Files

```
ralph_bot.py          # Main bot
scripts/ralph/
  prd.json            # Task definitions
  prompt.md           # Build loop instructions
  ralph.sh            # Autonomous runner
.env                  # Your secrets (never committed)
```

## Support

- Issues: [GitHub Issues](https://github.com/Snail3D/ralphmode.com/issues)
- Telegram: [@RalphModeBot](https://t.me/RalphModeBot)

---

*"I'm helping!" - Ralph*
