"""
styles.py - Glassmorphism theme for inCode NGX Configuration Tool

Frosted glass aesthetic inspired by iOS/macOS with:
- Semi-transparent backgrounds with backdrop blur
- Subtle borders and shadows  
- Layered depth perception
- Smooth transitions and animations
"""

# =============================================================================
# Color Palette - ADA Compliant with WCAG AA contrast ratios
# =============================================================================

COLORS = {
    # Background Colors (Dark Theme)
    "bg_primary": "#2a2a2a",       # Main app background (slightly darker for better contrast)
    "bg_secondary": "#1a1a1a",     # Secondary surfaces
    "bg_card": "#3C3C3C",          # Card backgrounds
    "bg_dark": "#1a1a1a",          # Darkest background
    "bg_medium": "#252525",        # Medium background
    "bg_light": "#3a3a3a",         # Light background
    "bg_lighter": "#454545",       # Lighter background
    
    # Glass Effects
    "glass_bg": "rgba(25, 25, 25, 0.85)",          # Glass background (more opaque)
    "widget_glass_bg": "rgba(55, 55, 55, 0.9)",   # Widget glass (more opaque)
    "glass_border": "rgba(255, 255, 255, 0.15)",  # Glass border
    "widget_glass_border": "rgba(255, 255, 255, 0.2)",  # Widget border
    
    # Text Colors - ADA Compliant (min 4.5:1 contrast on dark backgrounds)
    "text_primary": "#ffffff",                     # White - 12:1 contrast
    "text_secondary": "rgba(255, 255, 255, 0.85)", # ~#D9D9D9 - 10:1 contrast
    "text_muted": "rgba(180, 180, 180, 1.0)",     # #B4B4B4 - 7:1 contrast (was too dim)
    
    # Accent Colors - Brightened for better contrast
    "accent_primary": "#6BC5F8",    # Brighter blue for better contrast
    "accent_secondary": "#9DD5FA",  # Lighter accent
    "accent_blue": "#6BC5F8",
    "accent_green": "#34D399",      # Brighter green
    "accent_yellow": "#FBBF24",     # Brighter yellow
    "accent_orange": "#FB923C",     # Brighter orange
    "accent_red": "#F87171",        # Brighter red
    "accent_purple": "#A78BFA",     # Brighter purple
    
    # Semantic Colors - Brightened for accessibility
    "success": "#34D399",           # Brighter green
    "danger": "#F87171",            # Brighter red
    "warning": "#FBBF24",           # Brighter yellow
    "info": "#6BC5F8",              # Brighter blue
    
    # Border Colors
    "border_default": "rgba(255, 255, 255, 0.15)",
    "border_muted": "rgba(255, 255, 255, 0.08)",
    "border_accent": "#6BC5F8",
    
    # Special
    "highlight_row": "rgba(107, 197, 248, 0.15)",
    "selection": "rgba(107, 197, 248, 0.35)",
    
    # Shadows
    "shadow_sm": "0px 2px 8px rgba(0, 0, 0, 0.3)",
    "shadow_md": "0px 4px 16px rgba(0, 0, 0, 0.25)",
    "shadow_lg": "0px 8px 24px rgba(0, 0, 0, 0.35)",
}

# =============================================================================
# Gradient Background
# =============================================================================

BACKGROUND_GRADIENT = """
    qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #303030, stop:0.5 #252525, stop:1 #1a1a1a)
"""

# =============================================================================
# Main Application Stylesheet - Glassmorphism
# =============================================================================

MAIN_STYLESHEET = f"""
/* ============================================
   Global Styles - Glassmorphism Base
   ============================================ */

QMainWindow {{
    background: {BACKGROUND_GRADIENT};
}}

QWidget {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    font-family: Arial;
    font-size: 13px;
}}

/* ============================================
   Glass Panel Base - No borders for smooth rendering
   ============================================ */

QWidget#glassPanel {{
    background-color: rgba(55, 55, 55, 0.85);
    border: none;
    border-radius: 16px;
}}

/* ============================================
   Buttons - Solid backgrounds with hover effects
   ============================================ */

QPushButton {{
    background-color: rgba(70, 70, 70, 0.9);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 14px;
    min-height: 24px;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_primary']};
    color: white;
}}

QPushButton:pressed {{
    background-color: {COLORS['accent_secondary']};
    color: white;
}}

QPushButton:disabled {{
    background-color: rgba(50, 50, 50, 0.7);
    color: rgba(255, 255, 255, 0.45);
}}

QPushButton#primaryButton {{
    background-color: {COLORS['accent_primary']};
    color: white;
}}

QPushButton#primaryButton:hover {{
    background-color: {COLORS['accent_secondary']};
}}

QPushButton#primaryButton:pressed {{
    background-color: #70C0F0;
}}

QPushButton#primaryButton:disabled {{
    background-color: rgba(107, 197, 248, 0.35);
    color: rgba(255, 255, 255, 0.55);
}}

QPushButton#dangerButton {{
    background-color: {COLORS['danger']};
    color: white;
}}

QPushButton#dangerButton:hover {{
    background-color: #dc2626;
}}

QPushButton#dangerButton:pressed {{
    background-color: #b91c1c;
}}

/* ============================================
   Input Fields - Solid backgrounds, no border aliasing
   ============================================ */

QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: rgba(30, 30, 30, 0.95);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: {COLORS['selection']};
    font-size: 14px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    background-color: rgba(40, 40, 40, 0.95);
}}

QLineEdit:disabled, QSpinBox:disabled {{
    background-color: rgba(30, 30, 30, 0.7);
    color: rgba(160, 160, 160, 1.0);
}}

/* ============================================
   ComboBox (Dropdowns) - Solid backgrounds
   ============================================ */

QComboBox {{
    background-color: rgba(30, 30, 30, 0.95);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    min-width: 140px;
    font-size: 14px;
}}

QComboBox:hover {{
    background-color: rgba(40, 40, 40, 0.95);
}}

QComboBox:focus {{
    background-color: rgba(40, 40, 40, 0.95);
}}

QComboBox::drop-down {{
    border: none;
    width: 32px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: rgba(50, 50, 50, 0.98);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 8px;
    selection-background-color: {COLORS['accent_primary']};
    outline: none;
    padding: 6px;
}}

QComboBox QAbstractItemView::item {{
    padding: 10px 14px;
    border-radius: 8px;
    margin: 2px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: rgba(96, 176, 225, 0.2);
}}

/* ============================================
   List Widget - Solid backgrounds
   ============================================ */

QListWidget {{
    background-color: rgba(30, 30, 30, 0.9);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 12px;
    padding: 8px;
    outline: none;
}}

QListWidget::item {{
    padding: 12px 16px;
    border-radius: 6px;
    margin: 3px 0;
}}

QListWidget::item:selected {{
    background-color: {COLORS['accent_primary']};
    color: white;
}}

QListWidget::item:hover:!selected {{
    background-color: rgba(96, 176, 225, 0.15);
}}

/* ============================================
   Text Edit / Log Area - Solid backgrounds
   ============================================ */

QTextEdit, QPlainTextEdit {{
    background-color: rgba(25, 25, 25, 0.95);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-family: 'Monaco', 'Consolas', monospace;
    font-size: 12px;
    selection-background-color: {COLORS['selection']};
}}

/* ============================================
   Labels
   ============================================ */

QLabel {{
    color: {COLORS['text_primary']};
    background-color: transparent;
}}

QLabel#headerLabel {{
    font-size: 22px;
    font-weight: 700;
    color: {COLORS['text_primary']};
    padding: 8px 0;
}}

QLabel#subHeaderLabel {{
    font-size: 15px;
    font-weight: 500;
    color: {COLORS['text_secondary']};
}}

QLabel#statusLabel {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
    padding: 6px 12px;
    border-radius: 8px;
    background-color: rgba(60, 60, 60, 0.5);
}}

/* ============================================
   Group Box - Solid backgrounds
   ============================================ */

QGroupBox {{
    background-color: rgba(55, 55, 55, 0.8);
    border: none;
    border-radius: 12px;
    margin-top: 20px;
    padding: 20px;
    padding-top: 32px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 12px;
    color: {COLORS['accent_primary']};
    background-color: transparent;
    font-size: 14px;
}}

/* ============================================
   Check Box - High contrast solid backgrounds
   ============================================ */

QCheckBox {{
    color: {COLORS['text_primary']};
    spacing: 10px;
    font-size: 14px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: none;
    background-color: rgba(90, 90, 90, 0.95);
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent_primary']};
}}

QCheckBox::indicator:hover {{
    background-color: rgba(110, 110, 110, 1.0);
}}

QCheckBox::indicator:checked:hover {{
    background-color: {COLORS['accent_secondary']};
}}

/* ============================================
   Slider - Solid backgrounds
   ============================================ */

QSlider::groove:horizontal {{
    height: 6px;
    background-color: rgba(50, 50, 50, 0.9);
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background-color: {COLORS['accent_primary']};
    border-radius: 9px;
    border: none;
}}

QSlider::handle:horizontal:hover {{
    background-color: {COLORS['accent_secondary']};
}}

QSlider::sub-page:horizontal {{
    background-color: {COLORS['accent_primary']};
    border-radius: 3px;
}}

/* ============================================
   Scroll Bar - Minimal style
   ============================================ */

QScrollBar:vertical {{
    background-color: transparent;
    width: 10px;
    border-radius: 5px;
    margin: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 5px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: rgba(255, 255, 255, 0.35);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 10px;
    border-radius: 5px;
    margin: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 5px;
    min-width: 40px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: rgba(255, 255, 255, 0.35);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ============================================
   Progress Bar - Solid backgrounds
   ============================================ */

QProgressBar {{
    background-color: rgba(40, 40, 40, 0.9);
    border: none;
    border-radius: 6px;
    height: 14px;
    text-align: center;
    color: white;
    font-weight: 600;
    font-size: 11px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_primary']};
    border-radius: 6px;
}}

/* ============================================
   Menu - Solid backgrounds
   ============================================ */

QMenuBar {{
    background-color: rgba(30, 30, 30, 0.95);
    color: {COLORS['text_primary']};
    border: none;
    padding: 6px;
}}

QMenuBar::item:selected {{
    background-color: rgba(96, 176, 225, 0.2);
    border-radius: 4px;
}}

QMenu {{
    background-color: rgba(45, 45, 45, 0.98);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 8px;
    padding: 8px;
}}

QMenu::item {{
    padding: 10px 20px;
    border-radius: 4px;
    margin: 2px;
}}

QMenu::item:selected {{
    background-color: {COLORS['accent_primary']};
    color: white;
}}

QMenu::separator {{
    height: 1px;
    background-color: rgba(255, 255, 255, 0.1);
    margin: 6px 12px;
}}

/* ============================================
   Tool Tip - Solid backgrounds
   ============================================ */

QToolTip {{
    background-color: rgba(45, 45, 45, 0.98);
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}}

/* ============================================
   Frame
   ============================================ */

QFrame#separator {{
    background-color: rgba(255, 255, 255, 0.1);
    max-height: 1px;
}}

QFrame#glassCard {{
    background-color: rgba(55, 55, 55, 0.85);
    border: none;
    border-radius: 16px;
    padding: 24px;
}}

/* ============================================
   Scroll Area - Transparent
   ============================================ */

QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ============================================
   Tab Widget - Solid backgrounds
   ============================================ */

QTabWidget::pane {{
    border: none;
    border-radius: 12px;
    background-color: rgba(55, 55, 55, 0.7);
    padding: 12px;
}}

QTabBar::tab {{
    background-color: rgba(50, 50, 50, 0.7);
    color: {COLORS['text_secondary']};
    padding: 12px 24px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}}

QTabBar::tab:selected {{
    background-color: rgba(70, 70, 70, 0.9);
    color: {COLORS['text_primary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: rgba(96, 176, 225, 0.15);
    color: {COLORS['text_primary']};
}}

/* ============================================
   Special Component Styles
   ============================================ */

QWidget#connectionStatus {{
    background-color: rgba(55, 55, 55, 0.8);
    border: none;
    border-radius: 12px;
    padding: 20px;
}}

QLabel#connectionStatusConnected {{
    color: {COLORS['accent_green']};
    font-weight: 700;
    font-size: 15px;
}}

QLabel#connectionStatusDisconnected {{
    color: {COLORS['text_muted']};
    font-weight: 600;
    font-size: 15px;
}}
"""

# =============================================================================
# Icon/Symbol Characters (Unicode)
# =============================================================================

ICONS = {
    "connected": "●",
    "disconnected": "○",
    "input_configured": "▶",
    "input_empty": "▷",
    "check": "✓",
    "cross": "✕",
    "warning": "⚠",
    "info": "ℹ",
    "arrow_right": "→",
    "arrow_down": "↓",
    "gear": "⚙",
    "power": "⏻",
    "refresh": "↻",
    "save": "💾",
    "folder": "📁",
    "file": "📄",
    "trash": "🗑",
    "edit": "✎",
    "plus": "+",
    "minus": "−",
}

# =============================================================================
# Glass Panel Style Helpers
# =============================================================================

def glass_panel_style(border_radius: int = 16) -> str:
    """Generate a solid panel style string - no borders for smooth corners"""
    return f"""
        background-color: rgba(55, 55, 55, 0.85);
        border: none;
        border-radius: {border_radius}px;
    """

def accent_button_style() -> str:
    """Generate accent button style - no borders for smooth corners"""
    return f"""
        background-color: {COLORS['accent_primary']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
    """
