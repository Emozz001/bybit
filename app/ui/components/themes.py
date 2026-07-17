"""
Theme System for the Bybit Trading TUI
Support for multiple color themes with instant switching.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Theme:
    """Represents a color theme configuration."""
    
    name: str
    primary: str
    secondary: str
    success: str
    error: str
    warning: str
    background: str
    surface: str
    text: str
    text_dim: str
    
    # CSS variables for Textual
    def get_css_variables(self) -> Dict[str, str]:
        return {
            "--primary": self.primary,
            "--secondary": self.secondary,
            "--success": self.success,
            "--error": self.error,
            "--warning": self.warning,
            "--background": self.background,
            "--surface": self.surface,
            "--text": self.text,
            "--text-dim": self.text_dim,
        }
    
    def get_css_string(self) -> str:
        """Generate CSS string for this theme."""
        vars = self.get_css_variables()
        css_lines = [":root {"]
        for key, value in vars.items():
            css_lines.append(f"    {key}: {value};")
        css_lines.append("}")
        return "\n".join(css_lines)


# Predefined themes
THEMES = {
    "dark": Theme(
        name="Dark",
        primary="#0066cc",
        secondary="#6633aa",
        success="#00aa55",
        error="#dd3333",
        warning="#ffaa00",
        background="#1a1a2e",
        surface="#16213e",
        text="#ffffff",
        text_dim="#888888",
    ),
    
    "light": Theme(
        name="Light",
        primary="#0066cc",
        secondary="#6633aa",
        success="#00aa55",
        error="#dd3333",
        warning="#ffaa00",
        background="#f5f5f5",
        surface="#ffffff",
        text="#1a1a1a",
        text_dim="#666666",
    ),
    
    "cyber": Theme(
        name="Cyber",
        primary="#00ffff",
        secondary="#ff00ff",
        success="#00ff00",
        error="#ff0000",
        warning="#ffff00",
        background="#0d0d0d",
        surface="#1a1a1a",
        text="#00ff00",
        text_dim="#008800",
    ),
    
    "monochrome": Theme(
        name="Monochrome",
        primary="#ffffff",
        secondary="#cccccc",
        success="#ffffff",
        error="#ffffff",
        warning="#ffffff",
        background="#000000",
        surface="#1a1a1a",
        text="#ffffff",
        text_dim="#666666",
    ),
    
    "ocean": Theme(
        name="Ocean",
        primary="#0077be",
        secondary="#00a896",
        success="#00b894",
        error="#d63031",
        warning="#fdcb6e",
        background="#0c1929",
        surface="#152238",
        text="#dfe6e9",
        text_dim="#636e72",
    ),
    
    "forest": Theme(
        name="Forest",
        primary="#2d5016",
        secondary="#4a7c23",
        success="#56ab2f",
        error="#a83232",
        warning="#d4a017",
        background="#1a2f1a",
        surface="#233823",
        text="#c8d8c8",
        text_dim="#6b8c6b",
    ),
}


class ThemeManager:
    """
    Manages application themes with persistence.
    
    Usage:
        manager = ThemeManager()
        manager.set_theme("dark")
        app.theme = manager.current_theme
    """
    
    DEFAULT_THEME = "dark"
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._current_theme_name = self.DEFAULT_THEME
        self._load_saved_theme()
    
    @property
    def current_theme(self) -> Theme:
        """Get the current theme object."""
        return THEMES.get(self._current_theme_name, THEMES[self.DEFAULT_THEME])
    
    @property
    def current_theme_name(self) -> str:
        """Get the current theme name."""
        return self._current_theme_name
    
    def set_theme(self, theme_name: str) -> bool:
        """
        Set the current theme.
        
        Returns True if theme was found and set, False otherwise.
        """
        if theme_name in THEMES:
            self._current_theme_name = theme_name
            self._save_theme()
            return True
        return False
    
    def list_themes(self) -> list:
        """Return list of available theme names."""
        return list(THEMES.keys())
    
    def get_theme_info(self, theme_name: str) -> Optional[Theme]:
        """Get theme object by name."""
        return THEMES.get(theme_name)
    
    def _load_saved_theme(self):
        """Load saved theme from storage."""
        if self.storage_path:
            try:
                import json
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    saved_theme = data.get('theme', self.DEFAULT_THEME)
                    if saved_theme in THEMES:
                        self._current_theme_name = saved_theme
            except (FileNotFoundError, json.JSONDecodeError):
                pass
    
    def _save_theme(self):
        """Save current theme to storage."""
        if self.storage_path:
            try:
                import json
                from pathlib import Path
                Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_path, 'w') as f:
                    json.dump({'theme': self._current_theme_name}, f)
            except Exception:
                pass
    
    def get_css_for_theme(self, theme_name: str) -> str:
        """Get CSS string for a specific theme."""
        theme = THEMES.get(theme_name, THEMES[self.DEFAULT_THEME])
        return theme.get_css_string()


# Global theme manager instance
_global_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get or create the global theme manager."""
    global _global_theme_manager
    if _global_theme_manager is None:
        _global_theme_manager = ThemeManager()
    return _global_theme_manager


def get_theme(theme_name: str = None) -> Theme:
    """Get a theme by name or the current theme."""
    if theme_name:
        return THEMES.get(theme_name, THEMES["dark"])
    return get_theme_manager().current_theme


def set_theme(theme_name: str) -> bool:
    """Set the global current theme."""
    return get_theme_manager().set_theme(theme_name)


# Common CSS shared across all themes
BASE_CSS = """
Screen {
    background: $surface;
}

#main-banner, #page-banner {
    width: 100%;
    content-align: center middle;
    margin: 1 0;
    text-align: center;
}

.stat-card {
    width: auto;
    height: auto;
    padding: 1 2;
    margin: 0 1;
    border: solid $primary-darken-2;
    background: $surface-darken-2;
}

#dialog-container {
    width: 60;
    height: auto;
    align: center middle;
    border: solid $primary;
    padding: 2 3;
    background: $surface;
}

#form-container {
    width: 70;
    height: auto;
    align: center middle;
    border: solid $primary;
    padding: 2 3;
    background: $surface;
}

.form-label {
    margin-top: 1;
    margin-bottom: 0;
}

#dialog-buttons, #form-buttons, #wizard-buttons {
    margin-top: 2;
    align: center middle;
}

#loading-container {
    width: 60;
    height: auto;
    align: center middle;
    padding: 2;
}

#table-content {
    width: 100%;
    height: 100%;
}

.notification-success {
    background: $success-darken-3;
    color: $success-text;
    padding: 1 2;
    margin: 1 0;
    border: solid $success;
}

.notification-error {
    background: $error-darken-3;
    color: $error-text;
    padding: 1 2;
    margin: 1 0;
    border: solid $error;
}

.notification-warning {
    background: $warning-darken-3;
    color: $warning-text;
    padding: 1 2;
    margin: 1 0;
    border: solid $warning;
}

.notification-info {
    background: $primary-darken-3;
    color: $text;
    padding: 1 2;
    margin: 1 0;
    border: solid $primary;
}
"""
