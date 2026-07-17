#!/usr/bin/env python3
"""
Bybit AI Trading Platform - Main Entry Point
Enterprise-grade cryptocurrency trading system.
"""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.config import get_config, Config
from app.core.models import SystemHealth, PerformanceProfile
from app.api.client import BybitAPIClient
from app.exchange.websocket import WebSocketManager


class TradingPlatform:
    """
    Main orchestrator for the Bybit AI Trading Platform.
    
    Coordinates all components:
    - API connections (REST + WebSocket)
    - Strategy execution
    - Risk management
    - Portfolio tracking
    - Notifications
    - Database operations
    """

    def __init__(self, config: Config):
        self.config = config
        self._running = False
        self._start_time: Optional[datetime] = None
        
        # Initialize components
        self.api_client: Optional[BybitAPIClient] = None
        self.ws_manager: Optional[WebSocketManager] = None
        
        # State
        self.system_health = SystemHealth()
        self.system_health.performance_profile = self.config.performance.profile
        
        # Setup logging
        self._setup_logging()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_logging(self):
        """Configure application logging."""
        logger.remove()  # Remove default handler

        # Console handler with colors
        if self.config.logging.console_output:
            logger.add(
                sys.stderr,
                level=self.config.logging.level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                colorize=True,
            )

        # File handler
        if self.config.logging.file_output:
            log_dir = Path(self.config.logging.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                f"{log_dir}/bybit_ai_{{time:YYYY-MM-DD}}.log",
                level=self.config.logging.level,
                rotation="00:00",
                retention=f"{self.config.logging.max_log_files} days",
                compression="zip",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            )

        logger.info("Logging initialized")
        logger.info(f"Performance profile: {self.config.performance.profile}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing platform...")
        
        try:
            # Initialize API client if credentials available
            if self.config.exchange.api_key and self.config.exchange.secret_key:
                self.api_client = BybitAPIClient(self.config.exchange)
                await self.api_client.connect()
                logger.info("API client connected")
                
                # Fetch symbols
                symbols = await self.api_client.get_symbols()
                logger.info(f"Loaded {len(symbols)} symbols")
            else:
                logger.warning("No API credentials configured - running in read-only mode")

            # Initialize WebSocket manager
            self.ws_manager = WebSocketManager(self.config)
            
            # Update system health
            self.system_health.is_healthy = True
            self.system_health.last_heartbeat = datetime.utcnow()

            logger.info("Initialization complete")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    async def start(self):
        """Start the trading platform."""
        logger.info("Starting platform...")
        self._running = True
        self._start_time = datetime.utcnow()

        try:
            # Connect WebSocket if we have symbols to subscribe to
            if self.config.scanner.enabled and self.config.scanner.symbols:
                ws_url = "wss://stream-testnet.bybit.com/v5/public/spot" if self.config.exchange.testnet else "wss://stream.bybit.com/v5/public/spot"
                
                # Subscribe to order book channels for configured symbols
                channels = [f"orderbook.50.{sym}" for sym in self.config.scanner.symbols[:10]]
                
                await self.ws_manager.connect(ws_url)
                await self.ws_manager.subscribe(channels)
                
                logger.info(f"WebSocket connected - subscribed to {len(channels)} channels")

            # Main trading loop
            await self._trading_loop()

        except Exception as e:
            logger.error(f"Platform error: {e}")
            raise
        finally:
            await self.shutdown()

    async def _trading_loop(self):
        """Main trading loop."""
        logger.info("Starting trading loop...")
        
        scan_count = 0
        scanner_interval = self.config.performance.scanner_refresh_ms / 1000

        while self._running:
            try:
                scan_start = datetime.utcnow()
                
                # Update system health metrics
                self._update_system_health()
                
                # Log periodic status
                if scan_count % 60 == 0:
                    logger.info(
                        f"Platform status: uptime={self._get_uptime()}, "
                        f"scans={scan_count}, "
                        f"WS latency={self.ws_manager.latency_ms:.1f}ms" if self.ws_manager else ""
                    )
                
                scan_count += 1
                
                # Wait for next iteration
                elapsed = (datetime.utcnow() - scan_start).total_seconds()
                sleep_time = max(0, scanner_interval - elapsed)
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(1)

        logger.info("Trading loop stopped")

    def _update_system_health(self):
        """Update system health metrics."""
        import psutil
        
        self.system_health.cpu_usage_percent = psutil.cpu_percent(interval=0.1)
        self.system_health.memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
        self.system_health.active_connections = self.ws_manager.subscription_count if self.ws_manager else 0
        self.system_health.last_heartbeat = datetime.utcnow()
        
        # Check resource limits
        if self.system_health.cpu_usage_percent > self.config.performance.max_cpu_percent:
            self.system_health.issues.append(f"High CPU usage: {self.system_health.cpu_usage_percent:.1f}%")
        
        if self.system_health.memory_usage_mb > self.config.performance.max_memory_mb:
            self.system_health.issues.append(f"High memory usage: {self.system_health.memory_usage_mb:.1f}MB")

    def _get_uptime(self) -> str:
        """Get platform uptime as formatted string."""
        if not self._start_time:
            return "0s"
        
        delta = datetime.utcnow() - self._start_time
        total_seconds = int(delta.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    async def shutdown(self):
        """Gracefully shutdown the platform."""
        logger.info("Shutting down...")
        self._running = False

        # Close WebSocket
        if self.ws_manager:
            await self.ws_manager.disconnect()

        # Close API client
        if self.api_client:
            await self.api_client.close()

        logger.info(f"Shutdown complete - Total uptime: {self._get_uptime()}")


async def main():
    """Main entry point."""
    try:
        # Load configuration
        config = get_config()
        
        # Validate for live mode
        if config.trading.mode == "live":
            config.validate_for_live_trading()

        # Create and run platform
        platform = TradingPlatform(config)

        await platform.initialize()
        await platform.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
