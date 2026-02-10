#!/bin/bash
# Phase 3: Services
# Deploys: Twenty CRM, Plane PM, Temporal, AutoKitteh, Uptime Kuma

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

# 1. Temporal + AutoKitteh (shared PostgreSQL)
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

# 2. AutoKitteh
log_step "Installing AutoKitteh..."

# Install ak CLI
if ! command_exists ak; then
    log_step "Installing AutoKitteh CLI via Homebrew..."
    brew install autokitteh/tap/autokitteh
fi

# Create AutoKitteh config
AUTOKITTEH_DIR="$SERVICES_DIR/autokitteh"
ensure_dir "$AUTOKITTEH_DIR"

# Copy config template
if [[ -f "$REPO_DIR/services/autokitteh/config.yaml.template" ]]; then
    cp "$REPO_DIR/services/autokitteh/config.yaml.template" "$AUTOKITTEH_DIR/config.yaml"
fi

# Start AutoKitteh in background
cd "$AUTOKITTEH_DIR"
nohup ak up > ak.log 2>&1 &
sleep 5

# Verify AutoKitteh is running
if wait_for_port 9980 30; then
    log_success "AutoKitteh running on :9980"
else
    log_warning "AutoKitteh may not have started correctly"
    log_info "Check logs: $AUTOKITTEH_DIR/ak.log"
fi

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

# Clone Plane repo if needed
if [[ ! -d "$PLANE_DIR/plane-app" ]]; then
    log_step "Cloning Plane repository..."
    git clone https://github.com/makeplane/plane.git "$PLANE_DIR/plane-app" --depth 1 --branch master
fi

cd "$PLANE_DIR/plane-app"

# Copy .env template
cp "$REPO_DIR/services/plane/plane.env.template" "$PLANE_DIR/plane.env"

# Generate secrets
SECRET_KEY=$(openssl rand -hex 32)
replace_placeholder "$PLANE_DIR/plane.env" "SECRET_KEY" "$SECRET_KEY"
replace_placeholder "$PLANE_DIR/plane.env" "DATABASE_PASSWORD" "$(openssl rand -hex 16)"
replace_placeholder "$PLANE_DIR/plane.env" "REDIS_PASSWORD" "$(openssl rand -hex 16)"

# Copy plane.env to deployment location
cp "$PLANE_DIR/plane.env" "$PLANE_DIR/plane-app/plane.env"

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

# 6. Create AutoKitteh project directories
log_step "Setting up AutoKitteh projects..."
WORKSPACE_DIR="$HOME/clawd"
ensure_dir "$WORKSPACE_DIR/autokitteh-projects"

# Copy AutoKitteh workflow templates
for workflow_dir in "$REPO_DIR/autokitteh-templates/"*/; do
    if [[ ! -d "$workflow_dir" ]]; then
        continue
    fi
    
    workflow_name=$(basename "$workflow_dir")
    target_dir="$WORKSPACE_DIR/autokitteh-projects/$workflow_name"
    
    ensure_dir "$target_dir"
    cp -R "$workflow_dir"/* "$target_dir/"
done

log_success "AutoKitteh project templates copied"

# Summary
echo ""
log_section "Services Summary"
log_info "Temporal: http://localhost:8233 (UI)"
log_info "AutoKitteh: http://localhost:9980"
log_info "Twenty CRM: http://localhost:3000"
log_info "Plane PM: http://localhost:8080"
log_info "Uptime Kuma: http://localhost:3001"

echo ""
log_info "Docker containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(temporal|twenty|plane|kuma|autokitteh)" || true

echo ""
log_success "Phase 3 complete - All services deployed"
