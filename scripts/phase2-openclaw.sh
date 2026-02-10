#!/bin/bash
# Phase 2: OpenClaw & Claude
# Installs OpenClaw, sets up Claude CLI, creates initial config

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Ensure Homebrew and its packages are in PATH
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

log_section "Installing OpenClaw & Claude"

WORKSPACE_DIR="$HOME/clawd"
OPENCLAW_CONFIG_DIR="$HOME/.openclaw"

# 1. Install OpenClaw
if command_exists openclaw; then
    log_success "OpenClaw already installed ($(openclaw --version))"
else
    log_step "Installing OpenClaw..."
    
    # Install via npm
    npm install -g openclaw
    
    log_success "OpenClaw installed"
fi

# 2. Install Claude CLI
if command_exists claude; then
    log_success "Claude CLI already installed"
else
    log_step "Installing Claude CLI..."
    npm install -g @anthropic-ai/claude-cli
    log_success "Claude CLI installed"
fi

# 3. Claude Login
log_step "Setting up Claude authentication..."
echo ""
log_warning "You'll need to authenticate with Claude"
log_info "Run: claude login"
log_info "This will open a browser window to authenticate"
echo ""

if ! is_automated; then
    read -p "Press Enter when ready to authenticate Claude..." -r
    claude login || true
    
    # Verify login
    if claude whoami > /dev/null 2>&1; then
        log_success "Claude authentication successful"
    else
        log_warning "Claude authentication may have failed"
        log_info "You can run 'claude login' again later"
    fi
else
    log_warning "Automated mode - skipping Claude login"
    log_info "Run 'claude login' manually after installation"
fi

# 4. Create OpenClaw config directory
ensure_dir "$OPENCLAW_CONFIG_DIR"
ensure_dir "$OPENCLAW_CONFIG_DIR/agents"
ensure_dir "$OPENCLAW_CONFIG_DIR/hooks"

# 5. Copy config template
log_step "Creating OpenClaw configuration..."
TEMPLATE_FILE="$REPO_DIR/config/openclaw.template.json"
CONFIG_FILE="$OPENCLAW_CONFIG_DIR/openclaw.json"

if [[ -f "$CONFIG_FILE" ]]; then
    backup_file "$CONFIG_FILE"
fi

cp "$TEMPLATE_FILE" "$CONFIG_FILE"

# 6. Copy workspace files
log_step "Setting up workspace files..."

# Copy core framework files
cp "$REPO_DIR/config/SOUL.md" "$WORKSPACE_DIR/"
cp "$REPO_DIR/config/AGENTS.md" "$WORKSPACE_DIR/"
cp "$REPO_DIR/config/IDENTITY.md" "$WORKSPACE_DIR/"
cp "$REPO_DIR/config/HEARTBEAT.md" "$WORKSPACE_DIR/"
cp "$REPO_DIR/config/SECURITY.md" "$WORKSPACE_DIR/"
cp "$REPO_DIR/config/MEMORY.md" "$WORKSPACE_DIR/"

# USER.md and TOOLS.md are populated by the wizard
cp "$REPO_DIR/config/USER.md.template" "$WORKSPACE_DIR/USER.md.template"
cp "$REPO_DIR/config/TOOLS.md.template" "$WORKSPACE_DIR/TOOLS.md.template"

log_success "Workspace files copied"

# 7. Copy agent configurations
log_step "Setting up agent configurations..."
for agent_dir in "$REPO_DIR/agents/"*/; do
    if [[ ! -d "$agent_dir" ]]; then
        continue
    fi
    
    agent_name=$(basename "$agent_dir")
    target_dir="$OPENCLAW_CONFIG_DIR/agents/$agent_name"
    
    ensure_dir "$target_dir"
    
    if [[ -d "$agent_dir/agent" ]]; then
        cp -R "$agent_dir/agent" "$target_dir/"
    fi
done

log_success "Agent configurations copied"

# 8. Copy skills
log_step "Setting up skills..."
for skill_dir in "$REPO_DIR/skills/"*/; do
    if [[ ! -d "$skill_dir" ]]; then
        continue
    fi
    
    skill_name=$(basename "$skill_dir")
    target_dir="$WORKSPACE_DIR/skills/$skill_name"
    
    ensure_dir "$target_dir"
    cp -R "$skill_dir"/* "$target_dir/"
done

log_success "Skills copied"

# 9. Copy runtime scripts
log_step "Installing runtime scripts..."
ensure_dir "$WORKSPACE_DIR/scripts"
cp -R "$REPO_DIR/scripts-runtime/"* "$WORKSPACE_DIR/scripts/"
chmod +x "$WORKSPACE_DIR/scripts/"*.{sh,py} 2>/dev/null || true

log_success "Runtime scripts installed"

# 10. Create memory structure
ensure_dir "$WORKSPACE_DIR/memory"
touch "$WORKSPACE_DIR/memory/$(date +%Y-%m-%d).md"
cat > "$WORKSPACE_DIR/memory/$(date +%Y-%m-%d).md" <<EOF
# $(date +%Y-%m-%d) - Installation Day

## Initial Setup

Vanilla Alfred Mac installer completed successfully.

System installed:
- OpenClaw $(openclaw --version 2>/dev/null || echo "unknown")
- Claude CLI
- All services configured
- Agent framework deployed

Status: Ready for first interaction
EOF

log_success "Memory structure created"

# 11. Set permissions
chmod 700 "$OPENCLAW_CONFIG_DIR"
chmod 600 "$CONFIG_FILE" 2>/dev/null || true

# Summary
echo ""
log_section "OpenClaw & Claude Summary"
log_info "OpenClaw: $(openclaw --version 2>/dev/null || echo 'installed')"
log_info "Claude CLI: $(claude --version 2>/dev/null || echo 'installed')"
log_info "Config: $CONFIG_FILE"
log_info "Workspace: $WORKSPACE_DIR"
log_info "Agents: $OPENCLAW_CONFIG_DIR/agents/"

echo ""
log_success "Phase 2 complete - OpenClaw & Claude configured"
