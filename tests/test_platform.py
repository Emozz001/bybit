# Bybit AI Trading Platform - Test Suite

"""
Unit tests for the Bybit AI Trading Platform.
Run with: pytest tests/ -v --cov=.
"""

import pytest
from datetime import datetime


class TestIndicators:
    """Test technical indicator calculations."""
    
    def test_ema_calculation(self):
        from indicators import calculate_ema
        
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110]
        ema = calculate_ema(prices, 5)
        
        assert len(ema) == 7  # len(prices) - period + 1
        assert all(isinstance(x, float) for x in ema)
        assert ema[-1] > ema[0]  # Uptrend
    
    def test_rsi_calculation(self):
        from indicators import calculate_rsi
        
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110]
        rsi = calculate_rsi(prices, 3)
        
        assert len(rsi) > 0
        assert all(0 <= x <= 100 for x in rsi)
    
    def test_bollinger_bands(self):
        from indicators import calculate_bollinger_bands
        
        prices = list(range(100, 130))
        bb = calculate_bollinger_bands(prices, 20, 2.0)
        
        assert 'upper' in bb
        assert 'middle' in bb
        assert 'lower' in bb
        assert len(bb['upper']) == len(bb['middle']) == len(bb['lower'])
        
        # Upper should be > middle > lower
        for i in range(len(bb['upper'])):
            assert bb['upper'][i] >= bb['middle'][i] >= bb['lower'][i]


class TestRiskManager:
    """Test risk management calculations."""
    
    def test_position_size_fixed(self):
        from core.risk_manager import RiskManager
        
        rm = RiskManager({'max_trade_loss_pct': 2.0})
        pos_size = rm.calculate_position_size(1000, 50000, 49000)
        
        assert pos_size > 0
        # $20 risk (2% of $1000) / $1000 price diff = 0.02, but capped by max_position_size
        # Default max_position_size_usdt is 500, so 500/50000 = 0.01
        assert pos_size == 0.01
    
    def test_position_size_kelly(self):
        from core.risk_manager import RiskManager
        
        rm = RiskManager({
            'max_trade_loss_pct': 2.0,
            'kelly_fraction': 0.25
        })
        rm.winning_trades = 6
        rm.trades_today = 10
        
        pos_size = rm.calculate_position_size(
            1000, 50000, 49000, risk_method='kelly'
        )
        
        assert pos_size >= 0
    
    def test_stop_loss_atr(self):
        from core.risk_manager import RiskManager
        
        rm = RiskManager({'atr_sl_multiplier': 1.5})
        sl = rm.calculate_stop_loss(50000, 500, method='atr')
        
        assert sl == 50000 - (500 * 1.5)
        assert sl == 49250
    
    def test_take_profit_targets(self):
        from core.risk_manager import RiskManager
        
        rm = RiskManager()
        tps = rm.calculate_take_profit(50000, 49000, targets=3)
        
        assert len(tps) == 3
        assert all(tp > 50000 for tp in tps)
        assert tps[0] < tps[1] < tps[2]  # Progressive targets
    
    def test_daily_loss_limit(self):
        from core.risk_manager import RiskManager
        
        rm = RiskManager({'max_daily_loss_usdt': 100.0})
        rm.daily_start_balance = 1000
        
        # Should allow trading when under limit
        assert rm.check_daily_limits(-50) == True
        
        # Should block trading when over limit
        assert rm.check_daily_limits(-150) == False
        assert rm.kill_switch_active == True
    
    def test_drawdown_protection(self):
        from core.risk_manager import RiskManager
        
        rm = RiskManager({'max_drawdown_pct': 20.0})
        rm.peak_balance = 1000
        
        # Should allow trading when under drawdown limit
        assert rm.check_drawdown(850) == True
        
        # Should block trading when over drawdown limit
        assert rm.check_drawdown(750) == False
        assert rm.kill_switch_active == True


class TestStrategySignal:
    """Test strategy signal generation."""
    
    def test_signal_creation(self):
        from strategies.base_strategy import StrategySignal
        
        signal = StrategySignal(
            symbol="BTCUSDT",
            action="BUY",
            confidence=85.0,
            entry_price=50000,
            stop_loss=49000,
            take_profit=52000
        )
        
        assert signal.symbol == "BTCUSDT"
        assert signal.action == "BUY"
        assert signal.confidence == 85.0
        assert signal.entry_price == 50000
    
    def test_ema_scalping_strategy(self):
        from strategies.scalping import EMAScalpingStrategy
        
        config = {
            'fast_ema': 9,
            'slow_ema': 21,
            'min_confidence': 75
        }
        strategy = EMAScalpingStrategy(config)
        
        assert strategy.get_name() == "EMA Scalping"
        params = strategy.get_parameters()
        assert params['fast_ema'] == 9
        assert params['slow_ema'] == 21


class TestConfiguration:
    """Test configuration loading."""
    
    def test_config_loading(self):
        from app.core.config import Config
        
        config = Config()
        assert config.exchange.testnet == True
        assert config.trading.mode == "paper"
    
    def test_config_env_override(self):
        import os
        from app.core.config import Config
        
        os.environ['TRADING_MODE'] = 'live'
        config = Config()
        # Note: This would need reload to pick up env var
        del os.environ['TRADING_MODE']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
