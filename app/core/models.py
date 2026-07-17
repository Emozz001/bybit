"""
Core data models for the Bybit AI Trading Platform.
Defines all data structures used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import uuid


# =============================================================================
# ENUMERATIONS
# =============================================================================

class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "Buy"
    SELL = "Sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "Market"
    LIMIT = "Limit"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "PostOnly"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class TradeStatus(str, Enum):
    """Trade status enumeration."""
    SCANNING = "scanning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class PositionSide(str, Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"
    NONE = "none"


class TimeInForce(str, Enum):
    """Time in force enumeration."""
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    GTD = "GTD"  # Good Till Date


class SignalType(str, Enum):
    """Signal type enumeration."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class StrategyType(str, Enum):
    """Strategy type enumeration."""
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    VWAP = "vwap"
    SUPER_TREND = "super_trend"
    BOLLINGER = "bollinger"
    ORDER_FLOW = "order_flow"
    VOLUME_PROFILE = "volume_profile"
    FAIR_VALUE_GAP = "fvg"
    ICT = "ict"
    SMART_MONEY = "smart_money"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    MARKET_STRUCTURE = "market_structure"
    SUPPORT_RESISTANCE = "support_resistance"
    FUNDING_RATE = "funding_rate"
    OPEN_INTEREST = "open_interest"
    ML_SIGNAL = "ml_signal"
    TRIANGULAR_ARB = "triangular_arb"


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    """Notification type enumeration."""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    PROFIT = "profit"
    LOSS = "loss"
    LIQUIDATION_WARNING = "liquidation_warning"
    RISK_WARNING = "risk_warning"
    CONNECTION_LOST = "connection_lost"
    API_FAILURE = "api_failure"
    DAILY_SUMMARY = "daily_summary"


# =============================================================================
# MARKET DATA MODELS
# =============================================================================

@dataclass(frozen=True)
class Symbol:
    """Represents a trading symbol on an exchange."""
    symbol: str
    base_asset: str
    quote_asset: str
    tick_size: float
    lot_size: float
    min_order_qty: float
    max_order_qty: float
    price_precision: int
    qty_precision: int
    is_active: bool = True
    exchange: str = "bybit"
    category: str = "spot"  # spot, linear, inverse, option

    def __post_init__(self):
        if self.price_precision < 0 or self.qty_precision < 0:
            raise ValueError("Precision values must be non-negative")


@dataclass
class OrderBookLevel:
    """Single level in an order book."""
    price: float
    quantity: float
    order_count: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrderBook:
    """Order book snapshot for a symbol."""
    symbol: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence: int = 0
    exchange: str = "bybit"

    @property
    def best_bid(self) -> Optional[float]:
        """Get best bid price."""
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        """Get best ask price."""
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> Optional[float]:
        """Get mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def spread(self) -> Optional[float]:
        """Get bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None

    @property
    def spread_pct(self) -> Optional[float]:
        """Get spread as percentage of mid price."""
        if self.mid_price and self.spread:
            return (self.spread / self.mid_price) * 100
        return None

    def get_liquidity_at_price(self, side: OrderSide, price: float, qty: float) -> bool:
        """Check if there's sufficient liquidity at a given price."""
        levels = self.bids if side == OrderSide.SELL else self.asks
        remaining_qty = qty

        for level in levels:
            if side == OrderSide.SELL and level.price < price:
                break
            if side == OrderSide.BUY and level.price > price:
                break
            remaining_qty -= level.quantity
            if remaining_qty <= 0:
                return True

        return False

    def estimate_slippage(self, side: OrderSide, qty: float) -> float:
        """Estimate slippage for a given order size."""
        levels = self.bids if side == OrderSide.SELL else self.asks
        if not levels:
            return float('inf')

        reference_price = self.mid_price or levels[0].price
        remaining_qty = qty
        total_value = 0.0
        filled_qty = 0.0

        for level in levels:
            fill_qty = min(remaining_qty, level.quantity)
            total_value += fill_qty * level.price
            filled_qty += fill_qty
            remaining_qty -= fill_qty
            if remaining_qty <= 0:
                break

        if filled_qty == 0:
            return float('inf')

        avg_price = total_value / filled_qty
        slippage = abs(avg_price - reference_price) / reference_price * 100
        return slippage

    def get_depth(self, levels: int = 10) -> Dict[str, float]:
        """Get order book depth up to N levels."""
        bid_depth = sum(level.quantity for level in self.bids[:levels])
        ask_depth = sum(level.quantity for level in self.asks[:levels])
        return {"bids": bid_depth, "asks": ask_depth, "total": bid_depth + ask_depth}


@dataclass
class Ticker:
    """Ticker data for a symbol."""
    symbol: str
    last_price: float
    bid_price: float
    ask_price: float
    volume_24h: float
    turnover_24h: float
    high_24h: float
    low_24h: float
    price_change_24h: float
    price_change_pct_24h: float
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Candle:
    """OHLCV candle data."""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float
    start_time: datetime
    end_time: datetime
    interval: str = "1m"  # 1m, 5m, 15m, 1h, 4h, 1d, etc.


# =============================================================================
# TRIANGULAR ARBITRAGE MODELS
# =============================================================================

@dataclass(frozen=True)
class Triangle:
    """Represents a triangular arbitrage path."""
    id: str
    leg1_symbol: str  # e.g., BTCUSDT
    leg2_symbol: str  # e.g., ETHBTC
    leg3_symbol: str  # e.g., ETHUSDT
    leg1_side: OrderSide
    leg2_side: OrderSide
    leg3_side: OrderSide
    start_asset: str  # e.g., USDT
    middle_asset1: str  # e.g., BTC
    middle_asset2: str  # e.g., ETH
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, leg1: str, leg2: str, leg3: str,
               side1: OrderSide, side2: OrderSide, side3: OrderSide,
               start: str, mid1: str, mid2: str) -> "Triangle":
        """Factory method to create a triangle with UUID."""
        return cls(
            id=str(uuid.uuid4()),
            leg1_symbol=leg1,
            leg2_symbol=leg2,
            leg3_symbol=leg3,
            leg1_side=side1,
            leg2_side=side2,
            leg3_side=side3,
            start_asset=start,
            middle_asset1=mid1,
            middle_asset2=mid2,
        )

    def get_symbols(self) -> List[str]:
        """Get list of symbols in the triangle."""
        return [self.leg1_symbol, self.leg2_symbol, self.leg3_symbol]

    def get_assets(self) -> List[str]:
        """Get list of unique assets in the triangle."""
        return [self.start_asset, self.middle_asset1, self.middle_asset2]


@dataclass
class Opportunity:
    """Represents a detected arbitrage opportunity."""
    triangle: Triangle
    gross_profit_pct: float
    net_profit_pct: float
    trade_amount_usdt: float
    expected_profit_usdt: float
    confidence_score: int  # 0-100
    liquidity_score: int  # 0-100
    slippage_estimate: float
    spread_estimate: float
    fees_estimate: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    legs_data: List[Dict[str, Any]] = field(default_factory=list)
    exchange: str = "bybit"

    @property
    def is_profitable(self) -> bool:
        """Check if opportunity meets minimum profit threshold."""
        return self.net_profit_pct > 0


# =============================================================================
# ORDER AND TRADE MODELS
# =============================================================================

@dataclass
class Order:
    """Represents a trading order."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: Optional[float] = None
    commission: float = 0.0
    commission_asset: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    exchange: str = "bybit"
    reduce_only: bool = False
    post_only: bool = False

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED

    @property
    def fill_rate(self) -> float:
        """Get fill percentage."""
        if self.quantity == 0:
            return 0.0
        return (self.filled_qty / self.quantity) * 100

    @property
    def remaining_qty(self) -> float:
        """Get remaining quantity to fill."""
        return self.quantity - self.filled_qty


@dataclass
class TradeLeg:
    """Represents one leg of a triangular trade."""
    leg_number: int
    symbol: str
    side: OrderSide
    order: Optional[Order] = None
    expected_qty: float = 0.0
    actual_qty: float = 0.0
    expected_price: float = 0.0
    actual_price: float = 0.0
    status: str = "pending"
    error: Optional[str] = None


@dataclass
class Trade:
    """Represents a complete trade (single or multi-leg)."""
    trade_id: str
    strategy_name: str
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float = 0.0
    leverage: float = 1.0
    pnl_usdt: float = 0.0
    pnl_pct: float = 0.0
    fees_usdt: float = 0.0
    status: TradeStatus = TradeStatus.SCANNING
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    notes: str = ""
    exchange: str = "bybit"
    legs: List[TradeLeg] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        """Check if trade is still open."""
        return self.exit_price is None

    @property
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.exit_price is not None


@dataclass
class Position:
    """Represents an open position."""
    position_id: str
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    leverage: float = 1.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    liquidation_price: Optional[float] = None
    margin_mode: str = "cross"  # cross or isolated
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    opened_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    exchange: str = "bybit"

    def update_price(self, price: float):
        """Update current price and recalculate PnL."""
        self.current_price = price
        self.updated_at = datetime.utcnow()

        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.quantity

        if self.entry_price > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / (self.entry_price * self.quantity)) * 100


# =============================================================================
# STRATEGY AND SIGNAL MODELS
# =============================================================================

@dataclass
class Signal:
    """Trading signal from a strategy."""
    signal_id: str
    strategy_name: str
    symbol: str
    signal_type: SignalType
    confidence: float  # 0-100
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: float = 0.0
    suggested_leverage: float = 1.0
    reason: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expiry: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """Check if signal has expired."""
        if self.expiry is None:
            return False
        return datetime.utcnow() > self.expiry


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy."""
    name: str
    strategy_type: StrategyType
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=list)
    max_positions: int = 1
    risk_per_trade: float = 1.0  # % of portfolio
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_usdt: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: float
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)


# =============================================================================
# RISK MANAGEMENT MODELS
# =============================================================================

@dataclass
class RiskLimits:
    """Risk limit configuration."""
    max_daily_loss_usdt: float = 100.0
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 20.0
    max_exposure_usdt: float = 1000.0
    max_leverage: float = 10.0
    max_position_size_usdt: float = 500.0
    max_concurrent_positions: int = 5
    max_correlation: float = 0.8
    kelly_criterion_enabled: bool = False
    kelly_fraction: float = 0.25  # Fractional Kelly
    auto_hedge_enabled: bool = False
    kill_switch_enabled: bool = False


@dataclass
class RiskMetrics:
    """Current risk metrics."""
    daily_pnl_usdt: float = 0.0
    daily_pnl_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    peak_balance_usdt: float = 0.0
    total_exposure_usdt: float = 0.0
    correlation_matrix: Dict[str, float] = field(default_factory=dict)
    var_95: float = 0.0  # Value at Risk
    expected_shortfall: float = 0.0
    risk_score: float = 0.0  # 0-100
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StopLossConfig:
    """Stop loss configuration."""
    stop_loss_type: str = "fixed"  # fixed, atr, trailing, breakeven
    stop_loss_pct: float = 2.0
    stop_loss_atr_multiplier: float = 2.0
    trailing_stop_pct: float = 1.0
    breakeven_trigger_pct: float = 1.0
    partial_close_levels: List[float] = field(default_factory=lambda: [0.5, 0.75, 1.0])


# =============================================================================
# PORTFOLIO AND PERFORMANCE MODELS
# =============================================================================

@dataclass
class PortfolioStats:
    """Portfolio statistics."""
    total_balance_usdt: float = 0.0
    available_balance_usdt: float = 0.0
    locked_balance_usdt: float = 0.0
    today_pnl_usdt: float = 0.0
    today_pnl_pct: float = 0.0
    weekly_pnl_usdt: float = 0.0
    monthly_pnl_usdt: float = 0.0
    yearly_pnl_usdt: float = 0.0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    avg_trade_usdt: float = 0.0
    best_trade_usdt: float = 0.0
    worst_trade_usdt: float = 0.0
    longest_winning_streak: int = 0
    longest_losing_streak: int = 0
    current_drawdown_usdt: float = 0.0
    max_drawdown_usdt: float = 0.0
    max_drawdown_pct: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def update_win_rate(self):
        """Update win rate calculation."""
        if self.total_trades > 0:
            self.win_rate = (self.successful_trades / self.total_trades) * 100
        if self.successful_trades > 0:
            self.avg_trade_usdt = self.today_pnl_usdt / self.successful_trades


@dataclass
class PerformanceReport:
    """Performance report for a period."""
    period: str  # daily, weekly, monthly, yearly
    start_date: datetime
    end_date: datetime
    starting_balance: float
    ending_balance: float
    pnl_usdt: float
    pnl_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    best_trade: float
    worst_trade: float
    avg_trade_duration: float
    generated_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# SYSTEM HEALTH AND METRICS
# =============================================================================

@dataclass
class LatencyMetrics:
    """Latency metrics for monitoring."""
    websocket_latency_ms: float = 0.0
    api_latency_ms: float = 0.0
    scanner_latency_ms: float = 0.0
    execution_latency_ms: float = 0.0
    database_latency_ms: float = 0.0
    processing_latency_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_latency_ms(self) -> float:
        """Get total latency across all components."""
        return (
            self.websocket_latency_ms +
            self.api_latency_ms +
            self.scanner_latency_ms +
            self.execution_latency_ms +
            self.database_latency_ms +
            self.processing_latency_ms
        )


@dataclass
class SystemHealth:
    """System health status."""
    is_healthy: bool = True
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_percent: float = 0.0
    active_connections: int = 0
    pending_orders: int = 0
    active_trades: int = 0
    active_positions: int = 0
    errors_last_hour: int = 0
    warnings_last_hour: int = 0
    uptime_seconds: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    issues: List[str] = field(default_factory=list)
    performance_profile: str = "balanced"  # low, balanced, high


@dataclass
class APIMetrics:
    """API performance metrics."""
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    rate_limit_hits: int = 0
    avg_latency_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_errors: int = 0


# =============================================================================
# NOTIFICATION MODELS
# =============================================================================

@dataclass
class Notification:
    """Notification message."""
    notification_id: str
    notification_type: NotificationType
    title: str
    message: str
    priority: str = "normal"  # low, normal, high, critical
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent: bool = False
    channels: List[str] = field(default_factory=list)  # telegram, discord, email, etc.


# =============================================================================
# DATABASE MODELS
# =============================================================================

@dataclass
class DatabaseRecord:
    """Base class for database records."""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradeRecord(DatabaseRecord):
    """Trade record for database storage."""
    trade_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    side: str = ""
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    leverage: float = 1.0
    pnl_usdt: float = 0.0
    pnl_pct: float = 0.0
    fees_usdt: float = 0.0
    status: str = ""
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    exchange: str = "bybit"
    notes: str = ""


@dataclass
class OrderRecord(DatabaseRecord):
    """Order record for database storage."""
    order_id: str = ""
    trade_id: Optional[str] = None
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    quantity: float = 0.0
    price: Optional[float] = None
    filled_qty: float = 0.0
    avg_fill_price: Optional[float] = None
    commission: float = 0.0
    status: str = ""
    error_message: Optional[str] = None
    exchange: str = "bybit"


@dataclass
class SignalRecord(DatabaseRecord):
    """Signal record for database storage."""
    signal_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    signal_type: str = ""
    confidence: float = 0.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    result: Optional[str] = None  # executed, ignored, expired
    pnl_usdt: Optional[float] = None


# =============================================================================
# SCANNER MODELS
# =============================================================================

@dataclass
class ScanResult:
    """Result from market scanner."""
    symbol: str
    scan_type: str  # volatility, liquidity, breakout, etc.
    signal: SignalType
    confidence: float
    trend: str = "neutral"
    risk_level: RiskLevel = RiskLevel.MEDIUM
    expected_rr: float = 0.0
    suggested_leverage: float = 1.0
    reasons: List[str] = field(default_factory=list)
    indicators: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScannerConfig:
    """Configuration for market scanner."""
    scan_types: List[str] = field(default_factory=lambda: [
        "volatility", "liquidity", "breakout", "reversal",
        "trend_continuation", "funding", "volume_spike",
        "order_book_imbalance", "whale_movement",
        "liquidation_cluster", "momentum", "vwap_deviation"
    ])
    symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=lambda: ["5m", "15m", "1h", "4h"])
    min_confidence: float = 70.0
    scan_interval_seconds: int = 60
    max_results: int = 20


# =============================================================================
# PLUGIN MODELS
# =============================================================================

@dataclass
class PluginInfo:
    """Information about a plugin."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: str  # strategy, notifier, scanner, indicator, risk
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================

@dataclass
class ExchangeConfig:
    """Exchange configuration."""
    name: str = "bybit"
    api_key: str = ""
    secret_key: str = ""
    testnet: bool = True
    sandbox: bool = True
    rate_limit_per_second: int = 10
    retry_attempts: int = 3
    timeout_seconds: int = 30


@dataclass
class PerformanceProfile:
    """Performance profile for resource management."""
    profile_name: str  # low, balanced, high
    max_cpu_percent: float = 25.0
    max_memory_mb: int = 500
    websocket_ping_interval: int = 30
    scanner_refresh_ms: int = 100
    max_concurrent_requests: int = 5
    cache_ttl_seconds: int = 300
    background_tasks_enabled: bool = True
    analytics_enabled: bool = True

    @classmethod
    def low(cls) -> "PerformanceProfile":
        """Low resource profile for constrained systems."""
        return cls(
            profile_name="low",
            max_cpu_percent=15.0,
            max_memory_mb=256,
            websocket_ping_interval=60,
            scanner_refresh_ms=500,
            max_concurrent_requests=2,
            cache_ttl_seconds=600,
            background_tasks_enabled=False,
            analytics_enabled=False,
        )

    @classmethod
    def balanced(cls) -> "PerformanceProfile":
        """Balanced profile for typical systems."""
        return cls(
            profile_name="balanced",
            max_cpu_percent=25.0,
            max_memory_mb=512,
            websocket_ping_interval=30,
            scanner_refresh_ms=100,
            max_concurrent_requests=5,
            cache_ttl_seconds=300,
            background_tasks_enabled=True,
            analytics_enabled=True,
        )

    @classmethod
    def high(cls) -> "PerformanceProfile":
        """High performance profile for powerful systems."""
        return cls(
            profile_name="high",
            max_cpu_percent=50.0,
            max_memory_mb=1024,
            websocket_ping_interval=15,
            scanner_refresh_ms=50,
            max_concurrent_requests=10,
            cache_ttl_seconds=120,
            background_tasks_enabled=True,
            analytics_enabled=True,
        )
