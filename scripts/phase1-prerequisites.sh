#!/bin/bash
# Phase 1: Prerequisites
# Installs: Homebrew, Docker Desktop, Node.js, Git, Tailscale, Python dependencies

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/lib/common.sh"

log_section "Installing Prerequisites"

# 1. Homebrew
if command_exists brew; then
    log_success "Homebrew already installed"
else
    log_step "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon
    if [[ "$(uname -m)" == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    
    log_success "Homebrew installed"
fi

# Update Homebrew
log_step "Updating Homebrew..."
brew update > /dev/null 2>&1 || true

# 2. Git
if command_exists git; then
    log_success "Git already installed"
else
    log_step "Installing Git..."
    brew install git
    log_success "Git installed"
fi

# 3. Node.js (using nvm for version management)
if command_exists node; then
    log_success "Node.js already installed ($(node --version))"
else
    log_step "Installing Node.js..."
    brew install node@20
    brew link --overwrite node@20
    log_success "Node.js installed ($(node --version))"
fi

# 4. Python 3
if command_exists python3; then
    log_success "Python 3 already installed ($(python3 --version))"
else
    log_step "Installing Python 3..."
    brew install python@3.12
    log_success "Python 3 installed"
fi

# Install essential Python packages
log_step "Installing Python dependencies..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install --quiet requests anthropic beautifulsoup4 lxml

# 5. Docker Desktop
if command_exists docker && docker ps >/dev/null 2>&1; then
    log_success "Docker Desktop already installed and running"
else
    if [[ -d "/Applications/Docker.app" ]]; then
        log_warning "Docker Desktop installed but not running"
        log_step "Starting Docker Desktop..."
        open -a Docker
        wait_for_docker 120
    else
        log_step "Installing Docker Desktop..."
        
        # Download Docker Desktop for Apple Silicon
        DOCKER_DMG="/tmp/Docker.dmg"
        curl -fsSL https://desktop.docker.com/mac/main/arm64/Docker.dmg -o "$DOCKER_DMG"
        
        # Mount and install
        log_step "Mounting Docker.dmg..."
        hdiutil attach "$DOCKER_DMG" -nobrowse -quiet
        
        log_step "Copying Docker.app..."
        cp -R /Volumes/Docker/Docker.app /Applications/
        
        log_step "Unmounting..."
        hdiutil detach /Volumes/Docker -quiet
        rm "$DOCKER_DMG"
        
        log_step "Starting Docker Desktop..."
        check_security_prompt "Docker Desktop"
        open -a Docker
        
        log_warning "Docker Desktop is starting for the first time..."
        log_info "This may take 2-3 minutes and may require your password"
        
        wait_for_docker 180
        
        log_success "Docker Desktop installed and running"
    fi
fi

# 6. Tailscale (optional but recommended)
if command_exists tailscale; then
    log_success "Tailscale already installed"
else
    if confirm "Install Tailscale? (Recommended for remote access)" "y"; then
        log_step "Installing Tailscale..."
        brew install --cask tailscale
        log_success "Tailscale installed"
        log_warning "You'll need to authenticate Tailscale in Phase 4"
    else
        log_info "Skipping Tailscale installation"
    fi
fi

# 7. Essential CLI tools
log_step "Installing CLI tools..."
brew_packages=(
    "jq"           # JSON processing
    "yq"           # YAML processing
    "curl"         # Already installed but ensure latest
    "wget"         # Alternative downloader
    "netcat"       # Network utilities
)

for pkg in "${brew_packages[@]}"; do
    if command_exists "${pkg%% *}"; then
        continue
    fi
    brew install "$pkg" > /dev/null 2>&1 || true
done

log_success "CLI tools installed"

# 8. GitHub CLI (optional, useful for cloning)
if command_exists gh; then
    log_success "GitHub CLI already installed"
else
    if confirm "Install GitHub CLI? (Useful for cloning private repos)" "n"; then
        log_step "Installing GitHub CLI..."
        brew install gh
        log_success "GitHub CLI installed"
    fi
fi

# 9. Create workspace directory
WORKSPACE_DIR="$HOME/clawd"
if [[ ! -d "$WORKSPACE_DIR" ]]; then
    log_step "Creating workspace directory: $WORKSPACE_DIR"
    mkdir -p "$WORKSPACE_DIR"
    log_success "Workspace created"
else
    log_success "Workspace already exists: $WORKSPACE_DIR"
fi

# 10. Create logs directory
ensure_dir "$WORKSPACE_DIR/logs"
ensure_dir "$WORKSPACE_DIR/memory"
ensure_dir "$WORKSPACE_DIR/scripts"
ensure_dir "$WORKSPACE_DIR/skills"

# Summary
echo ""
log_section "Prerequisites Summary"
log_info "Homebrew: $(brew --version | head -1)"
log_info "Git: $(git --version)"
log_info "Node.js: $(node --version)"
log_info "Python: $(python3 --version)"
log_info "Docker: $(docker --version)"
if command_exists tailscale; then
    log_info "Tailscale: $(tailscale version | head -1)"
fi
log_info "Workspace: $WORKSPACE_DIR"

echo ""
log_success "Phase 1 complete - Prerequisites installed"
