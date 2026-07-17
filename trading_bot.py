"""
Functional Trading Bot - Refactored for immutability and performance
=====================================================================
This module implements a trend-following trading bot using functional programming principles.
"""

import ccxt
import time
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple, NamedTuple
from collections import deque
from dataclasses import dataclass, field
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
import logging
from functools import lru_cache, reduce
from itertools import islice
from operator import add

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

# =============================================================================
# IMMUTABLE CONFIGURATION
# =============================================================================

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_SECRET = os.getenv("BYBIT_SECRET", "")

@dataclass(frozen=True)
class Config:
    """Immutable configuration using frozen dataclass"""
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
    test_mode: bool = True

CONFIG = Config()

# =============================================================================
# IMMUTABLE DATA STRUCTURES
# =============================================================================

class Position(NamedTuple):
    """Immutable trading position using NamedTuple"""
    side: str
    entry_price: float
    size: float
    timestamp: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    @classmethod
    def create(cls, side: str, entry_price: float, size: float, 
               stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> 'Position':
        """Factory method for creating positions"""
        return cls(side=side, entry_price=entry_price, size=size, 
                   timestamp=time.time(), stop_loss=stop_loss, take_profit=take_profit)


class TradeStats(NamedTuple):
    """Immutable trading statistics using NamedTuple"""
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
    
    def reset_daily(self) -> 'TradeStats':
        """Return new instance with daily counters reset"""
        return self._replace(daily_trades=0, daily_pnl=0.0)
    
    def add_trade(self, pnl_usd: float, is_win: bool) -> 'TradeStats':
        """Return new instance with updated trade statistics"""
        return self._replace(
            total_trades=self.total_trades + 1,
            winning_trades=self.winning_trades + (1 if is_win else 0),
            losing_trades=self.losing_trades + (0 if is_win else 1),
            total_pnl=self.total_pnl + pnl_usd,
            daily_pnl=self.daily_pnl + pnl_usd,
            consecutive_losses=0 if is_win else self.consecutive_losses + 1
        )
    
    def update_balance(self, balance: float) -> 'TradeStats':
        """Return new instance with updated balance tracking"""
        new_peak = max(self.peak_balance, balance)
        drawdown = (new_peak - balance) / new_peak if new_peak > 0 else 0
        return self._replace(
            account_balance=balance,
            peak_balance=new_peak,
            max_drawdown=max(self.max_drawdown, drawdown)
        )
    
    def is_trading_allowed(self) -> Tuple[bool, str]:
        """Check if trading is allowed based on safety rules"""
        if self.daily_trades >= CONFIG.max_daily_trades:
            return False, f"Daily trade limit reached ({CONFIG.max_daily_trades})"
        
        if self.daily_pnl <= -self.account_balance * CONFIG.max_daily_loss_pct:
            return False, f"Daily loss limit reached ({CONFIG.max_daily_loss_pct*100}%)"
        
        if time.time() - self.last_trade_time < CONFIG.cooldown_period and self.consecutive_losses > 0:
            remaining = CONFIG.cooldown_period - (time.time() - self.last_trade_time)
            return False, f"Cooldown period active ({remaining:.0f}s remaining)"
        
        return True, "OK"


# =============================================================================
# FUNCTIONAL DATA CACHING
# =============================================================================

class CachedData:
    """Efficient data caching for market data using deque for O(1) operations"""
    __slots__ = ['closes', 'timestamps', 'last_update']
    
    def __init__(self, max_size: int = CONFIG.cache_max_size):
        self.closes: deque = deque(maxlen=max_size)
        self.timestamps: deque = deque(maxlen=max_size)
        self.last_update: float = 0.0
        
    def update(self, ohlcv: List[List]) -> bool:
        """Update cache only if new data available - O(n) optimized"""
        if not ohlcv:
            return False
            
        latest_timestamp = ohlcv[-1][0]
        if latest_timestamp <= self.last_update:
            return False
        
        # Use extend for bulk update - more efficient than individual appends
        self.closes.extend(candle[4] for candle in ohlcv)
        self.timestamps.extend(candle[0] for candle in ohlcv)
        self.last_update = latest_timestamp
        return True
    
    def get_closes(self, count: int) -> List[float]:
        """Get last N closing prices efficiently - O(k) where k <= count"""
        return list(islice(self.closes, max(0, len(self.closes) - count), len(self.closes)))

class TradingBot:
    def __init__(self):
        self.exchange = ccxt.bybit({
            'apiKey': BYBIT_API_KEY,
            'secret': BYBIT_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # Use dataclass for position management
        self.position: Optional[Position] = None
        self.account_balance = 0.0
        
        # Use TradeStats for better statistics tracking
        self.stats = TradeStats()
        self.starting_balance = 0.0
        self.emergency_stop = False
        self.last_error_time = 0.0
        self.consecutive_errors = 0

        self.running = True
        
        # Performance optimization: cache market data
        self.data_cache = CachedData()
        self.last_ticker_fetch = 0.0
        self.ticker_cache_ttl = 1.0  # Cache ticker for 1 second
        
        # Pre-calculate constants to avoid repeated computation
        self._stop_loss_multiplier_buy = 1 - CONFIG.stop_loss_pct
        self._take_profit_multiplier_buy = 1 + CONFIG.take_profit_pct
        self._stop_loss_multiplier_sell = 1 + CONFIG.stop_loss_pct
        self._take_profit_multiplier_sell = 1 - CONFIG.take_profit_pct
        
        if CONFIG.test_mode:
            console.print("[bold yellow]WARNING: RUNNING IN TEST MODE - No real trades will be executed[/bold yellow]")

    def check_connection(self) -> bool:
        """Verify API connection with error handling"""
        try:
            markets = self.exchange.load_markets()
            balance = self.exchange.fetch_balance()
            self.account_balance = float(balance.get('USDT', {}).get('free', 0))
            return True
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
            return False

    def get_market_data(self) -> Tuple[Optional[Dict], Optional[List]]:
        """Fetch ticker and OHLCV data with caching"""
        current_time = time.time()
        ticker = None
        ohlcv = None
        
        try:
            # Fetch ticker with simple time-based caching
            if current_time - self.last_ticker_fetch > self.ticker_cache_ttl:
                ticker = self.exchange.fetch_ticker(CONFIG.symbol)
                self.last_ticker_fetch = current_time
            
            # Always fetch fresh OHLCV for accurate analysis
            ohlcv = self.exchange.fetch_ohlcv(CONFIG.symbol, CONFIG.timeframe, limit=100)
            
            # Update cache if new data available
            if ohlcv:
                self.data_cache.update(ohlcv)
            
            return ticker, ohlcv
        except Exception as e:
            console.print(f"[yellow]Data fetch warning: {e}[/yellow]")
            return None, None

    def calculate_indicators(self, ohlcv: Optional[List] = None) -> Optional[Dict[str, float]]:
        """Calculate technical indicators using cached data for efficiency"""
        # Use cached data if available and OHLCV not provided
        closes = self.data_cache.get_closes(50) if ohlcv is None else (
            [candle[4] for candle in ohlcv] if len(ohlcv) >= 50 else None
        )
        
        if not closes or len(closes) < 50:
            return None
        
        # Optimized SMA calculation using reduce for functional approach
        sma_20 = reduce(add, closes[-20:]) / 20
        sma_50 = reduce(add, closes[-50:]) / 50
        
        # Optimized RSI Calculation (14 period) - functional vectorized approach
        rsi_period = 14
        if len(closes) < rsi_period + 1:
            rsi = 50.0  # Default neutral RSI
        else:
            # Calculate price changes using map
            indices = range(1, rsi_period + 1)
            changes = list(map(lambda i: closes[-i] - closes[-i-1], indices))
            
            # Separate gains and losses using filter and map
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
        """
        TRADING STRATEGY LOGIC - Functional approach with pattern matching
        
        This implements a conservative trend-following strategy:
        - BUY when price > SMA_20 > SMA_50 and RSI < 70 (not overbought)
        - SELL when price < SMA_20 < SMA_50 and RSI > 30 (not oversold)
        
        IMPORTANT: This is educational code. You MUST backtest and 
        optimize any strategy before using real money.
        """
        if not indicators:
            return 'HOLD'
        
        # Extract values for pattern matching
        price = indicators['current_price']
        sma_20 = indicators['sma_20']
        sma_50 = indicators['sma_50']
        rsi = indicators['rsi']
        
        # Define signal conditions as pure functions
        is_bullish_trend = lambda: price > sma_20 > sma_50
        is_bearish_trend = lambda: price < sma_20 < sma_50
        is_rsi_neutral = lambda: 30 < rsi < 70
        is_rsi_bullish = lambda: 50 < rsi < 70
        is_rsi_bearish = lambda: 30 < rsi < 50
        
        # Signal determination using functional composition
        buy_signal = is_bullish_trend() and is_rsi_bullish()
        sell_signal = is_bearish_trend() and is_rsi_bearish()
        
        return 'BUY' if buy_signal else ('SELL' if sell_signal else 'HOLD')

    def execute_trade(self, side: str, price: float) -> bool:
        """Execute a market order with position sizing and safety checks - Functional approach"""
        try:
            # Safety checks as pure predicates
            checks = [
                (not self.emergency_stop, "Emergency stop active"),
                (*self.stats.is_trading_allowed(),),
                (self.consecutive_errors < 3, "Too many consecutive errors")
            ]
            
            for condition, message in checks[:1]:
                if not condition:
                    console.print(f"[red]Trading blocked - {message}[/red]")
                    return False
            
            allowed, reason = checks[1][0], checks[1][1] if len(checks[1]) > 1 else "OK"
            if not allowed:
                console.print(f"[yellow]Trading blocked - {reason}[/yellow]")
                return False
            
            if checks[2][0] is False:
                console.print(f"[red]Trading blocked - {checks[2][1]}[/red]")
                return False
            
            # Calculate position size based on risk (pure calculation)
            risk_amount = self.account_balance * CONFIG.risk_per_trade
            stop_distance = price * CONFIG.stop_loss_pct
            contract_size = (risk_amount / stop_distance) / price
            
            # Calculate SL/TP levels using pre-computed multipliers
            stop_loss, take_profit = (
                (price * self._stop_loss_multiplier_buy, price * self._take_profit_multiplier_buy)
                if side == 'buy' else
                (price * self._stop_loss_multiplier_sell, price * self._take_profit_multiplier_sell)
            )
            
            if CONFIG.test_mode:
                console.print(f"[cyan][TEST] Would execute {side.upper()} order for {contract_size:.6f} BTC[/cyan]")
                console.print(f"[cyan][TEST] SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}[/cyan]")
                self.position = Position.create(side, price, contract_size, stop_loss, take_profit)
                # Update stats immutably
                self.stats = self.stats._replace(
                    daily_trades=self.stats.daily_trades + 1,
                    last_trade_time=time.time()
                )
                return True
            
            # Live trading execution with slippage check
            order = self.exchange.create_order(CONFIG.symbol, 'market', side, contract_size)
            entry_price = order.get('average', price)
            
            # Check slippage
            slippage = abs(entry_price - price) / price
            if slippage > CONFIG.max_slippage_pct:
                console.print(f"[red]High slippage detected: {slippage*100:.3f}% - Closing immediately[/red]")
                close_side = 'sell' if side == 'buy' else 'buy'
                self.exchange.create_order(CONFIG.symbol, 'market', close_side, contract_size)
                return False
            
            self.position = Position.create(side, entry_price, contract_size, stop_loss, take_profit)
            self.stats = self.stats._replace(
                daily_trades=self.stats.daily_trades + 1,
                last_trade_time=time.time()
            )
            
            console.print(f"[green]Executed {side.upper()} at {entry_price}[/green]")
            console.print(f"[green]SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}[/green]")
            return True
            
        except Exception as e:
            self.consecutive_errors += 1
            self.last_error_time = time.time()
            logger.error(f"Trade execution error: {e}")
            console.print(f"[red]Trade failed: {e}[/red]")
            return False


    def check_exit_conditions(self, current_price: float) -> None:
        """Check if SL or TP is hit using pre-calculated multipliers"""
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
        """Close the current position with PnL tracking and safety updates"""
        try:
            if not self.position or not self.position.size:
                self.position = None
                return

            side = 'sell' if self.position.side == 'buy' else 'buy'

            # Calculate PnL
            if self.position.side == 'buy':
                pnl_pct = (current_price - self.position.entry_price) / self.position.entry_price
            else:
                pnl_pct = (self.position.entry_price - current_price) / self.position.entry_price

            pnl_usd = self.position.size * current_price * pnl_pct

            if CONFIG.test_mode:
                console.print(f"[cyan][TEST] Closing position - {reason} - PnL: ${pnl_usd:.2f} ({pnl_pct*100:.2f}%)[/cyan]")
            else:
                self.exchange.create_order(CONFIG.symbol, 'market', side, self.position.size)
                console.print(f"[green]Closed position - {reason} - PnL: ${pnl_usd:.2f}[/green]")

            # Update statistics
            if pnl_usd > 0:
                self.stats.winning_trades += 1
                self.stats.consecutive_losses = 0  # Reset on win
            else:
                self.stats.losing_trades += 1
                self.stats.consecutive_losses += 1
                
                # Check for emergency stop conditions
                if CONFIG.emergency_stop_enabled and self.stats.consecutive_losses >= 5:
                    self.emergency_stop = True
                    console.print("[bold red]EMERGENCY STOP ACTIVATED - 5 consecutive losses[/bold red]")
            
            self.stats.total_trades += 1
            self.stats.total_pnl += pnl_usd
            self.stats.daily_pnl += pnl_usd
            
            # Update drawdown tracking
            if CONFIG.test_mode:
                current_balance = 10000.0 + self.stats.total_pnl
            else:
                current_balance = self.account_balance
                
            if current_balance > self.stats.peak_balance:
                self.stats.peak_balance = current_balance
            
            drawdown = (self.stats.peak_balance - current_balance) / self.stats.peak_balance if self.stats.peak_balance > 0 else 0
            if drawdown > self.stats.max_drawdown:
                self.stats.max_drawdown = drawdown
            
            # Check daily loss limit
            if self.stats.daily_pnl <= -self.account_balance * CONFIG.max_daily_loss_pct:
                console.print("[bold red]Daily loss limit reached - Trading halted for today[/bold red]")
            
            # Reset error counter on successful trade close
            self.consecutive_errors = 0

            # Clear position
            self.position = None

        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            console.print(f"[red]Failed to close: {e}[/red]")
    def generate_ui(self, ticker: Optional[Dict], ohlcv: Optional[List], 
                    signal: str, indicators: Optional[Dict]) -> Layout:
        """Generate the Rich Terminal UI with optimized rendering"""
        # Create main layout
        layout = Layout()
        
        # Create sub-layouts
        market_indicator_layout = Layout()
        position_stats_layout = Layout()

        # Header
        header_text = Text()
        header_text.append("Bybit Trading Bot\n", style="bold blue")
        header_text.append(f"Symbol: {CONFIG.symbol} | Timeframe: {CONFIG.timeframe} | Leverage: {CONFIG.leverage}x", style="dim")
        if CONFIG.test_mode:
            header_text.append(" | WARNING: TEST MODE", style="bold yellow")
        
        header = Panel(header_text, border_style="blue")

        # Market Data Table
        market_table = Table(show_header=True, header_style="bold cyan", title="Market Data")
        market_table.add_column("Metric", style="cyan")
        market_table.add_column("Value", justify="right")
        
        if ticker:
            change_color = "green" if ticker.get('percentage', 0) >= 0 else "red"
            market_table.add_row("Current Price", f"${ticker['last']:,.2f}")
            market_table.add_row("24h Change", f"[{change_color}]{ticker.get('percentage', 0):.2f}%[/{change_color}]")
            market_table.add_row("24h High", f"${ticker['high']:,.2f}")
            market_table.add_row("24h Low", f"${ticker['low']:,.2f}")
            market_table.add_row("Volume", f"{ticker.get('baseVolume', 0):,.4f}")
        else:
            market_table.add_row("Status", "[yellow]Fetching data...[/yellow]")

        # Indicators Table
        indicator_table = Table(show_header=True, header_style="bold magenta", title="Technical Indicators")
        indicator_table.add_column("Indicator", style="magenta")
        indicator_table.add_column("Value", justify="right")
        
        if indicators:
            indicator_table.add_row("SMA (20)", f"${indicators['sma_20']:,.2f}")
            indicator_table.add_row("SMA (50)", f"${indicators['sma_50']:,.2f}")
            
            rsi_color = "red" if indicators['rsi'] > 70 else "green" if indicators['rsi'] < 30 else "white"
            indicator_table.add_row("RSI (14)", f"[{rsi_color}]{indicators['rsi']:.2f}[/{rsi_color}]")
        else:
            indicator_table.add_row("Status", "Calculating...")

        # Position Panel
        pos_status = self.position.side if self.position else "NONE"
        pos_color = "green" if self.position and self.position.side == 'buy' else "red" if self.position and self.position.side == 'sell' else "white"
        
        pnl_display = ""
        if self.position and ticker:
            if self.position.side == 'buy':
                pnl = (ticker['last'] - self.position.entry_price) / self.position.entry_price * 100
            else:
                pnl = (self.position.entry_price - ticker['last']) / self.position.entry_price * 100
            pnl_color = "green" if pnl > 0 else "red"
            pnl_display = f"\nUnrealized PnL: [{pnl_color}]{pnl:+.2f}%[/{pnl_color}]"
        
        signal_color = 'green' if signal == 'BUY' else 'red' if signal == 'SELL' else 'white'
        position_panel = Panel(
            f"Position: [{pos_color}][bold]{pos_status}[/bold][/{pos_color}]\n"
            f"Entry: ${self.position.entry_price if self.position else 0:,.2f}\n"
            f"Signal: [{signal_color}]{signal}[/{signal_color}]"
            f"{pnl_display}",
            title="Position Status",
            border_style=pos_color
        )

        # Stats Panel - using TradeStats dataclass
        stats_panel = Panel(
            f"Total Trades: {self.stats.total_trades}\n"
            f"Winning: {self.stats.winning_trades}\n"
            f"Win Rate: {self.stats.win_rate:.1f}%\n"
            f"Total PnL: ${self.stats.total_pnl:+.2f}\n"
            f"Balance: ${self.account_balance:,.2f}",
            title="Performance",
            border_style="yellow"
        )

        # Risk Warning
        risk_panel = Panel(
            "[yellow]DISCLAIMER: This bot is for educational purposes only.\n"
            "Cryptocurrency trading involves significant risk. Never trade with money you cannot afford to lose.\n"
            "Always backtest strategies before live trading.[/yellow]",
            title="Risk Warning",
            border_style="red"
        )

        # Layout assembly - split into rows first
        layout.split(
            Layout(header, size=4),
            Layout(name="middle"),
            Layout(risk_panel, size=6),
        )
        
        # Split middle row into two columns
        layout["middle"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        
        # Split left column into market and indicators
        layout["left"].split(
            Layout(market_table),
            Layout(indicator_table),
        )
        
        # Split right column into position and stats
        layout["right"].split(
            Layout(position_panel),
            Layout(stats_panel),
        )
        
        return layout

    def run(self) -> None:
        """Main bot loop with optimized execution and safety monitoring"""
        console.clear()

        if not BYBIT_API_KEY or BYBIT_API_KEY == "":
            console.print("[bold red]ERROR: API Keys not configured![/bold red]")
            console.print("\nSet your keys via environment variables:")
            console.print("  export BYBIT_API_KEY='your_key_here'")
            console.print("  export BYBIT_SECRET='your_secret_here'")
            console.print("\nOr edit the script directly (not recommended for production).")
            console.print("\n[yellow]Starting in demo mode with simulated data...[/yellow]\n")
            time.sleep(2)

        console.print("[bold green]Starting Trading Bot...[/bold green]\n")
        
        # Initialize balance tracking
        self.starting_balance = self.account_balance if not CONFIG.test_mode else 10000.0
        self.stats.peak_balance = self.starting_balance
        self.stats.account_balance = self.starting_balance

        # Pre-fetch initial data
        ticker, ohlcv = self.get_market_data()
        if ticker:
            console.print(f"[green]✓ Connected to exchange - {CONFIG.symbol} @ ${ticker['last']:,.2f}[/green]")
        else:
            console.print("[yellow]⚠ Unable to fetch market data - running in simulation mode[/yellow]")
        
        # Display safety settings
        console.print(f"\n[bold cyan]Safety Settings:[/bold cyan]")
        console.print(f"  • Max Daily Trades: {CONFIG.max_daily_trades}")
        console.print(f"  • Max Daily Loss: {CONFIG.max_daily_loss_pct*100}%")
        console.print(f"  • Cooldown Period: {CONFIG.cooldown_period}s")
        console.print(f"  • Emergency Stop: {'Enabled' if CONFIG.emergency_stop_enabled else 'Disabled'}")
        console.print(f"  • Max Slippage: {CONFIG.max_slippage_pct*100}%\n")
        
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while self.running:
                try:
                    # Check emergency stop
                    if self.emergency_stop:
                        console.print("[bold red]EMERGENCY STOP ACTIVE - Bot halted[/bold red]")
                        time.sleep(CONFIG.update_interval * 5)
                        continue
                    
                    # Fetch market data with caching
                    ticker, ohlcv = self.get_market_data()

                    # Calculate indicators using cached data
                    indicators = self.calculate_indicators(ohlcv)

                    # Analyze market and get signal
                    signal = self.analyze_market(indicators) if indicators else 'HOLD'

                    # Execute trading logic with safety checks
                    if signal != 'HOLD' and not self.position:
                        if ticker:
                            self.execute_trade(signal, ticker['last'])

                    if self.position and ticker:
                        self.check_exit_conditions(ticker['last'])

                    # Update balance (simulated in test mode)
                    if CONFIG.test_mode:
                        self.account_balance = 10000.0 + self.stats.total_pnl
                        self.stats.account_balance = self.account_balance
                    
                    # Reset daily counters at midnight (simplified check)
                    current_hour = datetime.now().hour
                    if current_hour == 0 and self.stats.daily_trades > 0:
                        # Simple daily reset logic
                        self.stats.reset_daily()
                        console.print("[cyan]Daily statistics reset[/cyan]")

                    # Render UI
                    live.update(self.generate_ui(ticker, ohlcv, signal, indicators))

                    # Sleep for update interval
                    time.sleep(CONFIG.update_interval)

                except KeyboardInterrupt:
                    console.print("\n[bold yellow]Bot stopped by user.[/bold yellow]")
                    self.running = False
                    if self.position:
                        console.print(f"[yellow]Warning: Open position still active![/yellow]")
                except Exception as e:
                    logger.error(f"Main loop error: {e}")
                    self.consecutive_errors += 1
                    self.last_error_time = time.time()
                    
                    # Activate emergency stop on too many errors
                    if self.consecutive_errors >= 5:
                        self.emergency_stop = True
                        console.print("[bold red]Emergency stop activated - Too many consecutive errors[/bold red]")
                    
                    console.print(f"[red]Error: {e}[/red]")
                    time.sleep(CONFIG.update_interval * 2)  # Longer sleep on error

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
