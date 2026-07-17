"""
Data models for Bybit Triangle Arbitrage Bot.
Defines core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "Buy"
    SELL = "Sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "Market"
    LIMIT = "Limit"


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
    EXECUTING_LEG1 = "executing_leg1"
    EXECUTING_LEG2 = "executing_leg2"
    EXECUTING_LEG3 = "executing_leg3"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class Symbol:
    """Represents a trading symbol on Bybit."""
    
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
    
    def __post_init__(self):
        # Validate precision values
        if self.price_precision < 0 or self.qty_precision < 0:
            raise ValueError("Precision values must be non-negative")


@dataclass
class OrderBookLevel:
    """Single level in an order book."""
    
    price: float
    quantity: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrderBook:
    """Order book snapshot for a symbol."""
    
    symbol: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence: int = 0
    
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
    
    @property
    def is_profitable(self) -> bool:
        """Check if opportunity meets minimum profit threshold."""
        return self.net_profit_pct > 0


@dataclass
class Order:
    """Represents a trading order."""
    
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: Optional[float] = None
    commission: float = 0.0
    commission_asset: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    
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
    """Represents a complete triangular arbitrage trade."""
    
    trade_id: str
    triangle: Triangle
    status: TradeStatus = TradeStatus.SCANNING
    legs: List[TradeLeg] = field(default_factory=list)
    initial_balance_usdt: float = 0.0
    final_balance_usdt: 0.0
    profit_usdt: float = 0.0
    profit_pct: float = 0.0
    total_fees_usdt: float = 0.0
    total_slippage_pct: float = 0.0
    execution_time_ms: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def is_completed(self) -> bool:
        """Check if trade is completed."""
        return self.status == TradeStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if trade failed."""
        return self.status in [TradeStatus.FAILED, TradeStatus.ROLLED_BACK]


@dataclass
class PortfolioStats:
    """Portfolio statistics."""
    
    total_balance_usdt: float = 0.0
    available_balance_usdt: float = 0.0
    locked_balance_usdt: float = 0.0
    today_profit_usdt: float = 0.0
    today_profit_pct: float = 0.0
    weekly_profit_usdt: float = 0.0
    monthly_profit_usdt: float = 0.0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    win_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    largest_win_usdt: float = 0.0
    largest_loss_usdt: float = 0.0
    current_drawdown_usdt: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def update_win_rate(self):
        """Update win rate calculation."""
        if self.total_trades > 0:
            self.win_rate = (self.successful_trades / self.total_trades) * 100
        if self.successful_trades > 0:
            self.avg_profit_per_trade = self.today_profit_usdt / self.successful_trades


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
    active_connections: int = 0
    pending_orders: int = 0
    active_trades: int = 0
    errors_last_hour: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    issues: List[str] = field(default_factory=list)
