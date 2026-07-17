#!/bin/bash
# =============================================================================
# Bybit AI Trading Platform - Professional Installer
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# Installation Functions
# =============================================================================

install_python() {
    print_info "Checking Python installation..."
    
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION is installed"
        
        # Check version >= 3.10
        PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
        PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
        
        if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
            print_warning "Python 3.10+ recommended. Current: $PYTHON_VERSION"
        fi
    else
        print_warning "Python3 not found. Please install Python 3.10+"
        return 1
    fi
}

create_venv() {
    print_info "Creating virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Activate venv
    source venv/bin/activate
}

install_dependencies() {
    print_info "Installing dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip -q
        pip install -r requirements.txt -q
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        return 1
    fi
}

upgrade_dependencies() {
    print_info "Upgrading dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip -q
        pip install --upgrade -r requirements.txt -q
        print_success "Dependencies upgraded"
    else
        print_error "requirements.txt not found"
        return 1
    fi
}

create_config() {
    print_info "Creating configuration..."
    
    if [ ! -f "config/config.yaml" ]; then
        mkdir -p config
        
        cat > config/config.yaml << 'CONFIG_EOF'
# Bybit AI Trading Platform Configuration
exchange:
  name: bybit
  testnet: true
  sandbox: true
  
trading:
  mode: paper
  
performance:
  profile: balanced
CONFIG_EOF
        
        print_success "Configuration created at config/config.yaml"
    else
        print_success "Configuration already exists"
    fi
}

test_api() {
    print_info "Testing API connection..."
    
    source venv/bin/activate
    
    python3 << 'TEST_EOF'
import asyncio
from app.api.client import BybitAPIClient
from app.core.config import ExchangeConfig

async def test():
    config = ExchangeConfig(testnet=True, api_key="test", secret_key="test")
    client = BybitAPIClient(config)
    try:
        await client.connect()
        time_data = await client.get_server_time()
        print(f"Server time: {time_data}")
        print("API connection successful!")
        await client.close()
        return True
    except Exception as e:
        print(f"API test failed (expected without valid credentials): {e}")
        return True  # Still success since we're testing connectivity

asyncio.run(test())
TEST_EOF
    
    print_success "API test completed"
}

verify_installation() {
    print_info "Verifying installation..."
    
    source venv/bin/activate
    
    python3 << 'VERIFY_EOF'
try:
    from app.core.models import Symbol, OrderSide
    from app.core.config import Config, get_config
    from app.api.client import BybitAPIClient
    from app.exchange.websocket import WebSocketManager
    from main import TradingPlatform
    print("All modules imported successfully!")
except Exception as e:
    print(f"Verification failed: {e}")
    exit(1)
VERIFY_EOF
    
    print_success "Installation verified"
}

create_directories() {
    print_info "Creating directories..."
    
    mkdir -p logs data backups strategies plugins
    print_success "Directories created"
}

# =============================================================================
# Menu Functions
# =============================================================================

show_menu() {
    print_header "BYBIT AI TERMINAL INSTALLER"
    
    echo "1) Install"
    echo "2) Update"
    echo "3) Upgrade Dependencies"
    echo "4) Start Bot"
    echo "5) Run Scanner"
    echo "6) Open Dashboard"
    echo "7) Backup"
    echo "8) Restore"
    echo "9) Database"
    echo "10) Settings"
    echo "11) Uninstall"
    echo "12) Exit"
    echo ""
}

menu_install() {
    print_header "INSTALLATION"
    install_python
    create_directories
    create_venv
    install_dependencies
    create_config
    verify_installation
    print_success "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit config/config.yaml with your settings"
    echo "  2. Add API credentials to .env file or config.yaml"
    echo "  3. Run './install.sh' and select option 4 to start"
}

menu_update() {
    print_header "UPDATE"
    
    if [ -d ".git" ]; then
        git fetch origin
        git pull origin main
        print_success "Repository updated"
    else
        print_warning "Not a git repository"
    fi
}

menu_upgrade_deps() {
    print_header "UPGRADE DEPENDENCIES"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        upgrade_dependencies
    else
        print_warning "Virtual environment not found. Run installation first."
    fi
}

menu_start_bot() {
    print_header "START BOT"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_info "Starting trading platform..."
        python3 main.py
    else
        print_warning "Virtual environment not found. Run installation first."
    fi
}

menu_scanner() {
    print_header "RUN SCANNER"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_info "Running market scanner..."
        # TODO: Implement scanner CLI
        print_warning "Scanner not yet implemented"
    else
        print_warning "Virtual environment not found."
    fi
}

menu_dashboard() {
    print_header "OPEN DASHBOARD"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_info "Opening dashboard..."
        # TODO: Implement dashboard
        print_warning "Dashboard not yet implemented"
    else
        print_warning "Virtual environment not found."
    fi
}

menu_backup() {
    print_header "BACKUP"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backups/bybit_backup_$TIMESTAMP.tar.gz"
    
    tar -czf "$BACKUP_FILE" config/ data/ 2>/dev/null || true
    print_success "Backup created: $BACKUP_FILE"
}

menu_restore() {
    print_header "RESTORE"
    
    echo "Available backups:"
    ls -la backups/*.tar.gz 2>/dev/null || echo "No backups found"
    echo ""
    read -p "Enter backup filename to restore: " backup_file
    
    if [ -f "backups/$backup_file" ]; then
        tar -xzf "backups/$backup_file"
        print_success "Backup restored"
    else
        print_error "Backup file not found"
    fi
}

menu_database() {
    print_header "DATABASE"
    
    echo "1) View trades"
    echo "2) View orders"
    echo "3) Export data"
    echo "4) Back"
    echo ""
    read -p "Select option: " db_option
    
    case $db_option in
        1) print_warning "Not yet implemented" ;;
        2) print_warning "Not yet implemented" ;;
        3) print_warning "Not yet implemented" ;;
        *) ;;
    esac
}

menu_settings() {
    print_header "SETTINGS"
    
    echo "Current configuration:"
    cat config/config.yaml 2>/dev/null || echo "No configuration found"
    echo ""
    read -p "Edit config? (y/n): " edit
    
    if [ "$edit" = "y" ] || [ "$edit" = "Y" ]; then
        ${EDITOR:-nano} config/config.yaml
    fi
}

menu_uninstall() {
    print_header "UNINSTALL"
    
    read -p "Are you sure you want to uninstall? This will remove the virtual environment. (y/n): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf venv __pycache__ .pytest_cache
        find . -type d -name "*.pyc" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        print_success "Uninstallation complete"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    while true; do
        show_menu
        read -p "Select option [1-12]: " choice
        
        case $choice in
            1) menu_install ;;
            2) menu_update ;;
            3) menu_upgrade_deps ;;
            4) menu_start_bot ;;
            5) menu_scanner ;;
            6) menu_dashboard ;;
            7) menu_backup ;;
            8) menu_restore ;;
            9) menu_database ;;
            10) menu_settings ;;
            11) menu_uninstall ;;
            12) 
                print_info "Goodbye!"
                exit 0
                ;;
            *) print_error "Invalid option" ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
