#!/bin/bash
# Phase 5: Interactive Wizard
# Collects: API keys, user info, preferences, completes configuration

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Ensure Homebrew and its packages are in PATH
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

log_section "Configuration Wizard"

WORKSPACE_DIR="$HOME/clawd"
OPENCLAW_CONFIG_DIR="$HOME/.openclaw"
CONFIG_FILE="$OPENCLAW_CONFIG_DIR/openclaw.json"

# Skip in automated mode
if is_automated; then
    log_warning "Automated mode - wizard skipped"
    log_info "You'll need to configure these manually:"
    log_info "  • USER.md (workspace profile)"
    log_info "  • TOOLS.md (API keys and credentials)"
    log_info "  • openclaw.json (integrations)"
    exit 0
fi

echo ""
log_info "This wizard will collect configuration details for your Alfred butler"
echo ""

# 1. Basic user information
log_section "User Profile"

prompt "What's your name?" "" USER_NAME
prompt "What's your email?" "" USER_EMAIL
prompt "What's your timezone?" "$(date +%Z)" USER_TIMEZONE

# Optional phone number
if confirm "Add phone number? (Optional, for SMS/voice)" "n"; then
    prompt "Phone number (with country code, e.g., +1234567890)" "" USER_PHONE
else
    USER_PHONE=""
fi

# 2. Create USER.md
log_step "Creating USER.md..."
cat > "$WORKSPACE_DIR/USER.md" <<EOF
# USER.md - Who You're Helping

**Name:** $USER_NAME
**Email:** $USER_EMAIL
**Timezone:** $USER_TIMEZONE
$(if [[ -n "$USER_PHONE" ]]; then echo "**Phone:** $USER_PHONE"; fi)

## Context

Add information about yourself that Alfred should know:
- Your preferences
- Your schedule patterns
- Your communication style
- Your priorities

## Family / Team

List people Alfred should know about and their relationships to you.

## Projects

What are you currently working on? What matters most?

---

*Edit this file to give Alfred context about your life and work.*
EOF

log_success "USER.md created"

# 3. API Keys
log_section "API Keys"

echo ""
log_info "Alfred needs these API keys to function. Some are required, others optional."
echo ""

# Required: Brave Search
log_step "Brave Search API (Required for web search)"
log_info "Get your key from: https://brave.com/search/api/"
prompt_secret "Brave Search API Key" BRAVE_API_KEY

# Optional: ElevenLabs
echo ""
if confirm "Configure ElevenLabs TTS? (Recommended for voice features)" "y"; then
    log_info "Get your key from: https://elevenlabs.io/api"
    prompt_secret "ElevenLabs API Key" ELEVENLABS_API_KEY
    prompt "ElevenLabs Voice ID" "21m00Tcm4TlvDq8ikWAM" ELEVENLABS_VOICE_ID
    prompt "ElevenLabs Model" "eleven_flash_v2_5" ELEVENLABS_MODEL
else
    ELEVENLABS_API_KEY=""
    ELEVENLABS_VOICE_ID=""
    ELEVENLABS_MODEL=""
fi

# Optional: Anthropic API key (fallback)
echo ""
if confirm "Add Anthropic API key? (Optional, Claude token auth is preferred)" "n"; then
    log_info "Get your key from: https://console.anthropic.com/"
    prompt_secret "Anthropic API Key" ANTHROPIC_API_KEY
else
    ANTHROPIC_API_KEY=""
fi

# Optional: HuggingFace
echo ""
if confirm "Add HuggingFace token? (Optional, for model training workflows)" "n"; then
    log_info "Get your token from: https://huggingface.co/settings/tokens"
    prompt_secret "HuggingFace Token" HUGGINGFACE_TOKEN
    
    ensure_dir "$HOME/.config/huggingface"
    echo "$HUGGINGFACE_TOKEN" > "$HOME/.config/huggingface/token"
    chmod 600 "$HOME/.config/huggingface/token"
else
    HUGGINGFACE_TOKEN=""
fi

# Optional: Stripe
echo ""
if confirm "Add Stripe API key? (Optional, for invoicing/payments)" "n"; then
    log_info "Get your key from: https://dashboard.stripe.com/apikeys"
    prompt_secret "Stripe API Key" STRIPE_API_KEY
    
    ensure_dir "$HOME/.config/stripe"
    echo "$STRIPE_API_KEY" > "$HOME/.config/stripe/api_key"
    chmod 600 "$HOME/.config/stripe/api_key"
fi

# 4. Update openclaw.json with API keys
log_step "Updating OpenClaw configuration..."

# Update config using jq
if command_exists jq; then
    # Brave API key
    jq --arg key "$BRAVE_API_KEY" \
        '.env.vars.BRAVE_API_KEY = $key' \
        "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    
    # ElevenLabs
    if [[ -n "$ELEVENLABS_API_KEY" ]]; then
        jq --arg key "$ELEVENLABS_API_KEY" \
           --arg voice "$ELEVENLABS_VOICE_ID" \
           --arg model "$ELEVENLABS_MODEL" \
           '.messages.tts.elevenlabs.apiKey = $key |
            .messages.tts.elevenlabs.voiceId = $voice |
            .messages.tts.elevenlabs.modelId = $model' \
           "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    fi
    
    # User timezone
    jq --arg tz "$USER_TIMEZONE" \
        '.agents.defaults.userTimezone = $tz' \
        "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    
    # Workspace
    jq --arg ws "$WORKSPACE_DIR" \
        '.agents.defaults.workspace = $ws |
         .agents.list[].workspace = $ws' \
        "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
fi

log_success "Configuration updated"

# 5. Create TOOLS.md
log_step "Creating TOOLS.md..."
cat > "$WORKSPACE_DIR/TOOLS.md" <<EOF
# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## User Information
- **Name:** $USER_NAME
- **Email:** $USER_EMAIL
- **Timezone:** $USER_TIMEZONE
$(if [[ -n "$USER_PHONE" ]]; then echo "- **Phone:** $USER_PHONE"; fi)

## API Keys

### Brave Search
- API Key: Configured ✓

$(if [[ -n "$ELEVENLABS_API_KEY" ]]; then
cat <<ELABS
### ElevenLabs TTS
- API Key: Configured ✓
- Voice ID: $ELEVENLABS_VOICE_ID
- Model: $ELEVENLABS_MODEL
ELABS
fi)

$(if [[ -f "$HOME/.config/agentmail/api_key" ]]; then
cat <<AMAIL
### AgentMail
- API Key: Configured ✓
- Email: $(cat "$WORKSPACE_DIR/USER.md" | grep "Email:" | cut -d: -f2 | xargs)
AMAIL
fi)

$(if command -v gog >/dev/null 2>&1; then
cat <<GOG
### Google (gog)
- Configured ✓
- Account: $USER_EMAIL
EOF

if [[ -f "$HOME/.config/stripe/api_key" ]]; then
cat <<STRIPE >> "$WORKSPACE_DIR/TOOLS.md"

### Stripe
- API Key: Configured ✓
STRIPE
fi

if [[ -f "$HOME/.config/huggingface/token" ]]; then
cat <<HF >> "$WORKSPACE_DIR/TOOLS.md"

### HuggingFace
- Token: Configured ✓
HF
fi

cat >> "$WORKSPACE_DIR/TOOLS.md" <<'EOF'

## Services
- **Twenty CRM:** http://localhost:3000
- **Plane PM:** http://localhost:8080
- **Temporal UI:** http://localhost:8233
- **AutoKitteh:** http://localhost:9980
- **Uptime Kuma:** http://localhost:3001

## Obsidian Vault
- **Vault name:** alfred
- **Vault path:** ~/alfred/alfred (create this manually)

---

*Add your own notes, credentials, and configuration details here.*
EOF

log_success "TOOLS.md created"

# 6. Update authorization.json
log_step "Updating authorization..."
cat > "$OPENCLAW_CONFIG_DIR/authorization.json" <<EOF
{
  "version": "1.0",
  "authorizedEmails": [
    "$USER_EMAIL"
  ],
  "lastModified": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

log_success "Authorization configured"

# 7. Optional: Slack integration
echo ""
log_section "Optional: Slack Integration"
echo ""
log_info "Slack allows Alfred to communicate with you via messages"
log_info "You'll need to create a Slack app and get bot/app tokens"
log_info "Guide: https://openclaw.sh/docs/integrations/slack"
echo ""

if confirm "Configure Slack now?" "n"; then
    prompt "Slack Bot Token (xoxb-...)" "" SLACK_BOT_TOKEN
    prompt "Slack App Token (xapp-...)" "" SLACK_APP_TOKEN
    
    # Update config
    if command_exists jq; then
        jq --arg bot "$SLACK_BOT_TOKEN" \
           --arg app "$SLACK_APP_TOKEN" \
           '.channels.slack.enabled = true |
            .channels.slack.botToken = $bot |
            .channels.slack.appToken = $app' \
           "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        
        log_success "Slack configured"
    fi
else
    log_info "Skipping Slack - you can configure it later"
fi

# 8. Create Obsidian vault
echo ""
log_section "Obsidian Vault"
echo ""
log_info "Alfred uses an Obsidian vault as his knowledge base"
log_info "The vault will be created at: ~/alfred/alfred"
echo ""

VAULT_DIR="$HOME/alfred/alfred"

if confirm "Create Obsidian vault now?" "y"; then
    ensure_dir "$VAULT_DIR"
    
    # Copy vault template
    cp -R "$REPO_DIR/vault-template/"* "$VAULT_DIR/"
    
    log_success "Vault created at: $VAULT_DIR"
    log_info "Install Obsidian from: https://obsidian.md"
    log_info "Then open vault: $VAULT_DIR"
else
    log_info "Skipping vault creation"
    log_warning "Alfred's knowledge management features won't work without a vault"
fi

# Summary
echo ""
log_section "Configuration Summary"
log_info "User: $USER_NAME ($USER_EMAIL)"
log_info "Timezone: $USER_TIMEZONE"
log_info "Workspace: $WORKSPACE_DIR"
log_info "Config: $CONFIG_FILE"

echo ""
log_info "API Keys Configured:"
log_info "  • Brave Search ✓"
[[ -n "$ELEVENLABS_API_KEY" ]] && log_info "  • ElevenLabs TTS ✓"
[[ -f "$HOME/.config/agentmail/api_key" ]] && log_info "  • AgentMail ✓"
[[ -f "$HOME/.config/stripe/api_key" ]] && log_info "  • Stripe ✓"
[[ -f "$HOME/.config/huggingface/token" ]] && log_info "  • HuggingFace ✓"

echo ""
log_success "Phase 5 complete - Configuration wizard finished"
