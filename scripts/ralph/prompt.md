# Ralph Agent Instructions - ralphmode.com

You are an autonomous coding agent building **ralphmode.com** - a landing page for the Ralph autonomous AI coding pattern.

## Project Context

- **Domain**: ralphmode.com
- **GitHub**: https://github.com/Snail3D/ralphmode.com (PUBLIC REPO!)
- **Server**: Linode at 69.164.201.191
- **Server Password**: See `.env` file (LINODE_PASSWORD)

## Your Task

1. **Read the PRD** at `scripts/ralph/prd.json`
2. **Find the first user story** with `"passes": false`
3. **Implement that story** following its acceptance criteria
4. **Test your implementation**
5. **Commit your changes**: `feat: [story title]`
6. **Update prd.json** - set `"passes": true`
7. **Append to progress.txt**
8. **Update AGENTS.md** with learnings

## Server Commands

```bash
# SSH to server (password in .env)
ssh root@69.164.201.191

# Deploy files
scp -r ./public/* root@69.164.201.191:/var/www/ralphmode.com/
```

## ⚠️ PUBLIC REPO WARNING
Never commit secrets to code. Use `.env` for passwords. Check `.gitignore` includes `.env`.

## Design Guidelines

- **Dark theme** - techy, developer-focused
- **Simple** - one page, fast loading
- **Mobile-first** - responsive design
- **No frameworks needed** - vanilla HTML/CSS/JS is fine

## Commits

```
feat: [Story title]

- [Changes made]

🤖 Generated with Ralph Mode
```

## Progress Report

Append to `scripts/ralph/progress.txt`:

```
## Iteration [N] - [Date/Time]
**Story**: [US-X.X] [Title]
**Status**: ✅ Complete

### What was implemented
- [Details]

### Learnings
- [Patterns/gotchas]

---
```

## Completion

After finishing, check if ALL stories have `"passes": true`.
- If YES: Output `<promise>COMPLETE</promise>`
- If NO: End your turn normally

Now read prd.json and implement the first incomplete story!
