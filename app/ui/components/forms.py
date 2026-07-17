"""
Form Components for the Bybit Trading TUI
Input forms for trading, API setup, and settings.
"""

from textual.screen import Screen
from textual.widgets import Static, Button, Input, Label, Select
from textual.containers import Container, Vertical, Horizontal
from textual.app import ComposeResult
from textual.binding import Binding


class TradeForm(Screen):
    """
    Trade execution form with symbol, side, size, and order type.
    
    Usage:
        result = await app.push_screen_wait(TradeForm(symbol="BTCUSDT"))
    """
    
    BINDINGS = [
        Binding("enter", "submit", "Submit"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, symbol: str = "", balance: float = 0.0, callback=None):
        super().__init__()
        self.symbol = symbol
        self.balance = balance
        self.callback = callback
        self.result = None
    
    def compose(self) -> ComposeResult:
        with Container(id="form-container"):
            yield Static(
                "╔══════════════════════════════╗\n       [cyan bold]PLACE ORDER[/cyan bold]       \n╚══════════════════════════════╝",
                id="form-title"
            )
            
            with Vertical(id="form-fields"):
                # Symbol
                yield Static("\n[cyan]Trading Pair:[/cyan]", classes="form-label")
                yield Input(value=self.symbol, id="input-symbol", placeholder="e.g., BTCUSDT")
                
                # Side
                yield Static("\n[cyan]Side:[/cyan]", classes="form-label")
                with Horizontal(id="side-buttons"):
                    yield Button("[green]Buy / Long[/green]", id="btn-buy", variant="success")
                    yield Button("[red]Sell / Short[/red]", id="btn-sell", variant="error")
                
                # Size
                yield Static("\n[cyan]Size:[/cyan]", classes="form-label")
                yield Input(id="input-size", placeholder="Position size", type="decimal")
                
                # Order Type
                yield Static("\n[cyan]Order Type:[/cyan]", classes="form-label")
                yield Select(
                    [("Market", "market"), ("Limit", "limit"), ("Stop Loss", "stop_loss")],
                    value="market",
                    id="select-order-type"
                )
                
                # Price (for limit orders)
                yield Static("\n[cyan]Price (optional for market):[/cyan]", classes="form-label")
                yield Input(id="input-price", placeholder="Limit price", type="decimal")
                
                # Balance info
                yield Static(f"\n[dim]Available Balance: {self.balance:.2f} USDT[/dim]", id="balance-info")
                
                # Action buttons
                with Horizontal(id="form-buttons"):
                    yield Button("[green]Submit (Enter)[/green]", id="btn-submit", variant="success")
                    yield Button("[red]Cancel (Esc)[/red]", id="btn-cancel", variant="error")
    
    def action_submit(self) -> None:
        symbol = self.query_one("#input-symbol", Input).value
        size_input = self.query_one("#input-size", Input).value
        order_type = self.query_one("#select-order-type", Select).value
        price = self.query_one("#input-price", Input).value
        
        if not symbol or not size_input:
            self.notify("Symbol and size are required", severity="error")
            return
        
        self.result = {
            "symbol": symbol,
            "size": float(size_input) if size_input else 0,
            "order_type": order_type,
            "price": float(price) if price else None,
        }
        
        if self.callback:
            self.callback(self.result)
        
        self.dismiss(self.result)
    
    def action_cancel(self) -> None:
        self.dismiss(None)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            self.action_submit()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-buy":
            # Pre-select buy side visual feedback
            self.notify("Buy/Long selected", severity="information")
        elif event.button.id == "btn-sell":
            # Pre-select sell side visual feedback
            self.notify("Sell/Short selected", severity="information")


class APIKeyForm(Screen):
    """
    API Key configuration form.
    
    Usage:
        result = await app.push_screen_wait(APIKeyForm())
    """
    
    BINDINGS = [
        Binding("enter", "submit", "Submit"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, api_key: str = "", secret_key: str = "", testnet: bool = True, callback=None):
        super().__init__()
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self.callback = callback
        self.result = None
    
    def compose(self) -> ComposeResult:
        with Container(id="form-container"):
            yield Static(
                "╔══════════════════════════════╗\n   [cyan bold]API CONFIGURATION[/cyan bold]   \n╚══════════════════════════════╝",
                id="form-title"
            )
            
            with Vertical(id="form-fields"):
                # API Key
                yield Static("\n[cyan]API Key:[/cyan]", classes="form-label")
                yield Input(value=self.api_key, id="input-api-key", placeholder="Enter your API key")
                
                # Secret Key
                yield Static("\n[cyan]Secret Key:[/cyan]", classes="form-label")
                yield Input(value=self.secret_key, id="input-secret", placeholder="Enter your secret key", password=True)
                
                # Testnet toggle
                yield Static("\n[cyan]Environment:[/cyan]", classes="form-label")
                with Horizontal(id="env-buttons"):
                    testnet_style = "green" if self.testnet else "default"
                    mainnet_style = "red" if not self.testnet else "default"
                    yield Button(f"[{testnet_style}]Testnet[/]", id="btn-testnet", variant="success" if self.testnet else "default")
                    yield Button(f"[{mainnet_style}]Mainnet[/]", id="btn-mainnet", variant="error" if not self.testnet else "default")
                
                yield Static(f"\n[dim]Current: {'Testnet' if self.testnet else 'Mainnet'}[/dim]", id="env-info")
                
                # Action buttons
                with Horizontal(id="form-buttons"):
                    yield Button("[green]Save (Enter)[/green]", id="btn-submit", variant="success")
                    yield Button("[red]Cancel (Esc)[/red]", id="btn-cancel", variant="error")
    
    def action_submit(self) -> None:
        api_key = self.query_one("#input-api-key", Input).value
        secret = self.query_one("#input-secret", Input).value
        
        if not api_key or not secret:
            self.notify("API Key and Secret are required", severity="error")
            return
        
        self.result = {
            "api_key": api_key,
            "secret_key": secret,
            "testnet": self.testnet,
        }
        
        if self.callback:
            self.callback(self.result)
        
        self.dismiss(self.result)
    
    def action_cancel(self) -> None:
        self.dismiss(None)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            self.action_submit()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-testnet":
            self.testnet = True
            self.refresh()
        elif event.button.id == "btn-mainnet":
            self.testnet = False
            self.refresh()


class SettingsForm(Screen):
    """
    General settings configuration form.
    """
    
    BINDINGS = [
        Binding("enter", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, settings: dict = None, callback=None):
        super().__init__()
        self.settings = settings or {}
        self.callback = callback
        self.result = None
    
    def compose(self) -> ComposeResult:
        with Container(id="form-container"):
            yield Static(
                "╔══════════════════════════════╗\n        [cyan bold]SETTINGS[/cyan bold]         \n╚══════════════════════════════╝",
                id="form-title"
            )
            
            with Vertical(id="form-fields"):
                # Risk Level
                yield Static("\n[cyan]Risk Level:[/cyan]", classes="form-label")
                risk_level = self.settings.get("risk_level", "medium")
                yield Select(
                    [("Low", "low"), ("Medium", "medium"), ("High", "high")],
                    value=risk_level,
                    id="select-risk"
                )
                
                # Max Position Size
                yield Static("\n[cyan]Max Position Size (USDT):[/cyan]", classes="form-label")
                yield Input(
                    value=str(self.settings.get("max_position_size", "100")),
                    id="input-max-position",
                    type="decimal"
                )
                
                # Stop Loss %
                yield Static("\n[cyan]Default Stop Loss (%):[/cyan]", classes="form-label")
                yield Input(
                    value=str(self.settings.get("stop_loss_pct", "2.0")),
                    id="input-stop-loss",
                    type="decimal"
                )
                
                # Take Profit %
                yield Static("\n[cyan]Default Take Profit (%):[/cyan]", classes="form-label")
                yield Input(
                    value=str(self.settings.get("take_profit_pct", "4.0")),
                    id="input-take-profit",
                    type="decimal"
                )
                
                # Auto Trading
                yield Static("\n[cyan]Auto Trading:[/cyan]", classes="form-label")
                auto_trading = self.settings.get("auto_trading", False)
                yield Button(
                    f"[{'green' if auto_trading else 'red'}]{'Enabled' if auto_trading else 'Disabled'}[/]",
                    id="btn-auto-trading",
                    variant="success" if auto_trading else "default"
                )
                
                # Notifications
                yield Static("\n[cyan]Notifications:[/cyan]", classes="form-label")
                notifications = self.settings.get("notifications", True)
                yield Button(
                    f"[{'green' if notifications else 'red'}]{'Enabled' if notifications else 'Disabled'}[/]",
                    id="btn-notifications",
                    variant="success" if notifications else "default"
                )
                
                # Action buttons
                with Horizontal(id="form-buttons"):
                    yield Button("[green]Save (Enter)[/green]", id="btn-submit", variant="success")
                    yield Button("[red]Cancel (Esc)[/red]", id="btn-cancel", variant="error")
    
    def action_save(self) -> None:
        risk = self.query_one("#select-risk", Select).value
        max_pos = self.query_one("#input-max-position", Input).value
        stop_loss = self.query_one("#input-stop-loss", Input).value
        take_profit = self.query_one("#input-take-profit", Input).value
        
        self.result = {
            "risk_level": risk,
            "max_position_size": float(max_pos) if max_pos else 100,
            "stop_loss_pct": float(stop_loss) if stop_loss else 2.0,
            "take_profit_pct": float(take_profit) if take_profit else 4.0,
        }
        
        if self.callback:
            self.callback(self.result)
        
        self.dismiss(self.result)
    
    def action_cancel(self) -> None:
        self.dismiss(None)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id in ["btn-auto-trading", "btn-notifications"]:
            # Toggle logic would go here
            self.refresh()
