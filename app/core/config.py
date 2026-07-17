"""
Configuration management for Bybit AI Trading Platform.
Uses YAML configuration with environment variable overrides.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExchangeConfig:
    """Exchange API configuration."""
    name: str = "bybit"
    api_key: str = ""
    secret_key: str = ""
    testnet: bool = True
    sandbox: bool = True
    rate_limit_per_second: int = 10
    retry_attempts: int = 3
    timeout_seconds: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExchangeConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TradingConfig:
    """Trading parameters configuration."""
    mode: str = "paper"  # paper, live
    min_net_profit_pct: float = 0.1
    max_slippage_pct: float = 0.5
    max_spread_pct: float = 0.3
    min_liquidity_score: int = 70
    confidence_threshold: int = 85
    max_trade_size_usdt: float = 100.0
    min_trade_size_usdt: float = 10.0
    daily_loss_limit_usdt: float = 50.0
    max_concurrent_trades: int = 1
    default_leverage: float = 1.0
    auto_hedge_enabled: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RiskConfig:
    """Risk management configuration."""
    max_daily_loss_usdt: float = 100.0
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 20.0
    max_exposure_usdt: float = 1000.0
    max_leverage: float = 10.0
    max_position_size_usdt: float = 500.0
    max_concurrent_positions: int = 5
    kelly_criterion_enabled: bool = False
    kelly_fraction: float = 0.25
    kill_switch_enabled: bool = False
    stop_loss_type: str = "fixed"
    stop_loss_pct: float = 2.0
    trailing_stop_pct: float = 1.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/bybit_ai.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_backup_count: int = 7
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    console_output: bool = True
    file_output: bool = True
    log_dir: str = "logs"
    max_log_files: int = 7
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggingConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class NotificationConfig:
    """Notification configuration."""
    enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    notify_on_trade: bool = True
    notify_on_error: bool = True
    notify_daily_summary: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PerformanceConfig:
    """Performance optimization settings."""
    profile: str = "balanced"  # low, balanced, high
    max_cpu_percent: float = 25.0
    max_memory_mb: int = 512
    websocket_ping_interval: int = 30
    scanner_refresh_ms: int = 100
    max_concurrent_requests: int = 5
    cache_ttl_seconds: int = 300
    background_tasks_enabled: bool = True
    analytics_enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def apply_profile(self, profile_name: str):
        """Apply a predefined performance profile."""
        profiles = {
            "low": {
                "max_cpu_percent": 15.0,
                "max_memory_mb": 256,
                "websocket_ping_interval": 60,
                "scanner_refresh_ms": 500,
                "max_concurrent_requests": 2,
                "cache_ttl_seconds": 600,
                "background_tasks_enabled": False,
                "analytics_enabled": False,
            },
            "balanced": {
                "max_cpu_percent": 25.0,
                "max_memory_mb": 512,
                "websocket_ping_interval": 30,
                "scanner_refresh_ms": 100,
                "max_concurrent_requests": 5,
                "cache_ttl_seconds": 300,
                "background_tasks_enabled": True,
                "analytics_enabled": True,
            },
            "high": {
                "max_cpu_percent": 50.0,
                "max_memory_mb": 1024,
                "websocket_ping_interval": 15,
                "scanner_refresh_ms": 50,
                "max_concurrent_requests": 10,
                "cache_ttl_seconds": 120,
                "background_tasks_enabled": True,
                "analytics_enabled": True,
            },
        }
        
        if profile_name in profiles:
            for key, value in profiles[profile_name].items():
                setattr(self, key, value)
            self.profile = profile_name


@dataclass
class ScannerConfig:
    """Market scanner configuration."""
    enabled: bool = True
    scan_types: List[str] = field(default_factory=lambda: [
        "volatility", "liquidity", "breakout", "reversal",
        "trend_continuation", "funding", "volume_spike"
    ])
    symbols: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT"
    ])
    timeframes: List[str] = field(default_factory=lambda: ["5m", "15m", "1h", "4h"])
    min_confidence: float = 70.0
    scan_interval_seconds: int = 60
    max_results: int = 20
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScannerConfig":
        fields = cls.__dataclass_fields__
        filtered = {k: v for k, v in data.items() if k in fields}
        # Handle list defaults
        if "scan_types" not in filtered:
            filtered["scan_types"] = cls().scan_types
        if "symbols" not in filtered:
            filtered["symbols"] = cls().symbols
        if "timeframes" not in filtered:
            filtered["timeframes"] = cls().timeframes
        return cls(**filtered)


@dataclass
class StrategyConfig:
    """Strategy configuration."""
    enabled_strategies: List[str] = field(default_factory=list)
    strategy_parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyConfig":
        return cls(
            enabled_strategies=data.get("enabled_strategies", []),
            strategy_parameters=data.get("strategy_parameters", {}),
        )


@dataclass
class Config:
    """Main application configuration."""
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    strategies: StrategyConfig = field(default_factory=StrategyConfig)
    
    @classmethod
    def load_from_yaml(cls, config_path: str = "config/config.yaml") -> "Config":
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            # Create default config
            default_config = cls._create_default()
            default_config.save_to_yaml(config_path)
            return default_config
        
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        # Apply environment variable overrides
        data = cls._apply_env_overrides(data)
        
        return cls(
            exchange=ExchangeConfig.from_dict(data.get("exchange", {})),
            trading=TradingConfig.from_dict(data.get("trading", {})),
            risk=RiskConfig.from_dict(data.get("risk", {})),
            database=DatabaseConfig.from_dict(data.get("database", {})),
            logging=LoggingConfig.from_dict(data.get("logging", {})),
            notifications=NotificationConfig.from_dict(data.get("notifications", {})),
            performance=PerformanceConfig.from_dict(data.get("performance", {})),
            scanner=ScannerConfig.from_dict(data.get("scanner", {})),
            strategies=StrategyConfig.from_dict(data.get("strategies", {})),
        )
    
    @classmethod
    def _apply_env_overrides(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_mapping = {
            "BYBIT_API_KEY": ("exchange", "api_key"),
            "BYBIT_SECRET_KEY": ("exchange", "secret_key"),
            "BYBIT_TESTNET": ("exchange", "testnet"),
            "TRADING_MODE": ("trading", "mode"),
            "MIN_NET_PROFIT_PCT": ("trading", "min_net_profit_pct"),
            "MAX_TRADE_SIZE_USDT": ("trading", "max_trade_size_usdt"),
            "DAILY_LOSS_LIMIT_USDT": ("risk", "max_daily_loss_usdt"),
            "MAX_LEVERAGE": ("risk", "max_leverage"),
            "LOG_LEVEL": ("logging", "level"),
            "PERFORMANCE_PROFILE": ("performance", "profile"),
        }
        
        for env_var, (section, key) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                if section not in data:
                    data[section] = {}
                
                # Type conversion
                if isinstance(value, str):
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.replace(".", "").isdigit():
                        value = float(value) if "." in value else int(value)
                
                data[section][key] = value
        
        return data
    
    @classmethod
    def _create_default(cls) -> "Config":
        """Create default configuration."""
        return cls()
    
    def save_to_yaml(self, config_path: str = "config/config.yaml"):
        """Save configuration to YAML file."""
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "exchange": {
                "name": self.exchange.name,
                "testnet": self.exchange.testnet,
                "sandbox": self.exchange.sandbox,
                "rate_limit_per_second": self.exchange.rate_limit_per_second,
            },
            "trading": {
                "mode": self.trading.mode,
                "min_net_profit_pct": self.trading.min_net_profit_pct,
                "max_slippage_pct": self.trading.max_slippage_pct,
                "max_trade_size_usdt": self.trading.max_trade_size_usdt,
                "daily_loss_limit_usdt": self.trading.daily_loss_limit_usdt,
            },
            "risk": {
                "max_daily_loss_usdt": self.risk.max_daily_loss_usdt,
                "max_drawdown_pct": self.risk.max_drawdown_pct,
                "max_leverage": self.risk.max_leverage,
                "kill_switch_enabled": self.risk.kill_switch_enabled,
            },
            "database": {
                "path": self.database.path,
                "backup_enabled": self.database.backup_enabled,
            },
            "logging": {
                "level": self.logging.level,
                "console_output": self.logging.console_output,
                "file_output": self.logging.file_output,
            },
            "notifications": {
                "enabled": self.notifications.enabled,
                "notify_on_trade": self.notifications.notify_on_trade,
            },
            "performance": {
                "profile": self.performance.profile,
                "max_cpu_percent": self.performance.max_cpu_percent,
                "max_memory_mb": self.performance.max_memory_mb,
            },
            "scanner": {
                "enabled": self.scanner.enabled,
                "symbols": self.scanner.symbols,
                "min_confidence": self.scanner.min_confidence,
            },
            "strategies": {
                "enabled_strategies": self.strategies.enabled_strategies,
            },
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def validate_for_live_trading(self) -> None:
        """Validate configuration for live trading mode."""
        if self.trading.mode == "live":
            if not self.exchange.api_key or not self.exchange.secret_key:
                raise ValueError("API credentials required for live trading")
            if self.exchange.testnet:
                raise ValueError("Cannot use testnet for live trading")


# Singleton instance
_config: Optional[Config] = None


def get_config(config_path: str = "config/config.yaml", reload: bool = False) -> Config:
    """Get application configuration singleton."""
    global _config
    
    if _config is None or reload:
        _config = Config.load_from_yaml(config_path)
    
    return _config


def reload_config(config_path: str = "config/config.yaml") -> Config:
    """Reload configuration from file."""
    global _config
    _config = Config.load_from_yaml(config_path)
    return _config
