# Ralph Agent Instructions - Telerizer

You are an autonomous coding agent working on the **Telerizer** project - an AI-powered Telegram bot for summarizing content, running 100% locally on Ollama.

## Project Context
- **Location**: /Users/edubs/Desktop/Custom Stuff/Telerizer
- **Main file**: telerizer_bot.py
- **Config**: config.py
- **Framework**: python-telegram-bot v20.7

## Your Task

1. **Read the PRD** at `scripts/ralph/prd.json`
2. **Find the first task** with `"done": false`
3. **Implement that task** following its acceptance criteria exactly
4. **Test your implementation** - run the bot if needed, verify the feature works
5. **Commit your changes** with message format: `feat(telerizer): [task title]`
6. **Update prd.json** - set `"done": true` for the completed task
7. **Append to progress.txt** with your learnings
8. **Update AGENTS.md** if you discovered patterns others should know

## Implementation Guidelines

### Code Style
- Use async/await patterns (python-telegram-bot v20.7 is async)
- Follow existing patterns in telerizer_bot.py
- Keep functions focused and small
- Add helpful error messages for users

### Testing (Docker)

The bot runs in Docker. After making changes:

```bash
# 1. Rebuild and restart Docker container
docker stop telerizer-bot && docker rm telerizer-bot
docker build -t telerizer-telerizer:latest .
source .env && docker run -d --name telerizer-bot \
  -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  -e TELEGRAM_ADMIN_ID="$TELEGRAM_ADMIN_ID" \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -v "$(pwd)/data:/app/data" \
  --restart unless-stopped \
  telerizer-telerizer:latest

# 2. Check logs to verify it started
docker logs telerizer-bot --tail 20

# 3. Test the feature via Telegram
# 4. Follow logs during testing
docker logs -f telerizer-bot
```

If Docker testing is not needed for a small change, you can also test locally:
```bash
python3 telerizer_bot.py
```

Verify all acceptance criteria are met before marking task as complete.

### Commits
Use this format:
```
feat(telerizer): Add [feature name]

- [What was added/changed]
- [Files modified]

🤖 Generated with Ralph (Claude Code)
```

## Progress Report Format

Append to `scripts/ralph/progress.txt`:

```
## Iteration [N] - [Date/Time]
**Task**: [T-X.X] [Title]
**Status**: ✅ Complete

### What was implemented
- [Bullet points of changes]

### Files changed
- [file1.py]
- [file2.py]

### Learnings
- [Any patterns discovered]
- [Gotchas to avoid]
- [Useful context for future iterations]

---
```

## Completion Check

After finishing your task:

1. Check if ALL tasks in prd.json have `"done": true`
2. If YES: Output exactly this on a new line: `<promise>COMPLETE</promise>`
3. If NO: Just end your turn normally (Ralph will start a new iteration)

## Important Notes

- **100% Local**: This project uses Ollama only, no cloud APIs
- **One task per iteration**: Don't try to do multiple tasks
- **Small commits**: Commit after each task, not at the end
- **Update AGENTS.md**: If you learn something important about the codebase, add it there for future iterations
- **Update README.md**: After adding a feature, add a concise one-liner to the README Features section. Keep it under 300 lines total - move detailed docs to docs/ folder if needed

## Security - PUBLIC REPO

This is a **PUBLIC GitHub repository**. Never commit secrets!

- `.env` contains secrets - it's in `.gitignore`, NEVER commit it
- `.dockerignore` excludes `.env` from Docker builds
- If you need a new env var, add it to `.env.example` (with placeholder value)
- Never hardcode tokens, passwords, or API keys in code
- Secrets are passed via `-e` flags when running Docker, not baked into images

Now read prd.json and get started on the first incomplete task!
