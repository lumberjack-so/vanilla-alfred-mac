#!/bin/bash
# Common functions for Vanilla Alfred installer

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_section() {
    echo -e "\n${BOLD}${BLUE}▸ $1${NC}\n"
}

log_step() {
    echo -e "  ${BLUE}→${NC} $1"
}

# Spinner for long-running tasks
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while ps -p $pid > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Run command with spinner
run_with_spinner() {
    local message=$1
    shift
    
    log_step "$message..."
    "$@" > /dev/null 2>&1 &
    local pid=$!
    spinner $pid
    wait $pid
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e " ${GREEN}✓${NC}"
        return 0
    else
        echo -e " ${RED}✗${NC}"
        return $exit_code
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if binary exists
binary_exists() {
    command_exists "$1"
}

# Wait for user confirmation
confirm() {
    local message=$1
    local default=${2:-n}
    
    if [[ $default == "y" ]]; then
        local prompt="[Y/n]"
    else
        local prompt="[y/N]"
    fi
    
    read -p "$(echo -e ${YELLOW}${message}${NC}) $prompt " -n 1 -r
    echo ""
    
    if [[ -z $REPLY ]]; then
        [[ $default == "y" ]]
    else
        [[ $REPLY =~ ^[Yy]$ ]]
    fi
}

# Prompt for input with default
prompt() {
    local message=$1
    local default=$2
    local var_name=$3
    
    if [[ -n $default ]]; then
        read -p "$(echo -e ${BLUE}${message}${NC} [${default}]: )" value
        value=${value:-$default}
    else
        read -p "$(echo -e ${BLUE}${message}:${NC} )" value
    fi
    
    if [[ -n $var_name ]]; then
        eval "$var_name='$value'"
    else
        echo "$value"
    fi
}

# Prompt for secret (no echo)
prompt_secret() {
    local message=$1
    local var_name=$2
    
    read -sp "$(echo -e ${BLUE}${message}:${NC} )" value
    echo ""
    
    if [[ -n $var_name ]]; then
        eval "$var_name='$value'"
    else
        echo "$value"
    fi
}

# Check macOS security prompts
check_security_prompt() {
    local app=$1
    log_warning "macOS may show a security prompt for $app"
    log_info "Please approve it in System Settings > Privacy & Security if prompted"
}

# Wait for process to be ready
wait_for_port() {
    local port=$1
    local timeout=${2:-60}
    local elapsed=0
    
    while ! nc -z localhost $port >/dev/null 2>&1; do
        if [ $elapsed -ge $timeout ]; then
            return 1
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 0
}

# Wait for Docker daemon
wait_for_docker() {
    local timeout=${1:-120}
    local elapsed=0
    
    log_step "Waiting for Docker daemon..."
    while ! docker ps >/dev/null 2>&1; do
        if [ $elapsed -ge $timeout ]; then
            log_error "Docker daemon did not start within $timeout seconds"
            return 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    log_success "Docker daemon ready"
    return 0
}

# Check if running in CI/automated mode
is_automated() {
    [[ -n "${CI:-}" ]] || [[ -n "${AUTOMATED:-}" ]]
}

# Template substitution
replace_placeholder() {
    local file=$1
    local placeholder=$2
    local value=$3
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|{{${placeholder}}}|${value}|g" "$file"
    else
        sed -i "s|{{${placeholder}}}|${value}|g" "$file"
    fi
}

# Create directory if it doesn't exist
ensure_dir() {
    local dir=$1
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
    fi
}

# Backup file if exists
backup_file() {
    local file=$1
    if [[ -f "$file" ]]; then
        local backup="${file}.backup.$(date +%Y%m%d-%H%M%S)"
        cp "$file" "$backup"
        log_info "Backed up existing file to: $backup"
    fi
}

# Check if service is running via docker compose
is_service_running() {
    local service_name=$1
    docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$service_name"
}

# Get macOS version
get_macos_version() {
    sw_vers -productVersion
}

# Get architecture
get_arch() {
    uname -m
}

# Check if Homebrew is installed
is_homebrew_installed() {
    command_exists brew
}

# Add to PATH for current session
add_to_path() {
    local path=$1
    if [[ ":$PATH:" != *":$path:"* ]]; then
        export PATH="$path:$PATH"
    fi
}

# Source shell RC file
reload_shell() {
    if [[ -f "$HOME/.zshrc" ]]; then
        source "$HOME/.zshrc" 2>/dev/null || true
    elif [[ -f "$HOME/.bashrc" ]]; then
        source "$HOME/.bashrc" 2>/dev/null || true
    fi
}

# Check internet connectivity
check_internet() {
    if ! ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        log_error "No internet connection detected"
        return 1
    fi
    return 0
}

# Get current timestamp (ISO 8601)
timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Log to file
log_to_file() {
    local log_file=$1
    local message=$2
    echo "[$(timestamp)] $message" >> "$log_file"
}

# Export functions for use in subshells
export -f log_info log_success log_warning log_error log_section log_step
export -f command_exists binary_exists confirm prompt prompt_secret
export -f wait_for_port wait_for_docker is_automated
export -f replace_placeholder ensure_dir backup_file
export -f is_service_running get_macos_version get_arch
export -f check_internet timestamp log_to_file
