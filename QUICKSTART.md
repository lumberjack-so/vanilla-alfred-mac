# Quick Start Guide

## Fresh Mac Installation

```bash
# 1. Download and run installer
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/vanilla-alfred-mac/main/install.sh | bash

# Or clone first
git clone https://github.com/YOUR_ORG/vanilla-alfred-mac.git
cd vanilla-alfred-mac
./install.sh
```

## What You Need Ready

1. **Claude Authentication**
   - Have your Anthropic account ready
   - Installer will open browser for auth

2. **API Keys**
   - Brave Search: https://brave.com/search/api/
   - AgentMail: https://agentmail.to (optional)
   - ElevenLabs: https://elevenlabs.io (optional)

3. **Google Account** (optional)
   - For Gmail, Calendar integration

4. **~45 minutes** of time

## Installation Flow

1. **Phase 1 (~10 min):** Homebrew, Docker, Node, Python
2. **Phase 2 (~5 min):** OpenClaw, Claude, agent setup
3. **Phase 3 (~15 min):** Services (Twenty, Plane, Temporal, etc.)
4. **Phase 4 (~5 min):** Integrations (email, Google, webhooks)
5. **Phase 5 (~5 min):** Interactive wizard (API keys, config)
6. **Phase 6 (~2 min):** Verification

## After Installation

### Start Chatting

```bash
# CLI
claude chat

# Or web interface
open http://localhost:18789
```

### Check Services

```bash
# All containers running
docker ps

# Service URLs
open http://localhost:3000  # Twenty CRM
open http://localhost:8080  # Plane PM
open http://localhost:8233  # Temporal UI
open http://localhost:9980  # AutoKitteh
open http://localhost:3001  # Uptime Kuma
```

### First Conversation

Try these:
```
"Hello Alfred, introduce yourself"
"What services are running?"
"Show me my vault structure"
"Set a reminder for tomorrow at 9am"
```

## Customization

### Edit Your Profile
```bash
# Tell Alfred about yourself
vi ~/clawd/USER.md

# Add API keys and notes
vi ~/clawd/TOOLS.md
```

### Create Your Vault
```bash
# Install Obsidian
brew install --cask obsidian

# Open vault
open ~/alfred/alfred
```

### Add Workflows
```bash
cd ~/clawd/autokitteh-projects/
cp -R daily-briefing my-workflow
# Edit workflow files
cd my-workflow
ak deploy .
```

## Troubleshooting

### Docker Not Starting
```bash
# Restart Docker
osascript -e 'quit app "Docker Desktop"'
sleep 5
open -a "Docker Desktop"
```

### Services Not Accessible
```bash
# Check containers
docker ps

# Restart specific service
cd ~/services/temporal && docker compose restart
```

### OpenClaw Issues
```bash
# Check logs
tail -f ~/clawd/logs/gateway.log

# Restart gateway
openclaw gateway restart
```

### Reinstall
```bash
# Stop everything
docker compose down -v  # in each service dir

# Remove and reinstall
rm -rf ~/clawd ~/.openclaw ~/services
./install.sh
```

## Next Steps

1. **Configure channels** - Add Slack/Telegram for messaging
2. **Set up monitoring** - Configure Uptime Kuma alerts
3. **Create entities** - Add people, projects to vault
4. **Schedule workflows** - Set up daily briefings, reminders
5. **Customize persona** - Edit SOUL.md, AGENTS.md to match your style

## Resources

- **Full README:** [README.md](README.md)
- **Security:** [config/SECURITY.md](config/SECURITY.md)
- **OpenClaw Docs:** https://openclaw.sh/docs
- **Temporal Docs:** https://docs.temporal.io
- **Plane Docs:** https://docs.plane.so

## Support

- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **OpenClaw Discord:** https://discord.gg/openclaw

---

**Welcome to Alfred! 🎩**
