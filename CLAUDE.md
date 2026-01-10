# ralphmode.com - Project Context

## ⚠️ IMPORTANT: Public Repo - Use .env for Secrets!

This repo is **PUBLIC** on GitHub. Never commit passwords or secrets directly to code.

### What is .env?
A `.env` file stores secrets locally on your machine. It's listed in `.gitignore` so it never gets pushed to GitHub.

```bash
# Create .env file (this stays LOCAL, never pushed)
echo "LINODE_PASSWORD=your_actual_password" > .env

# Create .env.example (this IS pushed, shows what's needed)
echo "LINODE_PASSWORD=your_password_here" > .env.example
```

### Secrets for this project:
- **Linode Password**: Store in `.env`, use `LINODE_PASSWORD`
- **Server IP**: 69.164.201.191 (this is fine to commit, IPs are public)

### .gitignore must include:
```
.env
```

---

## What This Is

A landing page + download package for the **Ralph Pattern** - an autonomous AI coding loop that lets Claude Code implement features while you sleep.

**Domain**: ralphmode.com (purchased on GoDaddy)
**GitHub**: https://github.com/Snail3D/ralphmode.com
**Server**: Linode at 69.164.201.191 (label: ralphmode.com)

## The Vision

Create the #1 resource for people wanting to use the Ralph pattern with Claude Code. One-click download of a ready-to-go Ralph starter kit.

### What Ralph Is

Ralph (named after Ralph Wiggum) is a bash loop that:
1. Reads a `prd.json` with user stories
2. Spawns Claude Code with `--dangerously-skip-permissions`
3. Claude picks a story, implements it, commits, marks it done
4. Loop repeats until all stories pass
5. You wake up to shipped features

Created by Geoffrey Huntley, popularized by Ryan Carson (700k+ views on his X post).

## Infrastructure

### Linode Server
- **IP**: 69.164.201.191
- **Label**: ralphmode.com
- **Password**: See `.env` file (LINODE_PASSWORD)
- **SSH**: `ssh root@69.164.201.191`

### GoDaddy DNS Setup (MANUAL STEP REQUIRED)

**Current Status**: Domain is parked at Afternic (GoDaddy's parking service). Needs manual configuration.

#### Step 1: Change Nameservers (if using Afternic)
1. Log into GoDaddy: https://dcc.godaddy.com
2. Go to Domain Settings → DNS → Nameservers
3. Change from Afternic to GoDaddy nameservers:
   - `ns1.domaincontrol.com`
   - `ns2.domaincontrol.com`

#### Step 2: Configure A Records
1. Go to DNS Management
2. Delete any existing A records for @ and www
3. Add new A records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | 69.164.201.191 | 600 |
| A | www | 69.164.201.191 | 600 |

#### Step 3: Wait for Propagation
- DNS changes can take 15 minutes to 48 hours
- Check progress: `dig ralphmode.com A`
- Expected result: `69.164.201.191`

#### Step 4: Get SSL Certificate
Once DNS is pointing to the server:
```bash
ssh root@69.164.201.191
certbot --nginx -d ralphmode.com -d www.ralphmode.com
```

### Tech Stack (Suggested)
- Simple static site (HTML/CSS/JS) or Astro/Next.js
- Hosted on Linode with nginx
- Or use GitHub Pages / Vercel for simplicity

## Website Sections

1. **Hero**: "Ship features while you sleep" + demo gif
2. **What is Ralph?**: 30-second explainer
3. **How it works**: Visual loop diagram
4. **Download**: Big button → zip file
5. **Quick Start**: 3 steps to get running
6. **Credits**: Link to Ryan Carson + original repo

## The Download Package

```
ralph-starter/
├── scripts/ralph/
│   ├── ralph.sh           # The bash loop
│   ├── prompt.md          # System instructions for Claude
│   ├── prd.json           # Example PRD template
│   └── progress.txt       # Short-term memory
├── AGENTS.md              # Long-term memory template
├── setup.sh               # One-command setup
└── README.md              # Quick start guide
```

## Key Resources

- **Original Ralph repo**: https://github.com/snarktank/ralph
- **Ryan Carson's X**: https://x.com/ryancarson
- **The viral post**: 700k+ views explaining Ralph
- **Claude Code docs**: https://docs.anthropic.com/claude-code

## Commands

```bash
# SSH to server
ssh root@69.164.201.191

# Deploy (once set up)
git pull && npm run build  # or however we deploy

# Test locally
npm run dev  # or python -m http.server
```

## Next Steps

1. Set up DNS in GoDaddy (A records to 69.164.201.191)
2. SSH to Linode, install nginx
3. Create the landing page
4. Create the downloadable zip package
5. Deploy and test
6. Share on X and profit

---

*Let's make Ralph accessible to everyone!*
