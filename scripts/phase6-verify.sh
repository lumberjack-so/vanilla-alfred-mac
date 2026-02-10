#!/bin/bash
# Phase 6: Verification
# Tests all components and services

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/lib/common.sh"

log_section "System Verification"

WORKSPACE_DIR="$HOME/clawd"
OPENCLAW_CONFIG_DIR="$HOME/.openclaw"

CHECKS_PASSED=0
CHECKS_FAILED=0

# Helper function to run checks
run_check() {
    local name=$1
    local command=$2
    
    log_step "Checking $name..."
    if eval "$command" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $name"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "  ${RED}✗${NC} $name"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# 1. Core tools
log_section "Core Tools"
run_check "Homebrew" "brew --version"
run_check "Node.js" "node --version"
run_check "Python 3" "python3 --version"
run_check "Git" "git --version"
run_check "Docker" "docker ps"
run_check "OpenClaw" "openclaw --version"
run_check "Claude CLI" "claude --version"

# 2. Services
echo ""
log_section "Services"
run_check "Docker daemon" "docker info"
run_check "Temporal (port 7233)" "nc -z localhost 7233"
run_check "Temporal UI (port 8233)" "nc -z localhost 8233"
run_check "AutoKitteh (port 9980)" "nc -z localhost 9980"
run_check "Twenty CRM (port 3000)" "nc -z localhost 3000"
run_check "Plane PM (port 8080)" "nc -z localhost 8080"
run_check "Uptime Kuma (port 3001)" "nc -z localhost 3001"

# 3. Docker containers
echo ""
log_section "Docker Containers"
run_check "Temporal server" "docker ps | grep -q temporal-temporal"
run_check "Temporal PostgreSQL" "docker ps | grep -q temporal-postgresql"
run_check "Twenty server" "docker ps | grep -q twenty-server"
run_check "Twenty PostgreSQL" "docker ps | grep -q twenty-db"
run_check "Plane web" "docker ps | grep -q plane-app-web"
run_check "Uptime Kuma" "docker ps | grep -q uptime-kuma"

# 4. Configuration files
echo ""
log_section "Configuration Files"
run_check "OpenClaw config" "test -f $OPENCLAW_CONFIG_DIR/openclaw.json"
run_check "SOUL.md" "test -f $WORKSPACE_DIR/SOUL.md"
run_check "AGENTS.md" "test -f $WORKSPACE_DIR/AGENTS.md"
run_check "IDENTITY.md" "test -f $WORKSPACE_DIR/IDENTITY.md"
run_check "HEARTBEAT.md" "test -f $WORKSPACE_DIR/HEARTBEAT.md"
run_check "SECURITY.md" "test -f $WORKSPACE_DIR/SECURITY.md"
run_check "USER.md" "test -f $WORKSPACE_DIR/USER.md"
run_check "TOOLS.md" "test -f $WORKSPACE_DIR/TOOLS.md"
run_check "MEMORY.md" "test -f $WORKSPACE_DIR/MEMORY.md"

# 5. Agents
echo ""
log_section "Agent Configurations"
for agent in alfred kb-curator ops-guardian briefing-butler content-agent coding-agent finance-auditor; do
    run_check "$agent agent" "test -d $OPENCLAW_CONFIG_DIR/agents/$agent/agent"
done

# 6. Scripts
echo ""
log_section "Runtime Scripts"
run_check "infra-health-check.sh" "test -x $WORKSPACE_DIR/scripts/infra-health-check.sh"
run_check "email-processor.py" "test -f $WORKSPACE_DIR/scripts/email-processor.py"
run_check "agentmail-relay.py" "test -f $WORKSPACE_DIR/scripts/agentmail-relay.py"

# 7. Integrations
echo ""
log_section "Integrations"

# AgentMail
if [[ -f "$HOME/.config/agentmail/api_key" ]]; then
    run_check "AgentMail API key" "test -s $HOME/.config/agentmail/api_key"
    run_check "AgentMail relay process" "pgrep -f agentmail-relay.py"
else
    log_warning "AgentMail not configured"
fi

# Google
if command_exists gog; then
    run_check "Google CLI (gog)" "gog --version"
    if gog calendar list >/dev/null 2>&1; then
        run_check "Google OAuth" "gog calendar list"
    else
        log_warning "Google OAuth not authenticated"
    fi
else
    log_warning "Google integration (gog) not installed"
fi

# Tailscale
if command_exists tailscale; then
    run_check "Tailscale CLI" "tailscale --version"
    if tailscale status >/dev/null 2>&1; then
        run_check "Tailscale connection" "tailscale status"
    else
        log_warning "Tailscale not connected"
    fi
else
    log_warning "Tailscale not installed"
fi

# 8. Python packages
echo ""
log_section "Python Packages"
run_check "requests" "python3 -c 'import requests'"
run_check "anthropic" "python3 -c 'import anthropic'"
run_check "beautifulsoup4" "python3 -c 'import bs4'"

# 9. Claude authentication
echo ""
log_section "Claude Authentication"
if claude whoami >/dev/null 2>&1; then
    CLAUDE_USER=$(claude whoami 2>/dev/null | head -1)
    log_success "Claude authenticated as: $CLAUDE_USER"
    ((CHECKS_PASSED++))
else
    log_warning "Claude not authenticated - run 'claude login'"
    ((CHECKS_FAILED++))
fi

# 10. Test OpenClaw
echo ""
log_section "OpenClaw Gateway"

# Start gateway if not running
if ! pgrep -f "openclaw gateway" >/dev/null 2>&1; then
    log_step "Starting OpenClaw gateway..."
    nohup openclaw gateway start > "$WORKSPACE_DIR/logs/gateway.log" 2>&1 &
    sleep 3
fi

run_check "Gateway process" "pgrep -f 'openclaw gateway'"
run_check "Gateway port (18789)" "nc -z localhost 18789"

# Test gateway health
if curl -s http://localhost:18789/health >/dev/null 2>&1; then
    log_success "Gateway responding to health check"
    ((CHECKS_PASSED++))
else
    log_warning "Gateway not responding to health checks"
    ((CHECKS_FAILED++))
fi

# 11. AutoKitteh projects
echo ""
log_section "AutoKitteh Projects"
if [[ -d "$WORKSPACE_DIR/autokitteh-projects" ]]; then
    PROJECT_COUNT=$(find "$WORKSPACE_DIR/autokitteh-projects" -maxdepth 1 -type d | wc -l | xargs)
    PROJECT_COUNT=$((PROJECT_COUNT - 1))  # Exclude parent dir
    log_info "Found $PROJECT_COUNT AutoKitteh project templates"
    ((CHECKS_PASSED++))
else
    log_warning "No AutoKitteh projects found"
    ((CHECKS_FAILED++))
fi

# 12. Vault
echo ""
log_section "Obsidian Vault"
VAULT_DIR="$HOME/alfred/alfred"
if [[ -d "$VAULT_DIR" ]]; then
    # Check ontology folders
    FOLDERS=(person org proj evt learn doc loc acct asset proc content _archive _templates)
    MISSING=0
    for folder in "${FOLDERS[@]}"; do
        if [[ ! -d "$VAULT_DIR/$folder" ]]; then
            ((MISSING++))
        fi
    done
    
    if [[ $MISSING -eq 0 ]]; then
        log_success "Vault structure complete"
        ((CHECKS_PASSED++))
    else
        log_warning "Vault structure incomplete ($MISSING folders missing)"
        ((CHECKS_FAILED++))
    fi
else
    log_warning "Obsidian vault not created"
    ((CHECKS_FAILED++))
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
log_section "Verification Summary"
echo ""
echo -e "${BOLD}Results:${NC}"
echo -e "  ${GREEN}✓ Passed:${NC} $CHECKS_PASSED"
echo -e "  ${RED}✗ Failed:${NC} $CHECKS_FAILED"
echo ""

if [[ $CHECKS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo -e "${BOLD}Your Alfred system is ready!${NC}"
    echo ""
    echo "Start chatting with Alfred:"
    echo -e "  ${BLUE}claude chat${NC}"
    echo ""
    echo "Or use the web interface:"
    echo -e "  ${BLUE}http://localhost:18789${NC}"
    echo ""
    exit 0
else
    echo -e "${YELLOW}${BOLD}⚠ SOME CHECKS FAILED${NC}"
    echo ""
    echo "Review the failures above. Most issues can be fixed by:"
    echo "  1. Restarting Docker: open -a Docker"
    echo "  2. Re-running authentication: claude login, gog auth, etc."
    echo "  3. Checking logs in: $WORKSPACE_DIR/logs/"
    echo ""
    echo "The system may still work, but some features might not be available."
    echo ""
    exit 1
fi
