"""
Base Strategy Module - Abstract base class for all trading strategies.
All custom strategies must inherit from BaseStrategy.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class StrategySignal:
    """Represents a trading signal from a strategy."""
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-100
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    reason: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    All strategies must implement:
    - analyze(): Generate trading signals based on market data
    - get_name(): Return strategy name
    - get_parameters(): Return configurable parameters
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize strategy with optional configuration."""
        self.config = config or {}
        self.name = self.get_name()
        self.enabled = self.config.get('enabled', True)
        self.symbols = self.config.get('symbols', [])
        self.timeframes = self.config.get('timeframes', ['5m', '15m', '1h'])
        
    @abstractmethod
    def analyze(self, candles: List[Dict[str, Any]], indicators: Dict[str, Any]) -> StrategySignal:
        """
        Analyze market data and generate trading signal.
        
        Args:
            candles: List of OHLCV candle data
            indicators: Pre-calculated technical indicators
            
        Returns:
            StrategySignal object with trading recommendation
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the strategy name."""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return configurable parameters for this strategy."""
        pass
    
    def validate_signal(self, signal: StrategySignal) -> bool:
        """Validate a trading signal before execution."""
        if not signal.symbol:
            return False
        if signal.confidence < self.config.get('min_confidence', 70):
            return False
        if signal.action not in ['BUY', 'SELL', 'HOLD']:
            return False
        return True
    
    def calculate_position_size(self, balance: float, risk_pct: float, 
                                entry_price: float, stop_loss: float) -> float:
        """
        Calculate position size based on risk parameters.
        
        Args:
            balance: Account balance in USDT
            risk_pct: Risk percentage (e.g., 2.0 for 2%)
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size in base currency
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0.0
        
        risk_amount = balance * (risk_pct / 100)
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff <= 0:
            return 0.0
        
        position_size = risk_amount / price_diff
        return position_size
    
    def on_trade_executed(self, trade_data: Dict[str, Any]):
        """Callback when a trade is executed by this strategy."""
        pass
    
    def on_trade_closed(self, trade_data: Dict[str, Any]):
        """Callback when a trade is closed by this strategy."""
        pass
    
    def cleanup(self):
        """Cleanup resources when strategy is stopped."""
        pass
