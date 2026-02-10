#!/bin/bash
# Vanilla Alfred Mac Installer
# One-command install: takes a bare metal Mac Mini to a fully running Alfred butler system
# Target: macOS (Apple Silicon M-series)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/vanilla-alfred-mac/main/install.sh | bash
#   OR
#   ./install.sh

set -euo pipefail

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$SCRIPT_DIR"

# Source common functions
source "$SCRIPT_DIR/scripts/lib/common.sh"

# Installation phases
PHASES=(
    "phase1-prerequisites"
    "phase2-openclaw"
    "phase3-services"
    "phase4-integrations"
    "phase5-wizard"
    "phase6-verify"
)

# Banner
print_banner() {
    echo ""
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}    🎩 VANILLA ALFRED MAC INSTALLER${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}This installer will:${NC}"
    echo "  • Install all prerequisites (Homebrew, Docker Desktop, Node.js, etc.)"
    echo "  • Install and configure OpenClaw + Claude CLI"
    echo "  • Deploy all services (Twenty CRM, Plane PM, Temporal, AutoKitteh)"
    echo "  • Set up integrations (AgentMail, Google, Tailscale)"
    echo "  • Configure your Alfred butler persona and workspace"
    echo "  • Verify everything works"
    echo ""
    echo -e "${BOLD}Target:${NC} Fresh macOS (Apple Silicon M-series Mac Mini)"
    echo -e "${BOLD}Time:${NC} ~30-45 minutes (depending on download speeds)"
    echo ""
    echo -e "${YELLOW}⚠️  You will be prompted for:${NC}"
    echo "  • Your sudo password (for system installations)"
    echo "  • API keys and credentials (AgentMail, Google, etc.)"
    echo "  • Basic configuration (name, email, timezone)"
    echo ""
}

# Pre-flight checks
preflight_checks() {
    log_section "Pre-flight Checks"
    
    # Check macOS
    if [[ "$(uname)" != "Darwin" ]]; then
        log_error "This installer only works on macOS"
        exit 1
    fi
    
    # Check Apple Silicon
    if [[ "$(uname -m)" != "arm64" ]]; then
        log_error "This installer requires Apple Silicon (M-series) Mac"
        log_info "Detected architecture: $(uname -m)"
        exit 1
    fi
    
    # Check macOS version (minimum 13.0 Ventura)
    macos_version=$(sw_vers -productVersion | cut -d. -f1)
    if [[ $macos_version -lt 13 ]]; then
        log_error "macOS 13.0 (Ventura) or later required"
        log_info "Current version: $(sw_vers -productVersion)"
        exit 1
    fi
    
    # Check disk space (minimum 20GB free)
    available_gb=$(df -g / | tail -1 | awk '{print $4}')
    if [[ $available_gb -lt 20 ]]; then
        log_error "At least 20GB free disk space required"
        log_info "Available: ${available_gb}GB"
        exit 1
    fi
    
    log_success "Pre-flight checks passed"
    echo ""
}

# Resume capability
STATE_FILE="$HOME/.vanilla-alfred-install-state.json"

save_state() {
    local phase=$1
    cat > "$STATE_FILE" <<EOF
{
  "lastCompletedPhase": "$phase",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "version": "1.0.0"
}
EOF
}

get_last_phase() {
    if [[ -f "$STATE_FILE" ]]; then
        grep -o '"lastCompletedPhase": "[^"]*"' "$STATE_FILE" | cut -d'"' -f4
    else
        echo ""
    fi
}

# Main installation flow
main() {
    print_banner
    
    # Check if resuming
    last_phase=$(get_last_phase)
    start_index=0
    
    if [[ -n "$last_phase" ]]; then
        log_warning "Found previous installation state"
        log_info "Last completed phase: $last_phase"
        echo ""
        read -p "Resume from next phase? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for i in "${!PHASES[@]}"; do
                if [[ "${PHASES[$i]}" == "$last_phase" ]]; then
                    start_index=$((i + 1))
                    break
                fi
            done
            log_info "Resuming from phase $((start_index + 1))"
        else
            rm -f "$STATE_FILE"
            log_info "Starting fresh installation"
        fi
        echo ""
    fi
    
    preflight_checks
    
    # Run phases
    for i in $(seq $start_index $((${#PHASES[@]} - 1))); do
        phase="${PHASES[$i]}"
        phase_num=$((i + 1))
        
        log_section "Phase $phase_num/${#PHASES[@]}: ${phase#phase?-}"
        
        if bash "$SCRIPT_DIR/scripts/$phase.sh"; then
            save_state "$phase"
            log_success "Phase $phase_num complete"
            echo ""
        else
            log_error "Phase $phase_num failed"
            log_info "To resume, run this script again"
            log_info "State saved to: $STATE_FILE"
            exit 1
        fi
    done
    
    # Success!
    echo ""
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}    ✓ ALFRED IS READY TO SERVE${NC}"
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Your Alfred butler system is now running!${NC}"
    echo ""
    echo -e "${BOLD}What's next:${NC}"
    echo "  1. Open a new terminal and run: ${BLUE}claude chat${NC}"
    echo "  2. Say hello to Alfred!"
    echo "  3. Check the dashboard: ${BLUE}http://localhost:18789${NC}"
    echo ""
    echo -e "${BOLD}Services running:${NC}"
    echo "  • OpenClaw Gateway: http://localhost:18789"
    echo "  • Twenty CRM: http://localhost:3000"
    echo "  • Plane PM: http://localhost:8080"
    echo "  • Temporal UI: http://localhost:8233"
    echo "  • AutoKitteh: http://localhost:9980"
    echo "  • Uptime Kuma: http://localhost:3001"
    echo ""
    echo -e "${BOLD}Documentation:${NC}"
    echo "  • Workspace: ~/clawd/"
    echo "  • Config: ~/.openclaw/openclaw.json"
    echo "  • README: $SCRIPT_DIR/README.md"
    echo ""
    echo -e "${BOLD}Need help?${NC} Check the README or visit:"
    echo "  • OpenClaw docs: https://openclaw.sh/docs"
    echo "  • GitHub: https://github.com/YOUR_ORG/vanilla-alfred-mac"
    echo ""
    
    # Clean up state file
    rm -f "$STATE_FILE"
}

# Run main
main "$@"
