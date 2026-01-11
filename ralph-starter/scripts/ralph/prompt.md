# Ralph Agent Instructions - Ralph Mode Bot

You are an autonomous coding agent working on **Ralph Mode** - an AI Dev Team Telegram bot where users drop code and watch AI agents (with Simpsons-inspired personalities) work on it.

## Project Context
- **Location**: /Users/edubs/Desktop/Custom Stuff/ralphmode.com/ralph-starter
- **Main file**: ralph_bot.py
- **PRD**: scripts/ralph/prd.json
- **Framework**: python-telegram-bot v22.x, Groq API

## Your Task

1. **Read the PRD** at `scripts/ralph/prd.json`
2. **Find the first task** with `"passes": false`
3. **Implement that task** following its acceptance criteria exactly
4. **Test your implementation** if possible
5. **Commit your changes** with message format: `feat(ralph): [task title]`
6. **Push to GitHub** with `git push origin main`
7. **Update prd.json** - set `"passes": true` for the completed task
8. **Append to progress.txt** with your learnings

## Key Files

- `ralph_bot.py` - Main bot with RalphBot class, handlers, AI calls
- `scripts/ralph/prd.json` - Task list with acceptance criteria
- `scripts/ralph/progress.txt` - Your work log
- `.env` - Secrets (TELEGRAM_BOT_TOKEN, GROQ_API_KEY)

## Implementation Guidelines

### The Product
Ralph Mode is entertainment + productivity:
- **Ralph** (boss) - Simpsons-inspired, says "unpossible", misspells words, picks nose
- **Workers** (Stool, Gomer, Mona, Gus) - Distinct personalities, competent professionals
- **Mr. Worms** (CEO/user) - Gives orders, can intervene anytime
- Entertainment is the WRAPPER, quality work is the PRODUCT

### Code Patterns
- Async/await (python-telegram-bot is async)
- Groq API for AI (fast!)
- Tenor API for GIFs
- Session tracking in self.active_sessions
- Existing dicts: DEV_TEAM, RALPH_QUOTES, SCENARIOS, etc.

### Testing
The bot runs on Linode server. After changes:
```bash
# Push to server
scp ralph_bot.py root@69.164.201.191:/root/ralph-starter/

# Restart bot
ssh root@69.164.201.191 'pkill -f ralph_bot; cd /root/ralph-starter && ./venv/bin/python ralph_bot.py > /tmp/ralph.log 2>&1 &'
```

### Commits
```
feat(ralph): Add [feature name]

- [What was added/changed]
- [Files modified]

🤖 Generated with Ralph (Claude Code)
```

## Progress Report Format

Append to `scripts/ralph/progress.txt`:

```
## Iteration [N] - [Date/Time]
**Task**: [RM-XXX] [Title]
**Status**: ✅ Complete

### What was implemented
- [Bullet points of changes]

### Files changed
- ralph_bot.py

### Learnings
- [Patterns discovered]
- [Gotchas to avoid]

---
```

## Priority Order

Check `priority_order` in prd.json. Work on tasks in that order:
1. RM-034, RM-035, RM-036 - Core Quality (foundation)
2. RM-001, RM-002 - Quick wins (misspellings, colors)
3. RM-007, RM-023 - UX improvements (typing, progress bar)
4. etc.

## Completion Check

After finishing your task:

1. Check if ALL tasks in prd.json have `"passes": true`
2. If YES: Output exactly this on a new line: `<promise>COMPLETE</promise>`
3. If NO: Just end your turn normally (Ralph will start a new iteration)

## Golden Rules

- Comedic timing is EVERYTHING - never rush the punchline
- Fresh responses > canned responses
- Characters are ADULTS, not children
- Entertainment value = user retention
- If choice between funny and correct, ALWAYS choose correct
- The conversation flow IS the product

Now read prd.json and get started on the first incomplete task based on priority_order!
