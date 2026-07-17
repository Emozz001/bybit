"""
Modern Terminal User Interface for Bybit Trading System
A minimalist, keyboard-driven TUI built with Textual

Architecture:
- Modular component-based design
- Number-based navigation throughout
- Consistent y/n confirmations
- Multi-step wizards for complex workflows
- Theme support with instant switching
- Professional error handling
"""

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Label, Input, Select
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
from textual.message import Message
from rich.panel import Panel
from rich.align import Align
from rich.table import Table as RichTable

# Import modular components
from app.ui.components.widgets import Banner, MenuItem, StatCard, LoadingWidget
from app.ui.components.dialogs import ConfirmationDialog, InputDialog, MessageDialog, MultiStepWizard
from app.ui.components.tables import MarketTable, PositionsTable, OrdersTable
from app.ui.components.forms import TradeForm, APIKeyForm, SettingsForm
from app.ui.components.notifications import notify_success, notify_error, notify_warning, notify_info
from app.ui.components.progress import SpinnerWidget, ProgressBar
from app.ui.components.themes import ThemeManager, get_theme, set_theme, BASE_CSS, THEMES


class MainMenuScreen(Screen):
    """Main menu screen with all primary options - number based navigation."""
    
    BINDINGS = [
        Binding("0", "exit_app", "Exit"),
        Binding("q", "quit_app", "Quit"),
        Binding("h", "show_help", "Help"),
        Binding("1", "go_dashboard", "Dashboard"),
        Binding("2", "go_trading", "Trading"),
        Binding("3", "go_scanner", "Scanner"),
        Binding("4", "go_portfolio", "Portfolio"),
        Binding("5", "go_bots", "Bots"),
        Binding("6", "go_settings", "Settings"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="main-menu-container"):
            yield Banner("main")
            
            with Vertical(id="menu-sections"):
                # Account Section
                yield Static("\n[cyan bold]Account[/cyan bold]", classes="section-title")
                yield Static("───────────────────────────────────────", classes="section-divider")
                yield MenuItem("1", "Login", "Connect to Bybit")
                yield MenuItem("2", "Switch Account", "Change active account")
                yield MenuItem("3", "Logout", "Disconnect from exchange")
                
                # Trading Section
                yield Static("\n[cyan bold]Trading[/cyan bold]", classes="section-title")
                yield Static("───────────────────────────────────────", classes="section-divider")
                yield MenuItem("4", "Manual Trade", "Execute trades manually")
                yield MenuItem("5", "Auto Trading", "Enable automated trading")
                yield MenuItem("6", "Paper Trading", "Practice with fake money")
                yield MenuItem("7", "Arbitrage Scanner", "Find arbitrage opportunities")
                
                # Portfolio Section
                yield Static("\n[cyan bold]Portfolio[/cyan bold]", classes="section-title")
                yield Static("───────────────────────────────────────", classes="section-divider")
                yield MenuItem("8", "Positions", "View open positions")
                yield MenuItem("9", "Orders", "Manage orders")
                yield MenuItem("0", "Assets", "View balances")
                yield MenuItem("a", "PnL History", "Trading history")
                
                # Tools Section
                yield Static("\n[cyan bold]Tools[/cyan bold]", classes="section-title")
                yield Static("───────────────────────────────────────", classes="section-divider")
                yield MenuItem("b", "Market Scanner", "Scan for opportunities")
                yield MenuItem("c", "Backtesting", "Test strategies")
                yield MenuItem("d", "Settings", "Configure system")
                yield MenuItem("e", "Update System", "Check for updates")
                
                # System Section
                yield Static("\n[cyan bold]System[/cyan bold]", classes="section-title")
                yield Static("───────────────────────────────────────", classes="section-divider")
                yield MenuItem("f", "Help", "Documentation")
                yield MenuItem("g", "About", "About this application")
                yield MenuItem("0", "Exit", "Close application")
        
        yield Footer()
    
    def on_key(self, event) -> None:
        """Handle number key presses for menu navigation."""
        key = event.key.lower()
        
        # Map keys to actions
        action_map = {
            "1": self.action_go_login,
            "2": self.action_go_switch_account,
            "3": self.action_go_logout,
            "4": self.action_go_trade,
            "5": self.action_go_auto_trading,
            "6": self.action_go_paper_trading,
            "7": self.action_go_arbitrage,
            "8": self.action_go_positions,
            "9": self.action_go_orders,
            "0": self.action_go_assets,
            "a": self.action_go_pnl,
            "b": self.action_go_scanner,
            "c": self.action_go_backtest,
            "d": self.action_go_settings,
            "e": self.action_go_update,
            "f": self.action_go_help,
            "g": self.action_go_about,
        }
        
        if key in action_map:
            action_map[key]()
            event.prevent_default()
    
    def action_exit_app(self) -> None:
        self.app.push_screen(ExitConfirmationScreen())
    
    def action_quit_app(self) -> None:
        self.app.exit()
    
    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())
    
    def action_go_dashboard(self) -> None:
        self.app.push_screen(DashboardScreen())
    
    def action_go_login(self) -> None:
        self.app.push_screen(LoginScreen())
    
    def action_go_switch_account(self) -> None:
        self.app.push_screen(SwitchAccountScreen())
    
    def action_go_logout(self) -> None:
        def on_confirm():
            notify_success(self.app, "Logged out successfully")
        self.app.push_screen(ConfirmationDialog("Logout from current account?", on_confirm))
    
    def action_go_trade(self) -> None:
        self.app.push_screen(TradeScreen())
    
    def action_go_auto_trading(self) -> None:
        self.app.push_screen(AutoTradingScreen())
    
    def action_go_paper_trading(self) -> None:
        self.app.push_screen(PaperTradingScreen())
    
    def action_go_arbitrage(self) -> None:
        self.app.push_screen(ArbitrageScreen())
    
    def action_go_positions(self) -> None:
        self.app.push_screen(PositionsScreen())
    
    def action_go_orders(self) -> None:
        self.app.push_screen(OrdersScreen())
    
    def action_go_assets(self) -> None:
        self.app.push_screen(AssetsScreen())
    
    def action_go_pnl(self) -> None:
        self.app.push_screen(PnLScreen())
    
    def action_go_scanner(self) -> None:
        self.app.push_screen(ScannerScreen())
    
    def action_go_backtest(self) -> None:
        self.app.push_screen(BacktestScreen())
    
    def action_go_settings(self) -> None:
        self.app.push_screen(SettingsScreen())
    
    def action_go_update(self) -> None:
        self.app.push_screen(UpdateScreen())
    
    def action_go_help(self) -> None:
        self.app.push_screen(HelpScreen())
    
    def action_go_about(self) -> None:
        self.app.push_screen(AboutScreen())


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
        margin: 2 0;
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
