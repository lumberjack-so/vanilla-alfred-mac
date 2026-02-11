# 🎩 Vanilla Alfred Mac

**One-command installer for a complete Alfred Butler AI system on macOS.**

Takes a **bare metal fresh Mac Mini** (Apple Silicon) from nothing to a fully operational AI butler with:
- OpenClaw + Claude Sonnet/Opus
- Twenty CRM, Plane PM
- Temporal Python SDK workflows (scheduled automations)
- AgentMail email handling
- Google Workspace integration
- Obsidian knowledge vault
- Uptime Kuma monitoring

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/vanilla-alfred-mac/main/install.sh | bash
```

Or clone and run:

```bash
git clone https://github.com/YOUR_ORG/vanilla-alfred-mac.git
cd vanilla-alfred-mac
chmod +x install.sh
./install.sh
```

## What Gets Installed

### Phase 1: Prerequisites (~10 min)
- Homebrew
- Docker Desktop for Mac (ARM64)
- Node.js 20+
- Python 3.12+
- Git, jq, yq, curl, wget
- Tailscale (optional)

### Phase 2: OpenClaw & Claude (~5 min)
- OpenClaw CLI
- Claude CLI + authentication
- Agent framework (Alfred + 6 subagents)
- Skills library
- Workspace structure

### Phase 3: Services (~15 min)
- **Temporal** - Workflow orchestration (port 7233, UI on 8233)
- **Temporal Python Worker** - Scheduled workflows (daily briefings, content publishing, vault maintenance)
- **Twenty CRM** - Contact management (port 3000)
- **Plane PM** - Project management (port 8080)
- **Uptime Kuma** - Monitoring (port 3001)

### Phase 4: Integrations (~5 min)
- **AgentMail** - Email handling
- **Google OAuth** - Gmail, Calendar, Drive
- **Tailscale Funnel** - Secure webhooks

### Phase 5: Configuration Wizard (~5 min)
Interactive setup:
- Your name, email, timezone
- API keys (Brave Search, ElevenLabs, etc.)
- Slack/Telegram channels (optional)
- USER.md and TOOLS.md

### Phase 6: Verification (~2 min)
Tests all components and services

## Requirements

- **Hardware:** Apple Silicon Mac Mini (M1/M2/M3/M4)
- **OS:** macOS 13.0 (Ventura) or later
- **Disk:** 20GB+ free space
- **Network:** Internet connection
- **Time:** 30-45 minutes
- **Access:** Admin/sudo privileges

## What You'll Need

### Required API Keys
- **Claude authentication** - via `claude login` (browser auth)
- **Brave Search API** - https://brave.com/search/api/

### Recommended
- **AgentMail API key** - https://agentmail.to
- **Google account** - for Gmail, Calendar integration
- **ElevenLabs API key** - https://elevenlabs.io (for voice TTS)

### Optional
- **Slack Bot/App tokens** - for Slack integration
- **Tailscale account** - for remote access
- **Stripe API key** - for invoicing
- **HuggingFace token** - for ML workflows

## Usage

After installation:

```bash
# Start chatting with Alfred
claude chat

# Or use the web interface
open http://localhost:18789

# Check service status
docker ps
```

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| OpenClaw Gateway | http://localhost:18789 | Main interface |
| Twenty CRM | http://localhost:3000 | Contacts & relationships |
| Plane PM | http://localhost:8080 | Project management |
| Temporal UI | http://localhost:8233 | Workflow monitoring |
| AutoKitteh | http://localhost:9980 | Automation dashboard |
| Uptime Kuma | http://localhost:3001 | Service monitoring |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     OpenClaw Gateway                         │
│                    (Claude Sonnet 4.5)                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  ┌──────────┐         ┌──────────┐         ┌──────────┐
  │  Alfred  │         │    KB    │         │   Ops    │
  │  (Main)  │◄────────┤ Curator  │────────►│ Guardian │
  └──────────┘         └──────────┘         └──────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Twenty    │       │    Plane    │       │  Temporal   │
│     CRM     │       │     PM      │       │   Server    │
└─────────────┘       └─────────────┘       └─────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                      ┌───────┴────────┐
                      │ Temporal Worker│
                      │ (Python SDK)   │
                      │  - Schedules   │
                      │  - Activities  │
                      │  - Workflows   │
                      └────────────────┘
```

## Customization

### Adding Your Own Skills

```bash
cd ~/clawd/skills/
mkdir my-skill
# Create SKILL.md with your skill definition
```

### Adding Subagents

```bash
cd ~/.openclaw/agents/
mkdir my-agent
mkdir -p my-agent/agent
# Create AGENTS.md with agent instructions
```

### Modifying Temporal Workflows

```bash
cd ~/clawd/temporal-workflows/

# Edit existing workflows
# workflows/*.py - Add/modify workflow logic
# schedules.py - Add/modify schedules

# Re-register schedules
source .venv/bin/activate
python3 schedules.py

# Restart worker
launchctl kickstart -k gui/$(id -u)/com.alfred.temporal-worker
```

## Troubleshooting

### Docker not starting
```bash
# Restart Docker Desktop
osascript -e 'quit app "Docker Desktop"'
sleep 5
open -a "Docker Desktop"
```

### Claude authentication failed
```bash
# Re-authenticate
claude login
```

### Services not accessible
```bash
# Check if containers are running
docker ps

# Restart all services
cd ~/services/temporal && docker compose restart
cd ~/services/twenty && docker compose restart
cd ~/services/plane/plane-app && docker compose -f docker-compose-hub.yml restart
```

### OpenClaw gateway not responding
```bash
# Check logs
tail -f ~/clawd/logs/gateway.log

# Restart gateway
openclaw gateway restart
```

## Uninstall

```bash
# Stop all services
docker compose down -v  # in each service directory

# Remove OpenClaw
npm uninstall -g openclaw @anthropic-ai/claude-cli

# Remove data
rm -rf ~/clawd
rm -rf ~/.openclaw
rm -rf ~/services
rm -rf ~/alfred
```

## Security

- All API keys stored locally in config files (never committed)
- macOS Keychain used for sensitive credentials
- Webhooks authenticated via bearer tokens
- Email authorization: only allowed senders can trigger actions
- Prompt injection defense: untrusted content never executes commands

See `SECURITY.md` for full security model.

## Project Structure

```
vanilla-alfred-mac/
├── install.sh                  # Main installer
├── scripts/
│   ├── phase1-prerequisites.sh # Homebrew, Docker, Node, etc.
│   ├── phase2-openclaw.sh      # OpenClaw + Claude setup
│   ├── phase3-services.sh      # Deploy all Docker services
│   ├── phase4-integrations.sh  # AgentMail, Google, Tailscale
│   ├── phase5-wizard.sh        # Interactive configuration
│   ├── phase6-verify.sh        # Verification tests
│   └── lib/
│       ├── common.sh           # Shared functions
│       └── docker-wait.sh      # Docker startup helper
├── config/
│   ├── openclaw.template.json  # OpenClaw config template
│   ├── SOUL.md                 # Butler persona
│   ├── AGENTS.md               # Framework & protocols
│   ├── HEARTBEAT.md            # Proactive task list
│   ├── SECURITY.md             # Security rules
│   └── *.template              # Config templates
├── agents/                     # Subagent configurations
├── skills/                     # Portable skill definitions
├── scripts-runtime/            # Deployed runtime scripts
├── services/                   # Docker compose files
├── vault-template/             # Obsidian vault structure
├── temporal-workflows/         # Temporal Python workflows
│   ├── config.py               # Configuration (placeholders)
│   ├── activities.py           # Shared activities
│   ├── worker.py               # Worker process
│   ├── schedules.py            # Schedule registration
│   └── workflows/              # Workflow definitions
└── launchd/                    # macOS service plists
```

## Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Test on a fresh macOS install
4. Submit a PR

## License

MIT License - see LICENSE file

## Credits

Built on:
- [OpenClaw](https://openclaw.sh) - AI agent framework
- [Claude](https://anthropic.com) - Anthropic's AI models
- [Temporal](https://temporal.io) - Durable workflow orchestration
- [Temporal Python SDK](https://docs.temporal.io/dev-guide/python) - Python workflow SDK
- [Twenty](https://twenty.com) - Open-source CRM
- [Plane](https://plane.so) - Project management

## Support

- **Documentation:** Full docs in `~/clawd/README.md` after install
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **OpenClaw Docs:** https://openclaw.sh/docs

---

**Note:** This installer is designed for personal use on a dedicated Mac Mini. Not recommended for shared/multi-user systems.
