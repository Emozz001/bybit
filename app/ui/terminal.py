"""
Terminal UI for Bybit AI Trading Platform.
Minimalist, modern design using Textual framework.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static, Label, ProgressBar
from textual.binding import Binding
from textual.reactive import reactive
from textual import work

from rich.panel import Panel
from rich.text import Text
from rich.align import Align


class MinimalHeader(Header):
    """Custom minimalist header."""
    
    def render(self) -> str:
        return "BYBIT AI TRADING"


class StatusIndicator(Static):
    """Animated status indicator dot."""
    
    is_connected = reactive(False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._blink_state = True
    
    def compose(self) -> ComposeResult:
        yield Label("●", id="status-dot")
    
    def watch_is_connected(self, connected: bool):
        self.update_dot()
    
    def update_dot(self):
        if self.is_connected:
            self.update("[green]●[/green]")
        else:
            self.update("[red]●[/red]")


class MetricCard(Static):
    """A minimalist metric display card."""
    
    value = reactive("0")
    label = reactive("")
    unit = reactive("")
    trend = reactive("")  # "up", "down", "neutral"
    
    def __init__(self, label: str = "", value: str = "0", unit: str = "", trend: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label
        self.value = value
        self.unit = unit
        self.trend = trend
    
    def compose(self) -> ComposeResult:
        yield Static(self._render_card(), expand=True)
    
    def _render_card(self) -> str:
        trend_indicator = {
            "up": "[green]▲[/green] ",
            "down": "[red]▼[/red] ",
            "neutral": ""
        }.get(self.trend, "")
        
        return f"[dim]{self.label}[/dim]\n[bold white]{trend_indicator}{self.value} {self.unit}[/bold white]"
    
    def update_metric(self, value: str, trend: str = ""):
        self.value = value
        self.trend = trend
        self.update(self._render_card())


class SystemHealthWidget(Static):
    """Displays system health metrics."""
    
    cpu_usage = reactive(0.0)
    memory_usage = reactive(0.0)
    latency = reactive(0.0)
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("[dim]CPU[/dim]", id="cpu-label")
            yield Static(f"{self.cpu_usage:.1f}%", id="cpu-value")
            yield Static("[dim]MEM[/dim]", id="mem-label")
            yield Static(f"{self.memory_usage:.1f}MB", id="mem-value")
            yield Static("[dim]LATENCY[/dim]", id="lat-label")
            yield Static(f"{self.latency:.1f}ms", id="lat-value")
    
    def update_health(self, cpu: float, memory: float, latency: float):
        self.cpu_usage = cpu
        self.memory_usage = memory
        self.latency = latency
        self.refresh()


class TradeLogWidget(Static):
    """Minimalist trade log display."""
    
    trades = reactive([])
    
    def compose(self) -> ComposeResult:
        yield Static("", id="trade-log-content")
    
    def add_trade(self, trade_info: Dict[str, Any]):
        self.trades.append(trade_info)
        self._update_log()
    
    def _update_log(self):
        if not self.trades:
            self.update("[dim]No trades yet...[/dim]")
            return
        
        lines = []
        for trade in self.trades[-5:]:  # Show last 5 trades
            symbol = trade.get('symbol', 'N/A')
            side = trade.get('side', 'N/A')
            pnl = trade.get('pnl', 0)
            
            side_color = "[green]BUY[/green]" if side.upper() == 'BUY' else "[red]SELL[/red]"
            pnl_color = f"[green]+{pnl:.2f}[/green]" if pnl > 0 else f"[red]{pnl:.2f}[/red]" if pnl < 0 else "[dim]0.00[/dim]"
            
            lines.append(f"{symbol} {side_color} → {pnl_color}")
        
        self.update("\n".join(lines))


class MainScreen(Static):
    """Main application screen with minimalist layout."""
    
    uptime = reactive("0s")
    scan_count = reactive(0)
    ws_connected = reactive(False)
    
    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            # Top row: Key metrics
            with Horizontal(id="metrics-row"):
                yield MetricCard(label="UPTIME", value=self.uptime, id="uptime-card")
                yield MetricCard(label="SCANS", value=str(self.scan_count), id="scans-card")
                yield MetricCard(label="STATUS", value="ONLINE" if self.ws_connected else "OFFLINE", 
                               trend="up" if self.ws_connected else "down", id="status-card")
            
            # Middle section: System health
            with Container(id="health-section"):
                yield Static("[dim]SYSTEM HEALTH[/dim]", id="health-title")
                yield SystemHealthWidget(id="health-widget")
            
            # Bottom: Trade log
            with Container(id="log-section"):
                yield Static("[dim]RECENT ACTIVITY[/dim]", id="log-title")
                yield TradeLogWidget(id="trade-log")
    
    def watch_uptime(self, uptime: str):
        if self.query_one("#uptime-card", MetricCard):
            self.query_one("#uptime-card", MetricCard).update_metric(uptime)
    
    def watch_scan_count(self, count: int):
        if self.query_one("#scans-card", MetricCard):
            self.query_one("#scans-card", MetricCard).update_metric(str(count))
    
    def watch_ws_connected(self, connected: bool):
        if self.query_one("#status-card", MetricCard):
            self.query_one("#status-card", MetricCard).update_metric(
                "ONLINE" if connected else "OFFLINE",
                "up" if connected else "down"
            )
    
    def update_health(self, cpu: float, memory: float, latency: float):
        if health_widget := self.query_one("#health-widget", SystemHealthWidget):
            health_widget.update_health(cpu, memory, latency)
    
    def add_trade(self, trade_info: Dict[str, Any]):
        if trade_log := self.query_one("#trade-log", TradeLogWidget):
            trade_log.add_trade(trade_info)


class TradingPlatformApp(App):
    """
    Bybit AI Trading Platform - Terminal UI
    
    A minimalist, modern terminal interface for monitoring
    and controlling the trading platform.
    """
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    
    #metrics-row {
        height: auto;
        margin-bottom: 2;
    }
    
    MetricCard {
        width: 1fr;
        height: 4;
        margin: 0 1;
        background: $surface-darken-2;
        border: solid $primary-darken-2;
        padding: 1 2;
    }
    
    #health-section {
        height: auto;
        margin-bottom: 2;
        padding: 1 2;
        background: $surface-darken-3;
        border: solid $primary-darken-3;
    }
    
    #health-title {
        text-align: center;
        padding-bottom: 1;
    }
    
    #health-section Horizontal {
        align: center middle;
    }
    
    #health-section Static {
        margin: 0 2;
    }
    
    #log-section {
        height: 1fr;
        padding: 1 2;
        background: $surface-darken-3;
        border: solid $primary-darken-3;
    }
    
    #log-title {
        text-align: center;
        padding-bottom: 1;
    }
    
    #trade-log {
        height: 1fr;
    }
    
    Static {
        color: $text;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("r", "refresh", "Refresh"),
        Binding("h", "toggle_help", "Help"),
    ]
    
    def __init__(self, platform=None):
        super().__init__()
        self.platform = platform
        self._dark_mode = True
    
    def on_mount(self) -> None:
        self.title = "Bybit AI Trading"
        self.sub_title = "Minimalist Terminal UI"
        
        # Start background updates
        self._update_loop()
    
    def compose(self) -> ComposeResult:
        yield MinimalHeader()
        yield MainScreen(id="main-screen")
        yield Footer()
    
    @work(exclusive=True)
    async def _update_loop(self):
        """Background task to update UI from platform data."""
        while True:
            try:
                if self.platform:
                    # Get data from platform
                    main_screen = self.query_one("#main-screen", MainScreen)
                    
                    # Update uptime
                    if hasattr(self.platform, '_get_uptime'):
                        uptime = self.platform._get_uptime()
                        main_screen.uptime = uptime
                    
                    # Update scan count
                    if hasattr(self.platform, '_scan_count'):
                        main_screen.scan_count = self.platform._scan_count
                    
                    # Update WebSocket status
                    if hasattr(self.platform, 'ws_manager') and self.platform.ws_manager:
                        main_screen.ws_connected = True
                        latency = self.platform.ws_manager.latency_ms
                    else:
                        main_screen.ws_connected = False
                        latency = 0.0
                    
                    # Update system health
                    if hasattr(self.platform, 'system_health'):
                        health = self.platform.system_health
                        main_screen.update_health(
                            health.cpu_usage_percent,
                            health.memory_usage_mb,
                            latency
                        )
                
                await asyncio.sleep(0.5)  # Update twice per second
                
            except Exception as e:
                # Silently continue on errors
                await asyncio.sleep(1.0)
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self._dark_mode = not self._dark_mode
        # Textual handles theme switching automatically
    
    def action_refresh(self) -> None:
        """Force refresh all data."""
        if self.platform and hasattr(self.platform, '_update_system_health_fast'):
            self.platform._update_system_health_fast()
        self.notify("Data refreshed", title="Refresh", severity="information")
    
    def action_toggle_help(self) -> None:
        """Show/hide help."""
        self.notify(
            "Q: Quit | D: Toggle Theme | R: Refresh | H: Help",
            title="Keyboard Shortcuts",
            severity="information",
            timeout=3
        )
    
    def update_from_platform(self):
        """Manual update call from platform."""
        if self.platform:
            main_screen = self.query_one("#main-screen", MainScreen)
            
            if hasattr(self.platform, '_get_uptime'):
                main_screen.uptime = self.platform._get_uptime()
            
            if hasattr(self.platform, '_scan_count'):
                main_screen.scan_count = self.platform._scan_count
            
            if hasattr(self.platform, 'ws_manager') and self.platform.ws_manager:
                main_screen.ws_connected = True
            else:
                main_screen.ws_connected = False


# Import asyncio for the background task
import asyncio


def run_ui(platform=None):
    """Run the trading platform UI."""
    app = TradingPlatformApp(platform)
    app.run()


if __name__ == "__main__":
    run_ui()
