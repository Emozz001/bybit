import ccxt
import time
import os
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

# Initialize console
console = Console()

# =============================================================================
# CONFIGURATION - EDIT THESE VALUES
# =============================================================================
# Get your API keys from https://testnet.bybit.com/ (for testing) 
# or https://www.bybit.com/ (for live trading)
# NEVER share your keys. Set them as environment variables for security:
# export BYBIT_API_KEY="your_key"
# export BYBIT_SECRET="your_secret"

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_SECRET = os.getenv("BYBIT_SECRET", "")

# Trading Parameters
SYMBOL = "BTC/USDT"      # Trading pair
TIMEFRAME = "5m"         # Candlestick timeframe
LEVERAGE = 3             # Low leverage for risk management (1-10 recommended)
RISK_PER_TRADE = 0.01    # Risk 1% of account per trade
STOP_LOSS_PCT = 0.02     # 2% Stop Loss
TAKE_PROFIT_PCT = 0.04   # 4% Take Profit (1:2 Risk/Reward ratio)

# Test Mode: Set to True to run without executing real trades
TEST_MODE = True         

# =============================================================================

class TradingBot:
    def __init__(self):
        self.exchange = ccxt.bybit({
            'apiKey': BYBIT_API_KEY,
            'secret': BYBIT_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.position = None
        self.entry_price = 0.0
        self.position_size = 0.0
        self.account_balance = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.running = True
        
        if TEST_MODE:
            console.print("[bold yellow]WARNING: RUNNING IN TEST MODE - No real trades will be executed[/bold yellow]")

    def check_connection(self):
        """Verify API connection"""
        try:
            markets = self.exchange.load_markets()
            balance = self.exchange.fetch_balance()
            self.account_balance = float(balance.get('USDT', {}).get('free', 0))
            return True
        except Exception as e:
            return False

    def get_market_data(self):
        """Fetch ticker and OHLCV data"""
        try:
            ticker = self.exchange.fetch_ticker(SYMBOL)
            ohlcv = self.exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
            return ticker, ohlcv
        except Exception as e:
            return None, None

    def calculate_indicators(self, ohlcv):
        """Calculate technical indicators for strategy"""
        if not ohlcv or len(ohlcv) < 50:
            return None
            
        closes = [candle[4] for candle in ohlcv]
        
        # Simple Moving Averages
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50
        
        # RSI Calculation (14 period)
        gains = []
        losses = []
        for i in range(1, min(15, len(closes))):
            diff = closes[-i] - closes[-i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 1
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        return {
            'sma_20': sma_20,
            'sma_50': sma_50,
            'rsi': rsi,
            'current_price': closes[-1]
        }

    def analyze_market(self, indicators):
        """
        TRADING STRATEGY LOGIC
        
        This implements a conservative trend-following strategy:
        - BUY when price > SMA_20 > SMA_50 and RSI < 70 (not overbought)
        - SELL when price < SMA_20 < SMA_50 and RSI > 30 (not oversold)
        
        IMPORTANT: This is educational code. You MUST backtest and 
        optimize any strategy before using real money.
        """
        if not indicators:
            return 'HOLD'
        
        price = indicators['current_price']
        sma_20 = indicators['sma_20']
        sma_50 = indicators['sma_50']
        rsi = indicators['rsi']
        
        # Bullish conditions
        if price > sma_20 > sma_50 and rsi < 70 and rsi > 50:
            return 'BUY'
        
        # Bearish conditions  
        if price < sma_20 < sma_50 and rsi > 30 and rsi < 50:
            return 'SELL'
        
        return 'HOLD'

    def execute_trade(self, side, price):
        """Execute a market order with position sizing"""
        try:
            # Calculate position size based on risk
            risk_amount = self.account_balance * RISK_PER_TRADE
            stop_distance = price * STOP_LOSS_PCT
            position_size = risk_amount / stop_distance
            
            # Convert to contract size (simplified)
            contract_size = position_size / price
            
            if TEST_MODE:
                console.print(f"[cyan][TEST] Would execute {side.upper()} order for {contract_size:.6f} BTC[/cyan]")
                self.entry_price = price
                self.position = side
                self.position_size = contract_size
                return True
            
            # Live trading execution
            order = self.exchange.create_order(SYMBOL, 'market', side, contract_size)
            self.entry_price = order['average'] if order.get('average') else price
            self.position = side
            self.position_size = contract_size
            
            console.print(f"[green]Executed {side.upper()} at {self.entry_price}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Trade failed: {e}[/red]")
            return False

    def check_exit_conditions(self, current_price):
        """Check if SL or TP is hit"""
        if not self.position:
            return

        should_close = False
        reason = ""
        
        if self.position == 'buy':
            if current_price <= self.entry_price * (1 - STOP_LOSS_PCT):
                should_close = True
                reason = "STOP LOSS"
            elif current_price >= self.entry_price * (1 + TAKE_PROFIT_PCT):
                should_close = True
                reason = "TAKE PROFIT"
        elif self.position == 'sell':
            if current_price >= self.entry_price * (1 + STOP_LOSS_PCT):
                should_close = True
                reason = "STOP LOSS"
            elif current_price <= self.entry_price * (1 - TAKE_PROFIT_PCT):
                should_close = True
                reason = "TAKE PROFIT"
        
        if should_close:
            self.close_position(reason, current_price)

    def close_position(self, reason, current_price):
        """Close the current position"""
        try:
            if not self.position_size:
                self.position = None
                self.entry_price = 0.0
                return
                
            side = 'sell' if self.position == 'buy' else 'buy'
            
            # Calculate PnL
            if self.position == 'buy':
                pnl_pct = (current_price - self.entry_price) / self.entry_price
            else:
                pnl_pct = (self.entry_price - current_price) / self.entry_price
            
            pnl_usd = self.position_size * current_price * pnl_pct
            
            if TEST_MODE:
                console.print(f"[cyan][TEST] Closing position - {reason} - PnL: ${pnl_usd:.2f} ({pnl_pct*100:.2f}%)[/cyan]")
            else:
                self.exchange.create_order(SYMBOL, 'market', side, self.position_size)
                console.print(f"[green]Closed position - {reason} - PnL: ${pnl_usd:.2f}[/green]")
            
            if pnl_usd > 0:
                self.winning_trades += 1
            self.total_trades += 1
            
            self.position = None
            self.entry_price = 0.0
            self.position_size = 0.0
            
        except Exception as e:
            console.print(f"[red]Failed to close: {e}[/red]")

    def generate_ui(self, ticker, ohlcv, signal, indicators):
        """Generate the Rich Terminal UI"""
        # Create main layout
        layout = Layout()
        
        # Create sub-layouts
        market_indicator_layout = Layout()
        position_stats_layout = Layout()

        # Header
        header_text = Text()
        header_text.append("Bybit Trading Bot\n", style="bold blue")
        header_text.append(f"Symbol: {SYMBOL} | Timeframe: {TIMEFRAME} | Leverage: {LEVERAGE}x", style="dim")
        if TEST_MODE:
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
        pos_status = self.position or "NONE"
        pos_color = "green" if self.position == 'buy' else "red" if self.position == 'sell' else "white"
        
        pnl_display = ""
        if self.position and ticker:
            if self.position == 'buy':
                pnl = (ticker['last'] - self.entry_price) / self.entry_price * 100
            else:
                pnl = (self.entry_price - ticker['last']) / self.entry_price * 100
            pnl_color = "green" if pnl > 0 else "red"
            pnl_display = f"\nUnrealized PnL: [{pnl_color}]{pnl:+.2f}%[/{pnl_color}]"
        
        signal_color = 'green' if signal == 'BUY' else 'red' if signal == 'SELL' else 'white'
        position_panel = Panel(
            f"Position: [{pos_color}][bold]{pos_status}[/bold][/{pos_color}]\n"
            f"Entry: ${self.entry_price:,.2f}\n"
            f"Signal: [{signal_color}]{signal}[/{signal_color}]"
            f"{pnl_display}",
            title="Position Status",
            border_style=pos_color
        )

        # Stats Panel
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        stats_panel = Panel(
            f"Total Trades: {self.total_trades}\n"
            f"Winning: {self.winning_trades}\n"
            f"Win Rate: {win_rate:.1f}%\n"
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

    def run(self):
        """Main bot loop"""
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
        
        with Live(console=console, refresh_per_second=2) as live:
            while self.running:
                try:
                    ticker, ohlcv = self.get_market_data()
                    indicators = self.calculate_indicators(ohlcv)
                    signal = self.analyze_market(indicators) if indicators else 'HOLD'
                    
                    # Execute trading logic
                    if signal != 'HOLD' and not self.position:
                        if ticker:
                            self.execute_trade(signal, ticker['last'])
                    
                    if self.position and ticker:
                        self.check_exit_conditions(ticker['last'])
                    
                    # Update balance (simulated in test mode)
                    if TEST_MODE:
                        self.account_balance = 10000.0  # Simulated balance
                    
                    # Render UI
                    live.update(self.generate_ui(ticker, ohlcv, signal, indicators))
                    
                    time.sleep(2)
                    
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]Bot stopped by user.[/bold yellow]")
                    self.running = False
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    time.sleep(5)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
