# Bybit Triangular Arbitrage Bot - Setup & Usage Guide

## 🚀 Quick Start for Demo Trading

### 1. Get Your Bybit Demo Credentials

1. Go to [Bybit Testnet](https://testnet.bybit.com/)
2. Register/Login with your account
3. Navigate to **API Management**
4. Create a new API key with:
   - **Spot Trading** permissions enabled
   - IP whitelist (optional but recommended)
5. Copy your **API Key** and **API Secret**

### 2. Configure the Bot

#### Option A: Environment Variables (Recommended)
```bash
export BYBIT_API_KEY="your_demo_api_key"
export BYBIT_API_SECRET="your_demo_api_secret"
export MAX_TRADE_AMOUNT=50.0
export MIN_PROFIT_PERCENT=0.3
export MAX_DAILY_LOSS=20.0
```

#### Option B: Edit the Config Directly
Open `bybit_triangular_arb.py` and update lines 35-36:
```python
API_KEY = "your_demo_api_key_here"
API_SECRET = "your_demo_api_secret_here"
USE_TESTNET = True  # Keep this TRUE for demo trading
```

### 3. Run the Bot

```bash
# Install dependencies if needed
pip install aiohttp

# Run in simulation mode first (SAFE)
python bybit_triangular_arb.py
```

## 📊 Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_TRADE_AMOUNT_USDT` | 50.0 | Amount per trade (lower = safer) |
| `MIN_PROFIT_PERCENT` | 0.3 | Minimum profit % to trigger trade |
| `MAX_DAILY_LOSS_USDT` | 20.0 | Stop trading if daily loss exceeds this |
| `MAX_DAILY_TRADES` | 20 | Maximum trades per day |
| `MAX_CONSECUTIVE_ERRORS` | 3 | Stop after N errors |
| `MAX_CONSECUTIVE_LOSSES` | 5 | Stop after N losing trades |
| `COOLDOWN_AFTER_LOSS_SEC` | 60.0 | Wait time after a loss |
| `SCAN_INTERVAL` | 2.0 | Seconds between market scans |
| `CACHE_TTL` | 0.8 | Ticker cache duration (seconds) |

## 🛡️ Safety Features

✅ **Simulation Mode First** - Bot starts in safe simulation mode  
✅ **Daily Loss Limit** - Auto-stops if losses exceed threshold  
✅ **Trade Limits** - Maximum trades per day  
✅ **Cooldown Period** - Waits after losses to prevent revenge trading  
✅ **Error Handling** - Stops after consecutive errors  
✅ **Emergency Close** - Auto-closes positions if leg fails  
✅ **Testnet Support** - Built-in support for Bybit demo environment  

## 🔄 How It Works

1. **Scans** all USDT pairs every 2 seconds
2. **Detects** triangular arbitrage opportunities:
   - USDT → Coin A → Coin B → USDT
3. **Calculates** profit after fees (3 trades × 0.1% fee)
4. **Executes** only if profit > minimum threshold
5. **Tracks** all trades with detailed statistics

## 📈 Understanding the Output

```
============================================================
🚀 Bybit Triangular Arb Bot Started (DEMO MODE)
============================================================
Base URL: https://api-testnet.bybit.com
Scan Interval: 2.0s | Min Profit: 0.3%
Max Trade Amount: $50.0 | Max Daily Loss: $20.0
Max Daily Trades: 20 | Cooldown After Loss: 60.0s
============================================================
✅ Loaded 350 valid USDT pairs
🔄 Starting main loop...
🔍 Scanning... (350 pairs) | Scans: 20 | Opps: 0 | Trades: 0 | P&L: $0.0000
💰 OPPORTUNITY FOUND!
   Path: USDT->BTC->ETH->USDT
   Expected Profit: 0.45%
   Trade Amount: $50.00
   Est. Profit: $0.2250
============================================================
✅ SIMULATED: Profit $0.1912 (Win #1)
```

## ⚠️ Important Warnings

1. **Always test in simulation mode first** (`LIVE_MODE = False`)
2. **Triangular arbitrage is highly competitive** - profits are rare
3. **Market moves fast** - opportunities may disappear before execution
4. **Fees matter** - 3 trades × 0.1% = 0.3% minimum just to break even
5. **Demo ≠ Real** - testnet has different liquidity than mainnet
6. **Never risk more than you can afford to lose**

## 🔧 Troubleshooting

### "No valid tickers received"
- Check your internet connection
- Verify API keys are correct
- Ensure testnet is accessible

### "Failed to load symbols"
- API may be rate-limited, wait a moment
- Check if testnet is operational

### No opportunities found
- This is normal! True arb opportunities are rare
- Lower `MIN_PROFIT_PERCENT` slightly (but not below 0.3%)
- Market conditions change constantly

### Orders failing in live mode
- Ensure API key has Spot Trading permissions
- Check account has sufficient balance
- Verify symbol names are correct

## 📝 Performance Tips

1. **Run on a VPS** close to Bybit servers for lower latency
2. **Use WebSocket** instead of REST for faster data (advanced)
3. **Optimize scan interval** - balance between speed and rate limits
4. **Monitor regularly** - don't set and forget

## 💡 Next Steps

1. ✅ Run in simulation mode for at least 24 hours
2. 📊 Analyze the trade statistics and win rate
3. 🔬 Adjust parameters based on results
4. 🧪 Test with small amounts on testnet live mode
5. 📈 Only consider real trading after consistent testnet profits

---

**Remember**: This bot is for educational purposes. Cryptocurrency trading involves significant risk. Past performance does not guarantee future results.
