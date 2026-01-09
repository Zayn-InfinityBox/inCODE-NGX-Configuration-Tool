"""
view_mode.py - View mode system for inCODE NGX Configuration Tool

Defines the three view modes and a manager singleton that emits signals
when the mode changes, allowing all UI components to update.
"""

from enum import Enum, auto
from PyQt6.QtCore import QObject, pyqtSignal


class ViewMode(Enum):
    """
    Application view modes that control UI complexity and available features.
    
    BASIC: Simplified interface for common operations
        - Pre-configured "scripted" settings
        - Limited customization options
        - Ideal for standard installations
    
    ADVANCED: Full feature set with some restrictions
        - All configuration options visible
        - Some advanced features may be hidden
        - Default mode for experienced users
    
    ADMIN: Full unrestricted access (password protected)
        - All features and settings exposed
        - System-level configuration options
        - For factory/developer use
    """
    BASIC = auto()
    ADVANCED = auto()
    ADMIN = auto()


class ViewModeManager(QObject):
    """
    Singleton manager for application view mode state.
    Emits signals when view mode changes so all UI components can update.
    """
    
    # Signal emitted when view mode changes
    view_mode_changed = pyqtSignal(ViewMode)
    
    # Admin password (in production, this would be more secure)
    ADMIN_PASSWORD = "admin"
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._current_mode = ViewMode.ADVANCED  # Default to Advanced
        self._initialized = True
    
    @property
    def current_mode(self) -> ViewMode:
        return self._current_mode
    
    @property
    def is_basic(self) -> bool:
        return self._current_mode == ViewMode.BASIC
    
    @property
    def is_advanced(self) -> bool:
        return self._current_mode == ViewMode.ADVANCED
    
    @property
    def is_admin(self) -> bool:
        return self._current_mode == ViewMode.ADMIN
    
    def set_mode(self, mode: ViewMode, password: str = None) -> bool:
        """
        Set the view mode. Admin mode requires password.
        Returns True if mode was successfully changed.
        """
        if mode == ViewMode.ADMIN:
            if password != self.ADMIN_PASSWORD:
                return False
        
        if mode != self._current_mode:
            self._current_mode = mode
            self.view_mode_changed.emit(mode)
        return True
    
    def verify_admin_password(self, password: str) -> bool:
        """Check if password is correct for admin mode."""
        return password == self.ADMIN_PASSWORD


# Global instance - created once, shared across all modules
view_mode_manager = ViewModeManager()

