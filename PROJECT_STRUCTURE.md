# Vanilla Alfred Mac - Project Structure

## Complete File Tree

```
vanilla-alfred-mac/
├── README.md                          # Main documentation
├── QUICKSTART.md                      # Fast start guide
├── PROJECT_STRUCTURE.md               # This file
├── install.sh                         # Main installer (executable)
│
├── scripts/                           # Installation phases
│   ├── phase1-prerequisites.sh        # Homebrew, Docker, Node, Python, Tailscale
│   ├── phase2-openclaw.sh             # OpenClaw + Claude setup
│   ├── phase3-services.sh             # Deploy all Docker services
│   ├── phase4-integrations.sh         # AgentMail, Google, Tailscale funnel
│   ├── phase5-wizard.sh               # Interactive configuration wizard
│   ├── phase6-verify.sh               # System verification tests
│   └── lib/
│       └── common.sh                  # Shared bash functions
│
├── config/                            # Configuration templates
│   ├── openclaw.template.json         # OpenClaw config with placeholders
│   ├── SOUL.md                        # Alfred's persona (generic)
│   ├── AGENTS.md                      # Framework & protocols (sanitized)
│   ├── IDENTITY.md                    # Identity template
│   ├── HEARTBEAT.md                   # Heartbeat task list (generic)
│   ├── SECURITY.md                    # Security rules
│   ├── MEMORY.md                      # Empty starter memory
│   ├── USER.md.template               # User profile template
│   └── TOOLS.md.template              # Local notes template
│
├── agents/                            # Subagent configurations
│   ├── alfred/agent/AGENTS.md         # Main orchestrator
│   ├── kb-curator/agent/AGENTS.md     # Vault maintenance
│   ├── ops-guardian/agent/AGENTS.md   # Infrastructure health
│   ├── briefing-butler/agent/AGENTS.md# Daily briefings
│   ├── content-agent/agent/AGENTS.md  # Content creation
│   ├── coding-agent/agent/AGENTS.md   # Development work
│   └── finance-auditor/agent/AGENTS.md# Financial tracking
│
├── skills/                            # Portable skill definitions
│   ├── alfred-kb/SKILL.md             # Knowledge base management
│   ├── remind-me/SKILL.md             # Reminders via AutoKitteh
│   ├── email-handling/SKILL.md        # AgentMail integration
│   ├── daily-briefing/SKILL.md        # Briefing generation
│   └── project-manager/SKILL.md       # Project workflows
│
├── scripts-runtime/                   # Deployed runtime scripts
│   ├── infra-health-check.sh          # System health checks
│   ├── email-processor.py             # Email authorization pipeline
│   ├── backlog-handler.py             # Plane backlog processor
│   ├── agentmail-relay.py             # Webhook relay (port 18790)
│   ├── find-thin-entities.sh          # Vault entity scanner
│   └── vault-health.sh                # Vault statistics
│
├── services/                          # Docker service configs
│   ├── twenty/
│   │   ├── docker-compose.yml         # (copied from Twenty repo)
│   │   └── .env.template              # Environment config template
│   ├── plane/
│   │   └── plane.env.template         # Plane environment config
│   ├── temporal/
│   │   └── docker-compose.yml         # Temporal + PostgreSQL + UI + admin-tools
│   └── uptime-kuma/
│       └── docker-compose.yml         # (created by installer)
│
├── vault-template/                    # Obsidian vault structure
│   ├── person/.gitkeep                # People entities
│   ├── org/.gitkeep                   # Organizations
│   ├── proj/.gitkeep                  # Projects
│   ├── evt/.gitkeep                   # Events
│   ├── learn/.gitkeep                 # Learning resources
│   ├── doc/.gitkeep                   # Documents
│   ├── loc/.gitkeep                   # Locations
│   ├── acct/.gitkeep                  # Accounts
│   ├── asset/.gitkeep                 # Assets
│   ├── proc/.gitkeep                  # Procedures
│   ├── content/.gitkeep               # Published content
│   ├── _archive/.gitkeep              # Archived entities
│   └── _templates/                    # Entity templates
│       ├── person.md
│       ├── organization.md
│       ├── project.md
│       ├── event.md
│       └── learning.md
│
├── temporal-workflows/                # Temporal Python SDK workflows
│   ├── config.py                      # Configuration (with placeholders)
│   ├── activities.py                  # Shared activities
│   ├── worker.py                      # Worker process
│   ├── schedules.py                   # Schedule registration
│   ├── requirements.txt               # Python dependencies
│   ├── setup-config.sh                # Config replacement script
│   └── workflows/                     # Workflow definitions
│       ├── __init__.py
│       ├── daily_briefing.py
│       ├── weekly_goals.py
│       ├── integration_health.py
│       ├── vault_maintenance.py
│       ├── content_publishing.py
│       ├── content_weekly.py
│       ├── plane_polling.py
│       └── backlog_handler.py
│
├── launchd/                           # macOS service plists
│   ├── com.openclaw.gateway.plist     # OpenClaw gateway
│   └── com.alfred.temporal-worker.plist # Temporal worker
│   ├── plane-polling/
│   └── (additional templates)
│
└── launchd/                           # Auto-start on boot
    └── com.openclaw.gateway.plist     # OpenClaw gateway LaunchAgent
```

## Key Files by Purpose

### Installation
- `install.sh` - Main entry point
- `scripts/phase*.sh` - Installation phases
- `scripts/lib/common.sh` - Shared functions

### Configuration
- `config/openclaw.template.json` - OpenClaw config
- `config/SOUL.md` - Butler persona
- `config/AGENTS.md` - Framework protocols
- `config/*.template` - User-specific templates

### Agents
- All in `agents/*/agent/AGENTS.md`
- Define role, capabilities, responsibilities
- Reference skills for implementation

### Skills
- All in `skills/*/SKILL.md`
- Define HOW to do specific tasks
- Portable, no personal data

### Services
- Docker Compose files for each service
- Environment templates (no real secrets)
- Deployed to `~/services/` on target system

### Vault
- Empty structure with correct ontology
- Entity templates in `_templates/`
- Deployed to `~/alfred/alfred/` on target

### Workflows
- Temporal Python SDK workflows
- Activities, workers, and schedules
- Deployed to `~/clawd/temporal-workflows/`

### Runtime Scripts
- Copied to `~/clawd/scripts/` on target
- Executable (.sh, .py)
- Used by agents and workflows

## Deployment Locations

After installation, files are deployed to:

| Source | Target Location |
|--------|-----------------|
| `config/*.md` | `~/clawd/` |
| `agents/*` | `~/.openclaw/agents/` |
| `skills/*` | `~/clawd/skills/` |
| `scripts-runtime/*` | `~/clawd/scripts/` |
| `services/*` | `~/services/` |
| `vault-template/*` | `~/alfred/alfred/` |
| `temporal-workflows/*` | `~/clawd/temporal-workflows/` |
| `launchd/*` | `~/Library/LaunchAgents/` |
| `config/openclaw.template.json` | `~/.openclaw/openclaw.json` |

## Verification Checklist

After installation, verify:
- [ ] All scripts are executable
- [ ] No personal data in templates
- [ ] All placeholders use {{VARIABLE}} format
- [ ] Docker Compose files work standalone
- [ ] Agent AGENTS.md files are complete
- [ ] Skills have clear instructions
- [ ] Vault structure matches ontology
- [ ] AutoKitteh workflows are deployable

## Customization Points

Users customize:
1. `USER.md` - Personal profile
2. `TOOLS.md` - API keys, credentials
3. `authorization.json` - Authorized email addresses
4. `.env` files - Service-specific secrets
5. Agent AGENTS.md files - Modify behavior
6. Skills - Add new skills or modify existing

## No Personal Data

This repository must NOT contain:
- Real API keys
- Passwords or secrets
- Personal names, emails, phone numbers
- Addresses or locations
- Financial data
- Health information
- Private messages or content

All sensitive data uses `{{PLACEHOLDERS}}` or is collected via wizard.

## Testing

Test on a fresh macOS install:
1. Clone repo
2. Run `./install.sh`
3. Follow prompts
4. Verify all phases complete
5. Test basic Alfred interactions
6. Check all services are accessible

## Support Matrix

| OS | Arch | Status |
|----|------|--------|
| macOS 13+ | ARM64 (M1/M2/M3/M4) | ✓ Supported |
| macOS 13+ | x86_64 (Intel) | ⚠️ Untested |
| macOS 12- | Any | ✗ Unsupported |
| Linux | Any | ✗ Wrong installer |
| Windows | Any | ✗ Wrong installer |

## License

MIT License (see LICENSE file)

---

**Repository:** https://github.com/YOUR_ORG/vanilla-alfred-mac
**Issues:** https://github.com/YOUR_ORG/vanilla-alfred-mac/issues
**Docs:** See README.md and QUICKSTART.md
