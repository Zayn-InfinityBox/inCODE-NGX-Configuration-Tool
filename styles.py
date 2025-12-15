"""
styles.py - Dark theme and styling for inCode NGX Configuration Tool

Professional automotive/industrial aesthetic with high contrast and clear iconography.
"""

# =============================================================================
# Color Palette
# =============================================================================

COLORS = {
    # Base colors
    "bg_dark": "#0d1117",
    "bg_medium": "#161b22",
    "bg_light": "#21262d",
    "bg_lighter": "#30363d",
    
    # Text colors
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#6e7681",
    
    # Accent colors
    "accent_blue": "#58a6ff",
    "accent_green": "#3fb950",
    "accent_yellow": "#d29922",
    "accent_orange": "#db6d28",
    "accent_red": "#f85149",
    "accent_purple": "#a371f7",
    
    # Status colors
    "status_success": "#238636",
    "status_warning": "#9e6a03",
    "status_error": "#da3633",
    "status_info": "#1f6feb",
    
    # Border colors
    "border_default": "#30363d",
    "border_muted": "#21262d",
    "border_accent": "#58a6ff",
    
    # Special
    "highlight_row": "#1f2937",
    "selection": "#264f78",
}

# =============================================================================
# Main Application Stylesheet
# =============================================================================

MAIN_STYLESHEET = f"""
/* ============================================
   Global Styles
   ============================================ */

QMainWindow {{
    background-color: {COLORS['bg_dark']};
}}

QWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    font-family: 'Helvetica Neue', 'Arial', sans-serif;
    font-size: 13px;
}}

/* ============================================
   Tab Widget
   ============================================ */

QTabWidget::pane {{
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    background-color: {COLORS['bg_medium']};
    padding: 8px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_secondary']};
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_primary']};
    border-bottom: 2px solid {COLORS['accent_blue']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_lighter']};
    color: {COLORS['text_primary']};
}}

/* ============================================
   Buttons
   ============================================ */

QPushButton {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_lighter']};
    border-color: {COLORS['border_accent']};
}}

QPushButton:pressed {{
    background-color: {COLORS['selection']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_muted']};
    border-color: {COLORS['border_muted']};
}}

QPushButton#primaryButton {{
    background-color: {COLORS['status_success']};
    border-color: {COLORS['status_success']};
}}

QPushButton#primaryButton:hover {{
    background-color: #2ea043;
}}

QPushButton#dangerButton {{
    background-color: {COLORS['status_error']};
    border-color: {COLORS['status_error']};
}}

QPushButton#dangerButton:hover {{
    background-color: #b62324;
}}

/* ============================================
   Input Fields
   ============================================ */

QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {COLORS['selection']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['accent_blue']};
    outline: none;
}}

QLineEdit:disabled, QSpinBox:disabled {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_muted']};
}}

/* ============================================
   ComboBox (Dropdowns)
   ============================================ */

QComboBox {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {COLORS['border_accent']};
}}

QComboBox:focus {{
    border-color: {COLORS['accent_blue']};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    selection-background-color: {COLORS['selection']};
    outline: none;
}}

/* ============================================
   List Widget
   ============================================ */

QListWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-radius: 4px;
    margin: 2px 0;
}}

QListWidget::item:selected {{
    background-color: {COLORS['selection']};
    color: {COLORS['text_primary']};
}}

QListWidget::item:hover:!selected {{
    background-color: {COLORS['highlight_row']};
}}

/* ============================================
   Tree Widget
   ============================================ */

QTreeWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}

QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}

QTreeWidget::item:selected {{
    background-color: {COLORS['selection']};
}}

QTreeWidget::item:hover:!selected {{
    background-color: {COLORS['highlight_row']};
}}

QTreeWidget::branch {{
    background-color: transparent;
}}

/* ============================================
   Text Edit / Log Area
   ============================================ */

QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 6px;
    padding: 8px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
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
    font-size: 18px;
    font-weight: 600;
    color: {COLORS['text_primary']};
    padding: 8px 0;
}}

QLabel#subHeaderLabel {{
    font-size: 14px;
    font-weight: 500;
    color: {COLORS['text_secondary']};
}}

QLabel#statusLabel {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
    padding: 4px 8px;
    border-radius: 4px;
    background-color: {COLORS['bg_light']};
}}

/* ============================================
   Group Box
   ============================================ */

QGroupBox {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
    padding-top: 24px;
    font-weight: 500;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    color: {COLORS['accent_blue']};
    background-color: {COLORS['bg_medium']};
}}

/* ============================================
   Check Box
   ============================================ */

QCheckBox {{
    color: {COLORS['text_primary']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {COLORS['border_default']};
    background-color: {COLORS['bg_dark']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent_blue']};
    border-color: {COLORS['accent_blue']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['accent_blue']};
}}

/* ============================================
   Radio Button
   ============================================ */

QRadioButton {{
    color: {COLORS['text_primary']};
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid {COLORS['border_default']};
    background-color: {COLORS['bg_dark']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['accent_blue']};
    border-color: {COLORS['accent_blue']};
}}

/* ============================================
   Slider
   ============================================ */

QSlider::groove:horizontal {{
    height: 6px;
    background-color: {COLORS['bg_lighter']};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background-color: {COLORS['accent_blue']};
    border-radius: 9px;
}}

QSlider::handle:horizontal:hover {{
    background-color: #79b8ff;
}}

QSlider::sub-page:horizontal {{
    background-color: {COLORS['accent_blue']};
    border-radius: 3px;
}}

/* ============================================
   Scroll Bar
   ============================================ */

QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['bg_lighter']};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_muted']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {COLORS['bg_dark']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['bg_lighter']};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['text_muted']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ============================================
   Splitter
   ============================================ */

QSplitter::handle {{
    background-color: {COLORS['border_default']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* ============================================
   Progress Bar
   ============================================ */

QProgressBar {{
    background-color: {COLORS['bg_light']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_blue']};
    border-radius: 4px;
}}

/* ============================================
   Menu
   ============================================ */

QMenuBar {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border-bottom: 1px solid {COLORS['border_default']};
    padding: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['bg_light']};
    border-radius: 4px;
}}

QMenu {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['selection']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLORS['border_default']};
    margin: 4px 8px;
}}

/* ============================================
   Status Bar
   ============================================ */

QStatusBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border_default']};
    padding: 4px 8px;
}}

/* ============================================
   Tool Tip
   ============================================ */

QToolTip {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 4px;
    padding: 6px 10px;
}}

/* ============================================
   Frame
   ============================================ */

QFrame#separator {{
    background-color: {COLORS['border_default']};
    max-height: 1px;
}}

QFrame#card {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 8px;
    padding: 16px;
}}

/* ============================================
   Specific Component Styles
   ============================================ */

QWidget#inputListPanel {{
    background-color: {COLORS['bg_dark']};
    border-right: 1px solid {COLORS['border_default']};
}}

QWidget#inputConfigPanel {{
    background-color: {COLORS['bg_medium']};
}}

QWidget#caseCard {{
    background-color: {COLORS['bg_light']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 8px;
    padding: 12px;
}}

QWidget#caseCardEnabled {{
    background-color: {COLORS['bg_light']};
    border: 1px solid {COLORS['accent_blue']};
    border-radius: 8px;
    padding: 12px;
}}

QWidget#connectionStatus {{
    background-color: {COLORS['bg_light']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 8px;
    padding: 16px;
}}

QLabel#connectionStatusConnected {{
    color: {COLORS['accent_green']};
    font-weight: 600;
}}

QLabel#connectionStatusDisconnected {{
    color: {COLORS['text_muted']};
    font-weight: 600;
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

