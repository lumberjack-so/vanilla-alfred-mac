#!/bin/bash
# Infrastructure health check - run during heartbeats
# Returns non-zero and prints failures if anything is down

FAILURES=()

# 1. Docker daemon responsive (use docker ps which is faster than docker info)
if ! docker ps >/dev/null 2>&1; then
    FAILURES+=("Docker daemon unresponsive")
fi

# 2. Temporal containers running
if docker ps >/dev/null 2>&1; then
    for svc in temporal-temporal-1 temporal-postgresql-1; do
        if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$svc"; then
            FAILURES+=("Temporal container '$svc' not running")
        fi
    done
fi

# 3. AutoKitteh process running
if ! pgrep -f "ak up" >/dev/null 2>&1 && ! pgrep -f "autokitteh" >/dev/null 2>&1; then
    FAILURES+=("AutoKitteh not running")
fi

# 4. AutoKitteh can reach Temporal (check for recent deadline exceeded errors)
AK_LOG=~/services/autokitteh/ak.log
if [ -f "$AK_LOG" ]; then
    RECENT_ERRORS=$(tail -20 "$AK_LOG" | grep -c "context deadline exceeded" 2>/dev/null)
    if [ "$RECENT_ERRORS" -gt 3 ]; then
        FAILURES+=("AutoKitteh failing to reach Temporal ($RECENT_ERRORS recent deadline errors)")
    fi
fi

# 5. Google OAuth validity (quick check)
# Note: Update keyring service name and email in your config
GOG_KEYRING_SERVICE="${GOG_KEYRING_SERVICE:-gog-keyring}"
PRIMARY_EMAIL="${PRIMARY_EMAIL:-your-email@example.com}"
export GOG_KEYRING_PASSWORD=$(security find-generic-password -s "$GOG_KEYRING_SERVICE" -w 2>/dev/null)
if command -v gog >/dev/null 2>&1 && [ -n "$PRIMARY_EMAIL" ]; then
    GOG_OUT=$(gog calendar list "$PRIMARY_EMAIL" --account "$PRIMARY_EMAIL" 2>&1)
    if echo "$GOG_OUT" | grep -qi "invalid_grant\|expired\|revoked"; then
        FAILURES+=("Google OAuth token expired for $PRIMARY_EMAIL")
    fi
fi

# 6. AgentMail relay process running
if ! pgrep -f "agentmail-relay.py" >/dev/null 2>&1; then
    FAILURES+=("AgentMail relay not running — starting it")
    nohup python3 ~/clawd/scripts/agentmail-relay.py > ~/clawd/logs/agentmail-relay.log 2>&1 &
fi

# 7. Tailscale funnel on port 8443 (for AgentMail relay)
FUNNEL_STATUS=$(tailscale funnel status 2>&1)
if ! echo "$FUNNEL_STATUS" | grep -q "8443"; then
    FAILURES+=("Tailscale funnel on 8443 missing — re-enabling")
    tailscale funnel --bg --https 8443 18790 >/dev/null 2>&1
fi

# Report
if [ ${#FAILURES[@]} -eq 0 ]; then
    echo "ALL_OK"
    exit 0
else
    echo "FAILURES_DETECTED"
    for f in "${FAILURES[@]}"; do
        echo "  - $f"
    done
    exit 1
fi
