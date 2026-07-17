#!/bin/bash

# Bybit Trading Bot - Setup and Run Script
# This script installs dependencies and runs the trading bot

set -e  # Exit on error

echo "========================================="
echo "  Bybit Trading Bot - Setup & Run"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "Please install Python 3.8+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"

# Check if version is 3.8 or higher
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
    echo "❌ Error: Python 3.8 or higher is required."
    exit 1
fi

echo ""
echo "Installing required packages..."
pip3 install --upgrade pip setuptools wheel
pip3 uninstall ccxt -y || true
pip3 install ccxt --no-cache-dir
pip3 install rich

echo ""
echo "✓ Dependencies installed successfully!"
echo ""

# Check if .env file exists, if not create a template
if [ ! -f ".env" ]; then
    echo "Creating .env template file..."
    cat > .env << EOF
# Bybit API Configuration
# Get your API keys from: https://testnet.bybit.com/app/api-keys (for testnet)
# or https://www.bybit.com/app/api-keys (for mainnet)

BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here

# Trading Settings
TEST_MODE=true
SYMBOL=BTC/USDT
TIMEFRAME=5m
LEVERAGE=3
STOP_LOSS_PCT=2.0
TAKE_PROFIT_PCT=4.0
RISK_PER_TRADE=1.0
EOF
    echo "✓ Created .env file with default settings"
    echo "⚠️  IMPORTANT: Edit .env file with your actual Bybit API credentials before running!"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

echo "========================================="
echo "  Starting Trading Bot..."
echo "========================================="
echo ""
echo "Press Ctrl+C to stop the bot"
echo ""

# Run the trading bot
python3 trading_bot.py
