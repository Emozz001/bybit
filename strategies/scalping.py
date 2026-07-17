"""
EMA Crossover Scalping Strategy
Fast scalping strategy based on EMA crossovers with RSI and volume confirmation.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from strategies.base_strategy import BaseStrategy, StrategySignal


@dataclass
class EMAConfig:
    """Configuration for EMA strategy."""
    fast_ema: int = 9
    slow_ema: int = 21
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    volume_multiplier: float = 1.5
    min_confidence: float = 75


class EMAScalpingStrategy(BaseStrategy):
    """
    EMA Crossover Scalping Strategy.
    
    Entry Logic (LONG):
    - Fast EMA crosses above Slow EMA
    - RSI > 50 but not overbought (< 70)
    - Volume above average * multiplier
    
    Entry Logic (SHORT):
    - Fast EMA crosses below Slow EMA
    - RSI < 50 but not oversold (> 30)
    - Volume above average * multiplier
    
    Exit Logic:
    - Opposite EMA crossover
    - Stop loss hit
    - Take profit hit
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.ema_config = EMAConfig(
            fast_ema=self.config.get('fast_ema', 9),
            slow_ema=self.config.get('slow_ema', 21),
            rsi_period=self.config.get('rsi_period', 14),
            rsi_overbought=self.config.get('rsi_overbought', 70),
            rsi_oversold=self.config.get('rsi_oversold', 30),
            volume_multiplier=self.config.get('volume_multiplier', 1.5),
            min_confidence=self.config.get('min_confidence', 75),
        )
        
    def get_name(self) -> str:
        return "EMA Scalping"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            'fast_ema': self.ema_config.fast_ema,
            'slow_ema': self.ema_config.slow_ema,
            'rsi_period': self.ema_config.rsi_period,
            'rsi_overbought': self.ema_config.rsi_overbought,
            'rsi_oversold': self.ema_config.rsi_oversold,
            'volume_multiplier': self.ema_config.volume_multiplier,
            'min_confidence': self.ema_config.min_confidence,
        }
    
    def analyze(self, candles: List[Dict[str, Any]], indicators: Dict[str, Any]) -> StrategySignal:
        """
        Analyze market data and generate trading signal.
        
        Args:
            candles: List of OHLCV candle data (most recent last)
            indicators: Dictionary containing EMA, RSI, and volume data
            
        Returns:
            StrategySignal with trading recommendation
        """
        if len(candles) < 30:
            return StrategySignal(
                symbol="",
                action="HOLD",
                confidence=0,
                reason="Insufficient data"
            )
        
        # Extract indicators
        ema_fast = indicators.get('ema_fast', [])
        ema_slow = indicators.get('ema_slow', [])
        rsi = indicators.get('rsi', [])
        volume = indicators.get('volume', [])
        avg_volume = indicators.get('avg_volume', 0)
        
        if not ema_fast or not ema_slow or not rsi:
            return StrategySignal(
                symbol=candles[-1].get('symbol', ''),
                action="HOLD",
                confidence=0,
                reason="Missing indicators"
            )
        
        current_ema_fast = ema_fast[-1]
        current_ema_slow = ema_slow[-1]
        prev_ema_fast = ema_fast[-2]
        prev_ema_slow = ema_slow[-2]
        current_rsi = rsi[-1]
        current_volume = volume[-1] if volume else 0
        
        # Calculate confidence
        confidence = 50
        
        # Check for bullish crossover
        bullish_crossover = (prev_ema_fast <= prev_ema_slow and 
                            current_ema_fast > current_ema_slow)
        
        # Check for bearish crossover
        bearish_crossover = (prev_ema_fast >= prev_ema_slow and 
                            current_ema_fast < current_ema_slow)
        
        # Volume confirmation
        volume_confirmed = current_volume > (avg_volume * self.ema_config.volume_multiplier)
        
        if volume_confirmed:
            confidence += 15
        
        # RSI confirmation
        rsi_neutral = 30 < current_rsi < 70
        if rsi_neutral:
            confidence += 10
        
        # Determine signal
        symbol = candles[-1].get('symbol', '')
        current_price = candles[-1].get('close', 0)
        
        if bullish_crossover and rsi_neutral:
            action = "BUY"
            confidence += 25
            reason = f"Bullish EMA crossover, RSI={current_rsi:.1f}, Volume confirmed"
            
            # Calculate stop loss and take profit
            atr = indicators.get('atr', [0])[-1] if indicators.get('atr') else current_price * 0.02
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 3)
            
        elif bearish_crossover and rsi_neutral:
            action = "SELL"
            confidence += 25
            reason = f"Bearish EMA crossover, RSI={current_rsi:.1f}, Volume confirmed"
            
            atr = indicators.get('atr', [0])[-1] if indicators.get('atr') else current_price * 0.02
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 3)
            
        else:
            action = "HOLD"
            reason = "No clear signal"
            stop_loss = None
            take_profit = None
        
        # Ensure minimum confidence
        confidence = max(confidence, 0)
        confidence = min(confidence, 100)
        
        return StrategySignal(
            symbol=symbol,
            action=action,
            confidence=confidence,
            entry_price=current_price if action != "HOLD" else None,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            indicators={
                'ema_fast': current_ema_fast,
                'ema_slow': current_ema_slow,
                'rsi': current_rsi,
                'volume': current_volume,
            }
        )
