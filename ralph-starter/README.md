<div align="left">
<img src="https://api.qrserver.com/v1/create-qr-code/?size=80x80&data=https://github.com/Snail3D/ralphmode.com" alt="Scan to GitHub" />
</div>

# 🍩 Ralph Mode

> *"I'm a building helper!"* - Ralph Wiggum

**Your AI Dev Team, Live on Stage.** Drop code. Speak commands. Watch the magic happen.

---

## 🚀 Start Building in 60 Seconds

```bash
git clone https://github.com/Snail3D/ralphmode.com.git
cd ralphmode.com/ralph-starter
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
python ralph_bot.py
```

| You'll Need | Where to Get It |
|-------------|-----------------|
| 🤖 Telegram Bot Token | [Talk to BotFather](https://t.me/BotFather) |
| ⚡ Groq API Key | [console.groq.com](https://console.groq.com) *(free!)* |
| 🆔 Your Telegram ID | [Ask userinfobot](https://t.me/userinfobot) |

---

## 🎭 Meet the Team

| | Character | What They Do |
|---|-----------|--------------|
| 🧠 | **Ralph** *(Boss)* | *"Me fail English? That's unpossible!"* Lovably confused. Genuinely innocent. Runs the show. |
| 💼 | **Stool** *(Senior Dev)* | Gets things done. Slightly cynical. The one who actually knows stuff. |
| 🌟 | **Gomer** *(Junior Dev)* | Eager beaver! Asks good questions. Learning every day. |
| 🔍 | **Mona** *(QA Lead)* | Catches every edge case. Nothing escapes her. |
| 🔧 | **Gus** *(DevOps)* | *"The server room is my happy place."* Infrastructure wizard. |
| 👔 | **Mr. Worms** *(You!)* | The CEO. Your voice becomes theatrical dialogue. You're the boss. |

**Specialists on Call:** Frinky (UI), Willie (DevOps), Doc (Debugging)

---

## ✨ What Makes It Special

| Feature | The Ralph Way |
|---------|---------------|
| 🎤 **Voice-First** | Speak, don't type. Your tone shapes the scene. |
| 🎬 **Theater Mode** | Every response is part of the story. Dramatic pauses included. |
| 🤖 **Auto-Building** | Drop a zip, workers build it. You supervise (or nap). |
| 🔍 **Discovery Mode** | Ralph asks questions to clarify vague tasks. Better requirements = better code. |
| 🧠 **Intent Detection** | Understands what you mean, not just what you say. Vague input? Ralph asks for clarity. |
| 🔌 **Model Abstraction** | Switch AI providers without changing code. Mix and match! Ralph uses one model, workers use another. |
| 💾 **Model Registry** | Persistent model configs with metadata. Models survive restarts and track usage stats. |
| 💡 **Smart Recommendations** | Ask Ralph which AI model to use. Get personalized suggestions based on your use case, budget, and hardware. |
| 🔍 **Local Model Discovery** | Auto-detects Ollama, LM Studio, and llama.cpp servers. Zero-config local AI! |
| ✅ **Validation Cache** | Remembers which models passed tests. Skip re-testing! Smart model selection based on validation history. |
| 🧪 **Test Prompt Library** | 12 role-specific validation prompts. Test Ralph's personality, worker coding skills, builder planning, and design decisions. |
| 🏃 **Test Runner** | Execute validation tests against any model. Score results, measure latency, record to registry. CLI + integration ready! |
| 🎯 **Character Detection** | Smart validation checks if models truly "get" each character. Ralph friendly? Worker professional? Tests personality traits, not just responses! |
| 🔌 **Connection Testing** | Quick reachability checks before running full tests. Diagnose config issues fast! Two-stage validation: availability + minimal inference test. |
| 🔒 **Broadcast-Safe** | Secrets filtered. Swears become *\*jaw clenches\**. Stream it live! |
| 👥 **Multi-User** | Owner, Power Users, Viewers - everyone has a role. |
| 🛡️ **Enterprise Security** | OWASP Top 10 covered. We take this seriously. |

---

## 🎮 Commands

| Command | What Happens |
|---------|--------------|
| `/start` | *"Hi, I'm Ralph!"* - Begin a new adventure |
| `/setup` | Guided onboarding. Ralph holds your hand. |
| `/status` | *"The project is... um... this way!"* - Session status |
| `/mystatus` | Check your permissions and quality score |
| `/report` | Get a detailed work summary |
| `/lookaround` | See who's in the office right now |
| `/whos_here` | Alternative way to check who's present |
| `/setmodel` | Switch AI models on the fly. No restart needed! |
| `/retest` | Re-validate AI models. Check if they still work! |
| `/reorganize` | Re-cluster PRD tasks for optimal order |
| `/feedback` | Tell us what to build next *(paid users)* |
| `/theme` | Change visual theme |
| `/character` | Select character avatar |
| `/templates` | Browse project templates |
| `/setlocation` | Set your location for time-aware scenes |
| `/version` | Check current version |
| `/analytics` | View usage analytics |
| `/auditlog` | Security audit log *(owner only)* |
| `/hacktest` | Run security tests *(owner only)* |
| `/password` | Security password operations *(owner only)* |
| `/goodnews` | Celebrate milestones and victories |
| `/reconfigure` | Reconfigure bot settings *(owner only)* |

---

## 🧠 AI Providers

> *"I pick the good ones!"* - Ralph

**NEW:** Model Abstraction Layer lets you mix and match AI providers! Ralph uses Groq, workers use Anthropic, Frinky uses GLM - all at once! 🎭

| Provider | Status | Why |
|----------|--------|-----|
| 🏠 **Local AI (Ollama)** | ✅ **Preferred** | Free. Private. Your data stays home. |
| ⚡ **Groq** | ✅ Allowed | Fast! Free tier! Not Grok! *(Now pluggable!)* |
| 🤖 **Anthropic** | ✅ Allowed | Claude is our friend. *(Builder role ready!)* |
| 🎨 **GLM (Z.AI)** | ✅ **Design Agent** | Frinky's brain! All aesthetic decisions. |
| ❌ Grok (xAI) | **BANNED** | *"That's a bad word!"* |
| ❌ OpenAI | **BANNED** | *"Stranger danger!"* |

---

## 📊 Project Status

```
████████████████████░░░░░░░░  60% Complete

541 Tasks Total | 325 Done | 216 To Go
```

Building autonomously. Ralph never sleeps. *(He tried once. It was unpossible.)*

---

## 📚 Learn More

| 📖 | Link |
|----|------|
| 🎭 [Character Guide](docs/CHARACTERS.md) | Deep dive into personalities |
| 🔧 [Configuration](docs/CONFIG.md) | All the knobs and dials |
| 🛡️ [Security](docs/SECURITY.md) | How we keep things safe |
| 🎨 [Customization](docs/CUSTOMIZE.md) | Make it yours |

---

## 💬 Get Help

| | |
|---|---|
| 🐛 Found a bug? | [Open an Issue](https://github.com/Snail3D/ralphmode.com/issues) |
| 💬 Want to chat? | [@RalphModeBot](https://t.me/RalphModeBot) |
| 💡 Have an idea? | Use `/feedback` in the bot! |

---

<div align="center">

**Built with 🍩 by the Ralph Mode Team**

*"When I grow up, I want to be a principal or a caterpillar."*

![Ralph](https://media.giphy.com/media/3orif3j4dRfClbz18k/giphy.gif)

</div>
