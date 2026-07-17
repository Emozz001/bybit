"""
Modern Terminal User Interface for Bybit Trading System
A minimalist, keyboard-driven TUI built with Textual
"""

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Label, Input
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
from textual.message import Message
from rich.panel import Panel
from rich.align import Align


class Banner(Static):
    """Reusable banner component"""
    
    BANNERS = {
        "main": """
██████╗ ██╗   ██╗██████╗ ██╗████████╗
██╔══██╗╚██╗ ██╔╝██╔══██╗██║╚══██╔══╝
██████╔╝ ╚████╔╝ ██████╔╝██║   ██║
██╔══██╗  ╚██╔╝  ██╔══██╗██║   ██║
██████╔╝   ██║   ██████╔╝██║   ██║
╚═════╝    ╚═╝   ╚═════╝ ╚═╝   ╚═╝
        """,
        "dashboard": "DASHBOARD",
        "trading": "FUTURES TRADING",
        "scanner": "MARKET SCANNER",
        "positions": "OPEN POSITIONS",
        "orders": "ORDER MANAGER",
        "ai": "AI ANALYSIS",
        "backtesting": "BACKTEST ENGINE",
        "settings": "SETTINGS",
        "api": "API MANAGEMENT",
        "logs": "SYSTEM LOGS",
    }
    
    def __init__(self, screen_name: str = "main"):
        super().__init__()
        self.screen_name = screen_name
    
    def compose(self) -> ComposeResult:
        banner_text = self.BANNERS.get(self.screen_name, self.screen_name.upper())
        
        if self.screen_name == "main":
            yield Static(f"[cyan]{banner_text}[/cyan]\n\n[cyan bold]AI Trading Platform v2.0[/cyan bold]", id="main-banner")
        else:
            yield Static(f"╔══════════════════════════════╗\n      [cyan bold]{banner_text}[/cyan bold]      \n╚══════════════════════════════╝", id="page-banner")


class MenuItem(Static):
    """A single menu item with number navigation"""
    
    def __init__(self, number: str, text: str, description: str = ""):
        super().__init__()
        self.number = number
        self.text = text
        self.description = description
    
    def compose(self) -> ComposeResult:
        if self.description:
            yield Static(f"[blue][{self.number}][/blue] {self.text}\n    [dim]{self.description}[/dim]")
        else:
            yield Static(f"[blue][{self.number}][/blue] {self.text}")


class MainMenuScreen(Screen):
    """Main menu screen with all primary options"""
    
    BINDINGS = [
        Binding("0", "exit_app", "Exit"),
        Binding("q", "quit_app", "Quit"),
        Binding("h", "show_help", "Help"),
        Binding("d", "go_dashboard", "Dashboard"),
        Binding("t", "go_trading", "Trading"),
        Binding("s", "go_settings", "Settings"),
        Binding("l", "go_logs", "Logs"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="main-menu-container"):
            yield Banner("main")
            
            with Vertical(id="menu-items"):
                yield MenuItem("1", "Dashboard", "View portfolio and performance")
                yield MenuItem("2", "Futures Trading", "Manual and automated trading")
                yield MenuItem("3", "Spot Trading", "Spot market operations")
                yield MenuItem("4", "AI Market Analysis", "AI-powered insights")
                yield MenuItem("5", "Market Scanner", "Scan for opportunities")
                yield MenuItem("6", "Arbitrage Scanner", "Find arbitrage chances")
                yield MenuItem("7", "Open Positions", "Manage active positions")
                yield MenuItem("8", "Order Manager", "View and manage orders")
                yield MenuItem("9", "Risk Management", "Configure risk settings")
                yield MenuItem("0", "Portfolio", "View complete portfolio")
                yield MenuItem("a", "Backtesting", "Test strategies historically")
                yield MenuItem("b", "Reports", "Generate trading reports")
                yield MenuItem("c", "Strategy Manager", "Manage trading strategies")
                yield MenuItem("d", "Notifications", "Alert configuration")
                yield MenuItem("e", "Logs", "System logs viewer")
                yield MenuItem("f", "Database", "Database tools")
                yield MenuItem("g", "API Manager", "Configure API keys")
                yield MenuItem("h", "Updates", "Check for updates")
                yield MenuItem("i", "Help", "Help and documentation")
                yield MenuItem("j", "About", "About this application")
            
            with Vertical(id="exit-section"):
                yield MenuItem("0", "Exit", "Close the application")
        
        yield Footer()
    
    def action_exit_app(self) -> None:
        self.app.exit()
    
    def action_quit_app(self) -> None:
        self.app.exit()
    
    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())
    
    def action_go_dashboard(self) -> None:
        self.app.push_screen(DashboardScreen())
    
    def action_go_trading(self) -> None:
        self.app.push_screen(TradingScreen())
    
    def action_go_settings(self) -> None:
        self.app.push_screen(SettingsScreen())
    
    def action_go_logs(self) -> None:
        self.app.push_screen(LogsScreen())


class DashboardScreen(Screen):
    """Dashboard screen showing key metrics"""
    
    BINDINGS = [
        Binding("0", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Banner("dashboard")
        
        with ScrollableContainer(id="dashboard-content"):
            with Horizontal(id="stats-row-1"):
                with Container(classes="stat-panel"):
                    yield Static("[cyan]Balance[/cyan]")
                    yield Static("[green bold]$120.55[/green bold]", classes="stat-value")
                
                with Container(classes="stat-panel"):
                    yield Static("[cyan]Today's PNL[/cyan]")
                    yield Static("[green bold]+$7.25[/green bold]", classes="stat-value")
                
                with Container(classes="stat-panel"):
                    yield Static("[cyan]Open Positions[/cyan]")
                    yield Static("[yellow bold]2[/yellow bold]", classes="stat-value")
                
                with Container(classes="stat-panel"):
                    yield Static("[cyan]Win Rate[/cyan]")
                    yield Static("[green bold]74%[/green bold]", classes="stat-value")
            
            with Horizontal(id="stats-row-2"):
                with Container(classes="stat-panel"):
                    yield Static("[cyan]Total Trades[/cyan]")
                    yield Static("[white bold]285[/white bold]", classes="stat-value")
                
                with Container(classes="stat-panel"):
                    yield Static("[cyan]Current Strategy[/cyan]")
                    yield Static("[magenta bold]AI Momentum[/magenta bold]", classes="stat-value")
                
                with Container(classes="stat-panel"):
                    yield Static("[cyan]Bot Status[/cyan]")
                    yield Static("[green bold]🟢 Running[/green bold]", classes="stat-value")
            
            with Container(id="positions-preview"):
                yield Static("[cyan bold]Recent Positions[/cyan bold]")
                yield Static("""
┌─────────────┬──────────┬─────────┬──────────┬────────────┐
│ Symbol      │ Side     │ Size    │ PNL      │ Status     │
├─────────────┼──────────┼─────────┼──────────┼────────────┤
│ BTCUSDT     │ Long     │ 0.01    │ +$12.50  │ 🟢 Open    │
│ ETHUSDT     │ Short    │ 0.5     │ -$3.20   │ 🟢 Open    │
│ SOLUSDT     │ Long     │ 10      │ +$8.75   │ ✔ Closed   │
└─────────────┴──────────┴─────────┴──────────┴────────────┘
                """)
        
        yield Footer()
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    def action_refresh(self) -> None:
        # Refresh data logic here
        pass
    
    def action_quit_app(self) -> None:
        self.app.exit()


class TradingScreen(Screen):
    """Trading interface"""
    
    BINDINGS = [
        Binding("0", "go_back", "Back"),
        Binding("q", "quit_app", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Banner("trading")
        
        with Vertical(id="trading-menu"):
            yield MenuItem("1", "Manual Trade", "Execute a manual trade")
            yield MenuItem("2", "Auto Trade", "Enable automated trading")
            yield MenuItem("3", "AI Assisted Trade", "AI-powered trade suggestions")
            yield MenuItem("4", "Risk Calculator", "Calculate position size")
            yield MenuItem("5", "Position Size", "Quick position sizing")
            yield MenuItem("0", "Back", "Return to main menu")
        
        yield Footer()
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    def action_quit_app(self) -> None:
        self.app.exit()


class SettingsScreen(Screen):
    """Settings and configuration"""
    
    BINDINGS = [
        Binding("0", "go_back", "Back"),
        Binding("q", "quit_app", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Banner("settings")
        
        with Vertical(id="settings-menu"):
            yield MenuItem("1", "API Configuration", "Manage API keys")
            yield MenuItem("2", "Theme", "Change color theme")
            yield MenuItem("3", "Notifications", "Configure alerts")
            yield MenuItem("4", "Database", "Database settings")
            yield MenuItem("5", "Logs", "Log configuration")
            yield MenuItem("6", "Update", "Check for updates")
            yield MenuItem("0", "Back", "Return to main menu")
        
        yield Footer()
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    def action_quit_app(self) -> None:
        self.app.exit()


class LogsScreen(Screen):
    """System logs viewer"""
    
    BINDINGS = [
        Binding("0", "go_back", "Back"),
        Binding("q", "quit_app", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Banner("logs")
        
        with ScrollableContainer(id="logs-container"):
            yield Static("""
[green]2026-07-17 20:17:42[/green] | [bold]INFO[/bold]     | Platform initialized
[green]2026-07-17 20:17:43[/green] | [bold]INFO[/bold]     | Connected to Bybit
[green]2026-07-17 20:17:44[/green] | [bold]WARNING[/bold]  | Low balance warning
[yellow]2026-07-17 20:17:45[/yellow] | [bold]ERROR[/bold]   | Trade execution failed
[green]2026-07-17 20:17:46[/green] | [bold]INFO[/bold]     | Retry successful
            """)
        
        yield Footer()
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    def action_quit_app(self) -> None:
        self.app.exit()


class HelpScreen(Screen):
    """Help and keyboard shortcuts"""
    
    BINDINGS = [
        Binding("0", "go_back", "Back"),
        Binding("q", "quit_app", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("╔══════════════════════════════╗\n         [cyan bold]HELP[/cyan bold]         \n╚══════════════════════════════╝", id="help-banner")
        
        with ScrollableContainer(id="help-content"):
            yield Static("""
[cyan bold]Navigation:[/cyan bold]
  [blue]0[/blue] - Go back / Exit current screen
  [blue]1-9[/blue] - Select menu items
  [blue]Q[/blue] - Quit application

[cyan bold]Quick Access:[/cyan bold]
  [blue]D[/blue] - Dashboard
  [blue]T[/blue] - Trading
  [blue]S[/blue] - Settings
  [blue]L[/blue] - Logs
  [blue]H[/blue] - Help
  [blue]R[/blue] - Refresh

[cyan bold]Confirmations:[/cyan bold]
  [blue]Y[/blue] - Yes / Confirm
  [blue]N[/blue] - No / Cancel

[cyan bold]Tips:[/cyan bold]
  • All menus use numeric navigation
  • Type the number to select an option
  • Use arrow keys to scroll long lists
  • Press '0' to go back from any screen
            """)
        
        yield Footer()
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    def action_quit_app(self) -> None:
        self.app.exit()


class ConfirmationDialog(Screen):
    """Generic confirmation dialog"""
    
    def __init__(self, message: str, callback=None):
        super().__init__()
        self.message = message
        self.callback = callback
    
    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("0", "cancel", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Static(f"""
╔══════════════════════════════╗
       [yellow bold]CONFIRMATION[/yellow bold]
╚══════════════════════════════╝

{self.message}

[green][Y][/green] Yes
[red][N][/red] No
        """)
    
    def action_confirm(self) -> None:
        if self.callback:
            self.callback()
        self.app.pop_screen()
    
    def action_cancel(self) -> None:
        self.app.pop_screen()


class BybitTUIApp(App):
    """Main TUI Application"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-menu-container {
        width: 100%;
        height: 100%;
        align: center top;
        padding: 1 2;
    }
    
    #main-banner {
        width: 100%;
        content-align: center middle;
        margin: 1 0;
        text-align: center;
    }
    
    #page-banner {
        width: 100%;
        content-align: center middle;
        margin: 1 0;
        text-align: center;
    }
    
    #menu-items {
        width: 60;
        height: auto;
        border: solid blue;
        padding: 1 2;
        margin: 1 0;
    }
    
    .stat-panel {
        width: 20;
        height: 6;
        border: solid cyan;
        padding: 1;
        margin: 0 1;
        text-align: center;
    }
    
    .stat-value {
        text-align: center;
        margin-top: 1;
    }
    
    #dashboard-content {
        width: 100%;
        height: 100%;
    }
    
    #stats-row-1, #stats-row-2 {
        height: auto;
        margin: 1 0;
    }
    
    #positions-preview {
        width: 100%;
        border: solid green;
        padding: 1;
        margin: 1 0;
    }
    
    #trading-menu, #settings-menu {
        width: 60;
        height: auto;
        border: solid blue;
        padding: 1 2;
        margin: 2 auto;
    }
    
    #logs-container {
        width: 100%;
        height: 100%;
        background: $surface-darken-2;
        padding: 1;
    }
    
    #help-content {
        width: 80;
        height: auto;
        border: solid yellow;
        padding: 1 2;
        margin: 2 auto;
    }
    
    #help-banner {
        width: 100%;
        content-align: center middle;
        margin: 1 0;
        text-align: center;
    }
    
    Footer {
        dock: bottom;
        height: 3;
    }
    
    Header {
        dock: top;
        height: 3;
    }
    """
    
    TITLE = "Bybit AI Trading Platform"
    SUB_TITLE = "Professional Terminal Interface"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]
    
    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())
    
    def action_quit(self) -> None:
        self.exit()


def main():
    """Entry point for the TUI application"""
    app = BybitTUIApp()
    app.run()


if __name__ == "__main__":
    main()
