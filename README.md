# Bybit AI Trading Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Enterprise-grade cryptocurrency trading platform for Bybit with modular architecture, 
async performance, and advanced risk management.

## Features

### Core Capabilities
- **Asynchronous Architecture**: Built with asyncio, aiohttp, and websockets for maximum performance
- **Real-time Market Data**: WebSocket streaming with automatic reconnection
- **REST API Client**: Rate-limited, retry-enabled API client with connection pooling
- **Modular Design**: Clean separation of concerns with single-responsibility modules

### Trading Features
- **Triangular Arbitrage**: Automated detection and execution of triangular arbitrage opportunities
- **Strategy Engine**: Plugin-based strategy system (EMA, RSI, MACD, etc.)
- **Smart Order Manager**: Support for Market, Limit, IOC, FOK, Post-Only orders
- **Paper Trading**: Realistic simulation with fees, slippage, and latency

### Risk Management
- Maximum daily loss limits
- Maximum drawdown protection
- Kelly Criterion position sizing
- ATR-based stop losses
- Trailing stops and take profits
- Kill switch functionality

### Performance Optimization
- Configurable performance profiles (Low, Balanced, High)
- Resource monitoring and throttling
- Connection pooling and caching
- Background task management

### Developer Experience
- Professional logging with loguru
- YAML configuration with env overrides
- SQLite database with SQLAlchemy
- Comprehensive type hints
- Pre-commit hooks for code quality

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bybit-ai-terminal.git
cd bybit-ai-terminal

# Run the installer
./install.sh
```

### Configuration

Edit `config/config.yaml`:

```yaml
exchange:
  name: bybit
  testnet: true
  api_key: your_api_key
  secret_key: your_secret_key

trading:
  mode: paper  # or 'live'

performance:
  profile: balanced  # low, balanced, high
```

### Running

```bash
# Using the installer menu
./install.sh
# Select option 4: Start Bot

# Or directly
python main.py
```

## Project Structure

```
bybit/
├── app/
│   ├── core/           # Core models and configuration
│   ├── api/            # REST API client
│   ├── exchange/       # WebSocket manager
│   ├── trading/        # Trading engine
│   ├── strategy/       # Strategy implementations
│   ├── scanner/        # Market scanner
│   ├── indicators/     # Technical indicators
│   ├── portfolio/      # Portfolio tracking
│   ├── database/       # Database layer
│   ├── risk/           # Risk management
│   ├── notifier/       # Notifications
│   ├── analytics/      # Analytics engine
│   ├── scheduler/      # Task scheduling
│   ├── utils/          # Utilities
│   └── ui/             # Terminal UI
├── config/             # Configuration files
├── data/               # Data storage
├── logs/               # Log files
├── plugins/            # User plugins
├── strategies/         # Custom strategies
├── tests/              # Test suite
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── backups/            # Backup files
├── main.py             # Entry point
├── install.sh          # Installer script
└── requirements.txt    # Dependencies
```

## Performance Profiles

| Profile | CPU Limit | Memory Limit | Use Case |
|---------|-----------|--------------|----------|
| Low     | 15%       | 256 MB       | MacBook Air 2017, Raspberry Pi |
| Balanced| 25%       | 512 MB       | Standard laptop/desktop |
| High    | 50%       | 1 GB         | Powerful workstation |

## Security

- API keys encrypted with Fernet
- Environment variable support
- Input validation
- Rate limiting
- Secure logging (secret masking)

## Testing

```bash
# Run tests
pytest tests/ -v --cov=app

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This software is for educational purposes only. Cryptocurrency trading involves 
substantial risk of loss. Always do your own research and never trade with money 
you cannot afford to lose.

## Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Discussions: GitHub Discussions
