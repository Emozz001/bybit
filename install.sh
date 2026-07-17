#!/usr/bin/env bash
# =============================================================================
# Bybit AI Trading Platform - Unified Management Script
# Modern, production-ready installer and bot launcher
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration & Constants
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_DIR="$SCRIPT_DIR/venv"
readonly CONFIG_FILE="$SCRIPT_DIR/config/config.yaml"
readonly REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
readonly LOG_DIR="$SCRIPT_DIR/logs"
readonly DATA_DIR="$SCRIPT_DIR/data"
readonly BACKUP_DIR="$SCRIPT_DIR/backups"

# ANSI Color Codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# =============================================================================
# Logging & UI Functions
# =============================================================================

log_header() {
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error()   { echo -e "${RED}✗${NC} $1" >&2; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_info()    { echo -e "${BLUE}ℹ${NC} $1"; }

die() {
    log_error "$1"
    exit 1
}

# =============================================================================
# Utility Functions
# =============================================================================

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "Required command '$1' not found. Please install it first."
}

require_python() {
    require_command python3
    local version
    version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    
    if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 10 ]]; }; then
        die "Python 3.10+ required. Found: $version"
    fi
    log_success "Python $version detected"
}

ensure_directories() {
    log_info "Creating required directories..."
    mkdir -p "$LOG_DIR" "$DATA_DIR" "$BACKUP_DIR" "$SCRIPT_DIR/strategies" "$SCRIPT_DIR/plugins"
    log_success "Directories created"
}

activate_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        die "Virtual environment not found. Run '$0 install' first."
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
}

# =============================================================================
# Installation Functions
# =============================================================================

cmd_install() {
    log_header "INSTALLATION WIZARD"
    
    require_python
    ensure_directories
    
    # Create virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    else
        log_success "Virtual environment already exists"
    fi
    
    activate_venv
    
    # Install dependencies
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        log_info "Installing dependencies..."
        pip install --upgrade pip -qq
        pip install -r "$REQUIREMENTS_FILE" -qq
        log_success "Dependencies installed"
    else
        die "requirements.txt not found"
    fi
    
    # Create default config
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_info "Creating default configuration..."
        mkdir -p "$(dirname "$CONFIG_FILE")"
        cat > "$CONFIG_FILE" << 'EOF'
# Bybit AI Trading Platform Configuration
exchange:
  name: bybit
  testnet: true
  sandbox: true

trading:
  mode: paper

performance:
  profile: balanced
EOF
        log_success "Configuration created"
    else
        log_success "Configuration already exists"
    fi
    
    # Verify installation
    log_info "Verifying installation..."
    python3 -c "
try:
    from app.core.models import Symbol, OrderSide
    from app.core.config import Config, get_config
    from app.api.client import BybitAPIClient
    from app.exchange.websocket import WebSocketManager
    from main import TradingPlatform
    print('✓ All modules imported successfully')
except Exception as e:
    print(f'✗ Verification failed: {e}')
    exit(1)
" || die "Module verification failed"
    
    log_success "Installation complete!"
    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "  1. Edit config/config.yaml with your settings"
    echo "  2. Add API credentials to .env or config.yaml"
    echo "  3. Run '$0 start' to launch the bot"
}

cmd_update() {
    log_header "UPDATE PLATFORM"
    
    if [[ -d "$SCRIPT_DIR/.git" ]]; then
        git fetch origin
        git pull origin main
        log_success "Repository updated"
    else
        log_warning "Not a git repository"
    fi
}

cmd_upgrade_deps() {
    log_header "UPGRADE DEPENDENCIES"
    
    activate_venv
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        pip install --upgrade pip -qq
        pip install --upgrade -r "$REQUIREMENTS_FILE" -qq
        log_success "Dependencies upgraded"
    else
        die "requirements.txt not found"
    fi
}

cmd_uninstall() {
    log_header "UNINSTALL"
    
    read -rp "Are you sure? This will remove the virtual environment and cache. (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR" "$SCRIPT_DIR/__pycache__" "$SCRIPT_DIR/.pytest_cache"
        find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
        log_success "Uninstallation complete"
    else
        log_info "Uninstallation cancelled"
    fi
}

# =============================================================================
# Runtime Functions
# =============================================================================

cmd_start() {
    log_header "START TRADING BOT"
    
    activate_venv
    log_info "Starting trading platform..."
    python3 "$SCRIPT_DIR/main.py" "$@"
}

cmd_stop() {
    log_header "STOP TRADING BOT"
    pkill -f "python.*main.py" 2>/dev/null && log_success "Bot stopped" || log_warning "No running bot found"
}

cmd_scanner() {
    log_header "MARKET SCANNER"
    activate_venv
    log_warning "Market scanner coming soon"
}

cmd_backtest() {
    log_header "BACKTESTING"
    activate_venv
    log_warning "Backtesting engine coming soon"
}

cmd_dashboard() {
    log_header "DASHBOARD"
    activate_venv
    log_warning "Dashboard coming soon"
}

cmd_reports() {
    log_header "PERFORMANCE REPORTS"
    
    if [[ -f "$DATA_DIR/bybit_ai.db" ]]; then
        log_success "Trade history database found"
        activate_venv
        # TODO: Implement report generation
    else
        log_warning "No trade history yet"
    fi
}

# =============================================================================
# Configuration & Management
# =============================================================================

cmd_config() {
    log_header "CONFIGURATION"
    
    if [[ -f "$CONFIG_FILE" ]]; then
        echo -e "${BOLD}Current configuration:${NC}\n"
        cat "$CONFIG_FILE"
        echo ""
        read -rp "Edit configuration? (y/N): " edit
        if [[ "$edit" =~ ^[Yy]$ ]]; then
            "${EDITOR:-nano}" "$CONFIG_FILE"
        fi
    else
        log_warning "No configuration found. Run '$0 install' first."
    fi
}

cmd_env() {
    log_header "ENVIRONMENT VARIABLES"
    
    if [[ -f "$SCRIPT_DIR/.env" ]]; then
        "${EDITOR:-nano}" "$SCRIPT_DIR/.env"
    else
        log_info "Creating .env file..."
        touch "$SCRIPT_DIR/.env"
        "${EDITOR:-nano}" "$SCRIPT_DIR/.env"
    fi
}

cmd_paper_mode() {
    log_header "PAPER TRADING MODE"
    
    if [[ -f "$SCRIPT_DIR/.env" ]]; then
        sed -i.bak 's/TRADING_MODE=.*/TRADING_MODE=paper/' "$SCRIPT_DIR/.env" 2>/dev/null || true
        rm -f "$SCRIPT_DIR/.env.bak"
        log_success "Paper trading enabled"
    else
        log_warning ".env file not found"
    fi
}

cmd_backup() {
    log_header "CREATE BACKUP"
    
    local timestamp backup_file
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="$BACKUP_DIR/bybit_backup_$timestamp.tar.gz"
    
    tar -czf "$backup_file" config/ data/ 2>/dev/null || true
    log_success "Backup created: $backup_file"
}

cmd_restore() {
    log_header "RESTORE BACKUP"
    
    if [[ ! -d "$BACKUP_DIR" ]] || [[ -z "$(ls -A "$BACKUP_DIR"/*.tar.gz 2>/dev/null)" ]]; then
        log_warning "No backups found"
        return
    fi
    
    echo -e "${BOLD}Available backups:${NC}"
    ls -lh "$BACKUP_DIR"/*.tar.gz
    echo ""
    read -rp "Enter backup filename to restore: " backup_file
    
    if [[ -f "$BACKUP_DIR/$backup_file" ]]; then
        tar -xzf "$BACKUP_DIR/$backup_file"
        log_success "Backup restored"
    else
        log_error "Backup file not found"
    fi
}

# =============================================================================
# Interactive Menu
# =============================================================================

show_menu() {
    log_header "BYBIT AI TRADING TERMINAL"
    
    cat << EOF
${BOLD}CORE ACTIONS${NC}
  1) Start Trading Bot
  2) Stop Trading Bot
  3) Paper Trading Mode
  4) Market Scanner
  5) Run Backtest
  6) Performance Reports

${BOLD}CONFIGURATION${NC}
  7) Edit Settings
  8) Edit Environment (.env)
  9) Dashboard (Coming Soon)

${BOLD}MAINTENANCE${NC}
  10) Update Platform
  11) Upgrade Dependencies
  12) Create Backup
  13) Restore Backup

${BOLD}SYSTEM${NC}
  14) Uninstall
  0) Exit

EOF
}

cmd_menu() {
    while true; do
        show_menu
        read -rp "Select option: " choice
        
        case $choice in
            1) cmd_start ;;
            2) cmd_stop ;;
            3) cmd_paper_mode ;;
            4) cmd_scanner ;;
            5) cmd_backtest ;;
            6) cmd_reports ;;
            7) cmd_config ;;
            8) cmd_env ;;
            9) cmd_dashboard ;;
            10) cmd_update ;;
            11) cmd_upgrade_deps ;;
            12) cmd_backup ;;
            13) cmd_restore ;;
            14) cmd_uninstall ;;
            0|q|Q)
                log_info "Goodbye!"
                exit 0
                ;;
            *) log_error "Invalid option" ;;
        esac
        
        echo ""
        if [[ "${choice:-}" != "1" ]]; then
            read -rp "Press Enter to continue..."
        fi
    done
}

# =============================================================================
# CLI Interface
# =============================================================================

show_help() {
    cat << EOF
${BOLD}Bybit AI Trading Platform - Management Script${NC}

${BOLD}USAGE:${NC}
    $0 <command> [options]

${BOLD}COMMANDS:${NC}
    install         Install platform and dependencies
    start           Start the trading bot
    stop            Stop the trading bot
    update          Update platform from git
    upgrade         Upgrade Python dependencies
    config          View/edit configuration
    env             Edit environment variables
    paper           Enable paper trading mode
    backup          Create data backup
    restore         Restore from backup
    scanner         Run market scanner
    backtest        Run backtesting
    reports         View performance reports
    uninstall       Remove platform
    menu            Interactive menu (default)
    help            Show this help message

${BOLD}EXAMPLES:${NC}
    $0 install      # Full installation
    $0 start        # Launch trading bot
    $0 config       # Edit configuration
    $0 menu         # Interactive mode

EOF
}

# =============================================================================
# Main Entry Point
# =============================================================================

main() {
    cd "$SCRIPT_DIR"
    
    local command="${1:-menu}"
    shift || true
    
    case "$command" in
        install)     cmd_install "$@" ;;
        start)       cmd_start "$@" ;;
        stop)        cmd_stop ;;
        update)      cmd_update ;;
        upgrade)     cmd_upgrade_deps ;;
        config)      cmd_config ;;
        env)         cmd_env ;;
        paper)       cmd_paper_mode ;;
        backup)      cmd_backup ;;
        restore)     cmd_restore ;;
        scanner)     cmd_scanner ;;
        backtest)    cmd_backtest ;;
        reports)     cmd_reports ;;
        uninstall)   cmd_uninstall ;;
        menu)        cmd_menu ;;
        help|--help|-h) show_help ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
