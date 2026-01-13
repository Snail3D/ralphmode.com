# TeleRalph - "Cook the Sauce" Builder

> *"I'm a unitard! I'm learnding! Let's cook the sauce!"* - Ralph Wiggum

TeleRalph is a Telegram bot that turns your project ideas into **ready-to-build PRDs**. Just chat with Ralph about what you want to build, answer his sharp questions, and click **"🍳 Cook Sauce!"** to get a compressed PRD you can feed directly into Claude Code.

---

## What TeleRalph Does

1. **Chat** about your project idea in Telegram
2. Ralph asks **one sharp question at a time** (fast drilling)
3. Share **screenshots/URLs** for inspiration (optional)
4. Click **"🍳 Yes! Cook Sauce!"** when ready
5. Get a **compressed PRD file** + **build instructions**
6. Feed the PRD to Claude Code: `claude --dangerously-skip-permissions`

**The output is a token-optimized PRD** with:
- Security-first tasks (`.gitignore`, `.env.example`, `config.py`)
- Tech stack selection
- File structure
- 4-8 tasks per phase (Security → Setup → Core → API → Tests)
- Build instructions with the exact Claude Code command

---

## Quick Start (Docker - Recommended)

### 1. Create Telegram Bot

Message [@BotFather](https://t.me/BotFather) on Telegram:
```
/newbot
Name: TeleRalph
Username: YourTeleRalphBot
```
Save the token.

### 2. Get Groq API Key (Free & Fast)

Go to [console.groq.com](https://console.groq.com), create an account, and generate an API key. Groq is **free** and **fast** (Llama 3.3 70B).

### 3. Run with Docker

```bash
# Clone the repo
git clone https://github.com/Snail3D/ralphmode.com.git
cd ralphmode.com

# Create .env file
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=your_bot_token_here
GROQ_API_KEY=gsk_your_groq_key_here
EOF

# Build and run
docker build -t teleralph .
docker run -d \
  --name teleralph \
  --env-file .env \
  --restart unless-stopped \
  teleralph

# Check logs
docker logs -f teleralph
```

### 4. Start Cooking

1. Open Telegram and message your bot
2. Tell Ralph about your project idea
3. Answer his questions
4. Click **"🍳 Yes! Cook Sauce!"**
5. Download the compressed PRD file
6. Feed it to Claude Code!

---

## Quick Start (Python - No Docker)

```bash
# Clone and setup
git clone https://github.com/Snail3D/ralphmode.com.git
cd ralphmode.com
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=your_bot_token_here
GROQ_API_KEY=gsk_your_groq_key_here
EOF

# Run
python ralph_telegram.py
```

---

## Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
GROQ_API_KEY=your_groq_api_key

# Optional
TENOR_API_KEY=your_tenor_api_key  # For GIF reactions
RECIPE_API_BASE=https://ralphmode.com/api/recipes  # Cloud sync (future)
```

---

## What You Get

When Ralph "cooks the sauce", you receive:

1. **Compressed PRD File** (`project_prd_20250112_123456.txt`)
   - Token-optimized JSON with legend
   - Saves 50-70% tokens vs full JSON
   - Ready for Claude Code

2. **Build Instructions** (in chat + file)
   - Exact command: `claude --dangerously-skip-permissions`
   - Security-first setup steps
   - Tech stack explanation
   - Build order

3. **Full JSON Reference** (`project_prd_20250112_123456_full.json`)
   - Human-readable version
   - Complete task breakdown
   - Acceptance criteria

---

## The PRD Compression Legend

TeleRalph compresses PRDs to save tokens when feeding to Claude Code:

```
KEYS: pn=project_name pd=project_description sp=starter_prompt ts=tech_stack
      fs=file_structure p=prds n=name d=description t=tasks ti=title
      f=file pr=priority ac=acceptance_criteria pfc=prompt_for_claude
      cmd=commands ccs=claude_code_setup ifc=instructions_for_claude

PHRASES: C=Create I=Install R=Run T=Test V=Verify Py=Python JS=JavaScript
         env=environment var=variable cfg=config db=database api=API
```

Example:
```json
{
  "pn": "MyAPI",
  "pd": "REST API for task management",
  "sp": "RUN THIS FIRST: claude --dangerously-skip-permissions...",
  "ts": {"language": "Py", "framework": "FastAPI"}
}
```

Claude Code automatically decompresses this using the legend header.

---

## Features

- **Multi-language** - Ralph matches your language (Spanish→Spanish, etc.)
- **Visual Inspiration** - Send screenshots/URLs for reference
- **Voice Messages** - Talk to Ralph (transcribed via Groq Whisper)
- **Session Memory** - Conversations persist over days
- **Recipe Storage** - Save PRDs locally at `~/.ralph/recipes/`
- **Fast & Free** - Powered by Groq (no API costs)

---

## Ralph's Personality

- Confused but helpful
- Misspells words ("compooter", "thingy", "inspurashun")
- Calls you "boss"
- Scared of losing his job
- **ONE sharp question per turn**
- 1-2 sentences max

---

## Docker Commands

```bash
# Build
docker build -t teleralph .

# Run
docker run -d --name teleralph --env-file .env --restart unless-stopped teleralph

# View logs
docker logs -f teleralph

# Restart
docker restart teleralph

# Stop
docker stop teleralph

# Update (pull latest code + rebuild)
docker stop teleralph && docker rm teleralph
git pull
docker build -t teleralph .
docker run -d --name teleralph --env-file .env --restart unless-stopped teleralph
```

---

## Project Structure

```
ralphmode.com/
├── ralph_telegram.py    # Main bot (5937 lines)
├── recipe_api.py         # Recipe storage & compression
├── session_manager.py    # Session persistence
├── session_cloud.py      # Cloud sync (future)
├── Dockerfile            # Container config
├── requirements.txt      # Python deps
├── .env.example          # Config template
└── README.md             # This file
```

---

## Troubleshooting

**Bot not responding?**
```bash
docker logs -f teleralph
# Check for errors, missing API keys, or network issues
```

**"Cook sauce" fails?**
- Make sure you answered enough questions
- Try providing more details about your project
- Check Groq API key is valid

**Can't download PRD file?**
- Check Telegram file size limits (50MB for premium)
- File is saved locally in the container at `/app/`

---

## License

MIT

---

## Support

[Buy Me a Coffee](https://buymeacoffee.com/snail3d) ☕

---

*"When I grow up, I want to be a principal or a caterpillar."*
