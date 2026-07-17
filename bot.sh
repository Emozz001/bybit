#!/bin/bash
# =============================================================================
# BYBIT AI TRADING PLATFORM - BOT LAUNCHER
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${CYAN}==================================${NC}"
    echo -e "${CYAN}     BYBIT AI TRADING BOT${NC}"
    echo -e "${CYAN}==================================${NC}"
    echo ""
}

show_menu() {
    print_header
    
    # Get balance info if available
    BALANCE="N/A"
    STATUS="READY"
    
    echo "Balance: $BALANCE"
    echo "Status: $STATUS"
    echo ""
    echo "1. Start Trading"
    echo "2. Stop Trading"
    echo "3. Paper Trading Mode"
    echo "4. Run Backtest"
    echo "5. Market Scanner"
    echo "6. Performance Report"
    echo "7. Strategy Manager"
    echo "8. Risk Settings"
    echo "9. API Settings"
    echo "10. Update System"
    echo "11. Exit"
    echo ""
}

start_bot() {
    echo -e "${BLUE}Starting trading platform...${NC}"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        python main.py --tui
    else
        echo -e "${YELLOW}Virtual environment not found. Running installer first...${NC}"
        bash install.sh
    fi
}

stop_bot() {
    echo -e "${YELLOW}Stopping trading bot...${NC}"
    pkill -f "python.*main.py" 2>/dev/null || true
    echo -e "${GREEN}Bot stopped${NC}"
}

run_scanner() {
    echo -e "${BLUE}Running market scanner...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
        python -c "print('Market Scanner - Coming Soon')"
    fi
}

run_backtest() {
    echo -e "${BLUE}Running backtest...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
        python -c "print('Backtesting Engine - Coming Soon')"
    fi
}

show_reports() {
    echo -e "${BLUE}Performance Reports${NC}"
    if [ -f "data/bybit_ai.db" ]; then
        echo "Database found - reports available"
    else
        echo "No trade history yet"
    fi
}

update_system() {
    echo -e "${BLUE}Checking for updates...${NC}"
    if [ -d ".git" ]; then
        git fetch origin
        git pull origin main
        echo -e "${GREEN}Update complete${NC}"
    else
        echo -e "${YELLOW}Not a git repository${NC}"
    fi
}

# Main loop
while true; do
    show_menu
    read -p "Select option: " choice
    
    case $choice in
        1) start_bot ;;
        2) stop_bot ;;
        3) 
            echo "Switching to paper trading mode..."
            sed -i.bak 's/TRADING_MODE=.*/TRADING_MODE=paper/' .env 2>/dev/null || true
            echo -e "${GREEN}Paper trading enabled${NC}"
            ;;
        4) run_backtest ;;
        5) run_scanner ;;
        6) show_reports ;;
        7) echo "Strategy Manager - Coming Soon" ;;
        8) nano config/config.yaml 2>/dev/null || echo "Edit config/config.yaml manually" ;;
        9) nano .env 2>/dev/null || echo "Edit .env manually" ;;
        10) update_system ;;
        11|q|Q)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
done
