"""
Progress Indicators for the Bybit Trading TUI
Spinners and progress bars for loading states.
"""

from textual.widgets import Static
from textual.app import ComposeResult
import asyncio


class SpinnerWidget(Static):
    """
    Animated spinner widget for loading states.
    
    Usage:
        spinner = SpinnerWidget("Connecting to API...")
        # Call spinner.start() to begin animation
        # Call spinner.stop() to stop animation
    """
    
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, message: str = "Loading...", id: str = None):
        super().__init__(id=id)
        self.message = message
        self._is_running = False
        self._spinner_index = 0
        self._task = None
    
    def compose(self) -> ComposeResult:
        yield Static(self._render(), id="spinner-display")
    
    def _render(self) -> str:
        spinner = self.SPINNER_FRAMES[self._spinner_index]
        return f"[cyan]{spinner}[/cyan] {self.message}"
    
    def start(self):
        """Start the spinner animation."""
        self._is_running = True
        self._task = asyncio.create_task(self._animate())
    
    def stop(self):
        """Stop the spinner animation."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        self.update(f"✓ {self.message}")
    
    async def _animate(self):
        """Animation loop."""
        try:
            while self._is_running:
                await asyncio.sleep(0.1)
                self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
                self.refresh()
        except asyncio.CancelledError:
            pass
    
    def set_message(self, message: str):
        """Update the spinner message."""
        self.message = message
        self.refresh()


class ProgressBar(Static):
    """
    Progress bar widget with percentage display.
    
    Usage:
        progress = ProgressBar(total=100)
        progress.update_progress(50)  # 50%
    """
    
    def __init__(
        self,
        total: int = 100,
        message: str = "Loading...",
        width: int = 30,
        id: str = None
    ):
        super().__init__(id=id)
        self.total = total
        self.current = 0
        self.message = message
        self.width = width
    
    def compose(self) -> ComposeResult:
        yield Static(self._render(), id="progress-display")
    
    def _render(self) -> str:
        percentage = (self.current / self.total * 100) if self.total > 0 else 0
        
        filled = int(self.width * percentage / 100)
        empty = self.width - filled
        
        # Create progress bar
        bar = "█" * filled + "░" * empty
        
        # Color based on completion
        if percentage >= 100:
            color = "green"
        elif percentage >= 50:
            color = "yellow"
        else:
            color = "cyan"
        
        return f"{self.message}\n[{color}][{bar}] {percentage:.1f}%[/{color}]"
    
    def update_progress(self, current: int, message: str = None):
        """Update progress value and optionally change message."""
        self.current = current
        if message:
            self.message = message
        self.refresh()
    
    def advance(self, amount: int = 1):
        """Advance progress by specified amount."""
        self.current = min(self.total, self.current + amount)
        self.refresh()
    
    def reset(self):
        """Reset progress to zero."""
        self.current = 0
        self.refresh()
    
    def set_complete(self):
        """Mark progress as complete."""
        self.current = self.total
        self.message = "Complete!"
        self.refresh()


class LoadingScreen(Static):
    """
    Full-screen loading indicator with spinner and progress.
    
    Usage:
        loading = LoadingScreen("Initializing system...", total_steps=5)
        loading.update_step(2, "Loading market data...")
    """
    
    def __init__(
        self,
        message: str = "Loading...",
        total_steps: int = 100,
        id: str = None
    ):
        super().__init__(id=id)
        self.message = message
        self.total_steps = total_steps
        self.current_step = 0
    
    def compose(self) -> ComposeResult:
        with Container(id="loading-container"):
            yield Static(
                "╔══════════════════════════════╗\n       [cyan bold]LOADING[/cyan bold]        \n╚══════════════════════════════╝",
                id="loading-title"
            )
            
            yield SpinnerWidget(self.message, id="loading-spinner")
            
            yield ProgressBar(
                total=self.total_steps,
                message="",
                id="loading-progress"
            )
    
    def update_step(self, step: int, message: str = None):
        """Update current step and optionally change message."""
        self.current_step = step
        if message:
            self.message = message
        
        # Update child widgets
        if spinner := self.query_one("#loading-spinner", SpinnerWidget):
            spinner.set_message(self.message)
        
        if progress := self.query_one("#loading-progress", ProgressBar):
            progress.update_progress(step)
    
    def set_complete(self):
        """Mark loading as complete."""
        self.current_step = self.total_steps
        
        if spinner := self.query_one("#loading-spinner", SpinnerWidget):
            spinner.stop()
        
        if progress := self.query_one("#loading-progress", ProgressBar):
            progress.set_complete()


# Import Container here to avoid circular imports
from textual.containers import Container
