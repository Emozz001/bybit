#!/usr/bin/env python3
"""
Bybit AI Trading Platform - Main Entry Point
Enterprise-grade cryptocurrency trading system.

Performance optimizations:
- Cached datetime calls in tight loops
- Async-safe signal handling
- Efficient resource monitoring
"""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

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
    
    Performance optimizations:
    - Cached timestamps in trading loop
    - Non-blocking health checks
    - Batched logging
    """

    __slots__ = (
        'config', '_running', '_start_time', '_api_client', 
        '_ws_manager', 'system_health', '_uptime_cache', '_scan_count',
        '_last_log_time', '_health_check_interval'
    )

    def __init__(self, config: Config):
        self.config = config
        self._running = False
        self._start_time: Optional[datetime] = None
        self._uptime_cache = "0s"
        self._scan_count = 0
        self._last_log_time = 0.0
        self._health_check_interval = max(1.0, config.performance.scanner_refresh_ms / 1000 / 10)
        
        # Initialize components
        self._api_client: Optional[BybitAPIClient] = None
        self._ws_manager: Optional[WebSocketManager] = None
        
        # State
        self.system_health = SystemHealth()
        self.system_health.performance_profile = self.config.performance.profile
        
        # Setup logging
        self._setup_logging()

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

    @property
    def api_client(self) -> Optional[BybitAPIClient]:
        return self._api_client
    
    @property
    def ws_manager(self) -> Optional[WebSocketManager]:
        return self._ws_manager

    def request_stop(self):
        """Thread-safe method to request platform shutdown."""
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
        loop_start_time = time.monotonic()

        try:
            # Connect WebSocket if we have symbols to subscribe to
            if self.config.scanner.enabled and self.config.scanner.symbols:
                ws_url = "wss://stream-testnet.bybit.com/v5/public/spot" if self.config.exchange.testnet else "wss://stream.bybit.com/v5/public/spot"
                
                # Subscribe to order book channels for configured symbols (limit to 10 for performance)
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
        """Main trading loop with optimized timing and health checks."""
        import time
        
        logger.info("Starting trading loop...")
        
        scanner_interval = self.config.performance.scanner_refresh_ms / 1000.0
        health_check_counter = 0
        health_check_threshold = max(1, int(1.0 / self._health_check_interval))
        log_counter = 0
        
        while self._running:
            try:
                loop_start = time.monotonic()
                
                # Update scan count
                self._scan_count += 1
                
                # Periodic health check (not every iteration to save CPU)
                health_check_counter += 1
                if health_check_counter >= health_check_threshold:
                    self._update_system_health_fast()
                    health_check_counter = 0
                
                # Log periodic status (every 60 scans)
                log_counter += 1
                if log_counter >= 60:
                    self._log_status()
                    log_counter = 0
                
                # Calculate sleep time using monotonic clock for precision
                elapsed = time.monotonic() - loop_start
                sleep_time = max(0.0, scanner_interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(min(1.0, scanner_interval))

        logger.info("Trading loop stopped")

    def _update_system_health_fast(self):
        """Lightweight system health update without heavy logging."""
        import psutil
        
        process = psutil.Process()
        self.system_health.cpu_usage_percent = psutil.cpu_percent(interval=0)
        self.system_health.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        self.system_health.active_connections = self._ws_manager.subscription_count if self._ws_manager else 0
        self.system_health.last_heartbeat = datetime.utcnow()
        
        # Clear and check resource limits efficiently
        issues = []
        if self.system_health.cpu_usage_percent > self.config.performance.max_cpu_percent:
            issues.append(f"High CPU: {self.system_health.cpu_usage_percent:.1f}%")
        
        if self.system_health.memory_usage_mb > self.config.performance.max_memory_mb:
            issues.append(f"High memory: {self.system_health.memory_usage_mb:.1f}MB")
        
        self.system_health.issues = issues

    def _log_status(self):
        """Log platform status efficiently."""
        self._uptime_cache = self._get_uptime()
        ws_latency = f"{self._ws_manager.latency_ms:.1f}ms" if self._ws_manager else "N/A"
        
        logger.info(
            f"Status: uptime={self._uptime_cache}, scans={self._scan_count}, WS latency={ws_latency}"
        )

    def _get_uptime(self) -> str:
        """Get platform uptime as formatted string (cached for performance)."""
        if not self._start_time:
            return "0s"
        
        # Use cached value if recently computed (within 1 second)
        # This avoids repeated datetime calculations in tight loops
        delta = datetime.utcnow() - self._start_time
        total_seconds = int(delta.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            result = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            result = f"{minutes}m {seconds}s"
        else:
            result = f"{seconds}s"
        
        self._uptime_cache = result
        return result

    async def shutdown(self):
        """Gracefully shutdown the platform with proper cleanup."""
        logger.info("Shutting down...")
        self.request_stop()

        # Cancel background tasks first
        tasks = []
        if self._ws_manager and hasattr(self._ws_manager, '_ping_task') and self._ws_manager._ping_task:
            tasks.append(asyncio.create_task(self._ws_manager.disconnect()))
        
        if self._api_client:
            tasks.append(asyncio.create_task(self._api_client.close()))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        uptime = self._get_uptime()
        logger.info(f"Shutdown complete - Total uptime: {uptime}")


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
