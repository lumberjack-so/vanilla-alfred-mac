#!/bin/bash
# Phase 3: Services
# Deploys: Twenty CRM, Plane PM, Temporal Workflows, Uptime Kuma

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Ensure Homebrew and its packages are in PATH
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

log_section "Deploying Services"

SERVICES_DIR="$HOME/services"
ensure_dir "$SERVICES_DIR"

# Wait for Docker to be ready
if ! docker ps >/dev/null 2>&1; then
    log_warning "Docker is not running, attempting to start..."
    open -a Docker
    wait_for_docker 120 || {
        log_error "Docker failed to start"
        exit 1
    }
fi

log_success "Docker is ready"

# 1. Temporal Workflows
log_step "Deploying Temporal..."

TEMPORAL_DIR="$SERVICES_DIR/temporal"
ensure_dir "$TEMPORAL_DIR"

# Copy docker-compose
cp "$REPO_DIR/services/temporal/docker-compose.yml" "$TEMPORAL_DIR/"

# Copy dynamicconfig if exists
if [[ -d "$REPO_DIR/services/temporal/dynamicconfig" ]]; then
    cp -R "$REPO_DIR/services/temporal/dynamicconfig" "$TEMPORAL_DIR/"
fi

# Start Temporal
cd "$TEMPORAL_DIR"
docker compose up -d

# Wait for Temporal to be ready
log_step "Waiting for Temporal..."
wait_for_port 7233 120 || {
    log_error "Temporal failed to start"
    exit 1
}
log_success "Temporal running on :7233"
log_info "Temporal UI: http://localhost:8233"

# 2. Temporal Python Workflows
log_step "Setting up Temporal Python workflows..."

WORKSPACE_DIR="$HOME/clawd"
WORKFLOWS_DIR="$WORKSPACE_DIR/temporal-workflows"
ensure_dir "$WORKFLOWS_DIR"

# Copy workflow files
cp -R "$REPO_DIR/temporal-workflows/"* "$WORKFLOWS_DIR/"

# Create Python venv
cd "$WORKFLOWS_DIR"
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

log_success "Python dependencies installed"

# Configure workflows (replace placeholders)
# These values will be collected from the wizard in phase 5
# For now, we'll create a setup script that the wizard will call

cat > "$WORKFLOWS_DIR/setup-config.sh" <<'SETUP_EOF'
#!/bin/bash
# Replace placeholders in config.py with actual values
# Called by the wizard in phase 5

GATEWAY_URL="$1"
GATEWAY_TOKEN="$2"
SLACK_LOGS="$3"
DAVID_DM="$4"
VAULT_PATH="$5"
UPTIME_KUMA_URL="$6"

CONFIG_FILE="config.py"

sed -i.bak \
    -e "s|{{GATEWAY_URL}}|$GATEWAY_URL|g" \
    -e "s|{{GATEWAY_TOKEN}}|$GATEWAY_TOKEN|g" \
    -e "s|{{SLACK_LOGS_CHANNEL}}|$SLACK_LOGS|g" \
    -e "s|{{DAVID_DM_CHANNEL}}|$DAVID_DM|g" \
    -e "s|{{VAULT_PATH}}|$VAULT_PATH|g" \
    -e "s|{{UPTIME_KUMA_URL}}|$UPTIME_KUMA_URL|g" \
    "$CONFIG_FILE"

rm -f "$CONFIG_FILE.bak"
echo "Configuration updated"
SETUP_EOF

chmod +x "$WORKFLOWS_DIR/setup-config.sh"

log_info "Configuration setup script created"
log_info "Will be configured in Phase 5 (wizard)"

# 3. Twenty CRM
log_step "Deploying Twenty CRM..."

TWENTY_DIR="$SERVICES_DIR/twenty"
ensure_dir "$TWENTY_DIR"

# Copy docker-compose and .env
cp "$REPO_DIR/services/twenty/docker-compose.yml" "$TWENTY_DIR/"
cp "$REPO_DIR/services/twenty/.env.template" "$TWENTY_DIR/.env"

# Generate random secrets
APP_SECRET=$(openssl rand -hex 32)
replace_placeholder "$TWENTY_DIR/.env" "APP_SECRET" "$APP_SECRET"
replace_placeholder "$TWENTY_DIR/.env" "PG_DATABASE_PASSWORD" "$(openssl rand -hex 16)"
replace_placeholder "$TWENTY_DIR/.env" "SERVER_URL" "http://localhost:3000"

# Start Twenty
cd "$TWENTY_DIR"
docker compose up -d

# Wait for Twenty
log_step "Waiting for Twenty CRM..."
wait_for_port 3000 120 || {
    log_warning "Twenty CRM may not have started correctly"
}
log_success "Twenty CRM running on :3000"

# 4. Plane PM
log_step "Deploying Plane PM..."

PLANE_DIR="$SERVICES_DIR/plane"
ensure_dir "$PLANE_DIR"

# Copy bundled docker-compose and env (no git clone needed)
cp "$REPO_DIR/services/plane/docker-compose.yml" "$PLANE_DIR/docker-compose.yml"
cp "$REPO_DIR/services/plane/plane.env.template" "$PLANE_DIR/.env"

# Generate secrets
SECRET_KEY=$(openssl rand -hex 32)
LIVE_SECRET=$(openssl rand -hex 32)
replace_placeholder "$PLANE_DIR/.env" "SECRET_KEY" "$SECRET_KEY"
replace_placeholder "$PLANE_DIR/.env" "DATABASE_PASSWORD" "$(openssl rand -hex 16)"
replace_placeholder "$PLANE_DIR/.env" "LIVE_SECRET" "$LIVE_SECRET"

cd "$PLANE_DIR"

# Start Plane
docker compose up -d

# Wait for Plane
log_step "Waiting for Plane PM..."
wait_for_port 8080 120 || {
    log_warning "Plane PM may not have started correctly"
}
log_success "Plane PM running on :8080"

# 5. Uptime Kuma
log_step "Deploying Uptime Kuma..."

KUMA_DIR="$SERVICES_DIR/uptime-kuma"
ensure_dir "$KUMA_DIR"
ensure_dir "$KUMA_DIR/data"

# Create docker-compose for Uptime Kuma
cat > "$KUMA_DIR/docker-compose.yml" <<'EOF'
version: '3.8'

services:
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    container_name: uptime-kuma
    volumes:
      - ./data:/app/data
    ports:
      - "3001:3001"
    restart: always
EOF

# Start Uptime Kuma
cd "$KUMA_DIR"
docker compose up -d

# Wait for Uptime Kuma
log_step "Waiting for Uptime Kuma..."
wait_for_port 3001 60 || {
    log_warning "Uptime Kuma may not have started correctly"
}
log_success "Uptime Kuma running on :3001"

# Summary
echo ""
log_section "Services Summary"
log_info "Temporal: http://localhost:8233 (UI)"
log_info "Twenty CRM: http://localhost:3000"
log_info "Plane PM: http://localhost:8080"
log_info "Uptime Kuma: http://localhost:3001"

echo ""
log_info "Docker containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(temporal|twenty|plane|kuma)" || true

echo ""
log_success "Phase 3 complete - All services deployed"
log_info "⚠️  Temporal worker will be configured and started in Phase 5 (wizard)"
