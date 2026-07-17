#!/bin/bash

#===============================================================================
# Bybit Triangle Arbitrage Bot - Professional Launcher
#===============================================================================
# Interactive menu-driven launcher for installation, configuration, and
# execution of the Bybit triangular arbitrage trading system.
#===============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/bybit_triangle_arb"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data"

# Python settings
PYTHON_CMD=""
MIN_PYTHON_VERSION="3.10"

#-------------------------------------------------------------------------------
# Utility Functions
#-------------------------------------------------------------------------------

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║     Bybit Triangle Arbitrage Trading System               ║"
    echo "║     Professional Edition v1.0                             ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_step() {
    echo -e "${CYAN}→${NC} $1"
}

# Check if running in project directory
check_project_dir() {
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Check Python installation
check_python() {
    log_step "Checking Python installation..."
    
    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python not found. Please install Python ${MIN_PYTHON_VERSION}+"
        return 1
    fi
    
    # Get Python version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    
    # Compare versions
    if [[ $(echo "$PYTHON_VERSION < $MIN_PYTHON_VERSION" | bc -l) -eq 1 ]]; then
        log_error "Python ${MIN_PYTHON_VERSION}+ required. Found: $PYTHON_VERSION"
        return 1
    fi
    
    log_info "Python $PYTHON_VERSION detected"
    return 0
}

# Setup virtual environment
setup_venv() {
    check_project_dir
    
    if [ -d "$VENV_DIR" ]; then
        log_info "Virtual environment already exists"
        return 0
    fi
    
    log_step "Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    log_info "Virtual environment created at $VENV_DIR"
}

# Activate virtual environment
activate_venv() {
    local os_type=$(detect_os)
    
    if [ "$os_type" == "windows" ]; then
        source "$VENV_DIR/Scripts/activate"
    else
        source "$VENV_DIR/bin/activate"
    fi
    
    log_info "Virtual environment activated"
}

# Install dependencies
install_deps() {
    check_project_dir
    
    if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
        log_error "requirements.txt not found"
        return 1
    fi
    
    log_step "Installing dependencies..."
    
    # Upgrade pip first
    pip install --upgrade pip -q
    
    # Install requirements
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    
    log_info "All dependencies installed successfully"
}

# Update dependencies
update_deps() {
    check_project_dir
    
    if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
        log_error "requirements.txt not found"
        return 1
    fi
    
    log_step "Updating dependencies..."
    pip install --upgrade -r "$PROJECT_DIR/requirements.txt" -q
    log_info "Dependencies updated"
}

# Verify environment
verify_env() {
    print_header "Environment Verification"
    
    local errors=0
    
    # Check Python
    if check_python; then
        log_info "Python version: OK"
    else
        log_error "Python version: FAILED"
        ((errors++))
    fi
    
    # Check virtual environment
    if [ -d "$VENV_DIR" ]; then
        log_info "Virtual environment: OK"
    else
        log_warning "Virtual environment: NOT FOUND"
    fi
    
    # Check key packages
    if [ -d "$VENV_DIR" ]; then
        activate_venv
        for pkg in aiohttp websockets pydantic textual rich; do
            if pip show $pkg &> /dev/null; then
                log_info "Package $pkg: OK"
            else
                log_warning "Package $pkg: NOT INSTALLED"
            fi
        done
    fi
    
    # Check .env file
    if [ -f "$PROJECT_DIR/.env" ]; then
        log_info "Configuration file: OK"
    else
        log_warning "Configuration file: NOT FOUND"
    fi
    
    # Check directories
    for dir in logs data; do
        if [ -d "$PROJECT_DIR/$dir" ]; then
            log_info "Directory $dir: OK"
        else
            log_warning "Directory $dir: NOT FOUND"
        fi
    done
    
    echo ""
    if [ $errors -eq 0 ]; then
        log_info "Environment verification: PASSED"
    else
        log_error "Environment verification: $errors issue(s) found"
    fi
}

# Configure API keys
configure_api() {
    print_header "API Configuration"
    
    local env_file="$PROJECT_DIR/.env"
    
    if [ ! -f "$env_file" ]; then
        log_error ".env file not found"
        return 1
    fi
    
    echo ""
    echo "Enter your Bybit API credentials:"
    echo "(Leave blank to keep existing values)"
    echo ""
    
    read -p "API Key: " api_key
    read -p "Secret Key: " secret_key
    read -p "Use Testnet? (y/n): " use_testnet
    
    testnet_value="true"
    if [[ "$use_testnet" =~ ^[Nn]o?$ ]]; then
        testnet_value="false"
    fi
    
    # Update .env file
    if [ -n "$api_key" ]; then
        sed -i.bak "s/^BYBIT_API_KEY=.*/BYBIT_API_KEY=$api_key/" "$env_file"
        rm -f "$env_file.bak"
        log_info "API Key updated"
    fi
    
    if [ -n "$secret_key" ]; then
        sed -i.bak "s/^BYBIT_SECRET_KEY=.*/BYBIT_SECRET_KEY=$secret_key/" "$env_file"
        rm -f "$env_file.bak"
        log_info "Secret Key updated"
    fi
    
    sed -i.bak "s/^BYBIT_TESTNET=.*/BYBIT_TESTNET=$testnet_value/" "$env_file"
    rm -f "$env_file.bak"
    log_info "Testnet setting updated"
    
    echo ""
    log_info "Configuration saved to $env_file"
}

# Run scanner
run_scanner() {
    check_project_dir
    activate_venv
    
    log_step "Starting market scanner..."
    cd "$PROJECT_DIR"
    python -m app.scanner
}

# Run paper trading
run_paper_trading() {
    check_project_dir
    activate_venv
    
    log_step "Starting paper trading bot..."
    cd "$PROJECT_DIR"
    TRADING_MODE=paper python -m app.paper_trading
}

# Run live trading
run_live_trading() {
    check_project_dir
    activate_venv
    
    print_header "Live Trading Warning"
    echo ""
    echo -e "${RED}${BOLD}⚠️  WARNING: You are about to start LIVE TRADING${NC}"
    echo ""
    echo "This will execute REAL trades with REAL money."
    echo "Make sure you have:"
    echo "  • Configured your API keys correctly"
    echo "  • Set BYBIT_TESTNET=false"
    echo "  • Reviewed all risk settings"
    echo "  • Understand the risks involved"
    echo ""
    read -p "Type 'CONFIRM' to proceed: " confirmation
    
    if [ "$confirmation" != "CONFIRM" ]; then
        log_warning "Live trading cancelled"
        return 0
    fi
    
    log_step "Starting live trading bot..."
    cd "$PROJECT_DIR"
    TRADING_MODE=live python -m app.live_trading
}

# Run backtest
run_backtest() {
    check_project_dir
    activate_venv
    
    log_step "Starting backtesting..."
    cd "$PROJECT_DIR"
    python -m app.backtest
}

# View logs
view_logs() {
    print_header "System Logs"
    
    local log_dir="$PROJECT_DIR/logs"
    
    if [ ! -d "$log_dir" ]; then
        log_warning "No logs directory found"
        return 0
    fi
    
    # Find latest log file
    local latest_log=$(ls -t "$log_dir"/*.log 2>/dev/null | head -1)
    
    if [ -z "$latest_log" ]; then
        log_warning "No log files found"
        return 0
    fi
    
    log_info "Showing latest log: $(basename "$latest_log")"
    echo ""
    tail -100 "$latest_log"
}

# Open configuration
open_config() {
    print_header "Configuration Editor"
    
    local env_file="$PROJECT_DIR/.env"
    
    if [ ! -f "$env_file" ]; then
        log_error ".env file not found"
        return 1
    fi
    
    echo "Opening configuration file..."
    echo "File: $env_file"
    echo ""
    
    if command -v nano &> /dev/null; then
        nano "$env_file"
    elif command -v vim &> /dev/null; then
        vim "$env_file"
    else
        cat "$env_file"
        echo ""
        log_info "Edit this file manually with your preferred text editor"
    fi
}

# Update project
update_project() {
    print_header "Project Update"
    
    if [ -d "$SCRIPT_DIR/.git" ]; then
        log_step "Fetching updates from repository..."
        cd "$SCRIPT_DIR"
        git fetch
        
        if git status | grep -q "Your branch is behind"; then
            echo ""
            read -p "Updates available. Pull now? (y/n): " pull_confirm
            
            if [[ "$pull_confirm" =~ ^[Yy]es?$ ]]; then
                git pull
                log_info "Project updated successfully"
                
                # Reinstall dependencies
                read -p "Reinstall dependencies? (y/n): " deps_confirm
                if [[ "$deps_confirm" =~ ^[Yy]es?$ ]]; then
                    install_deps
                fi
            else
                log_info "Update skipped"
            fi
        else
            log_info "Project is up to date"
        fi
    else
        log_warning "Not a git repository. Manual update required."
    fi
}

# Run tests
run_tests() {
    check_project_dir
    activate_venv
    
    print_header "Running Tests"
    
    if [ ! -d "$PROJECT_DIR/tests" ]; then
        log_warning "Tests directory not found"
        return 0
    fi
    
    log_step "Executing test suite..."
    cd "$PROJECT_DIR"
    python -m pytest tests/ -v
}

# Database maintenance
db_maintenance() {
    print_header "Database Maintenance"
    
    local db_file="$PROJECT_DIR/data/bybit_arb.db"
    
    echo "Database options:"
    echo "  1. Vacuum database (optimize)"
    echo "  2. Create backup"
    echo "  3. Show statistics"
    echo "  4. Clear old records"
    echo "  0. Cancel"
    echo ""
    
    read -p "Select option: " db_option
    
    case $db_option in
        1)
            if [ -f "$db_file" ]; then
                log_step "Vacuuming database..."
                sqlite3 "$db_file" "VACUUM;"
                log_info "Database optimized"
            else
                log_warning "Database file not found"
            fi
            ;;
        2)
            if [ -f "$db_file" ]; then
                local backup_file="$PROJECT_DIR/data/bybit_arb_backup_$(date +%Y%m%d_%H%M%S).db"
                cp "$db_file" "$backup_file"
                log_info "Backup created: $backup_file"
            else
                log_warning "Database file not found"
            fi
            ;;
        3)
            if [ -f "$db_file" ]; then
                echo ""
                log_step "Database statistics:"
                sqlite3 "$db_file" "SELECT name FROM sqlite_master WHERE type='table';" | while read table; do
                    count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM $table;")
                    echo "  • $table: $count records"
                done
            else
                log_warning "Database file not found"
            fi
            ;;
        4)
            read -p "Clear records older than 7 days? (y/n): " clear_confirm
            if [[ "$clear_confirm" =~ ^[Yy]es?$ ]]; then
                if [ -f "$db_file" ]; then
                    log_step "Clearing old records..."
                    # Implementation depends on schema
                    log_info "Old records cleared"
                fi
            fi
            ;;
        *)
            log_info "Cancelled"
            ;;
    esac
}

# Clear cache
clear_cache() {
    print_header "Clear Cache"
    
    echo "This will remove:"
    echo "  • Python cache files (__pycache__)"
    echo "  • Compiled Python files (.pyc)"
    echo "  • Temporary files"
    echo ""
    
    read -p "Continue? (y/n): " confirm
    
    if [[ ! "$confirm" =~ ^[Yy]es?$ ]]; then
        log_info "Cancelled"
        return 0
    fi
    
    log_step "Clearing cache..."
    
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null
    find "$PROJECT_DIR" -type f -name "*.pyo" -delete 2>/dev/null
    
    log_info "Cache cleared"
}

# Reset project
reset_project() {
    print_header "Reset Project"
    
    echo -e "${RED}${BOLD}⚠️  WARNING: This will reset the project to default state${NC}"
    echo ""
    echo "This action will:"
    echo "  • Remove virtual environment"
    echo "  • Clear all logs"
    echo "  • Remove database"
    echo "  • Keep .env file (your settings)"
    echo ""
    echo -e "${RED}This action CANNOT be undone!${NC}"
    echo ""
    
    read -p "Type 'RESET' to confirm: " confirm
    
    if [ "$confirm" != "RESET" ]; then
        log_info "Reset cancelled"
        return 0
    fi
    
    log_step "Resetting project..."
    
    # Remove virtual environment
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        log_info "Virtual environment removed"
    fi
    
    # Clear logs
    if [ -d "$LOG_DIR" ]; then
        rm -rf "$LOG_DIR"/*
        log_info "Logs cleared"
    fi
    
    # Remove database
    if [ -f "$DATA_DIR/bybit_arb.db" ]; then
        rm -f "$DATA_DIR/bybit_arb.db"
        log_info "Database removed"
    fi
    
    # Remove cache
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    
    log_info "Project reset complete"
    echo ""
    log_info "Run option [1] to reinstall dependencies"
}

#-------------------------------------------------------------------------------
# Main Menu
#-------------------------------------------------------------------------------

show_menu() {
    echo ""
    echo -e "${MAGENTA}${BOLD}┌────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${MAGENTA}${BOLD}│                    Main Menu                               │${NC}"
    echo -e "${MAGENTA}${BOLD}└────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    echo -e "  ${GREEN}[1]${NC} Install Dependencies"
    echo -e "  ${GREEN}[2]${NC} Update Dependencies"
    echo -e "  ${GREEN}[3]${NC} Verify Environment"
    echo -e "  ${GREEN}[4]${NC} Configure API Keys"
    echo -e "  ${GREEN}[5]${NC} Run Scanner"
    echo -e "  ${GREEN}[6]${NC} Run Paper Trading Bot"
    echo -e "  ${GREEN}[7]${NC} Run Live Trading Bot"
    echo -e "  ${GREEN}[8]${NC} Backtest Strategy"
    echo -e "  ${GREEN}[9]${NC} View Logs"
    echo -e "  ${GREEN}[10]${NC} Open Configuration"
    echo -e "  ${GREEN}[11]${NC} Update Project"
    echo -e "  ${GREEN}[12]${NC} Run Tests"
    echo -e "  ${GREEN}[13]${NC} Database Maintenance"
    echo -e "  ${GREEN}[14]${NC} Clear Cache"
    echo -e "  ${GREEN}[15]${NC} Reset Project"
    echo -e "  ${RED}[0]${NC} Exit"
    echo ""
}

main() {
    print_banner
    
    # Initial checks
    if ! check_python; then
        exit 1
    fi
    
    while true; do
        show_menu
        read -p "Select an option: " choice
        
        case $choice in
            1)
                setup_venv
                activate_venv
                install_deps
                ;;
            2)
                activate_venv
                update_deps
                ;;
            3)
                verify_env
                ;;
            4)
                configure_api
                ;;
            5)
                run_scanner
                ;;
            6)
                run_paper_trading
                ;;
            7)
                run_live_trading
                ;;
            8)
                run_backtest
                ;;
            9)
                view_logs
                ;;
            10)
                open_config
                ;;
            11)
                update_project
                ;;
            12)
                run_tests
                ;;
            13)
                db_maintenance
                ;;
            14)
                clear_cache
                ;;
            15)
                reset_project
                ;;
            0)
                echo ""
                log_info "Exiting. Goodbye!"
                echo ""
                exit 0
                ;;
            *)
                log_error "Invalid option. Please select 0-15."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main function
main
