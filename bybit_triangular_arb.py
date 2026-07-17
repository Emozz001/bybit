"""
Bybit Triangular Arbitrage Bot - High Performance & Safe
--------------------------------------------------------
Scans all USDT pairs for triangular arbitrage opportunities.
Executes trades only when profit exceeds fees and risk thresholds.

SAFETY FIRST:
- Default mode is SIMULATION (Paper Trading).
- Set LIVE_MODE = True only after thorough testing.
- Ensure API keys have Spot Trading permissions.
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque
import sys

# ================= CONFIGURATION =================
API_KEY = "YOUR_BYBIT_API_KEY"
API_SECRET = "YOUR_BYBIT_API_SECRET"
LIVE_MODE = False  # KEEP FALSE FOR TESTING

# Risk Management
MAX_TRADE_AMOUNT_USDT = 100.0  # Amount to trade per arb
MIN_PROFIT_PERCENT = 0.15      # Minimum profit % to trigger (covers fees + slippage)
MAX_DAILY_LOSS_USDT = 50.0     # Stop trading if daily loss exceeds this
MAX_CONSECUTIVE_ERRORS = 5     # Stop after N errors

# Performance
SCAN_INTERVAL = 1.5            # Seconds between full market scans
REQUEST_TIMEOUT = 5            # Seconds
MAX_CONCURRENT_REQUESTS = 20   # Limit concurrent API calls

# Fees (Bybit Standard Spot Maker/Taker approx 0.1%)
TRADING_FEE_PERCENT = 0.1

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ArbBot")

# ================= DATA STRUCTURES =================

@dataclass
class Opportunity:
    symbol_a: str  # e.g., BTC
    symbol_b: str  # e.g., ETH
    path: str      # e.g., USDT -> BTC -> ETH -> USDT
    expected_profit_pct: float
    price_a: float # USDT/BTC
    price_b: float # BTC/ETH (derived)
    price_c: float # ETH/USDT
    timestamp: float

@dataclass
class TradeStats:
    total_scans: int = 0
    opportunities_found: int = 0
    trades_executed: int = 0
    total_profit_usdt: float = 0.0
    daily_pnl: float = 0.0
    consecutive_errors: int = 0
    last_error_time: float = 0.0

# ================= CORE SYSTEM =================

class BybitArbBot:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://api.bybit.com"
        self.symbols: List[str] = []
        self.tickers: Dict[str, dict] = {}
        self.stats = TradeStats()
        self.running = False
        self.cache_ttl = 1.0  # Cache tickers for 1 second
        self.last_fetch_time = 0.0
        
    async def start(self):
        """Initialize session and start loops"""
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        headers = {
            "X-BAPI-API-KEY": API_KEY,
            "X-BAPI-SIGN": "", # Will be generated for private calls
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": str(int(time.time() * 1000)),
            "X-BAPI-RECV-WINDOW": "5000",
            "Content-Type": "application/json"
        }
        
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers)
        self.running = True
        
        logger.info(f"Starting Bybit Triangular Arb Bot (Mode: {'LIVE' if LIVE_MODE else 'SIMULATION'})")
        logger.info(f"Scanning every {SCAN_INTERVAL}s | Min Profit: {MIN_PROFIT_PERCENT}%")
        
        # Load symbols first
        await self.load_symbols()
        
        # Start main loop
        try:
            await self.main_loop()
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user...")
        finally:
            await self.stop()

    async def stop(self):
        self.running = False
        if self.session:
            await self.session.close()
        logger.info(f"Bot stopped. Final Stats: Executed={self.stats.trades_executed}, Profit=${self.stats.total_profit_usdt:.2f}")

    async def load_symbols(self):
        """Fetch all USDT spot symbols"""
        url = f"{self.base_url}/v5/market/instruments-info?category=spot"
        try:
            async with self.session.get(url) as resp:
                data = await resp.json()
                if data['retCode'] == 0:
                    raw_symbols = [item['name'] for item in data['result']['list'] if item['quoteCoin'] == 'USDT']
                    # Filter out leveraged tokens or weird pairs if necessary
                    self.symbols = [s for s in raw_symbols if not s.endswith('UPUSDT') and not s.endswith('DOWNUSDT')]
                    logger.info(f"Loaded {len(self.symbols)} USDT pairs.")
                else:
                    logger.error(f"Failed to load symbols: {data}")
        except Exception as e:
            logger.error(f"Error loading symbols: {e}")
            self.stats.consecutive_errors += 1

    def _generate_signature(self, params: str, timestamp: str):
        """Generate HMAC SHA256 signature for private requests"""
        import hmac
        import hashlib
        param_str = timestamp + API_KEY + "5000" + params
        signature = hmac.new(API_SECRET.encode('utf-8'), param_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature

    async def get_tickers(self) -> Dict[str, dict]:
        """Fetch all tickers with caching"""
        now = time.time()
        if now - self.last_fetch_time < self.cache_ttl and self.tickers:
            return self.tickers
        
        url = f"{self.base_url}/v5/market/tickers?category=spot"
        try:
            async with self.session.get(url) as resp:
                data = await resp.json()
                if data['retCode'] == 0:
                    new_tickers = {}
                    for item in data['result']['list']:
                        symbol = item['symbol']
                        bid = float(item['bid1']) if item['bid1'] else 0
                        ask = float(item['ask1']) if item['ask1'] else 0
                        if bid > 0 and ask > 0:
                            new_tickers[symbol] = {'bid': bid, 'ask': ask, 'vol': float(item['volume24h'])}
                    
                    self.tickers = new_tickers
                    self.last_fetch_time = now
                    return new_tickers
                else:
                    logger.warning(f"Ticker fetch failed: {data['retMsg']}")
                    return self.tickers # Return stale data on error
        except Exception as e:
            logger.error(f"Network error fetching tickers: {e}")
            self.stats.consecutive_errors += 1
            return self.tickers

    def find_triangular_arbs(self, tickers: Dict[str, dict]) -> List[Opportunity]:
        """
        Scan for triangular arbitrage: USDT -> A -> B -> USDT
        Logic:
        1. Start with USDT
        2. Buy Asset A (USDT/A) -> Use Ask Price
        3. Buy Asset B using A (A/B) -> Need to derive or find direct pair
        4. Sell Asset B for USDT (B/USDT) -> Use Bid Price
        
        Optimized approach:
        Iterate all pairs ending in USDT (Base/USDT).
        For each Base (e.g., BTC), look for pairs where Base is Quote (e.g., ETH/BTC).
        Then check if the resulting Asset (ETH) has a pair back to USDT (ETH/USDT).
        """
        opportunities = []
        usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('USDT')}
        
        # Pre-calculate reverse maps for speed if needed, but direct lookup is O(1)
        
        for base_symbol in list(usdt_pairs.keys()):
            # Path: USDT -> BASE (Buy BASE with USDT)
            # Pair: BASEUSDT. We buy at Ask.
            if base_symbol not in tickers: continue
            
            entry_price = tickers[base_symbol]['ask'] # Price to buy BASE
            base_asset = base_symbol.replace('USDT', '')
            
            # Now look for pairs where BASE_ASSET is the QUOTE currency (e.g., ETHBTC)
            # We want to swap BASE_ASSET -> OTHER_ASSET
            # So we look for pairs like OTHER/BASE
            
            potential_targets = [k for k in tickers.keys() if k.endswith(base_asset) and k != base_symbol]
            
            for mid_pair in potential_targets:
                # Mid Pair: OTHER/BASE (e.g., ETH/BTC)
                # We hold BASE, we want to buy OTHER.
                # Price is quoted in BASE. We buy OTHER at Ask price of THIS pair.
                if mid_pair not in tickers: continue
                
                mid_price = tickers[mid_pair]['ask']
                target_asset = mid_pair.replace(f'{base_asset}', '') # Extract OTHER
                
                # Final Step: Sell OTHER for USDT
                # Pair: OTHERUSDT. We sell at Bid.
                exit_pair = f"{target_asset}USDT"
                if exit_pair not in tickers: continue
                
                exit_price = tickers[exit_pair]['bid']
                
                # Calculate Profit
                # 1 USDT -> (1 / entry_price) BASE
                # (1 / entry_price) BASE -> (1 / entry_price) / mid_price OTHER
                # Final USDT = ((1 / entry_price) / mid_price) * exit_price
                
                final_usdt = (1.0 / entry_price) / mid_price * exit_price
                gross_profit_pct = (final_usdt - 1.0) * 100
                
                # Deduct Fees (3 trades involved)
                # Fee factor = (1 - fee)^3
                fee_factor = (1 - (TRADING_FEE_PERCENT / 100)) ** 3
                net_profit_pct = (final_usdt * fee_factor - 1.0) * 100
                
                if net_profit_pct > MIN_PROFIT_PERCENT:
                    opp = Opportunity(
                        symbol_a=base_asset,
                        symbol_b=target_asset,
                        path=f"USDT->{base_asset}->{target_asset}->USDT",
                        expected_profit_pct=net_profit_pct,
                        price_a=entry_price,
                        price_b=mid_price,
                        price_c=exit_price,
                        timestamp=time.time()
                    )
                    opportunities.append(opp)
        
        return opportunities

    async def execute_trade(self, opp: Opportunity):
        """Execute the arbitrage trade sequence"""
        if self.stats.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.critical("Max consecutive errors reached. Stopping.")
            self.running = False
            return

        if self.stats.daily_pnl <= -MAX_DAILY_LOSS_USDT:
            logger.critical(f"Daily loss limit hit (-${MAX_DAILY_LOSS_USDT}). Stopping.")
            self.running = False
            return

        logger.info(f"💰 OPPORTUNITY FOUND: {opp.path} | Profit: {opp.expected_profit_pct:.4f}%")
        
        if not LIVE_MODE:
            # Simulation
            profit_usdt = MAX_TRADE_AMOUNT_USDT * (opp.expected_profit_pct / 100)
            self.stats.total_profit_usdt += profit_usdt
            self.stats.daily_pnl += profit_usdt
            self.stats.trades_executed += 1
            logger.info(f"✅ SIMULATED EXECUTION: Profit ${profit_usdt:.4f}")
            return

        # LIVE EXECUTION LOGIC (Skeleton)
        # WARNING: Real money involved. Requires precise order management.
        try:
            # 1. Buy Base Asset (USDT -> A)
            # 2. Buy Target Asset (A -> B)
            # 3. Sell Target Asset (B -> USDT)
            # Note: In reality, these must happen almost instantly. 
            # Using IOC (Immediate Or Cancel) orders is critical.
            
            logger.warning("LIVE EXECUTION NOT FULLY IMPLEMENTED IN THIS SNIPPET TO PREVENT LOSS.")
            logger.warning("To enable, implement signed POST requests to /v5/order/create")
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            self.stats.consecutive_errors += 1

    async def main_loop(self):
        while self.running:
            start_time = time.time()
            
            # 1. Fetch Data
            tickers = await self.get_tickers()
            self.stats.total_scans += 1
            
            if not tickers:
                await asyncio.sleep(1)
                continue

            # 2. Find Opportunities
            opps = await asyncio.to_thread(self.find_triangular_arbs, tickers)
            
            if opps:
                self.stats.opportunities_found += len(opps)
                # Sort by highest profit
                opps.sort(key=lambda x: x.expected_profit_pct, reverse=True)
                
                # Execute best one (or top N)
                # In high frequency, we usually only take the absolute best to avoid race conditions
                await self.execute_trade(opps[0])
            else:
                # Optional: Print dot for activity
                if self.stats.total_scans % 20 == 0:
                    logger.info(f"Scanning... ({len(tickers)} pairs checked)")

            # 3. Rate Limiting / Timing
            elapsed = time.time() - start_time
            sleep_time = max(0, SCAN_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    bot = BybitArbBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        pass
