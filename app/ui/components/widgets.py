"""
Reusable UI Widgets for the Bybit Trading TUI
"""

from textual.widgets import Static
from textual.app import ComposeResult
from rich.panel import Panel
from rich.align import Align


class Banner(Static):
    """Reusable banner component with ASCII art or text titles."""
    
    BANNERS = {
        "main": """
╔═══════════════════════════════════════════════╗
          BYBIT TRADING TERMINAL
╚═══════════════════════════════════════════════╝
        """,
        "dashboard": "DASHBOARD",
        "trading": "FUTURES TRADING",
        "scanner": "MARKET SCANNER",
        "positions": "OPEN POSITIONS",
        "orders": "ORDER MANAGER",
        "settings": "SETTINGS",
        "api": "API MANAGEMENT",
        "logs": "SYSTEM LOGS",
        "help": "HELP",
        "about": "ABOUT",
        "portfolio": "PORTFOLIO",
        "bots": "BOT MANAGER",
        "backtest": "BACKTESTING",
    }
    
    def __init__(self, screen_name: str = "main"):
        super().__init__()
        self.screen_name = screen_name
    
    def compose(self) -> ComposeResult:
        banner_text = self.BANNERS.get(self.screen_name, self.screen_name.upper())
        
        if self.screen_name == "main":
            yield Static(f"[cyan]{banner_text}[/cyan]", id="main-banner")
        else:
            yield Static(
                f"╔══════════════════════════════╗\n      [cyan bold]{banner_text}[/cyan bold]      \n╚══════════════════════════════╝",
                id="page-banner"
            )


class MenuItem(Static):
    """A single menu item with number navigation."""
    
    def __init__(self, number: str, text: str, description: str = ""):
        super().__init__()
        self.number = number
        self.text = text
        self.description = description
    
    def compose(self) -> ComposeResult:
        if self.description:
            yield Static(
                f"[bold blue][{self.number}][/bold blue] [white]{self.text}[/white]\n    [dim]{self.description}[/dim]"
            )
        else:
            yield Static(f"[bold blue][{self.number}][/bold blue] [white]{self.text}[/white]")


class StatCard(Static):
    """A statistics card displaying a metric with label and value."""
    
    def __init__(
        self,
        label: str = "",
        value: str = "0",
        unit: str = "",
        trend: str = "",
        color: str = "white",
        id: str = None
    ):
        super().__init__(id=id)
        self.label = label
        self.value = value
        self.unit = unit
        self.trend = trend  # "up", "down", "neutral"
        self.color = color
    
    def compose(self) -> ComposeResult:
        trend_indicator = {
            "up": "[green]▲[/green] ",
            "down": "[red]▼[/red] ",
            "neutral": ""
        }.get(self.trend, "")
        
        color_map = {
            "white": "white",
            "green": "green",
            "red": "red",
            "yellow": "yellow",
            "cyan": "cyan",
            "magenta": "magenta",
        }
        
        actual_color = color_map.get(self.color, "white")
        
        yield Static(
            f"[dim]{self.label}[/dim]\n[bold {actual_color}]{trend_indicator}{self.value} {self.unit}[/bold {actual_color}]",
            classes="stat-card"
        )
    
    def update_value(self, value: str, trend: str = ""):
        """Update the card's value and optionally trend."""
        self.value = value
        if trend:
            self.trend = trend
        self.refresh()


class LoadingWidget(Static):
    """A widget showing loading progress with spinner and message."""
    
    def __init__(self, message: str = "Loading...", total: int = 100):
        super().__init__()
        self.message = message
        self.total = total
        self.current = 0
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_index = 0
    
    def compose(self) -> ComposeResult:
        yield Static(self._render(), id="loading-display")
    
    def _render(self) -> str:
        spinner = self._spinner_frames[self._spinner_index]
        percentage = (self.current / self.total * 100) if self.total > 0 else 0
        
        bar_width = 30
        filled = int(bar_width * percentage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        return f"{spinner} {self.message}\n[cyan][{bar}] {percentage:.0f}%[/cyan]"
    
    def update_progress(self, current: int, message: str = None):
        """Update progress and optionally change message."""
        self.current = current
        if message:
            self.message = message
        
        # Advance spinner
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        self.refresh()
    
    def set_complete(self):
        """Mark loading as complete."""
        self.current = self.total
        self.refresh()
