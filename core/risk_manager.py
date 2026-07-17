"""
Risk Management Engine
Professional risk controls for position sizing, stop losses, and portfolio protection.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Current risk metrics for the portfolio."""
    total_exposure: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    positions_count: int = 0
    margin_used: float = 0.0
    available_margin: float = 0.0


@dataclass
class PositionLimits:
    """Position size limits."""
    max_position_size_usdt: float = 500.0
    max_leverage: float = 10.0
    max_concurrent_positions: int = 5
    max_exposure_usdt: float = 1000.0


@dataclass
class LossLimits:
    """Loss limit configuration."""
    max_daily_loss_usdt: float = 100.0
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 20.0
    max_trade_loss_pct: float = 2.0


class RiskManager:
    """
    Professional Risk Management Engine.
    
    Features:
    - Position sizing based on Kelly Criterion or fixed risk
    - Stop loss calculation (fixed, ATR-based, trailing)
    - Daily loss limits
    - Maximum drawdown protection
    - Exposure monitoring
    - Kill switch functionality
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Position limits
        self.position_limits = PositionLimits(
            max_position_size_usdt=self.config.get('max_position_size_usdt', 500.0),
            max_leverage=self.config.get('max_leverage', 10.0),
            max_concurrent_positions=self.config.get('max_concurrent_positions', 5),
            max_exposure_usdt=self.config.get('max_exposure_usdt', 1000.0),
        )
        
        # Loss limits
        self.loss_limits = LossLimits(
            max_daily_loss_usdt=self.config.get('max_daily_loss_usdt', 100.0),
            max_daily_loss_pct=self.config.get('max_daily_loss_pct', 5.0),
            max_drawdown_pct=self.config.get('max_drawdown_pct', 20.0),
            max_trade_loss_pct=self.config.get('max_trade_loss_pct', 2.0),
        )
        
        # State
        self.daily_pnl = 0.0
        self.daily_start_balance = 0.0
        self.peak_balance = 0.0
        self.current_balance = 0.0
        self.trades_today = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.kill_switch_active = False
        self.last_reset_date = datetime.utcnow().date()
        
        # Metrics history
        self.metrics_history: List[RiskMetrics] = []
        
    def check_daily_limits(self, current_pnl: float) -> bool:
        """
        Check if daily loss limits are exceeded.
        
        Returns:
            True if trading should continue, False if limits exceeded
        """
        self._check_date_reset()
        
        # Check absolute loss limit
        if current_pnl < -self.loss_limits.max_daily_loss_usdt:
            self.kill_switch_active = True
            return False
        
        # Check percentage loss limit
        if self.daily_start_balance > 0:
            daily_loss_pct = (abs(current_pnl) / self.daily_start_balance) * 100
            if daily_loss_pct > self.loss_limits.max_daily_loss_pct:
                self.kill_switch_active = True
                return False
        
        return True
    
    def check_drawdown(self, current_balance: float) -> bool:
        """
        Check if maximum drawdown is exceeded.
        
        Returns:
            True if trading should continue, False if drawdown exceeded
        """
        self.current_balance = current_balance
        
        # Update peak balance
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        # Calculate current drawdown
        if self.peak_balance > 0:
            drawdown = ((self.peak_balance - current_balance) / self.peak_balance) * 100
            
            if drawdown > self.loss_limits.max_drawdown_pct:
                self.kill_switch_active = True
                return False
        
        return True
    
    def calculate_position_size(self, balance: float, entry_price: float, 
                                stop_loss: float, risk_method: str = 'fixed') -> float:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            balance: Current account balance
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            risk_method: 'fixed' or 'kelly'
            
        Returns:
            Position size in base currency
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0.0
        
        price_diff = abs(entry_price - stop_loss)
        if price_diff <= 0:
            return 0.0
        
        if risk_method == 'kelly':
            # Kelly Criterion position sizing
            position_size = self._kelly_position_size(balance, entry_price, stop_loss)
        else:
            # Fixed percentage risk
            risk_amount = balance * (self.loss_limits.max_trade_loss_pct / 100)
            position_size = risk_amount / price_diff
        
        # Apply position limits
        max_position_value = self.position_limits.max_position_size_usdt
        max_position_by_price = max_position_value / entry_price
        
        position_size = min(position_size, max_position_by_price)
        
        return position_size
    
    def _kelly_position_size(self, balance: float, entry_price: float, 
                             stop_loss: float) -> float:
        """
        Calculate position size using Kelly Criterion.
        
        Kelly % = W - [(1-W)/R]
        Where:
        - W = Win probability
        - R = Win/Loss ratio
        """
        # Use historical win rate if available
        if self.trades_today > 0:
            win_prob = self.winning_trades / self.trades_today
        else:
            win_prob = 0.5  # Default assumption
        
        # Win/Loss ratio based on risk/reward
        risk = abs(entry_price - stop_loss)
        reward = risk * 2  # Assume 2:1 reward/risk
        win_loss_ratio = reward / risk if risk > 0 else 1
        
        # Kelly formula
        kelly_pct = win_prob - ((1 - win_prob) / win_loss_ratio)
        
        # Apply fractional Kelly (usually 0.25 to 0.5 of full Kelly)
        kelly_fraction = self.config.get('kelly_fraction', 0.25)
        kelly_pct = kelly_pct * kelly_fraction
        
        # Ensure non-negative
        kelly_pct = max(0, kelly_pct)
        
        # Calculate position size
        risk_amount = balance * (kelly_pct / 100)
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff > 0:
            return risk_amount / price_diff
        return 0.0
    
    def calculate_stop_loss(self, entry_price: float, atr: float, 
                           method: str = 'atr') -> float:
        """
        Calculate stop loss price based on method.
        
        Args:
            entry_price: Entry price
            atr: Average True Range value
            method: 'fixed', 'atr', or 'trailing'
            
        Returns:
            Stop loss price
        """
        if method == 'fixed':
            # Fixed percentage stop loss
            sl_pct = self.loss_limits.max_trade_loss_pct / 100
            return entry_price * (1 - sl_pct)
        
        elif method == 'atr':
            # ATR-based stop loss (typically 1.5-2x ATR)
            atr_multiplier = self.config.get('atr_sl_multiplier', 1.5)
            return entry_price - (atr * atr_multiplier)
        
        elif method == 'trailing':
            # Trailing stop (percentage)
            trailing_pct = self.config.get('trailing_stop_pct', 1.0) / 100
            return entry_price * (1 - trailing_pct)
        
        return entry_price * 0.98  # Default 2% stop loss
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float,
                             targets: int = 3) -> List[float]:
        """
        Calculate multiple take profit targets.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            targets: Number of profit targets (default 3)
            
        Returns:
            List of take profit prices
        """
        risk = abs(entry_price - stop_loss)
        
        # Risk/Reward ratios for each target
        rr_ratios = [1.5, 2.5, 4.0]  # Conservative progression
        
        take_profits = []
        for i in range(min(targets, len(rr_ratios))):
            reward = risk * rr_ratios[i]
            tp = entry_price + reward
            take_profits.append(tp)
        
        return take_profits
    
    def can_open_position(self, current_positions: int, exposure: float) -> bool:
        """
        Check if a new position can be opened.
        
        Returns:
            True if position can be opened, False otherwise
        """
        if self.kill_switch_active:
            return False
        
        if current_positions >= self.position_limits.max_concurrent_positions:
            return False
        
        if exposure >= self.position_limits.max_exposure_usdt:
            return False
        
        return True
    
    def get_risk_level(self, metrics: RiskMetrics) -> RiskLevel:
        """Determine overall risk level based on metrics."""
        score = 0
        
        # Drawdown scoring
        if metrics.current_drawdown > 15:
            score += 3
        elif metrics.current_drawdown > 10:
            score += 2
        elif metrics.current_drawdown > 5:
            score += 1
        
        # Daily loss scoring
        if metrics.daily_pnl_pct < -3:
            score += 3
        elif metrics.daily_pnl_pct < -1:
            score += 1
        
        # Exposure scoring
        if metrics.total_exposure > self.position_limits.max_exposure_usdt * 0.9:
            score += 2
        
        # Position count scoring
        if metrics.positions_count >= self.position_limits.max_concurrent_positions:
            score += 1
        
        # Determine level
        if score >= 6:
            return RiskLevel.CRITICAL
        elif score >= 4:
            return RiskLevel.HIGH
        elif score >= 2:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def reset_daily_stats(self, new_balance: float):
        """Reset daily statistics."""
        self.daily_pnl = 0.0
        self.daily_start_balance = new_balance
        self.trades_today = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.kill_switch_active = False
        self.last_reset_date = datetime.utcnow().date()
    
    def record_trade_result(self, pnl: float, is_winner: bool):
        """Record a trade result for statistics."""
        self.daily_pnl += pnl
        self.trades_today += 1
        
        if is_winner:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
    
    def _check_date_reset(self):
        """Check if date has changed and reset daily stats if needed."""
        today = datetime.utcnow().date()
        if today != self.last_reset_date:
            self.reset_daily_stats(self.current_balance)
    
    def get_metrics(self) -> RiskMetrics:
        """Get current risk metrics."""
        win_rate = 0.0
        if self.trades_today > 0:
            win_rate = (self.winning_trades / self.trades_today) * 100
        
        current_drawdown = 0.0
        if self.peak_balance > 0:
            current_drawdown = ((self.peak_balance - self.current_balance) / 
                               self.peak_balance) * 100
        
        daily_pnl_pct = 0.0
        if self.daily_start_balance > 0:
            daily_pnl_pct = (self.daily_pnl / self.daily_start_balance) * 100
        
        metrics = RiskMetrics(
            daily_pnl=self.daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            current_drawdown=current_drawdown,
            max_drawdown=((self.peak_balance - self.current_balance) / 
                         self.peak_balance * 100) if self.peak_balance > 0 else 0,
            win_rate=win_rate,
            positions_count=0,  # Should be updated externally
            risk_level=RiskLevel.LOW,  # Will be calculated
        )
        
        metrics.risk_level = self.get_risk_level(metrics)
        
        return metrics
    
    def emergency_stop(self, reason: str = ""):
        """Activate kill switch immediately."""
        self.kill_switch_active = True
        print(f"EMERGENCY STOP ACTIVATED: {reason}")
