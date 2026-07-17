"""
Dialog Components for the Bybit Trading TUI
Confirmation, Input, and Message dialogs with consistent UX.
"""

from textual.screen import Screen
from textual.widgets import Static, Button, Input, Label
from textual.containers import Container, Vertical, Horizontal
from textual.app import ComposeResult
from textual.binding import Binding


class ConfirmationDialog(Screen):
    """
    Generic confirmation dialog with y/n style.
    
    Usage:
        app.push_screen(ConfirmationDialog("Delete configuration?", callback=my_func))
    """
    
    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("0", "cancel", "Cancel"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, message: str, callback=None, title: str = "CONFIRMATION"):
        super().__init__()
        self.message = message
        self.callback = callback
        self.title = title
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Static(
                f"╔══════════════════════════════╗\n       [yellow bold]{self.title}[/yellow bold]       \n╚══════════════════════════════╝",
                id="dialog-title"
            )
            
            yield Static(f"\n{self.message}\n", id="dialog-message")
            
            with Horizontal(id="dialog-buttons"):
                yield Button("[green]Yes (Y)[/green]", id="btn-yes", variant="success")
                yield Button("[red]No (N)[/red]", id="btn-no", variant="error")
            
            yield Static("\n[yellow](y/n)[/yellow]", id="dialog-prompt")
    
    def action_confirm(self) -> None:
        if self.callback:
            self.callback()
        self.app.pop_screen()
    
    def action_cancel(self) -> None:
        self.app.pop_screen()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.action_confirm()
        else:
            self.action_cancel()


class InputDialog(Screen):
    """
    Single input dialog for collecting user text.
    
    Usage:
        result = await app.push_screen_wait(InputDialog("Enter API Key:"))
    """
    
    BINDINGS = [
        Binding("enter", "submit", "Submit"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(
        self,
        prompt: str,
        placeholder: str = "",
        password: bool = False,
        callback=None,
        title: str = "INPUT"
    ):
        super().__init__()
        self.prompt = prompt
        self.placeholder = placeholder
        self.password = password
        self.callback = callback
        self.title = title
        self.result_value = None
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Static(
                f"╔══════════════════════════════╗\n         [cyan bold]{self.title}[/cyan bold]         \n╚══════════════════════════════╝",
                id="dialog-title"
            )
            
            yield Static(f"\n{self.prompt}\n", id="dialog-message")
            
            yield Input(
                placeholder=self.placeholder,
                password=self.password,
                id="input-field"
            )
            
            with Horizontal(id="dialog-buttons"):
                yield Button("[green]Submit (Enter)[/green]", id="btn-submit", variant="success")
                yield Button("[red]Cancel (Esc)[/red]", id="btn-cancel", variant="error")
    
    def action_submit(self) -> None:
        input_widget = self.query_one("#input-field", Input)
        self.result_value = input_widget.value
        
        if self.callback:
            self.callback(self.result_value)
        
        self.dismiss(self.result_value)
    
    def action_cancel(self) -> None:
        self.dismiss(None)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            self.action_submit()
        else:
            self.action_cancel()


class MessageDialog(Screen):
    """
    Display a message with OK button.
    
    Usage:
        app.push_screen(MessageDialog("Operation completed successfully!", title="SUCCESS"))
    """
    
    BINDINGS = [
        Binding("enter", "dismiss", "OK"),
        Binding("escape", "dismiss", "OK"),
    ]
    
    def __init__(
        self,
        message: str,
        title: str = "MESSAGE",
        message_type: str = "info",  # info, success, warning, error
        callback=None
    ):
        super().__init__()
        self.message = message
        self.title = title
        self.message_type = message_type
        self.callback = callback
    
    def compose(self) -> ComposeResult:
        color_map = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        
        icon_map = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }
        
        color = color_map.get(self.message_type, "cyan")
        icon = icon_map.get(self.message_type, "ℹ")
        
        with Container(id="dialog-container"):
            yield Static(
                f"╔══════════════════════════════╗\n      [{color} bold]{icon} {self.title}[/{color} bold]      \n╚══════════════════════════════╝",
                id="dialog-title"
            )
            
            yield Static(f"\n{self.message}\n", id="dialog-message")
            
            with Horizontal(id="dialog-buttons"):
                yield Button(f"[{color}]OK (Enter)[/{color}]", id="btn-ok", variant="primary")
    
    def action_dismiss(self) -> None:
        if self.callback:
            self.callback()
        self.app.pop_screen()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ok":
            self.action_dismiss()


class MultiStepWizard(Screen):
    """
    Multi-step wizard for complex workflows.
    
    Usage:
        steps = [
            {"prompt": "Enter API Key", "key": "api_key"},
            {"prompt": "Enter Secret", "key": "secret", "password": True},
            {"prompt": "Use Testnet? (y/n)", "key": "testnet", "type": "confirm"},
        ]
        app.push_screen(MultiStepWizard(steps, callback=on_complete))
    """
    
    BINDINGS = [
        Binding("enter", "next_step", "Next"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(
        self,
        steps: list,
        callback=None,
        title: str = "SETUP WIZARD"
    ):
        super().__init__()
        self.steps = steps
        self.callback = callback
        self.title = title
        self.current_step = 0
        self.results = {}
    
    def compose(self) -> ComposeResult:
        step = self.steps[self.current_step]
        total = len(self.steps)
        
        with Container(id="wizard-container"):
            # Progress header
            yield Static(
                f"Step {self.current_step + 1} / {total}",
                id="wizard-progress"
            )
            
            yield Static("─" * 40, id="wizard-divider")
            
            # Step content
            yield Static(f"\n{step['prompt']}\n", id="wizard-prompt")
            
            if step.get("type") == "confirm":
                yield Static("[green][Y][/green] Yes  [red][N][/red] No", id="wizard-confirm-options")
            else:
                yield Input(
                    placeholder=step.get("placeholder", ""),
                    password=step.get("password", False),
                    id="wizard-input"
                )
            
            # Navigation
            with Horizontal(id="wizard-buttons"):
                if self.current_step > 0:
                    yield Button("[dim]Back[/dim]", id="btn-back", variant="default")
                
                if self.current_step < total - 1:
                    yield Button("[green]Next (Enter)[/green]", id="btn-next", variant="success")
                else:
                    yield Button("[green]Finish (Enter)[/green]", id="btn-finish", variant="success")
                
                yield Button("[red]Cancel[/red]", id="btn-cancel", variant="error")
    
    def action_next_step(self) -> None:
        step = self.steps[self.current_step]
        
        if step.get("type") == "confirm":
            # Handle yes/no input differently
            self.results[step["key"]] = True  # Default to yes
            self._advance_step()
        else:
            input_widget = self.query_one("#wizard-input", Input)
            self.results[step["key"]] = input_widget.value
            self._advance_step()
    
    def _advance_step(self):
        self.current_step += 1
        
        if self.current_step >= len(self.steps):
            # Wizard complete
            if self.callback:
                self.callback(self.results)
            self.dismiss(self.results)
        else:
            # Refresh to show next step
            self.refresh()
    
    def action_cancel(self) -> None:
        self.dismiss(None)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next" or event.button.id == "btn-finish":
            self.action_next_step()
        elif event.button.id == "btn-back":
            self.current_step = max(0, self.current_step - 1)
            self.refresh()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
