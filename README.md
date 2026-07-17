# Bybit Trading Bot

A Python-based cryptocurrency trading bot for Bybit with a beautiful terminal UI.

## Features

- **Real-time Market Data**: Live price, volume, and 24h change from Bybit
- **Technical Indicators**: SMA (20/50) and RSI (14) calculations
- **Risk Management**: 
  - Configurable stop-loss (default 2%)
  - Take-profit targets (default 4%, 1:2 risk/reward)
  - Position sizing based on account risk %
  - Low leverage settings (default 3x)
- **Beautiful Terminal UI**: Real-time dashboard using Rich library
- **Test Mode**: Safe simulation mode before live trading

## Installation

### Prerequisites
- Python 3.8+
- macOS/Linux terminal

### Install Dependencies
```bash
pip install ccxt rich
```

## Configuration

### 1. Set API Keys (Recommended - Secure)
```bash
export BYBIT_API_KEY="your_api_key_here"
export BYBIT_SECRET="your_secret_here"
```

### 2. Edit Trading Parameters
Open `trading_bot.py` and modify these values:

```python
SYMBOL = "BTC/USDT"      # Trading pair
TIMEFRAME = "5m"         # Candlestick timeframe  
LEVERAGE = 3             # Low leverage for safety
RISK_PER_TRADE = 0.01    # Risk 1% per trade
STOP_LOSS_PCT = 0.02     # 2% stop loss
TAKE_PROFIT_PCT = 0.04   # 4% take profit
TEST_MODE = True         # Keep TRUE for testing!
```

## Running the Bot

### Test Mode (Recommended First)
```bash
python3 trading_bot.py
```

### Live Trading (After Testing)
1. Set your API keys via environment variables
2. Change `TEST_MODE = False` in the script
3. Run: `python3 trading_bot.py`

## Strategy

The bot uses a conservative trend-following strategy:

**BUY Signal:**
- Price > SMA(20) > SMA(50)
- RSI between 50-70 (trend confirmation, not overbought)

**SELL Signal:**
- Price < SMA(20) < SMA(50)  
- RSI between 30-50 (trend confirmation, not oversold)

**Exit Conditions:**
- Stop Loss: 2% loss from entry
- Take Profit: 4% gain from entry

## Important Warnings

⚠️ **CRYPTOCURRENCY TRADING IS HIGHLY RISKY**

1. **Never trade with money you cannot afford to lose**
2. This bot is for **educational purposes only**
3. Always backtest strategies before live trading
4. Start with TEST_MODE enabled
5. Use small position sizes initially
6. Monitor the bot regularly
7. Past performance does not guarantee future results

## API Key Setup (Bybit)

1. Go to https://testnet.bybit.com/ for testing
2. Or https://www.bybit.com/ for live trading
3. Create API keys with:
   - Enable Futures Trading
   - Enable Reading (for market data)
   - IP whitelist (recommended)
   - Withdrawal permissions: DISABLED

## Stopping the Bot

Press `Ctrl+C` in the terminal to safely stop the bot.

## Troubleshooting

**Connection Errors:**
- Check your API keys are correct
- Ensure you have internet connection
- Verify Bybit API status

**No Trades Executing:**
- Check if market conditions match strategy signals
- Review indicator values in the UI
- Adjust strategy parameters if needed

## Disclaimer

This software is provided "as is" without warranty of any kind. The developers are not responsible for any financial losses. Use at your own risk.
