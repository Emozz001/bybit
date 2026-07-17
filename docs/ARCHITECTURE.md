# Bybit AI Trading Platform - Architecture Documentation

## Overview

The Bybit AI Trading Platform is designed as a modular, event-driven system built on Python's asyncio framework. The architecture emphasizes:

1. **Separation of Concerns** - Each module has a single responsibility
2. **Asynchronous Operations** - Non-blocking I/O for maximum throughput
3. **Fault Tolerance** - Automatic retry, reconnection, and error handling
4. **Resource Awareness** - Configurable performance profiles for different hardware

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py                                   │
│                    TradingPlatform                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Event Loop                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │   Scanner   │  │  Strategy   │  │  Risk Manager   │   │  │
│  │  │   Engine    │  │   Engine    │  │                 │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │   Order     │  │  Portfolio  │  │   Notifier      │   │  │
│  │  │   Manager   │  │   Tracker   │  │                 │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────────────┐
│   API Client    │    │   WebSocket Manager     │
│   (REST)        │    │   (Real-time Data)      │
└─────────────────┘    └─────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────────┐
│              Bybit Exchange API                  │
└─────────────────────────────────────────────────┘
```

## Module Descriptions

### Core (`app/core/`)

Central data models and configuration management.

**Key Components:**
- `models.py` - All data classes (Order, Trade, Position, Signal, etc.)
- `config.py` - YAML configuration with environment overrides

### API (`app/api/`)

REST API client for Bybit exchange.

**Features:**
- HMAC SHA256 authentication
- Rate limiting with configurable limits
- Automatic retry with exponential backoff
- Connection pooling via aiohttp

**Usage:**
```python
from app.api.client import BybitAPIClient
from app.core.config import ExchangeConfig

config = ExchangeConfig(api_key="...", secret_key="...")
client = BybitAPIClient(config)
await client.connect()

# Get market data
orderbook = await client.get_orderbook("BTCUSDT")
tickers = await client.get_tickers()

# Place order
order = await client.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    qty=0.001,
    price=50000
)
```

### Exchange (`app/exchange/`)

WebSocket manager for real-time market data.

**Features:**
- Automatic reconnection with exponential backoff
- Ping/pong heartbeat monitoring
- Multiple channel subscriptions
- Local order book cache

**Usage:**
```python
from app.exchange.websocket import WebSocketManager

ws = WebSocketManager(config)
await ws.connect("wss://stream.bybit.com/v5/public/spot")
await ws.subscribe(["orderbook.50.BTCUSDT", "tickers.BTCUSDT"])

# Access cached data
bid = ws.get_best_bid("BTCUSDT")
ask = ws.get_best_ask("BTCUSDT")
```

### Trading (`app/trading/`)

Core trading engine and order execution.

**Responsibilities:**
- Opportunity validation
- Order placement and monitoring
- Position management
- Trade lifecycle tracking

### Strategy (`app/strategy/`)

Plugin-based strategy system.

**Built-in Strategies:**
- EMA Crossover
- RSI Divergence
- MACD Signal
- Triangular Arbitrage

**Creating Custom Strategy:**
```python
from app.strategy.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def analyze(self, data: MarketData) -> Signal:
        # Your logic here
        return Signal(
            signal_type=SignalType.BUY,
            confidence=85.0,
            entry_price=data.price
        )
```

### Scanner (`app/scanner/`)

Market opportunity scanner.

**Scan Types:**
- Volatility analysis
- Liquidity detection
- Breakout identification
- Reversal patterns
- Trend continuation
- Funding rate opportunities
- Volume spikes
- Order book imbalance

### Risk (`app/risk/`)

Risk management engine.

**Features:**
- Daily loss limits
- Maximum drawdown protection
- Kelly Criterion position sizing
- ATR-based stop losses
- Trailing stops
- Kill switch

### Database (`app/database/`)

SQLite database layer using SQLAlchemy.

**Tables:**
- trades - Trade history
- orders - Order records
- positions - Open positions
- signals - Generated signals
- performance - Performance metrics

### Notifier (`app/notifier/`)

Multi-channel notification system.

**Channels:**
- Telegram
- Discord
- Email
- Webhook

### UI (`app/ui/`)

Terminal user interface using Textual.

**Views:**
- Dashboard - Real-time status
- Positions - Open positions
- Orders - Order history
- Settings - Configuration

## Data Flow

### Trade Execution Flow

```
1. Scanner detects opportunity
         │
         ▼
2. Strategy generates signal
         │
         ▼
3. Risk manager validates
         │
         ▼
4. Order manager places order
         │
         ▼
5. WebSocket confirms fill
         │
         ▼
6. Database records trade
         │
         ▼
7. Notifier sends alert
```

### Market Data Flow

```
Bybit WebSocket
       │
       ▼
WebSocketManager
       │
       ├──► Order Book Cache
       ├──► Ticker Cache
       └──► Strategy Engines
               │
               ▼
           Signal Generation
```

## Performance Optimization

### Connection Pooling

```python
# aiohttp session with connection pooling
connector = aiohttp.TCPConnector(
    limit=10,
    limit_per_host=5,
    ttl_dns_cache=300,
    use_dns_cache=True,
)
```

### Caching Strategy

```python
# LRU cache for frequently accessed data
@lru_cache(maxsize=1000)
def get_symbol_info(symbol: str) -> Symbol:
    ...
```

### Async Operations

All I/O operations are async:
- HTTP requests (aiohttp)
- WebSocket connections (websockets)
- Database queries (aiosqlite)
- File operations (aiofiles)

## Error Handling

### Retry Logic

```python
async def _request(self, method, endpoint, params, retry_count=3):
    for attempt in range(retry_count):
        try:
            return await self._do_request(method, endpoint, params)
        except RateLimitExceeded:
            await asyncio.sleep(2 ** attempt)
        except ConnectionError:
            if attempt == retry_count - 1:
                raise
            await asyncio.sleep(1)
```

### Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.recovery_time = recovery_time
        self.last_failure = None
    
    async def call(self, func, *args):
        if self.is_open():
            raise CircuitOpenError()
        try:
            result = await func(*args)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise
```

## Security

### API Key Encryption

```python
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()
```

### Input Validation

All user inputs are validated:
- Type checking
- Range validation
- Sanitization

## Testing Strategy

### Unit Tests

```python
import pytest
from app.core.models import Order, OrderSide

def test_order_creation():
    order = Order(
        order_id="test-123",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=0.001
    )
    assert order.symbol == "BTCUSDT"
    assert order.side == OrderSide.BUY
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_api_connection():
    config = ExchangeConfig(testnet=True)
    client = BybitAPIClient(config)
    await client.connect()
    time_data = await client.get_server_time()
    assert time_data is not None
    await client.close()
```

## Deployment

### Development

```bash
./install.sh  # Select option 1
python main.py
```

### Production

```bash
# Set environment variables
export BYBIT_API_KEY=your_key
export BYBIT_SECRET_KEY=your_secret
export TRADING_MODE=live

# Run with supervisor or systemd
supervisorctl start bybit-ai
```

### Docker (Future)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## Monitoring

### Health Checks

```python
health = SystemHealth(
    is_healthy=True,
    cpu_usage_percent=15.2,
    memory_usage_mb=256,
    active_connections=10,
    uptime_seconds=3600
)
```

### Metrics Collection

- Request latency
- Order execution time
- Win rate
- PnL tracking
- Error rates

## Future Enhancements

1. **Multi-exchange support** - Binance, Bitget, OKX
2. **Machine Learning** - RL-based strategies
3. **Web Dashboard** - FastAPI + React
4. **Mobile App** - Companion iOS/Android app
5. **Cloud Sync** - Configuration backup to cloud
6. **Advanced Analytics** - More detailed performance metrics
