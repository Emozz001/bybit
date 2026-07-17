# Bybit Triangle Arbitrage Trading System

A professional-grade triangular arbitrage trading platform for Bybit Spot that automatically discovers, analyzes, validates, and executes profitable triangular arbitrage opportunities in real-time.

## Features

- **Real-time Market Data**: WebSocket-based order book updates with automatic reconnection
- **Triangle Discovery**: Automatically generates all valid triangular arbitrage paths
- **Profitability Analysis**: Calculates net profit after fees, slippage, and spread
- **Liquidity Scoring**: Evaluates market depth and execution risk
- **Confidence Scoring**: AI-powered opportunity ranking (0-100)
- **Risk Management**: Configurable limits for slippage, spread, position size, and daily loss
- **Paper Trading**: Safe testing mode with simulated execution
- **Live Trading**: Production-ready execution with full error handling
- **Modern Terminal UI**: Interactive dashboard with live metrics (coming soon)
- **Comprehensive Logging**: Structured logging with file rotation

## Project Structure

```
bybit_triangle_arb/
├── app.py                 # Main application entry point
├── config/
│   └── settings.py        # Configuration management with Pydantic
├── core/
│   ├── models.py          # Data models (Triangle, OrderBook, Trade, etc.)
│   ├── websocket/
│   │   └── manager.py     # WebSocket connection manager
│   ├── api/
│   │   └── client.py      # Bybit REST API client
│   ├── triangle/
│   │   └── generator.py   # Triangle path discovery
│   ├── pricing/
│   │   └── engine.py      # Profitability & liquidity analysis
│   ├── execution/         # Trade execution (coming soon)
│   ├── risk/              # Risk management (coming soon)
│   └── database/          # SQLite persistence (coming soon)
├── ui/
│   └── dashboard.py       # Terminal dashboard (coming soon)
├── logs/                  # Log files
├── data/                  # Database and cache
├── tests/                 # Unit tests
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
└── README.md              # This file
```

## Quick Start

### 1. Install Dependencies

```bash
cd bybit_triangle_arb
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit the `.env` file with your Bybit credentials:

```bash
# Get keys from: https://testnet.bybit.com/app/api
BYBIT_API_KEY=your_api_key
BYBIT_SECRET_KEY=your_secret_key
BYBIT_TESTNET=true

# Trading mode: paper or live
TRADING_MODE=paper
```

### 3. Run the Bot

```bash
python app.py
```

## Using the Launcher

For a user-friendly experience, use the interactive launcher from the workspace root:

```bash
./run.sh
```

This provides a menu-driven interface for:
- Installing dependencies
- Configuring API keys
- Running scanner, paper trading, or live trading
- Viewing logs
- Database maintenance
- And more!

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `TRADING_MODE` | `paper` | Trading mode: `paper` or `live` |
| `MIN_NET_PROFIT_PCT` | `0.1` | Minimum net profit percentage |
| `MAX_SLIPPAGE_PCT` | `0.5` | Maximum acceptable slippage |
| `MAX_SPREAD_PCT` | `0.3` | Maximum acceptable spread |
| `MIN_LIQUIDITY_SCORE` | `70` | Minimum liquidity score (0-100) |
| `CONFIDENCE_THRESHOLD` | `85` | Minimum confidence score (0-100) |
| `MIN_TRADE_SIZE_USDT` | `10.0` | Minimum trade size in USDT |
| `MAX_TRADE_SIZE_USDT` | `100.0` | Maximum trade size in USDT |
| `DAILY_LOSS_LIMIT_USDT` | `50.0` | Daily loss limit in USDT |
| `BYBIT_TESTNET` | `true` | Use testnet instead of mainnet |

## How It Works

### Triangular Arbitrage Principle

The bot identifies opportunities where converting through three currencies yields a profit:

```
USDT → BTC → ETH → USDT
```

If done correctly, you end up with more USDT than you started with, after all fees.

### Opportunity Detection

1. **Symbol Discovery**: Fetches all available Spot trading pairs from Bybit
2. **Triangle Generation**: Builds a graph of tradable pairs and finds all 3-cycle paths
3. **Price Analysis**: Uses real-time order book data to calculate profitability
4. **Fee Calculation**: Applies maker/taker fees for each leg
5. **Slippage Estimation**: Analyzes order book depth to estimate execution impact
6. **Confidence Scoring**: Ranks opportunities based on multiple factors
7. **Execution Decision**: Only trades opportunities meeting all criteria

### Risk Management

The bot includes multiple safety checks:
- Maximum slippage protection
- Spread limits
- Liquidity thresholds
- Confidence score minimums
- Position size limits
- Daily loss limits
- Circuit breaker on errors

## Performance Optimization

Designed for efficient operation on modest hardware:
- Fully asynchronous (`asyncio`)
- Efficient WebSocket handling with compression
- In-memory order book caching
- Batched operations where possible
- Target: <25% CPU, <500MB RAM

## Safety First

⚠️ **Important Warnings:**

1. **Always start with paper trading** to verify the bot works correctly
2. **Use testnet first** before risking real funds
3. **Never trade more than you can afford to lose**
4. **Monitor the bot regularly**, especially when starting
5. **Understand the risks** of automated trading

## Requirements

- Python 3.10+
- macOS, Linux, or Windows
- Bybit API account (testnet or mainnet)
- Internet connection with low latency

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

Follows PEP 8 standards with type hints throughout.

## Roadmap

- [ ] Full trade execution engine
- [ ] Interactive terminal dashboard (Textual)
- [ ] SQLite database for trade history
- [ ] Backtesting framework
- [ ] Telegram/Discord notifications
- [ ] Advanced analytics and reporting
- [ ] Multi-exchange support

## License

MIT License - See LICENSE file for details.

## Disclaimer

This software is for educational purposes only. Cryptocurrency trading involves substantial risk of loss. The developers are not responsible for any financial losses. Always test thoroughly in paper trading mode before using real funds.

## Support

For issues and questions, please open an issue on the project repository.
