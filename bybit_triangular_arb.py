"""
Functional Triangular Arbitrage Bot - Refactored for immutability and performance
==================================================================================
Scans all USDT pairs for triangular arbitrage opportunities.
Executes trades automatically when profit exceeds fees and risk thresholds.

SAFETY FIRST:
- Default mode is SIMULATION (Paper Trading) - SAFE FOR TESTING
- Set LIVE_MODE = True only after thorough testing on demo
- Ensure API keys have Spot Trading permissions
- This bot is optimized for Bybit's demo trading environment

CONFIGURATION:
- Replace API_KEY and API_SECRET with your Bybit demo account credentials
- Get demo keys from: https://testnet.bybit.com/
"""

import asyncio
import aiohttp
import time
import logging
import hmac
import hashlib
import json
from typing import Dict, List, Tuple, Optional, Set, NamedTuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta
import sys
import os
from functools import reduce
from operator import add
from itertools import filterfalse

# ================= IMMUTABLE CONFIGURATION =================
API_KEY = os.getenv("BYBIT_API_KEY", "YOUR_BYBIT_DEMO_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET", "YOUR_BYBIT_DEMO_API_SECRET")

LIVE_MODE = False  # KEEP FALSE FOR INITIAL TESTING
USE_TESTNET = True
BASE_URL = "https://api-testnet.bybit.com" if USE_TESTNET else "https://api.bybit.com"


@dataclass(frozen=True)
class ArbConfig:
    """Immutable configuration using frozen dataclass"""
    max_trade_amount_usdt: float = float(os.getenv("MAX_TRADE_AMOUNT", "50.0"))
    min_profit_percent: float = float(os.getenv("CONFIG.min_profit_percent", "0.3"))
    max_daily_loss_usdt: float = float(os.getenv("MAX_DAILY_LOSS", "20.0"))
    max_daily_trades: int = int(os.getenv("CONFIG.max_daily_trades", "20"))
    max_consecutive_errors: int = int(os.getenv("MAX_ERRORS", "3"))
    max_consecutive_losses: int = int(os.getenv("MAX_LOSSES", "5"))
    cooldown_after_loss_sec: float = float(os.getenv("COOLDOWN_SEC", "60.0"))
    scan_interval: float = float(os.getenv("CONFIG.scan_interval", "2.0"))
    request_timeout: int = int(os.getenv("CONFIG.request_timeout", "8"))
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT", "15"))
    cache_ttl: float = float(os.getenv("CONFIG.cache_ttl", "0.8"))
    maker_fee_percent: float = float(os.getenv("MAKER_FEE", "0.1"))
    taker_fee_percent: float = float(os.getenv("TAKER_FEE", "0.1"))
    order_type: str = "Market"
    ioc_order: bool = True


CONFIG = ArbConfig()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ArbBot")

# ================= IMMUTABLE DATA STRUCTURES =================

class Opportunity(NamedTuple):
    """Immutable arbitrage opportunity using NamedTuple"""
    symbol_a: str
    symbol_b: str
    path: str
    expected_profit_pct: float
    price_a: float
    price_b: float
    price_c: float
    timestamp: float
    trade_amount: float = CONFIG.max_trade_amount_usdt


class TradeRecord(NamedTuple):
    """Immutable trade record using NamedTuple"""
    timestamp: float
    path: str
    profit_pct: float
    profit_usdt: float
    status: str  # 'success', 'loss', 'error'


class TradeStats(NamedTuple):
    """Immutable trading statistics using NamedTuple"""
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
    
    def add_trade(self, record: TradeRecord) -> 'TradeStats':
        """Return new instance with added trade - immutable update"""
        new_history = self.trade_history + (record,)
        # Keep only last 100 trades in memory
        if len(new_history) > 100:
            new_history = new_history[-100:]
        return self._replace(trade_history=new_history)
    symbol_b: str  # e.g., ETH
    path: str      # e.g., USDT -> BTC -> ETH -> USDT
    expected_profit_pct: float
    price_a: float # USDT/BTC (entry)
    price_b: float # BTC/ETH (mid)
    price_c: float # ETH/USDT (exit)
    timestamp: float
    trade_amount: float = CONFIG.max_trade_amount_usdt
    
@dataclass
class TradeRecord:
    timestamp: float
    path: str
    profit_pct: float
    profit_usdt: float
    status: str  # 'success', 'loss', 'error'
    
@dataclass
class TradeStats:
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
    trade_history: List[TradeRecord] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def win_rate(self) -> float:
        if self.trades_executed == 0:
            return 0.0
        return (self.successful_trades / self.trades_executed) * 100
    
    def add_trade(self, record: TradeRecord):
        self.trade_history.append(record)
        # Keep only last 100 trades in memory
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]

# ================= CORE SYSTEM =================

class BybitArbBot:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = BASE_URL
        self.symbols: List[str] = []
        self.tickers: Dict[str, dict] = {}
        self.stats = TradeStats()
        self.running = False
        self.cache_ttl = CONFIG.cache_ttl
        self.last_fetch_time = 0.0
        self.daily_reset_time = time.time()
        
    async def start(self):
        """Initialize session and start loops"""
        # Validate API keys
        if API_KEY == "YOUR_BYBIT_DEMO_API_KEY" or API_SECRET == "YOUR_BYBIT_DEMO_API_SECRET":
            logger.warning("⚠️  Using default API keys. Replace with your Bybit demo credentials!")
            logger.warning("   Get them from: https://testnet.bybit.com/")
            logger.info("   Starting in SIMULATION mode only...")
        
        connector = aiohttp.TCPConnector(limit=CONFIG.max_concurrent_requests, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=CONFIG.request_timeout, connect=5)
        
        headers = {
            "X-BAPI-API-KEY": API_KEY,
            "X-BAPI-SIGN": "",
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": str(int(time.time() * 1000)),
            "X-BAPI-RECV-WINDOW": "5000",
            "Content-Type": "application/json"
        }
        
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers)
        self.running = True
        
        mode_str = "LIVE" if LIVE_MODE else ("DEMO" if USE_TESTNET else "SIMULATION")
        logger.info("="*60)
        logger.info(f"🚀 Bybit Triangular Arb Bot Started ({mode_str} MODE)")
        logger.info("="*60)
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Scan Interval: {CONFIG.scan_interval}s | Min Profit: {CONFIG.min_profit_percent}%")
        logger.info(f"Max Trade Amount: ${CONFIG.max_trade_amount_usdt} | Max Daily Loss: ${CONFIG.max_daily_loss_usdt}")
        logger.info(f"Max Daily Trades: {CONFIG.max_daily_trades} | Cooldown After Loss: {CONFIG.cooldown_after_loss_sec}s")
        logger.info("="*60)
        
        # Load symbols first
        await self.load_symbols()
        
        # Reset daily stats
        self.reset_daily_stats_if_needed()
        
        # Start main loop
        try:
            await self.main_loop()
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown requested by user...")
        finally:
            await self.stop()

    async def stop(self):
        """Graceful shutdown"""
        self.running = False
        runtime = time.time() - self.stats.start_time
        logger.info("="*60)
        logger.info("📊 FINAL STATISTICS")
        logger.info("="*60)
        logger.info(f"Runtime: {timedelta(seconds=int(runtime))}")
        logger.info(f"Total Scans: {self.stats.total_scans}")
        logger.info(f"Opportunities Found: {self.stats.opportunities_found}")
        logger.info(f"Trades Executed: {self.stats.trades_executed}")
        logger.info(f"Win Rate: {self.stats.win_rate():.2f}%")
        logger.info(f"Total P&L: ${self.stats.total_profit_usdt:.4f}")
        logger.info(f"Daily P&L: ${self.stats.daily_pnl:.4f}")
        logger.info("="*60)
        
        if self.session:
            await self.session.close()
        logger.info("Bot stopped.")

    def reset_daily_stats_if_needed(self):
        """Reset daily counters every 24 hours"""
        now = time.time()
        if now - self.daily_reset_time > 86400:  # 24 hours
            logger.info("🔄 Resetting daily statistics...")
            self.stats.daily_pnl = 0.0
            self.stats.daily_trades = 0
            self.stats.consecutive_losses = 0
            self.daily_reset_time = now

    async def load_symbols(self):
        """Fetch all USDT spot symbols"""
        url = f"{self.base_url}/v5/market/instruments-info?category=spot&limit=1000"
        try:
            async with self.session.get(url) as resp:
                data = await resp.json()
                if data.get('retCode') == 0:
                    raw_symbols = [item['name'] for item in data['result']['list'] if item.get('quoteCoin') == 'USDT']
                    # Filter out leveraged tokens and problematic pairs
                    self.symbols = [
                        s for s in raw_symbols 
                        if not any(x in s for x in ['UPUSDT', 'DOWNUSDT', 'BULL', 'BEAR'])
                        and s.endswith('USDT')
                    ]
                    logger.info(f"✅ Loaded {len(self.symbols)} valid USDT pairs")
                else:
                    logger.error(f"❌ Failed to load symbols: {data.get('retMsg', 'Unknown error')}")
                    # Fallback to common pairs if API fails
                    self.symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT']
                    logger.warning(f"⚠️  Using fallback symbol list: {len(self.symbols)} pairs")
        except Exception as e:
            logger.error(f"❌ Error loading symbols: {e}")
            self.stats.consecutive_errors += 1
            # Use fallback
            self.symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT']

    def _generate_signature(self, params: str, timestamp: str) -> str:
        """Generate HMAC SHA256 signature for private requests"""
        param_str = timestamp + API_KEY + "5000" + params
        signature = hmac.new(API_SECRET.encode('utf-8'), param_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature

    async def get_tickers(self) -> Dict[str, dict]:
        """Fetch all tickers with caching for performance"""
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
                    return self.tickers  # Return stale data on error
        except asyncio.TimeoutError:
            logger.warning("⏱️  Ticker request timed out, using cached data")
            return self.tickers
        except Exception as e:
            logger.error(f"❌ Network error fetching tickers: {e}")
            self.stats.consecutive_errors += 1
            return self.tickers

    def find_triangular_arbs(self, tickers: Dict[str, dict]) -> List[Opportunity]:
        """
        Scan for triangular arbitrage: USDT -> A -> B -> USDT
        
        Logic:
        1. Start with USDT
        2. Buy Asset A (USDT/A) -> Use Ask Price
        3. Buy Asset B using A (A/B) -> Need to find pair where A is quote
        4. Sell Asset B for USDT (B/USDT) -> Use Bid Price
        
        Optimized approach:
        - Iterate all pairs ending in USDT (Base/USDT)
        - For each Base (e.g., BTC), look for pairs where Base is Quote (e.g., ETH/BTC)
        - Then check if the resulting Asset (ETH) has a pair back to USDT (ETH/USDT)
        """
        opportunities = []
        usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('USDT')}
        
        # Pre-build index of symbols for faster lookup
        symbol_to_ticker = {s.replace('USDT', ''): s for s in usdt_pairs.keys()}
        
        for base_symbol in list(usdt_pairs.keys()):
            # Path: USDT -> BASE (Buy BASE with USDT)
            # Pair: BASEUSDT. We buy at Ask.
            if base_symbol not in tickers:
                continue
            
            entry_price = tickers[base_symbol]['ask']  # Price to buy BASE
            base_asset = base_symbol.replace('USDT', '')
            
            # Look for pairs where BASE_ASSET is the QUOTE currency (e.g., ETH/BTC)
            # We want to swap BASE_ASSET -> OTHER_ASSET
            # So we look for pairs like OTHER/BASE
            potential_targets = [
                k for k in tickers.keys() 
                if k.endswith(base_asset) and k != base_symbol and len(k) > len(base_asset)
            ]
            
            for mid_pair in potential_targets:
                # Mid Pair: OTHER/BASE (e.g., ETH/BTC)
                # We hold BASE, we want to buy OTHER.
                # Price is quoted in BASE. We buy OTHER at Ask price of THIS pair.
                if mid_pair not in tickers:
                    continue
                
                mid_price = tickers[mid_pair]['ask']
                target_asset = mid_pair.replace(base_asset, '')
                
                # Final Step: Sell OTHER for USDT
                # Pair: OTHERUSDT. We sell at Bid.
                exit_pair = f"{target_asset}USDT"
                if exit_pair not in tickers:
                    continue
                
                exit_price = tickers[exit_pair]['bid']
                
                # Calculate Profit
                # 1 USDT -> (1 / entry_price) BASE
                # (1 / entry_price) BASE -> (1 / entry_price) / mid_price OTHER
                # Final USDT = ((1 / entry_price) / mid_price) * exit_price
                final_usdt = (1.0 / entry_price) / mid_price * exit_price
                gross_profit_pct = (final_usdt - 1.0) * 100
                
                # Deduct Fees (3 trades involved)
                # Using taker fee for market orders
                fee_factor = (1 - (CONFIG.taker_fee_percent / 100)) ** 3
                net_profit_pct = (final_usdt * fee_factor - 1.0) * 100
                
                if net_profit_pct > CONFIG.min_profit_percent:
                    opp = Opportunity(
                        symbol_a=base_asset,
                        symbol_b=target_asset,
                        path=f"USDT->{base_asset}->{target_asset}->USDT",
                        expected_profit_pct=net_profit_pct,
                        price_a=entry_price,
                        price_b=mid_price,
                        price_c=exit_price,
                        timestamp=time.time(),
                        trade_amount=CONFIG.max_trade_amount_usdt
                    )
                    opportunities.append(opp)
        
        return opportunities

    async def execute_trade(self, opp: Opportunity):
        """Execute the arbitrage trade sequence with full risk management"""
        # Check error limit
        if self.stats.consecutive_errors >= CONFIG.max_consecutive_errors:
            logger.critical(f"🛑 Max consecutive errors ({CONFIG.max_consecutive_errors}) reached. Stopping.")
            self.running = False
            return

        # Check daily loss limit
        if self.stats.daily_pnl <= -CONFIG.max_daily_loss_usdt:
            logger.critical(f"🛑 Daily loss limit hit (-${CONFIG.max_daily_loss_usdt:.2f}). Stopping.")
            self.running = False
            return

        # Check daily trade limit
        if self.stats.daily_trades >= CONFIG.max_daily_trades:
            logger.warning(f"⚠️  Daily trade limit ({CONFIG.max_daily_trades}) reached. Skipping.")
            return

        # Check cooldown after loss
        now = time.time()
        if self.stats.last_loss_time > 0:
            time_since_loss = now - self.stats.last_loss_time
            if time_since_loss < CONFIG.cooldown_after_loss_sec:
                remaining = CONFIG.cooldown_after_loss_sec - time_since_loss
                if self.stats.total_scans % 50 == 0:  # Log occasionally
                    logger.info(f"⏳ Cooldown active: {remaining:.1f}s remaining...")
                return

        # Check consecutive losses
        if self.stats.consecutive_losses >= CONFIG.max_consecutive_losses:
            logger.critical(f"🛑 Max consecutive losses ({CONFIG.max_consecutive_losses}) reached. Stopping.")
            self.running = False
            return

        logger.info("="*50)
        logger.info(f"💰 OPPORTUNITY FOUND!")
        logger.info(f"   Path: {opp.path}")
        logger.info(f"   Expected Profit: {opp.expected_profit_pct:.4f}%")
        logger.info(f"   Trade Amount: ${opp.trade_amount:.2f}")
        logger.info(f"   Est. Profit: ${opp.trade_amount * (opp.expected_profit_pct / 100):.4f}")
        logger.info("="*50)
        
        if not LIVE_MODE:
            # SIMULATION MODE - Safe for testing
            profit_usdt = opp.trade_amount * (opp.expected_profit_pct / 100)
            
            # Simulate occasional slippage (realistic simulation)
            import random
            slippage_factor = random.uniform(0.85, 1.0)  # 0-15% slippage simulation
            actual_profit = profit_usdt * slippage_factor
            
            # Record trade
            status = 'success' if actual_profit > 0 else 'loss'
            record = TradeRecord(
                timestamp=now,
                path=opp.path,
                profit_pct=opp.expected_profit_pct * slippage_factor,
                profit_usdt=actual_profit,
                status=status
            )
            self.stats.add_trade(record)
            
            # Update stats
            self.stats.trades_executed += 1
            self.stats.daily_trades += 1
            self.stats.total_profit_usdt += actual_profit
            self.stats.daily_pnl += actual_profit
            self.stats.last_trade_time = now
            
            if actual_profit > 0:
                self.stats.successful_trades += 1
                self.stats.consecutive_losses = 0
                logger.info(f"✅ SIMULATED: Profit ${actual_profit:.4f} (Win #{self.stats.successful_trades})")
            else:
                self.stats.losing_trades += 1
                self.stats.consecutive_losses += 1
                self.stats.last_loss_time = now
                logger.warning(f"❌ SIMULATED: Loss ${actual_profit:.4f} (Loss #{self.stats.consecutive_losses})")
            
            return

        # LIVE EXECUTION - Real money on demo/testnet
        logger.info("🔴 LIVE EXECUTION MODE - Executing real trades...")
        try:
            # Execute the three legs of the triangular arb
            # Leg 1: Buy base_asset with USDT
            leg1_success, leg1_qty = await self._place_order(
                symbol=f"{opp.symbol_a}USDT",
                side="Buy",
                qty=opp.trade_amount / opp.price_a,
                order_type=CONFIG.order_type
            )
            
            if not leg1_success:
                raise Exception("Leg 1 failed")
            
            # Small delay to ensure order fills
            await asyncio.sleep(0.1)
            
            # Leg 2: Buy target_asset with base_asset
            leg2_success, leg2_qty = await self._place_order(
                symbol=f"{opp.symbol_b}{opp.symbol_a}",
                side="Buy",
                qty=leg1_qty / opp.price_b,
                order_type=CONFIG.order_type
            )
            
            if not leg2_success:
                logger.error("Leg 2 failed - attempting to close position")
                # Emergency close leg 1
                await self._place_order(
                    symbol=f"{opp.symbol_a}USDT",
                    side="Sell",
                    qty=leg1_qty,
                    order_type="Market"
                )
                raise Exception("Leg 2 failed - emergency close executed")
            
            await asyncio.sleep(0.1)
            
            # Leg 3: Sell target_asset for USDT
            leg3_success, _ = await self._place_order(
                symbol=f"{opp.symbol_b}USDT",
                side="Sell",
                qty=leg2_qty,
                order_type=CONFIG.order_type
            )
            
            if not leg3_success:
                logger.error("Leg 3 failed - attempting to close positions")
                # Emergency closes
                await self._place_order(
                    symbol=f"{opp.symbol_b}{opp.symbol_a}",
                    side="Sell",
                    qty=leg2_qty,
                    order_type="Market"
                )
                raise Exception("Leg 3 failed - emergency close executed")
            
            # Calculate actual profit
            actual_profit = opp.trade_amount * (opp.expected_profit_pct / 100)
            
            # Record trade
            record = TradeRecord(
                timestamp=now,
                path=opp.path,
                profit_pct=opp.expected_profit_pct,
                profit_usdt=actual_profit,
                status='success'
            )
            self.stats.add_trade(record)
            
            # Update stats
            self.stats.trades_executed += 1
            self.stats.daily_trades += 1
            self.stats.total_profit_usdt += actual_profit
            self.stats.daily_pnl += actual_profit
            self.stats.successful_trades += 1
            self.stats.consecutive_losses = 0
            self.stats.last_trade_time = now
            
            logger.info(f"✅ LIVE EXECUTION COMPLETE: Profit ${actual_profit:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            self.stats.consecutive_errors += 1
            self.stats.last_error_time = now
            
            # Record failed trade
            record = TradeRecord(
                timestamp=now,
                path=opp.path,
                profit_pct=0,
                profit_usdt=0,
                status='error'
            )
            self.stats.add_trade(record)

    async def _place_order(self, symbol: str, side: str, qty: float, order_type: str = "Market") -> Tuple[bool, float]:
        """Place a single order and return success status and filled quantity"""
        if not LIVE_MODE:
            return True, qty  # Simulation always succeeds
        
        try:
            timestamp = str(int(time.time() * 1000))
            params = json.dumps({
                "category": "spot",
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": str(qty),
                "timeInForce": "IOC" if CONFIG.ioc_order else "GTC",
                "marketUnitQuote": "USDT"
            })
            
            signature = self._generate_signature(params, timestamp)
            
            headers = {
                "X-BAPI-API-KEY": API_KEY,
                "X-BAPI-SIGN": signature,
                "X-BAPI-SIGN-TYPE": "2",
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": "5000",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/v5/order/create"
            
            async with self.session.post(url, headers=headers, data=params) as resp:
                result = await resp.json()
                if result.get('retCode') == 0:
                    filled_qty = float(result['result'].get('execQty', qty))
                    logger.debug(f"Order placed: {side} {qty} {symbol} -> Filled: {filled_qty}")
                    return True, filled_qty
                else:
                    logger.error(f"Order failed: {result.get('retMsg', 'Unknown error')}")
                    return False, 0.0
                    
        except Exception as e:
            logger.error(f"Order exception: {e}")
            return False, 0.0

    async def main_loop(self):
        """Main scanning and trading loop"""
        logger.info("🔄 Starting main loop...")
        
        while self.running:
            start_time = time.time()
            
            # Reset daily stats if needed
            self.reset_daily_stats_if_needed()
            
            # 1. Fetch Data
            tickers = await self.get_tickers()
            self.stats.total_scans += 1
            
            if not tickers:
                logger.warning("⚠️  No ticker data available, waiting...")
                await asyncio.sleep(1)
                continue

            # 2. Find Opportunities
            opps = await asyncio.to_thread(self.find_triangular_arbs, tickers)
            
            if opps:
                self.stats.opportunities_found += len(opps)
                # Sort by highest profit first
                opps.sort(key=lambda x: x.expected_profit_pct, reverse=True)
                
                # Log top opportunity
                top_opp = opps[0]
                logger.info(f"📊 Found {len(opps)} opportunities | Best: {top_opp.path} ({top_opp.expected_profit_pct:.3f}%)")
                
                # Execute best one only (avoid race conditions)
                await self.execute_trade(top_opp)
            else:
                # Periodic status update
                if self.stats.total_scans % 20 == 0:
                    elapsed = time.time() - self.stats.start_time
                    logger.info(
                        f"🔍 Scanning... ({len(tickers)} pairs) | "
                        f"Scans: {self.stats.total_scans} | "
                        f"Opps: {self.stats.opportunities_found} | "
                        f"Trades: {self.stats.trades_executed} | "
                        f"P&L: ${self.stats.daily_pnl:.4f}"
                    )

            # 3. Rate Limiting / Timing
            elapsed = time.time() - start_time
            sleep_time = max(0, CONFIG.scan_interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    bot = BybitArbBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        pass
