#!/bin/bash
# Phase 4: Integrations
# Sets up: AgentMail, Google (gog), Tailscale funnel, webhooks

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Ensure Homebrew and its packages are in PATH
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

log_section "Configuring Integrations"

WORKSPACE_DIR="$HOME/clawd"
OPENCLAW_CONFIG_DIR="$HOME/.openclaw"

# 1. AgentMail
log_step "Setting up AgentMail..."
echo ""

if ! is_automated; then
    log_info "AgentMail provides email capabilities for Alfred"
    log_info "You'll need an API key from: https://agentmail.to"
    echo ""
    
    if confirm "Configure AgentMail now?" "y"; then
        prompt_secret "Enter AgentMail API key" AGENTMAIL_API_KEY
        
        # Store API key
        ensure_dir "$HOME/.config/agentmail"
        echo "$AGENTMAIL_API_KEY" > "$HOME/.config/agentmail/api_key"
        chmod 600 "$HOME/.config/agentmail/api_key"
        
        # Test API key
        if python3 -c "import requests; r=requests.get('https://api.agentmail.to/v0/me', headers={'X-API-Key': '$AGENTMAIL_API_KEY'}); exit(0 if r.status_code == 200 else 1)" 2>/dev/null; then
            log_success "AgentMail API key validated"
        else
            log_warning "AgentMail API key validation failed - check the key"
        fi
        
        # Get inbox email
        prompt "What email should Alfred use?" "alfred@agent.yourdomain.com" ALFRED_EMAIL
        log_info "Alfred's email: $ALFRED_EMAIL"
        
        # Start AgentMail relay
        log_step "Starting AgentMail webhook relay..."
        nohup python3 "$WORKSPACE_DIR/scripts/agentmail-relay.py" > "$WORKSPACE_DIR/logs/agentmail-relay.log" 2>&1 &
        
        sleep 2
        if pgrep -f "agentmail-relay.py" >/dev/null; then
            log_success "AgentMail relay running on :18790"
        else
            log_warning "AgentMail relay may not have started - check logs"
        fi
    else
        log_info "Skipping AgentMail configuration"
        log_warning "You can configure it later by running the wizard again"
    fi
else
    log_info "Automated mode - AgentMail configuration skipped"
    log_info "Configure manually: ~/.config/agentmail/api_key"
fi

echo ""

# 2. Google OAuth (gog)
log_step "Setting up Google integration..."
echo ""

if ! is_automated; then
    log_info "Google integration enables Gmail, Calendar, Drive access"
    log_info "This uses the 'gog' tool: https://github.com/caarlos0/gog"
    echo ""
    
    if confirm "Configure Google integration now?" "y"; then
        # Install gog
        if ! command_exists gog; then
            log_step "Installing gog..."
            brew tap caarlos0/gog
            brew install gog
        fi
        
        log_info "Starting Google OAuth flow..."
        log_warning "A browser window will open for authentication"
        echo ""
        
        prompt "Enter your primary email" "" GOOGLE_EMAIL
        
        # Authenticate
        gog auth "$GOOGLE_EMAIL" || {
            log_warning "Google authentication failed or was cancelled"
            log_info "You can retry later with: gog auth $GOOGLE_EMAIL"
        }
        
        # Test authentication
        if gog calendar list "$GOOGLE_EMAIL" --account "$GOOGLE_EMAIL" >/dev/null 2>&1; then
            log_success "Google authentication successful"
            
            # Set up keyring password in environment
            log_step "Setting up keyring password..."
            prompt_secret "Enter a password for Google keyring encryption" GOG_KEYRING_PASSWORD
            
            # Store in macOS Keychain
            security add-generic-password \
                -a "$USER" \
                -s "gog-keyring-alfred" \
                -w "$GOG_KEYRING_PASSWORD" \
                -U 2>/dev/null || \
            security add-generic-password \
                -a "$USER" \
                -s "gog-keyring-alfred" \
                -w "$GOG_KEYRING_PASSWORD"
            
            log_success "Keyring password stored in macOS Keychain"
        else
            log_warning "Google authentication may have failed"
        fi
    else
        log_info "Skipping Google integration"
    fi
else
    log_info "Automated mode - Google integration skipped"
    log_info "Configure manually: gog auth <email>"
fi

echo ""

# 3. Tailscale
log_step "Configuring Tailscale..."
echo ""

if command_exists tailscale; then
    if ! is_automated; then
        log_info "Tailscale provides secure remote access to Alfred"
        echo ""
        
        if confirm "Configure Tailscale now?" "y"; then
            # Check if already authenticated
            if tailscale status >/dev/null 2>&1; then
                log_success "Tailscale already authenticated"
            else
                log_step "Starting Tailscale authentication..."
                log_warning "A browser window will open"
                
                tailscale up || {
                    log_warning "Tailscale authentication failed or was cancelled"
                    log_info "You can retry later with: tailscale up"
                }
            fi
            
            # Set up Tailscale funnel for webhooks
            if tailscale status >/dev/null 2>&1; then
                log_step "Setting up Tailscale funnel for webhooks..."
                
                # Enable funnel on port 8443 → 18790 (AgentMail relay)
                tailscale funnel --bg --https 8443 18790 2>/dev/null || {
                    log_warning "Tailscale funnel setup failed"
                    log_info "You may need to enable it manually: tailscale funnel --https 8443 18790"
                }
                
                # Get Tailscale hostname
                TAILSCALE_NAME=$(tailscale status --json 2>/dev/null | jq -r '.Self.HostName' 2>/dev/null || echo "")
                if [[ -n "$TAILSCALE_NAME" ]]; then
                    log_success "Tailscale configured"
                    log_info "Hostname: ${TAILSCALE_NAME}.ts.net"
                    log_info "Webhook URL: https://${TAILSCALE_NAME}.ts.net:8443/webhook"
                fi
            fi
        else
            log_info "Skipping Tailscale configuration"
        fi
    else
        log_info "Automated mode - Tailscale configuration skipped"
    fi
else
    log_info "Tailscale not installed - skipping"
    log_info "Install later with: brew install --cask tailscale"
fi

echo ""

# 4. Webhook setup
log_step "Configuring webhooks..."

# Copy webhook transforms
if [[ -d "$REPO_DIR/config/hooks" ]]; then
    ensure_dir "$OPENCLAW_CONFIG_DIR/hooks"
    cp -R "$REPO_DIR/config/hooks/"* "$OPENCLAW_CONFIG_DIR/hooks/" 2>/dev/null || true
    log_success "Webhook transforms copied"
fi

# Create authorization.json
if [[ ! -f "$OPENCLAW_CONFIG_DIR/authorization.json" ]]; then
    cat > "$OPENCLAW_CONFIG_DIR/authorization.json" <<'EOF'
{
  "version": "1.0",
  "authorizedEmails": [
    "{{USER_EMAIL}}"
  ],
  "lastModified": "{{TIMESTAMP}}"
}
EOF
    log_success "Authorization config created"
fi

# Summary
echo ""
log_section "Integrations Summary"

if [[ -f "$HOME/.config/agentmail/api_key" ]]; then
    log_info "AgentMail: Configured ✓"
    log_info "  • Relay running on :18790"
else
    log_info "AgentMail: Not configured"
fi

if command_exists gog && gog calendar list >/dev/null 2>&1; then
    log_info "Google: Authenticated ✓"
else
    log_info "Google: Not configured"
fi

if command_exists tailscale && tailscale status >/dev/null 2>&1; then
    TAILSCALE_NAME=$(tailscale status --json 2>/dev/null | jq -r '.Self.HostName' 2>/dev/null || echo "unknown")
    log_info "Tailscale: Connected ✓"
    log_info "  • Hostname: ${TAILSCALE_NAME}.ts.net"
else
    log_info "Tailscale: Not configured"
fi

echo ""
log_success "Phase 4 complete - Integrations configured"
