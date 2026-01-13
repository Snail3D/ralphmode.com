# Ralph Local - "Cook the Sauce" Builder

> *"I'm a unitard! I'm learnding! Let's cook the sauce!"* - Ralph Wiggum

Ralph Local is a Telegram bot that helps you build software by chatting. Tell Ralph about your project, he asks smart questions, and when ready — **cooks the sauce** (generates a PRD).

---

## How It Works

1. **Chat with Ralph** on Telegram about your project idea
2. Ralph asks sharp questions (one at a time, fast drilling)
3. When ready, click **"🍳 Yes! Cook Sauce!"**
4. Ralph generates a **PRD** (Product Requirements Document)
5. PRD is saved as a "recipe" with compression legend

---

## The PRD Compression Legend

Ralph compresses PRDs to save tokens. The legend:

```
KEYS: pn=project_name pd=project_description sp=starter_prompt ts=tech_stack
      fs=file_structure p=prds n=name d=description t=tasks ti=title
      f=file pr=priority ac=acceptance_criteria pfc=prompt_for_claude
      cmd=commands ccs=claude_code_setup ifc=instructions_for_claude

PHRASES: C=Create I=Install R=Run T=Test V=Verify Py=Python JS=JavaScript
         env=environment var=variable cfg=config db=database api=API
         req=required opt=optional impl=implement dep=dependencies
```

---

## Quick Start

### 1. Create Telegram Bot

Message [@BotFather](https://t.me/BotFather) on Telegram:
```
/newbot
Name: Ralph Local
Username: YourRalphBot
```

Save the token.

### 2. Get Groq API Key (Free)

Go to [console.groq.com](https://console.groq.com) and create a free API key.

### 3. Run Locally

```bash
# Clone and setup
git clone https://github.com/Snail3D/ralphmode.com.git
cd ralphmode.com
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your bot token and Groq API key

# Run
python ralph_telegram.py
```

### 4. Run with Docker

```bash
# Build
docker build -t ralph-local .

# Run
docker run -d \
  --name ralph-telegram-bot \
  --env-file .env \
  ralph-local
```

---

## Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
GROQ_API_KEY=your_groq_api_key

# Optional
TENOR_API_KEY=your_tenor_api_key  # For GIFs
RECIPE_API_BASE=https://ralphmode.com/api/recipes  # Cloud sync (future)
```

---

## Files

| File | Purpose |
|------|---------|
| `ralph_telegram.py` | Main Telegram bot (5937 lines) |
| `recipe_api.py` | Recipe storage & compression |
| `session_manager.py` | Session persistence |
| `session_cloud.py` | Cloud sync (future) |

---

## Recipe Storage

Recipes (PRDs) are saved locally at:
```
~/.ralph/recipes/
```

Each recipe includes:
- Project name & description
- Tech stack
- File structure
- PRD tasks with acceptance criteria
- Model quality tier

---

## Ralph's Personality

- Confused but helpful
- Misspells words ("compooter", "thingy")
- Calls you "boss"
- Scared of losing job
- ONE sharp question per turn
- 1-2 sentences max

---

## License

MIT

---

*"When I grow up, I want to be a principal or a caterpillar."*
