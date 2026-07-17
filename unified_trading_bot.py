"""
Unified Trading Bot System - Bybit Triangle Arbitrage & Trend Trading
======================================================================
A comprehensive trading system combining:
1. Triangular Arbitrage (scans USDT pairs for arbitrage opportunities)
2. Trend-Following Trading (technical indicators: SMA, RSI)

SAFETY FEATURES:
- Default SIMULATION mode (no real trades)
- Configurable risk management
- Daily loss limits and trade limits
- Emergency stop mechanisms
- Cooldown periods after losses

CONFIGURATION:
Set environment variables before running:
  export BYBIT_API_KEY='your_api_key'
  export BYBIT_SECRET='your_secret'
  export LIVE_MODE=false  # Set to 'true' for live trading (TEST FIRST!)

Get demo keys from: https://testnet.bybit.com/
"""

import asyncio
import aiohttp
import ccxt
import time
import os
import hmac
import hashlib
import json
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Set, Any, NamedTuple
from collections import deque
from dataclasses import dataclass, field
from functools import reduce, lru_cache
from operator import add
from itertools import islice, filterfalse
import random

# Try to import Rich for UI (optional)
try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Rich library not available. Running in basic mode.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("UnifiedBot")

# =============================================================================
# IMMUTABLE CONFIGURATION
# =============================================================================

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_SECRET = os.getenv("BYBIT_SECRET")
LIVE_MODE = os.getenv("LIVE_MODE", "false").lower() == "true"
USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

# Validate API keys on startup
if not BYBIT_API_KEY or "YOUR_BYBIT" in str(BYBIT_API_KEY) or not BYBIT_SECRET or "YOUR_BYBIT" in str(BYBIT_SECRET):
    logger.warning("⚠️  API keys not properly configured. Running in SIMULATION mode only.")
    logger.warning("   Set BYBIT_API_KEY and BYBIT_SECRET environment variables.")
    logger.warning("   Get demo keys from: https://testnet.bybit.com/")


@dataclass(frozen=True)
class ArbConfig:
    """Immutable configuration for arbitrage trading."""
    max_trade_amount_usdt: float = float(os.getenv("MAX_TRADE_AMOUNT", "50.0"))
    min_profit_percent: float = float(os.getenv("MIN_PROFIT_PERCENT", "0.3"))
    max_daily_loss_usdt: float = float(os.getenv("MAX_DAILY_LOSS", "20.0"))
    max_daily_trades: int = int(os.getenv("MAX_DAILY_TRADES", "20"))
    max_consecutive_errors: int = int(os.getenv("MAX_ERRORS", "3"))
    max_consecutive_losses: int = int(os.getenv("MAX_LOSSES", "5"))
    cooldown_after_loss_sec: float = float(os.getenv("COOLDOWN_SEC", "60.0"))
    scan_interval: float = float(os.getenv("SCAN_INTERVAL", "2.0"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "8"))
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT", "15"))
    cache_ttl: float = float(os.getenv("CACHE_TTL", "0.8"))
    maker_fee_percent: float = float(os.getenv("MAKER_FEE", "0.1"))
    taker_fee_percent: float = float(os.getenv("TAKER_FEE", "0.1"))
    order_type: str = "Market"
    ioc_order: bool = True


@dataclass(frozen=True)
class TrendConfig:
    """Immutable configuration for trend-following trading."""
    symbol: str = "BTC/USDT"
    timeframe: str = "5m"
    leverage: int = 3
    risk_per_trade: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    cache_max_size: int = 100
    update_interval: int = 2
    max_concurrent_requests: int = 3
    max_daily_trades: int = 10
    max_daily_loss_pct: float = 0.05
    cooldown_period: float = 300.0
    emergency_stop_enabled: bool = True
    max_slippage_pct: float = 0.005
    test_mode: bool = not LIVE_MODE


ARB_CONFIG = ArbConfig()
TREND_CONFIG = TrendConfig()
BASE_URL = "https://api-testnet.bybit.com" if USE_TESTNET else "https://api.bybit.com"

# =============================================================================
# IMMUTABLE DATA STRUCTURES
# =============================================================================

class Position(NamedTuple):
    """Immutable trading position."""
    side: str
    entry_price: float
    size: float
    timestamp: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    @classmethod
    def create(cls, side: str, entry_price: float, size: float,
               stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> 'Position':
        return cls(side=side, entry_price=entry_price, size=size,
                   timestamp=time.time(), stop_loss=stop_loss, take_profit=take_profit)


class Opportunity(NamedTuple):
    """Immutable arbitrage opportunity."""
    symbol_a: str
    symbol_b: str
    path: str
    expected_profit_pct: float
    price_a: float
    price_b: float
    price_c: float
    timestamp: float
    trade_amount: float = ARB_CONFIG.max_trade_amount_usdt


class TradeRecord(NamedTuple):
    """Immutable trade record."""
    timestamp: float
    path: str
    profit_pct: float
    profit_usdt: float
    status: str


class ArbTradeStats(NamedTuple):
    """Immutable arbitrage trading statistics."""
    total_scans: int = 0
    opportunities_found: int = 0
    trades_executed: int = 0
    successful_trades: int = 0
    losing_trades: int = 0
    total_profit_usdt: float = 0.0
    daily_pnl: float = 0.0
    daily_trades: int = 0
    consecutive_errors: int = 0
    consecutive_losses: int = 0
    last_error_time: float = 0.0
    last_trade_time: float = 0.0
    last_loss_time: float = 0.0
    trade_history: Tuple[TradeRecord, ...] = ()
    start_time: float = field(default_factory=time.time)

    def win_rate(self) -> float:
        if self.trades_executed == 0:
            return 0.0
        return (self.successful_trades / self.trades_executed) * 100


class TrendTradeStats(NamedTuple):
    """Immutable trend-following trading statistics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    daily_trades: int = 0
    daily_pnl: float = 0.0
    last_trade_time: float = 0.0
    consecutive_losses: int = 0
    max_drawdown: float = 0.0
    peak_balance: float = 0.0
    account_balance: float = 0.0

    @property
    def win_rate(self) -> float:
        return (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0

    def reset_daily(self) -> 'TrendTradeStats':
        return self._replace(daily_trades=0, daily_pnl=0.0)

    def add_trade(self, pnl_usd: float, is_win: bool) -> 'TrendTradeStats':
        return self._replace(
            total_trades=self.total_trades + 1,
            winning_trades=self.winning_trades + (1 if is_win else 0),
            losing_trades=self.losing_trades + (0 if is_win else 1),
            total_pnl=self.total_pnl + pnl_usd,
            daily_pnl=self.daily_pnl + pnl_usd,
            consecutive_losses=0 if is_win else self.consecutive_losses + 1
        )

    def update_balance(self, balance: float) -> 'TrendTradeStats':
        new_peak = max(self.peak_balance, balance)
        drawdown = (new_peak - balance) / new_peak if new_peak > 0 else 0
        return self._replace(
            account_balance=balance,
            peak_balance=new_peak,
            max_drawdown=max(self.max_drawdown, drawdown)
        )

    def is_trading_allowed(self) -> Tuple[bool, str]:
        if self.daily_trades >= TREND_CONFIG.max_daily_trades:
            return False, f"Daily trade limit reached ({TREND_CONFIG.max_daily_trades})"
        if self.daily_pnl <= -self.account_balance * TREND_CONFIG.max_daily_loss_pct:
            return False, f"Daily loss limit reached ({TREND_CONFIG.max_daily_loss_pct*100}%)"
        if time.time() - self.last_trade_time < TREND_CONFIG.cooldown_period and self.consecutive_losses > 0:
            remaining = TREND_CONFIG.cooldown_period - (time.time() - self.last_trade_time)
            return False, f"Cooldown period active ({remaining:.0f}s remaining)"
        return True, "OK"


# =============================================================================
# CACHED DATA STRUCTURES
# =============================================================================

class CachedData:
    """Efficient data caching for market data."""
    __slots__ = ['closes', 'timestamps', 'last_update']

    def __init__(self, max_size: int = TREND_CONFIG.cache_max_size):
        self.closes: deque = deque(maxlen=max_size)
        self.timestamps: deque = deque(maxlen=max_size)
        self.last_update: float = 0.0

    def update(self, ohlcv: List[List]) -> bool:
        if not ohlcv:
            return False
        latest_timestamp = ohlcv[-1][0]
        if latest_timestamp <= self.last_update:
            return False
        self.closes.extend(candle[4] for candle in ohlcv)
        self.timestamps.extend(candle[0] for candle in ohlcv)
        self.last_update = latest_timestamp
        return True

    def get_closes(self, count: int) -> List[float]:
        return list(islice(self.closes, max(0, len(self.closes) - count), len(self.closes)))


# =============================================================================
# TRIANGULAR ARBITRAGE BOT
# =============================================================================

class BybitArbBot:
    """Triangular arbitrage bot for scanning and executing arb opportunities."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = BASE_URL
        self.symbols: List[str] = []
        self.tickers: Dict[str, dict] = {}
        self.stats = ArbTradeStats()
        self.running = False
        self.cache_ttl = ARB_CONFIG.cache_ttl
        self.last_fetch_time = 0.0
        self.daily_reset_time = time.time()

    async def start(self):
        """Initialize session and start loops."""
        connector = aiohttp.TCPConnector(limit=ARB_CONFIG.max_concurrent_requests, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=ARB_CONFIG.request_timeout, connect=5)

        headers = {
            "X-BAPI-API-KEY": BYBIT_API_KEY or "",
            "X-BAPI-SIGN": "",
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": str(int(time.time() * 1000)),
            "X-BAPI-RECV-WINDOW": "5000",
            "Content-Type": "application/json"
        }

        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers)
        self.running = True

        mode_str = "LIVE" if LIVE_MODE else ("DEMO" if USE_TESTNET else "SIMULATION")
        logger.info("=" * 60)
        logger.info(f"🚀 Triangular Arb Bot Started ({mode_str} MODE)")
        logger.info("=" * 60)
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Scan Interval: {ARB_CONFIG.scan_interval}s | Min Profit: {ARB_CONFIG.min_profit_percent}%")
        logger.info(f"Max Trade Amount: ${ARB_CONFIG.max_trade_amount_usdt} | Max Daily Loss: ${ARB_CONFIG.max_daily_loss_usdt}")
        logger.info("=" * 60)

        await self.load_symbols()
        self.reset_daily_stats_if_needed()

        try:
            await self.main_loop()
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown requested by user...")
        finally:
            await self.stop()

    async def stop(self):
        """Graceful shutdown."""
        self.running = False
        runtime = time.time() - self.stats.start_time
        logger.info("=" * 60)
        logger.info("📊 FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Runtime: {timedelta(seconds=int(runtime))}")
        logger.info(f"Total Scans: {self.stats.total_scans}")
        logger.info(f"Opportunities Found: {self.stats.opportunities_found}")
        logger.info(f"Trades Executed: {self.stats.trades_executed}")
        logger.info(f"Win Rate: {self.stats.win_rate():.2f}%")
        logger.info(f"Total P&L: ${self.stats.total_profit_usdt:.4f}")
        logger.info(f"Daily P&L: ${self.stats.daily_pnl:.4f}")
        logger.info("=" * 60)

        if self.session:
            await self.session.close()
        logger.info("Bot stopped.")

    def reset_daily_stats_if_needed(self):
        """Reset daily counters every 24 hours."""
        now = time.time()
        if now - self.daily_reset_time > 86400:
            logger.info("🔄 Resetting daily statistics...")
            self.stats.daily_pnl = 0.0
            self.stats.daily_trades = 0
            self.stats.consecutive_losses = 0
            self.daily_reset_time = now

    async def load_symbols(self):
        """Fetch all USDT spot symbols."""
        url = f"{self.base_url}/v5/market/instruments-info?category=spot&limit=1000"
        try:
            async with self.session.get(url) as resp:
                data = await resp.json()
                if data.get('retCode') == 0:
                    raw_symbols = [item['name'] for item in data['result']['list'] if item.get('quoteCoin') == 'USDT']
                    self.symbols = [
                        s for s in raw_symbols
                        if not any(x in s for x in ['UPUSDT', 'DOWNUSDT', 'BULL', 'BEAR'])
                        and s.endswith('USDT')
                    ]
                    logger.info(f"✅ Loaded {len(self.symbols)} valid USDT pairs")
                else:
                    logger.error(f"❌ Failed to load symbols: {data.get('retMsg', 'Unknown error')}")
                    self.symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT']
                    logger.warning(f"⚠️  Using fallback symbol list: {len(self.symbols)} pairs")
        except Exception as e:
            logger.error(f"❌ Error loading symbols: {e}")
            self.stats.consecutive_errors += 1
            self.symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT']

    def _generate_signature(self, params: str, timestamp: str) -> str:
        """Generate HMAC SHA256 signature for private requests."""
        param_str = timestamp + (BYBIT_API_KEY or "") + "5000" + params
        signature = hmac.new((BYBIT_SECRET or "").encode('utf-8'), param_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature

    async def get_tickers(self) -> Dict[str, dict]:
        """Fetch all tickers with caching."""
        now = time.time()
        if now - self.last_fetch_time < self.cache_ttl and self.tickers:
            return self.tickers

        url = f"{self.base_url}/v5/market/tickers?category=spot"
        try:
            async with self.session.get(url) as resp:
                data = await resp.json()
                if data.get('retCode') == 0:
                    new_tickers = {}
                    for item in data['result']['list']:
                        symbol = item['symbol']
                        try:
                            bid = float(item['bid1']) if item.get('bid1') else 0
                            ask = float(item['ask1']) if item.get('ask1') else 0
                            vol = float(item.get('volume24h', 0))
                            if bid > 0 and ask > 0 and vol > 0:
                                new_tickers[symbol] = {'bid': bid, 'ask': ask, 'vol': vol}
                        except (ValueError, TypeError):
                            continue

                    if new_tickers:
                        self.tickers = new_tickers
                        self.last_fetch_time = now
                        return new_tickers
                    else:
                        logger.warning("⚠️  No valid tickers received, using cached data")
                        return self.tickers
                else:
                    logger.warning(f"⚠️  Ticker fetch failed: {data.get('retMsg', 'Unknown error')}")
                    return self.tickers
        except asyncio.TimeoutError:
            logger.warning("⏱️  Ticker request timed out, using cached data")
            return self.tickers
        except Exception as e:
            logger.error(f"❌ Network error fetching tickers: {e}")
            self.stats.consecutive_errors += 1
            return self.tickers

    def find_triangular_arbs(self, tickers: Dict[str, dict]) -> List[Opportunity]:
        """Scan for triangular arbitrage: USDT -> A -> B -> USDT."""
        opportunities = []
        usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('USDT')}
        symbol_to_ticker = {s.replace('USDT', ''): s for s in usdt_pairs.keys()}

        for base_symbol in list(usdt_pairs.keys()):
            if base_symbol not in tickers:
                continue

            entry_price = tickers[base_symbol]['ask']
            base_asset = base_symbol.replace('USDT', '')

            potential_targets = [
                k for k in tickers.keys()
                if k.endswith(base_asset) and k != base_symbol and len(k) > len(base_asset)
            ]

            for mid_pair in potential_targets:
                if mid_pair not in tickers:
                    continue

                mid_price = tickers[mid_pair]['ask']
                target_asset = mid_pair.replace(base_asset, '')

                exit_pair = f"{target_asset}USDT"
                if exit_pair not in tickers:
                    continue

                exit_price = tickers[exit_pair]['bid']

                final_usdt = (1.0 / entry_price) / mid_price * exit_price
                gross_profit_pct = (final_usdt - 1.0) * 100

                fee_factor = (1 - (ARB_CONFIG.taker_fee_percent / 100)) ** 3
                net_profit_pct = (final_usdt * fee_factor - 1.0) * 100

                if net_profit_pct > ARB_CONFIG.min_profit_percent:
                    opp = Opportunity(
                        symbol_a=base_asset,
                        symbol_b=target_asset,
                        path=f"USDT->{base_asset}->{target_asset}->USDT",
                        expected_profit_pct=net_profit_pct,
                        price_a=entry_price,
                        price_b=mid_price,
                        price_c=exit_price,
                        timestamp=time.time(),
                        trade_amount=ARB_CONFIG.max_trade_amount_usdt
                    )
                    opportunities.append(opp)

        return opportunities

    async def execute_trade(self, opp: Opportunity):
        """Execute the arbitrage trade sequence with risk management."""
        if self.stats.consecutive_errors >= ARB_CONFIG.max_consecutive_errors:
            logger.critical(f"🛑 Max consecutive errors ({ARB_CONFIG.max_consecutive_errors}) reached. Stopping.")
            self.running = False
            return

        if self.stats.daily_pnl <= -ARB_CONFIG.max_daily_loss_usdt:
            logger.critical(f"🛑 Daily loss limit hit (-${ARB_CONFIG.max_daily_loss_usdt:.2f}). Stopping.")
            self.running = False
            return

        if self.stats.daily_trades >= ARB_CONFIG.max_daily_trades:
            logger.warning(f"⚠️  Daily trade limit ({ARB_CONFIG.max_daily_trades}) reached. Skipping.")
            return

        now = time.time()
        if self.stats.last_loss_time > 0:
            time_since_loss = now - self.stats.last_loss_time
            if time_since_loss < ARB_CONFIG.cooldown_after_loss_sec:
                remaining = ARB_CONFIG.cooldown_after_loss_sec - time_since_loss
                if self.stats.total_scans % 50 == 0:
                    logger.info(f"⏳ Cooldown active: {remaining:.1f}s remaining...")
                return

        if self.stats.consecutive_losses >= ARB_CONFIG.max_consecutive_losses:
            logger.critical(f"🛑 Max consecutive losses ({ARB_CONFIG.max_consecutive_losses}) reached. Stopping.")
            self.running = False
            return

        logger.info("=" * 50)
        logger.info(f"💰 OPPORTUNITY FOUND!")
        logger.info(f"   Path: {opp.path}")
        logger.info(f"   Expected Profit: {opp.expected_profit_pct:.4f}%")
        logger.info(f"   Trade Amount: ${opp.trade_amount:.2f}")
        logger.info(f"   Est. Profit: ${opp.trade_amount * (opp.expected_profit_pct / 100):.4f}")
        logger.info("=" * 50)

        if not LIVE_MODE:
            profit_usdt = opp.trade_amount * (opp.expected_profit_pct / 100)
            slippage_factor = random.uniform(0.85, 1.0)
            actual_profit = profit_usdt * slippage_factor

            status = 'success' if actual_profit > 0 else 'loss'
            record = TradeRecord(timestamp=now, path=opp.path, profit_pct=opp.expected_profit_pct * slippage_factor,
                                profit_usdt=actual_profit, status=status)

            self.stats = self.stats._replace(
                trade_history=self.stats.trade_history + (record,),
                trades_executed=self.stats.trades_executed + 1,
                daily_trades=self.stats.daily_trades + 1,
                total_profit_usdt=self.stats.total_profit_usdt + actual_profit,
                daily_pnl=self.stats.daily_pnl + actual_profit,
                last_trade_time=now
            )

            if actual_profit > 0:
                self.stats = self.stats._replace(
                    successful_trades=self.stats.successful_trades + 1,
                    consecutive_losses=0
                )
                logger.info(f"✅ SIMULATED: Profit ${actual_profit:.4f} (Win #{self.stats.successful_trades})")
            else:
                self.stats = self.stats._replace(
                    losing_trades=self.stats.losing_trades + 1,
                    consecutive_losses=self.stats.consecutive_losses + 1,
                    last_loss_time=now
                )
                logger.warning(f"❌ SIMULATED: Loss ${actual_profit:.4f} (Loss #{self.stats.consecutive_losses})")
            return

        logger.info("🔴 LIVE EXECUTION MODE - Executing real trades...")
        # Live execution logic would go here
        # For safety, we're keeping it in simulation mode by default

    async def main_loop(self):
        """Main scanning and trading loop."""
        logger.info("🔄 Starting main loop...")

        while self.running:
            start_time = time.time()
            self.reset_daily_stats_if_needed()

            tickers = await self.get_tickers()
            self.stats = self.stats._replace(total_scans=self.stats.total_scans + 1)

            if not tickers:
                logger.warning("⚠️  No ticker data available, waiting...")
                await asyncio.sleep(1)
                continue

            opps = await asyncio.to_thread(self.find_triangular_arbs, tickers)

            if opps:
                self.stats = self.stats._replace(opportunities_found=self.stats.opportunities_found + len(opps))
                opps.sort(key=lambda x: x.expected_profit_pct, reverse=True)
                top_opp = opps[0]
                logger.info(f"📊 Found {len(opps)} opportunities | Best: {top_opp.path} ({top_opp.expected_profit_pct:.3f}%)")
                await self.execute_trade(top_opp)
            else:
                if self.stats.total_scans % 20 == 0:
                    logger.info(
                        f"🔍 Scanning... ({len(tickers)} pairs) | "
                        f"Scans: {self.stats.total_scans} | "
                        f"Opps: {self.stats.opportunities_found} | "
                        f"Trades: {self.stats.trades_executed} | "
                        f"P&L: ${self.stats.daily_pnl:.4f}"
                    )

            elapsed = time.time() - start_time
            sleep_time = max(0, ARB_CONFIG.scan_interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)


# =============================================================================
# TREND-FOLLOWING TRADING BOT
# =============================================================================

class TrendTradingBot:
    """Trend-following trading bot with technical indicators."""

    def __init__(self):
        self.exchange = ccxt.bybit({
            'apiKey': BYBIT_API_KEY or '',
            'secret': BYBIT_SECRET or '',
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.position: Optional[Position] = None
        self.account_balance = 0.0
        self.stats = TrendTradeStats()
        self.starting_balance = 0.0
        self.emergency_stop = False
        self.last_error_time = 0.0
        self.consecutive_errors = 0
        self.start_time = time.time()
        self.running = True
        self.data_cache = CachedData()
        self.last_ticker_fetch = 0.0
        self.ticker_cache_ttl = 1.0
        self.last_daily_reset = datetime.min.date()
        self._stop_loss_multiplier_buy = 1 - TREND_CONFIG.stop_loss_pct
        self._take_profit_multiplier_buy = 1 + TREND_CONFIG.take_profit_pct
        self._stop_loss_multiplier_sell = 1 + TREND_CONFIG.stop_loss_pct
        self._take_profit_multiplier_sell = 1 - TREND_CONFIG.take_profit_pct

        if TREND_CONFIG.test_mode:
            logger.info("WARNING: RUNNING IN TEST MODE - No real trades will be executed")

    def check_connection(self) -> bool:
        """Verify API connection with error handling."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                markets = self.exchange.load_markets()
                balance = self.exchange.fetch_balance()
                self.account_balance = float(balance.get('USDT', {}).get('free', 0))
                return True
            except ccxt.NetworkError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Connection failed after {max_retries} attempts: {e}")
                    return False
                wait_time = 2 ** attempt
                logger.warning(f"Network error, retrying in {wait_time}s ({attempt + 1}/{max_retries}): {e}")
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected connection error: {e}")
                return False
        return False

    def get_market_data(self) -> Tuple[Optional[Dict], Optional[List]]:
        """Fetch ticker and OHLCV data with caching."""
        current_time = time.time()
        ticker = None
        ohlcv = None

        try:
            if current_time - self.last_ticker_fetch > self.ticker_cache_ttl:
                ticker = self.exchange.fetch_ticker(TREND_CONFIG.symbol)
                self.last_ticker_fetch = current_time

            ohlcv = self.exchange.fetch_ohlcv(TREND_CONFIG.symbol, TREND_CONFIG.timeframe, limit=100)

            if ohlcv:
                self.data_cache.update(ohlcv)

            return ticker, ohlcv
        except ccxt.NetworkError as e:
            logger.warning(f"Network error fetching market data: {e}")
            return None, None
        except Exception as e:
            logger.warning(f"Data fetch warning: {e}")
            return None, None

    def calculate_indicators(self, ohlcv: Optional[List] = None) -> Optional[Dict[str, float]]:
        """Calculate technical indicators using cached data."""
        closes = self.data_cache.get_closes(50) if ohlcv is None else (
            [candle[4] for candle in ohlcv] if len(ohlcv) >= 50 else None
        )

        if not closes or len(closes) < 50:
            return None

        sma_20 = reduce(add, closes[-20:]) / 20
        sma_50 = reduce(add, closes[-50:]) / 50

        rsi_period = 14
        if len(closes) < rsi_period + 1:
            rsi = 50.0
        else:
            indices = range(1, rsi_period + 1)
            changes = list(map(lambda i: closes[-i] - closes[-i-1], indices))
            gains = list(map(lambda x: max(0, x), changes))
            losses = list(map(lambda x: max(0, -x), changes))
            avg_gain = reduce(add, gains) / rsi_period
            avg_loss = reduce(add, losses) / rsi_period
            rsi = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))

        return {
            'sma_20': sma_20,
            'sma_50': sma_50,
            'rsi': rsi,
            'current_price': closes[-1]
        }

    def analyze_market(self, indicators: Optional[Dict[str, float]]) -> str:
        """Analyze market and return trading signal."""
        if not indicators:
            return 'HOLD'

        price = indicators['current_price']
        sma_20 = indicators['sma_20']
        sma_50 = indicators['sma_50']
        rsi = indicators['rsi']

        is_bullish_trend = lambda: price > sma_20 > sma_50
        is_bearish_trend = lambda: price < sma_20 < sma_50
        is_rsi_bullish = lambda: 50 < rsi < 70
        is_rsi_bearish = lambda: 30 < rsi < 50

        buy_signal = is_bullish_trend() and is_rsi_bullish()
        sell_signal = is_bearish_trend() and is_rsi_bearish()

        return 'BUY' if buy_signal else ('SELL' if sell_signal else 'HOLD')

    def execute_trade(self, side: str, price: float) -> bool:
        """Execute a market order with position sizing and safety checks."""
        try:
            if self.emergency_stop:
                logger.info("Trading blocked - Emergency stop active")
                return False

            allowed, reason = self.stats.is_trading_allowed()
            if not allowed:
                logger.info(f"Trading blocked - {reason}")
                return False

            if self.consecutive_errors >= 3:
                logger.info("Trading blocked - Too many consecutive errors")
                return False

            risk_amount = self.account_balance * TREND_CONFIG.risk_per_trade
            stop_distance = price * TREND_CONFIG.stop_loss_pct
            contract_size = (risk_amount / stop_distance) / price

            stop_loss, take_profit = (
                (price * self._stop_loss_multiplier_buy, price * self._take_profit_multiplier_buy)
                if side == 'buy' else
                (price * self._stop_loss_multiplier_sell, price * self._take_profit_multiplier_sell)
            )

            if TREND_CONFIG.test_mode:
                logger.info(f"[TEST] Would execute {side.upper()} order for {contract_size:.6f} BTC")
                logger.info(f"[TEST] SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
                self.position = Position.create(side, price, contract_size, stop_loss, take_profit)
                self.stats = self.stats._replace(
                    daily_trades=self.stats.daily_trades + 1,
                    last_trade_time=time.time()
                )
                return True

            # Live execution would go here
            logger.info(f"Live order execution not implemented for safety")
            return False

        except Exception as e:
            self.consecutive_errors += 1
            self.last_error_time = time.time()
            logger.error(f"Trade execution error: {e}")
            return False

    def check_exit_conditions(self, current_price: float) -> None:
        """Check if SL or TP is hit."""
        if not self.position:
            return

        should_close = False
        reason = ""

        if self.position.side == 'buy':
            if current_price <= self.position.entry_price * self._stop_loss_multiplier_buy:
                should_close = True
                reason = "STOP LOSS"
            elif current_price >= self.position.entry_price * self._take_profit_multiplier_buy:
                should_close = True
                reason = "TAKE PROFIT"
        elif self.position.side == 'sell':
            if current_price >= self.position.entry_price * self._stop_loss_multiplier_sell:
                should_close = True
                reason = "STOP LOSS"
            elif current_price <= self.position.entry_price * self._take_profit_multiplier_sell:
                should_close = True
                reason = "TAKE PROFIT"

        if should_close:
            self.close_position(reason, current_price)

    def close_position(self, reason: str, current_price: float) -> None:
        """Close the current position with PnL tracking."""
        try:
            if not self.position or not self.position.size:
                self.position = None
                return

            side = 'sell' if self.position.side == 'buy' else 'buy'

            if self.position.side == 'buy':
                pnl_pct = (current_price - self.position.entry_price) / self.position.entry_price
            else:
                pnl_pct = (self.position.entry_price - current_price) / self.position.entry_price

            pnl_usd = self.position.size * current_price * pnl_pct

            if TREND_CONFIG.test_mode:
                logger.info(f"[TEST] Closing position - {reason} - PnL: ${pnl_usd:.2f} ({pnl_pct*100:.2f}%)")
            else:
                logger.info(f"Closed position - {reason} - PnL: ${pnl_usd:.2f}")

            is_win = pnl_usd > 0
            self.stats = self.stats.add_trade(pnl_usd, is_win)

            if CONFIG.test_mode:
                current_balance = 10000.0 + self.stats.total_pnl
            else:
                current_balance = self.account_balance

            self.stats = self.stats.update_balance(current_balance)
            self.consecutive_errors = 0
            self.position = None

        except Exception as e:
            logger.error(f"Failed to close position: {e}")

    def generate_ui(self, ticker: Optional[Dict], ohlcv: Optional[List],
                    signal: str, indicators: Optional[Dict]) -> str:
        """Generate text-based UI output."""
        lines = []
        lines.append("=" * 60)
        lines.append("Bybit Trend Trading Bot")
        lines.append(f"Symbol: {TREND_CONFIG.symbol} | Timeframe: {TREND_CONFIG.timeframe} | Leverage: {TREND_CONFIG.leverage}x")
        if TREND_CONFIG.test_mode:
            lines.append("WARNING: TEST MODE")
        lines.append("=" * 60)

        if ticker:
            change_color = "+" if ticker.get('percentage', 0) >= 0 else ""
            lines.append(f"Current Price: ${ticker['last']:,.2f}")
            lines.append(f"24h Change: {change_color}{ticker.get('percentage', 0):.2f}%")
        else:
            lines.append("Status: Fetching data...")

        if indicators:
            rsi_status = "Overbought" if indicators['rsi'] > 70 else "Oversold" if indicators['rsi'] < 30 else "Neutral"
            lines.append(f"SMA (20): ${indicators['sma_20']:,.2f}")
            lines.append(f"SMA (50): ${indicators['sma_50']:,.2f}")
            lines.append(f"RSI (14): {indicators['rsi']:.2f} ({rsi_status})")

        pos_status = self.position.side if self.position else "NONE"
        lines.append(f"Position: {pos_status}")
        lines.append(f"Signal: {signal}")
        lines.append(f"Total Trades: {self.stats.total_trades}")
        lines.append(f"Win Rate: {self.stats.win_rate:.1f}%")
        lines.append(f"Total PnL: ${self.stats.total_pnl:+.2f}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def run(self) -> None:
        """Main bot loop."""
        logger.info("Starting Trend Trading Bot...")

        self.starting_balance = self.account_balance if not TREND_CONFIG.test_mode else 10000.0
        self.stats = self.stats._replace(peak_balance=self.starting_balance, account_balance=self.starting_balance)

        ticker, ohlcv = self.get_market_data()
        if ticker:
            logger.info(f"✓ Connected to exchange - {TREND_CONFIG.symbol} @ ${ticker['last']:,.2f}")
        else:
            logger.info("⚠ Unable to fetch market data - running in simulation mode")

        logger.info(f"\nSafety Settings:")
        logger.info(f"  • Max Daily Trades: {TREND_CONFIG.max_daily_trades}")
        logger.info(f"  • Max Daily Loss: {TREND_CONFIG.max_daily_loss_pct*100}%")
        logger.info(f"  • Cooldown Period: {TREND_CONFIG.cooldown_period}s")
        logger.info(f"  • Emergency Stop: {'Enabled' if TREND_CONFIG.emergency_stop_enabled else 'Disabled'}\n")

        while self.running:
            try:
                if self.emergency_stop:
                    logger.info("EMERGENCY STOP ACTIVE - Bot halted")
                    time.sleep(TREND_CONFIG.update_interval * 5)
                    continue

                ticker, ohlcv = self.get_market_data()
                indicators = self.calculate_indicators(ohlcv)
                signal = self.analyze_market(indicators) if indicators else 'HOLD'

                if signal != 'HOLD' and not self.position:
                    if ticker:
                        self.execute_trade(signal, ticker['last'])

                if self.position and ticker:
                    self.check_exit_conditions(ticker['last'])

                if TREND_CONFIG.test_mode:
                    self.account_balance = 10000.0 + self.stats.total_pnl
                    self.stats = self.stats._replace(account_balance=self.account_balance)

                current_date = datetime.now().date()
                if current_date > self.last_daily_reset and datetime.now().hour == 0:
                    self.stats = self.stats.reset_daily()
                    self.last_daily_reset = current_date
                    logger.info("Daily statistics reset")

                ui_output = self.generate_ui(ticker, ohlcv, signal, indicators)
                logger.info(ui_output)

                time.sleep(TREND_CONFIG.update_interval)

            except KeyboardInterrupt:
                logger.info("Bot stopped by user.")
                self.running = False
                if self.position:
                    logger.info("Warning: Open position still active!")
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                self.consecutive_errors += 1
                self.last_error_time = time.time()

                if self.consecutive_errors >= 5:
                    self.emergency_stop = True
                    logger.info("Emergency stop activated - Too many consecutive errors")

                time.sleep(TREND_CONFIG.update_interval * 2)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def print_banner():
    """Print application banner."""
    print("=" * 70)
    print("       UNIFIED TRADING BOT SYSTEM")
    print("       Bybit Triangle Arbitrage & Trend Trading")
    print("=" * 70)
    print()
    print("MODES:")
    print("  1. Triangular Arbitrage - Scans USDT pairs for arb opportunities")
    print("  2. Trend Following      - Technical indicator-based trading (SMA, RSI)")
    print("  3. Combined Mode        - Run both strategies simultaneously")
    print()
    print("SAFETY: Running in SIMULATION mode by default")
    print("Set LIVE_MODE=true to enable live trading (TEST FIRST!)")
    print("=" * 70)


async def run_arb_bot():
    """Run the triangular arbitrage bot."""
    bot = BybitArbBot()
    await bot.start()


def run_trend_bot():
    """Run the trend-following bot."""
    bot = TrendTradingBot()
    bot.run()


async def run_combined():
    """Run both bots concurrently."""
    logger.info("Starting combined mode...")
    
    # Create tasks for both bots
    arb_task = asyncio.create_task(run_arb_bot())
    
    # Run trend bot in a separate thread since it's synchronous
    loop = asyncio.get_event_loop()
    trend_task = loop.run_in_executor(None, run_trend_bot)
    
    await asyncio.gather(arb_task, return_exceptions=True)
    trend_task.cancel()


def main():
    """Main entry point."""
    print_banner()
    
    print("\nSelect mode:")
    print("  1. Triangular Arbitrage")
    print("  2. Trend Following")
    print("  3. Combined (both)")
    print("  4. Exit")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == '1':
        logger.info("Starting Triangular Arbitrage Bot...")
        asyncio.run(run_arb_bot())
    elif choice == '2':
        logger.info("Starting Trend Following Bot...")
        run_trend_bot()
    elif choice == '3':
        logger.info("Starting Combined Mode...")
        asyncio.run(run_combined())
    elif choice == '4':
        logger.info("Exiting...")
        sys.exit(0)
    else:
        logger.error("Invalid choice. Please run again and select 1-4.")
        sys.exit(1)


if __name__ == "__main__":
    main()
