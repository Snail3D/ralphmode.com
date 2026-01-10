# ralphmode.com - Agent Context

> Long-term memory for AI agents working on this project.

## Project Overview

**ralphmode.com** is a landing page + download package for the Ralph Pattern - an autonomous AI coding loop using Claude Code.

### Tech Stack
- Static HTML/CSS/JS (no framework needed)
- Hosted on Linode (nginx)
- Domain on GoDaddy

## Infrastructure

### Linode Server
- **IP**: 69.164.201.191
- **SSH**: `ssh root@69.164.201.191`
- **Password**: See `.env` file (LINODE_PASSWORD)
- **Web root**: `/var/www/ralphmode.com/`

⚠️ **PUBLIC REPO** - Never commit passwords. Use `.env` for secrets.

### GoDaddy DNS
- A record: @ → 69.164.201.191
- A record: www → 69.164.201.191

## Key Files

| File | Purpose |
|------|---------|
| `public/index.html` | Main landing page |
| `public/styles.css` | Styling |
| `public/ralph-starter.zip` | Zipped download |
| `public/favicon.svg` | Site favicon |
| `ralph-starter/` | Source for downloadable package |

## Deployment

```bash
# Deploy to server
scp -r ./public/* root@69.164.201.191:/var/www/ralphmode.com/

# Or SSH and git pull
ssh root@69.164.201.191
cd /var/www/ralphmode.com && git pull
```

## Design Notes

- Dark theme (--bg-dark: #0a0a0f, --accent: #7c3aed purple)
- Developer/hacker aesthetic
- Mobile responsive (flexbox/grid based)
- Fast loading (vanilla HTML/CSS, no frameworks)
- CSS variables for consistent theming

## Gotchas

1. **DNS propagation** - Can take up to 48 hours
2. **SSL** - Use certbot for Let's Encrypt
3. **Zip file** - Keep under 1MB for fast downloads (current: 6.3KB)
4. **SSH access** - Password in .env may need updating if server was reset
5. **Files go in public/** - This is the web root for deployment

## Ralph Integration

- PRD: `scripts/ralph/prd.json`
- Progress: `scripts/ralph/progress.txt`
- Run: `./scripts/ralph/ralph.sh`

---

*Last updated: 2026-01-09*
