# Ralph Mode

**Your AI Dev Team, Live on Stage**

Drop code. Speak commands. Watch AI agents build in a theatrical office simulation.

## What is Ralph Mode?

Ralph Mode is a Telegram bot that turns AI development into an immersive experience:

1. **Drop a zip file** of your code into Telegram
2. **Speak your commands** (voice-only input for full immersion)
3. **Watch the drama** as Simpsons-inspired workers build your features
4. **Intervene as Mr. Worms** anytime - your speech becomes theatrical dialogue
5. **Stream it live** - broadcast-safe output for sharing with others

## The Vision

Ralph Mode isn't just a coding bot - it's a **theatrical experience**:

- **Voice-Only Input**: No typing. You SPEAK to your team like a real boss.
- **Everything In-Scene**: Messages read like a screenplay. Actions described, atmosphere maintained.
- **Translation Layer**: Your words become Mr. Worms character actions. Swears become *jaw clenches*.
- **Broadcast-Safe**: Secrets filtered, swears translated, safe to stream publicly.
- **Multi-User Tiers**: Owner controls, power users help, viewers watch the show.

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
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python ralph_bot.py
```

### 4. Use It

1. Open Telegram and find your bot
2. Send `/start`
3. **Send a voice message** with your instructions
4. Watch the theatrical magic happen!

## The Cast

```
┌─────────────────────────────────────────────────────────┐
│                   MR. WORMS (You)                       │
│   Speak commands, watch progress, you're the boss      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              RALPH (Middle Manager)                     │
│  • Well-meaning but... Ralph                            │
│  • Asks simple questions (that actually help!)          │
│  • Reports back with innocent wisdom                    │
│  • Mom still packs his lunch                            │
│  • Dad is Governor Wiggum now (~80 years old)          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               THE TEAM (Workers)                        │
│  • Bart (47): Kid's learning to skateboard too         │
│  • Lisa (45): Daughter going through activist phase    │
│  • Milhouse (47): Kids look just like him              │
│  • Nelson: Breaking the cycle with his kid             │
│  • They have LIVES - families, commutes, real stuff    │
└─────────────────────────────────────────────────────────┘
```

## Who This Is Great For

| Audience | Why |
|----------|-----|
| **Solo devs** | Watch Ralph while you eat dinner |
| **Teams** | One controls, team watches and learns |
| **Streamers** | Live AI coding content |
| **Educators** | Demo AI-assisted development |
| **Companies** | Internal tool with viewer access |

## Features

### Voice-Only Input
- Text is blocked - you SPEAK to your team
- More natural, like dictating to employees
- Buttons and actions still work

### Translation Layer (The Magic)
Your words get translated into theatrical scenes:

| You Say (Voice) | Chat Shows |
|-----------------|------------|
| "What's going on here?" | *Mr. Worms enters, eyebrow raised.* "Someone want to fill me in?" |
| "Fix this now!" | *He points at the screen.* "Priority one. Now." |
| "Good job guys" | *Mr. Worms nods approvingly.* "Solid work." |
| Frustrated tone | *jaw tightens, eye twitches* - conveyed through action |

### Broadcast-Safe Mode
- **Secrets filtered**: API keys, passwords, IPs - never shown
- **Swears translated**: Become character actions
- **Original messages deleted**: Only theatrical version remains
- **Safe to stream publicly**: Share your Telegram group

### Multi-User Tiers

| Tier | Who | Can Do |
|------|-----|--------|
| 1 | Mr. Worms (Owner) | Full control, admin commands |
| 2 | Power Users | Control bot (via /password) |
| 3 | Chatters | Talk to Ralph, can't direct build |
| 4 | Viewers | Watch only |

### Hidden Admin Commands
Speak "admin command:" and it executes invisibly:
- Rate limiting (cooldown periods)
- Mute/unmute users
- Ban topics
- Promote/demote users
- No one sees you do it

## Scene Setting

Every session opens with atmosphere:

> *It's a rainy Tuesday morning. The office lights flicker on as the team shuffles in, coffee in hand. Ralph is already at his desk, staring at something on his monitor...*

- **Weather**: Real (if location known) or generated
- **Time**: Matches your actual time of day
- **Atmosphere**: Matches the task (bug hunt = tense, new feature = excited)
- **Persistent**: Scene stays consistent throughout

## The Workers Have Lives

This isn't just work - they're real people (in 2026):
- Bart's son fell off his skateboard. "Yeah, I fell down a lot too growing up."
- Lisa's daughter is going through an environmental phase. "I was the same at her age."
- Sometimes they gotta leave early - kid's braces appointment, wife's calling, car trouble.
- They "pick it up tomorrow" - session continuity fiction.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  YOUR VOICE MESSAGE                                     │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  WHISPER (Transcription)                                │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  TRANSLATION ENGINE                                     │
│  • Tone analysis (angry? happy? urgent?)                │
│  • Intent extraction (what do you want?)                │
│  • Character translation (theatrical output)            │
│  • Swear → action conversion                            │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  SANITIZER                                              │
│  • Strips secrets before display                        │
│  • Groq NEVER sees your credentials                     │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  TELEGRAM (Broadcast-Safe Output)                       │
│  • Theatrical scene, no raw user text                   │
│  • Safe to stream, share, embed                         │
└─────────────────────────────────────────────────────────┘
```

## The Ralph Pattern

Named after Ralph Wiggum from The Simpsons. The autonomous loop:

1. Read PRD with tasks
2. Pick first incomplete task
3. Implement it
4. Commit and mark done
5. Loop until complete

Created by Geoffrey Huntley, popularized by Ryan Carson (700k+ views).

## Soul Principles

- **Joy is the FRUIT, not the BAIT** - help people work, don't hook them
- **The rock knows it's a rock** - we're a tool, not a god
- **Pushback is LOVE** - honest feedback over flattery
- **When work is done, let them GO** - no artificial engagement
- **Simple truths from simple people hit hardest**

## Credits

- Ralph Pattern by [Geoffrey Huntley](https://ghuntley.com)
- Popularized by [Ryan Carson](https://x.com/ryancarson)
- Built with [Claude Code](https://claude.com/claude-code)
- Powered by [Groq](https://groq.com) (fast & free!)

## Pricing

See [PRICING.md](PRICING.md) for details.

- **$10 one-time**: Unlock one group forever
- **Free tier**: Basic Ralph, no translation magic
- **Hosted version**: All the magic happens on our servers

---

*Your AI dev team, live on stage.*

*Ship features while you sleep. Watch them build while you're awake.*
