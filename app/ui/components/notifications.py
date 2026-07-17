"""
Notification System for the Bybit Trading TUI
Colored notifications with icons for success, error, and warning messages.
"""

from textual.app import App
from typing import Optional


class NotificationManager:
    """
    Centralized notification manager for consistent UX.
    
    Usage:
        notify_success(app, "Order filled successfully!")
        notify_error(app, "API connection failed")
        notify_warning(app, "Low balance warning")
    """
    
    @staticmethod
    def notify(
        app: App,
        message: str,
        title: str = "",
        severity: str = "information",
        timeout: int = 3
    ):
        """Generic notification method."""
        if app:
            app.notify(message, title=title, severity=severity, timeout=timeout)
    
    @staticmethod
    def notify_success(app: App, message: str, title: str = "Success", timeout: int = 3):
        """Show a success notification with green color."""
        app.notify(
            f"✓ {message}",
            title=title,
            severity="information",
            timeout=timeout
        )
    
    @staticmethod
    def notify_error(app: App, message: str, title: str = "Error", timeout: int = 5):
        """Show an error notification with red color."""
        app.notify(
            f"✗ {message}",
            title=title,
            severity="error",
            timeout=timeout
        )
    
    @staticmethod
    def notify_warning(app: App, message: str, title: str = "Warning", timeout: int = 4):
        """Show a warning notification with yellow color."""
        app.notify(
            f"⚠ {message}",
            title=title,
            severity="warning",
            timeout=timeout
        )
    
    @staticmethod
    def notify_info(app: App, message: str, title: str = "Info", timeout: int = 3):
        """Show an information notification with blue/cyan color."""
        app.notify(
            f"ℹ {message}",
            title=title,
            severity="information",
            timeout=timeout
        )


# Convenience functions for direct usage
def notify_success(app: App, message: str, title: str = "Success", timeout: int = 3):
    """Show a success notification."""
    NotificationManager.notify_success(app, message, title, timeout)


def notify_error(app: App, message: str, title: str = "Error", timeout: int = 5):
    """Show an error notification."""
    NotificationManager.notify_error(app, message, title, timeout)


def notify_warning(app: App, message: str, title: str = "Warning", timeout: int = 4):
    """Show a warning notification."""
    NotificationManager.notify_warning(app, message, title, timeout)


def notify_info(app: App, message: str, title: str = "Info", timeout: int = 3):
    """Show an information notification."""
    NotificationManager.notify_info(app, message, title, timeout)


class NotificationStyles:
    """CSS styles for notification-like displays in static widgets."""
    
    SUCCESS = """
    .notification-success {
        background: $success-darken-3;
        color: $success-text;
        padding: 1 2;
        margin: 1 0;
        border: solid $success;
    }
    """
    
    ERROR = """
    .notification-error {
        background: $error-darken-3;
        color: $error-text;
        padding: 1 2;
        margin: 1 0;
        border: solid $error;
    }
    """
    
    WARNING = """
    .notification-warning {
        background: $warning-darken-3;
        color: $warning-text;
        padding: 1 2;
        margin: 1 0;
        border: solid $warning;
    }
    """
    
    INFO = """
    .notification-info {
        background: $primary-darken-3;
        color: $text;
        padding: 1 2;
        margin: 1 0;
        border: solid $primary;
    }
    """
    
    @classmethod
    def get_all(cls) -> str:
        """Return all notification styles combined."""
        return cls.SUCCESS + cls.ERROR + cls.WARNING + cls.INFO
