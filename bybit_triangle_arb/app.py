"""
Bybit Triangle Arbitrage Bot - Main Application Entry Point.
Orchestrates all components for triangular arbitrage trading.
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

from loguru import logger

from config.settings import get_config, Config
from core.models import SystemHealth, LatencyMetrics
from core.websocket.manager import WebSocketManager
from core.api.client import BybitAPIClient
from core.triangle.generator import TriangleGenerator
from core.pricing.engine import PricingEngine


class TriangleArbitrageBot:
    """
    Main orchestrator for the triangular arbitrage trading system.
    
    Coordinates:
    - Market data collection (WebSocket)
    - Symbol discovery (REST API)
    - Triangle generation
    - Opportunity scanning
    - Trade execution
    - Risk management
    - Logging and monitoring
    """
    
    def __init__(self, config: Config):
        self.config = config
        self._running = False
        
        # Initialize components
        self.ws_manager: Optional[WebSocketManager] = None
        self.api_client: Optional[BybitAPIClient] = None
        self.triangle_generator = TriangleGenerator()
        self.pricing_engine = PricingEngine(config)
        
        # State
        self.system_health = SystemHealth()
        self.latency_metrics = LatencyMetrics()
        
        # Setup logging
        self._setup_logging()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """Configure application logging."""
        logger.remove()  # Remove default handler
        
        # Console handler
        if self.config.logging.console_output:
            logger.add(
                sys.stderr,
                level=self.config.logging.level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                colorize=True,
            )
        
        # File handler
        if self.config.logging.file_output:
            logger.add(
                f"{self.config.logging.log_dir}/bybit_arb_{{time:YYYY-MM-DD}}.log",
                level=self.config.logging.level,
                rotation="00:00",
                retention=f"{self.config.logging.max_log_files} days",
                compression="zip",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            )
        
        logger.info("Logging initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing bot...")
        
        try:
            # Initialize API client if credentials available
            if self.config.api:
                self.api_client = BybitAPIClient(self.config.api)
                await self.api_client.connect()
                logger.info("API client connected")
                
                # Fetch symbols
                symbols = await self.api_client.get_symbols()
                self.triangle_generator.update_symbols(symbols)
                self.pricing_engine.update_symbols(symbols)
                logger.info(f"Loaded {len(symbols)} symbols")
                
                # Generate triangles
                triangles = self.triangle_generator.generate_triangles("USDT")
                logger.info(f"Generated {len(triangles)} triangle opportunities")
            
            # Initialize WebSocket manager
            self.ws_manager = WebSocketManager(self.config)
            
            logger.info("Initialization complete")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    async def start(self):
        """Start the trading bot."""
        logger.info("Starting bot...")
        self._running = True
        
        try:
            # Connect WebSocket
            ws_url = "wss://stream.bybit.com/v5/public/spot"
            if self.config.api and self.config.api.testnet:
                ws_url = "wss://stream-testnet.bybit.com/v5/public/spot"
            
            # Subscribe to order book channels for top symbols
            top_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
            channels = [f"orderbook.50.{sym}" for sym in top_symbols]
            
            await self.ws_manager.connect(ws_url)
            await self.ws_manager.subscribe(channels)
            
            logger.info("WebSocket connected and subscribed")
            
            # Main scanning loop
            await self._scanning_loop()
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _scanning_loop(self):
        """Main opportunity scanning loop."""
        logger.info("Starting opportunity scanner...")
        
        scan_count = 0
        opportunities_found = 0
        
        while self._running:
            try:
                scan_start = datetime.utcnow()
                
                # Get current triangles
                triangles = self.triangle_generator._triangles
                
                # Scan each triangle
                for triangle in triangles:
                    if not self._running:
                        break
                    
                    # Get order books
                    order_books = {}
                    for symbol in triangle.get_symbols():
                        ob = self.ws_manager.get_order_book(symbol)
                        if ob:
                            order_books[symbol] = ob
                    
                    # Skip if we don't have all order books
                    if len(order_books) != 3:
                        continue
                    
                    # Calculate opportunity
                    opportunity = self.pricing_engine.calculate_opportunity(
                        triangle,
                        order_books,
                        trade_amount_usdt=50.0  # Test amount
                    )
                    
                    if opportunity and opportunity.is_profitable:
                        should_execute, reason = self.pricing_engine.should_execute(opportunity)
                        
                        if should_execute:
                            opportunities_found += 1
                            logger.info(
                                f"🎯 Opportunity found! "
                                f"Triangle: {triangle.start_asset}→{triangle.middle_asset1}→{triangle.middle_asset2}→{triangle.start_asset} "
                                f"Net Profit: {opportunity.net_profit_pct:.3f}% "
                                f"Confidence: {opportunity.confidence_score}"
                            )
                            
                            # In live mode, would execute trade here
                            if self.config.trading.mode == "live":
                                await self._execute_trade(opportunity)
                        else:
                            logger.debug(f"Opportunity rejected: {reason}")
                
                # Update metrics
                scan_count += 1
                scan_time = (datetime.utcnow() - scan_start).total_seconds() * 1000
                self.latency_metrics.scanner_latency_ms = scan_time
                
                # Log periodic summary
                if scan_count % 100 == 0:
                    logger.info(
                        f"Scanner status: {scan_count} scans, "
                        f"{opportunities_found} opportunities found, "
                        f"Avg latency: {self.latency_metrics.scanner_latency_ms:.1f}ms"
                    )
                
                # Rate limiting
                refresh_interval = self.config.performance.scanner_refresh_ms / 1000
                await asyncio.sleep(refresh_interval)
                
            except Exception as e:
                logger.error(f"Scanner error: {e}")
                await asyncio.sleep(1)
        
        logger.info("Scanner stopped")
    
    async def _execute_trade(self, opportunity):
        """Execute a trade (placeholder for full implementation)."""
        logger.warning("Trade execution not yet implemented in this version")
        # Full implementation would:
        # 1. Lock prices
        # 2. Validate opportunity again
        # 3. Execute leg 1
        # 4. Wait for fill
        # 5. Execute leg 2
        # 6. Wait for fill
        # 7. Execute leg 3
        # 8. Verify result
        # 9. Record trade
    
    async def shutdown(self):
        """Gracefully shutdown the bot."""
        logger.info("Shutting down...")
        self._running = False
        
        # Close WebSocket
        if self.ws_manager:
            await self.ws_manager.disconnect()
        
        # Close API client
        if self.api_client:
            await self.api_client.close()
        
        logger.info("Shutdown complete")


async def main():
    """Main entry point."""
    try:
        # Load configuration
        config = get_config()
        
        # Validate for live mode
        if config.trading.mode == "live":
            config.validate_for_live_trading()
        
        # Create and run bot
        bot = TriangleArbitrageBot(config)
        
        await bot.initialize()
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
