"""
Configuration settings for Bybit Triangle Arbitrage Bot.
Uses Pydantic for validation and environment variable loading.
"""

import os
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class TradingConfig(BaseModel):
    """Trading parameters configuration."""
    
    mode: Literal["paper", "live"] = Field(
        default="paper",
        description="Trading mode: 'paper' or 'live'"
    )
    min_net_profit_pct: float = Field(
        default=0.1,
        ge=0.0,
        le=5.0,
        description="Minimum net profit percentage to execute trade"
    )
    max_slippage_pct: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Maximum acceptable slippage percentage"
    )
    max_spread_pct: float = Field(
        default=0.3,
        ge=0.0,
        le=5.0,
        description="Maximum acceptable spread percentage"
    )
    min_liquidity_score: int = Field(
        default=70,
        ge=0,
        le=100,
        description="Minimum liquidity score (0-100) to trade"
    )
    confidence_threshold: int = Field(
        default=85,
        ge=0,
        le=100,
        description="Minimum confidence score (0-100) to execute"
    )
    max_trade_size_usdt: float = Field(
        default=100.0,
        gt=0.0,
        description="Maximum trade size in USDT"
    )
    min_trade_size_usdt: float = Field(
        default=10.0,
        gt=0.0,
        description="Minimum trade size in USDT"
    )
    daily_loss_limit_usdt: float = Field(
        default=50.0,
        gt=0.0,
        description="Daily loss limit in USDT"
    )
    max_concurrent_trades: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum concurrent trades"
    )
    
    @field_validator('min_net_profit_pct', 'max_slippage_pct', 'max_spread_pct')
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Percentage cannot be negative")
        return v


class APIConfig(BaseModel):
    """Bybit API configuration."""
    
    api_key: str = Field(..., description="Bybit API Key")
    secret_key: str = Field(..., description="Bybit Secret Key")
    testnet: bool = Field(default=True, description="Use testnet instead of mainnet")
    
    @field_validator('api_key', 'secret_key')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError(f"{info.field_name} cannot be empty. Please set it in .env file.")
        return v.strip()
    
    @property
    def base_url(self) -> str:
        """Get the appropriate Bybit API base URL."""
        if self.testnet:
            return "https://api-testnet.bybit.com"
        return "https://api.bybit.com"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    path: str = Field(
        default="data/bybit_arb.db",
        description="SQLite database file path"
    )
    backup_enabled: bool = Field(
        default=True,
        description="Enable automatic database backups"
    )
    backup_interval_hours: int = Field(
        default=24,
        ge=1,
        description="Backup interval in hours"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    console_output: bool = Field(
        default=True,
        description="Enable console logging"
    )
    file_output: bool = Field(
        default=True,
        description="Enable file logging"
    )
    log_dir: str = Field(
        default="logs",
        description="Directory for log files"
    )
    max_log_files: int = Field(
        default=7,
        ge=1,
        description="Maximum number of log files to keep"
    )


class NotificationConfig(BaseModel):
    """Notification configuration."""
    
    enabled: bool = Field(default=False, description="Enable notifications")
    telegram_bot_token: Optional[str] = Field(default=None, description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram chat ID")
    discord_webhook_url: Optional[str] = Field(default=None, description="Discord webhook URL")
    notify_on_trade: bool = Field(default=True, description="Notify on trade execution")
    notify_on_error: bool = Field(default=True, description="Notify on errors")
    notify_daily_summary: bool = Field(default=True, description="Send daily summary")


class PerformanceConfig(BaseModel):
    """Performance optimization settings."""
    
    websocket_ping_interval: int = Field(
        default=30,
        ge=10,
        description="WebSocket ping interval in seconds"
    )
    order_book_cache_ttl: int = Field(
        default=5000,
        ge=100,
        description="Order book cache TTL in milliseconds"
    )
    scanner_refresh_ms: int = Field(
        default=100,
        ge=50,
        description="Scanner refresh interval in milliseconds"
    )
    max_cpu_percent: float = Field(
        default=25.0,
        ge=5.0,
        le=100.0,
        description="Maximum CPU usage percentage target"
    )
    max_memory_mb: int = Field(
        default=500,
        ge=100,
        description="Maximum memory usage in MB"
    )


class Config(BaseModel):
    """Main application configuration."""
    
    trading: TradingConfig = Field(default_factory=TradingConfig)
    api: Optional[APIConfig] = None
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    
    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Load API config only if keys are present
        api_key = os.getenv("BYBIT_API_KEY")
        secret_key = os.getenv("BYBIT_SECRET_KEY")
        
        api_config = None
        if api_key and secret_key:
            api_config = APIConfig(
                api_key=api_key,
                secret_key=secret_key,
                testnet=os.getenv("BYBIT_TESTNET", "true").lower() == "true"
            )
        
        return cls(
            trading=TradingConfig(
                mode=os.getenv("TRADING_MODE", "paper"),
                min_net_profit_pct=float(os.getenv("MIN_NET_PROFIT_PCT", "0.1")),
                max_slippage_pct=float(os.getenv("MAX_SLIPPAGE_PCT", "0.5")),
                max_spread_pct=float(os.getenv("MAX_SPREAD_PCT", "0.3")),
                min_liquidity_score=int(os.getenv("MIN_LIQUIDITY_SCORE", "70")),
                confidence_threshold=int(os.getenv("CONFIDENCE_THRESHOLD", "85")),
                max_trade_size_usdt=float(os.getenv("MAX_TRADE_SIZE_USDT", "100.0")),
                min_trade_size_usdt=float(os.getenv("MIN_TRADE_SIZE_USDT", "10.0")),
                daily_loss_limit_usdt=float(os.getenv("DAILY_LOSS_LIMIT_USDT", "50.0")),
                max_concurrent_trades=int(os.getenv("MAX_CONCURRENT_TRADES", "1")),
            ),
            api=api_config,
            database=DatabaseConfig(
                path=os.getenv("DATABASE_PATH", "data/bybit_arb.db"),
                backup_enabled=os.getenv("BACKUP_ENABLED", "true").lower() == "true",
                backup_interval_hours=int(os.getenv("BACKUP_INTERVAL_HOURS", "24")),
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                console_output=os.getenv("CONSOLE_LOGGING", "true").lower() == "true",
                file_output=os.getenv("FILE_LOGGING", "true").lower() == "true",
                log_dir=os.getenv("LOG_DIR", "logs"),
                max_log_files=int(os.getenv("MAX_LOG_FILES", "7")),
            ),
            notifications=NotificationConfig(
                enabled=os.getenv("NOTIFICATIONS_ENABLED", "false").lower() == "true",
                telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
                telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
                notify_on_trade=os.getenv("NOTIFY_ON_TRADE", "true").lower() == "true",
                notify_on_error=os.getenv("NOTIFY_ON_ERROR", "true").lower() == "true",
                notify_daily_summary=os.getenv("NOTIFY_DAILY_SUMMARY", "true").lower() == "true",
            ),
            performance=PerformanceConfig(
                websocket_ping_interval=int(os.getenv("WS_PING_INTERVAL", "30")),
                order_book_cache_ttl=int(os.getenv("ORDER_BOOK_TTL", "5000")),
                scanner_refresh_ms=int(os.getenv("SCANNER_REFRESH_MS", "100")),
                max_cpu_percent=float(os.getenv("MAX_CPU_PERCENT", "25.0")),
                max_memory_mb=int(os.getenv("MAX_MEMORY_MB", "500")),
            ),
        )
    
    def validate_for_live_trading(self) -> None:
        """Validate configuration for live trading mode."""
        if self.trading.mode == "live":
            if not self.api:
                raise ValueError("API credentials required for live trading")
            if self.api.testnet:
                raise ValueError("Cannot use testnet for live trading. Set BYBIT_TESTNET=false")


def get_config() -> Config:
    """Get application configuration singleton."""
    return Config.load_from_env()
