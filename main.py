"""
main.py - inCODE NGX Configuration Tool
Single-page wizard application for MASTERCELL configuration
"""

import sys
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFrame, QProgressBar,
    QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QColor, QPalette, QLinearGradient, QPainter

from styles import MAIN_STYLESHEET, COLORS, ICONS, BACKGROUND_GRADIENT
from can_interface import CANInterface
from config_data import FullConfiguration

# Import wizard pages
from pages.welcome_page import WelcomePage
from pages.connection_page import ConnectionPage
from pages.inputs_page import InputsPage
from pages.confirmation_page import ConfirmationPage
from pages.write_page import WritePage


class WizardNavigation(QWidget):
    """Bottom navigation bar for wizard - glass style"""
    
    back_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.setMinimumWidth(140)
        self.back_btn.setMinimumHeight(48)
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(70, 70, 70, 0.9);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_primary']};
            }}
            QPushButton:disabled {{
                background-color: rgba(50, 50, 50, 0.7);
                color: rgba(255, 255, 255, 0.45);
            }}
        """)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self.back_btn)
        
        layout.addStretch()
        
        # Step indicator with pill style
        self.step_label = QLabel("Step 1 of 5")
        self.step_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            background-color: rgba(50, 50, 50, 0.8);
            padding: 8px 20px;
            border-radius: 16px;
            font-size: 13px;
        """)
        layout.addWidget(self.step_label)
        
        layout.addStretch()
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.setMinimumWidth(160)
        self.next_btn.setMinimumHeight(48)
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_primary']};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_secondary']};
            }}
            QPushButton:disabled {{
                background-color: rgba(107, 197, 248, 0.35);
                color: rgba(255, 255, 255, 0.55);
            }}
        """)
        self.next_btn.clicked.connect(self.next_clicked.emit)
        layout.addWidget(self.next_btn)
    
    def set_step(self, current: int, total: int):
        self.step_label.setText(f"Step {current} of {total}")
        self.back_btn.setEnabled(current > 1)
    
    def set_next_text(self, text: str):
        self.next_btn.setText(text)
    
    def set_next_enabled(self, enabled: bool):
        self.next_btn.setEnabled(enabled)


class StepIndicator(QWidget):
    """Visual step indicator at top of wizard - glass style"""
    
    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self.steps = steps
        self.current_step = 0
        self.step_labels = []
        self.connectors = []
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 24, 48, 24)
        layout.setSpacing(0)
        
        for i, step_name in enumerate(self.steps):
            # Step container
            step_widget = QWidget()
            step_widget.setStyleSheet("background-color: transparent;")
            step_layout = QVBoxLayout(step_widget)
            step_layout.setSpacing(8)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Circle with number - larger for better visibility
            circle = QLabel(str(i + 1))
            circle.setFixedSize(40, 40)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setObjectName(f"stepCircle_{i}")
            step_layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
            
            # Step name
            label = QLabel(step_name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName(f"stepLabel_{i}")
            step_layout.addWidget(label)
            
            self.step_labels.append((circle, label))
            layout.addWidget(step_widget)
            
            # Connector line (except after last step)
            if i < len(self.steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(3)
                line.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 1px;")
                self.connectors.append(line)
                layout.addWidget(line, 1)
        
        self._update_styles()
    
    def set_step(self, step: int):
        self.current_step = step
        self._update_styles()
    
    def _update_styles(self):
        for i, (circle, label) in enumerate(self.step_labels):
            if i < self.current_step:
                # Completed - green with check
                circle.setText("✓")
                circle.setStyleSheet(f"""
                    QLabel {{
                        background-color: {COLORS['success']};
                        color: white;
                        border-radius: 20px;
                        font-weight: bold;
                        font-size: 16px;
                    }}
                """)
                label.setStyleSheet(f"QLabel {{ color: {COLORS['success']}; background: transparent; font-size: 12px; font-weight: 600; }}")
            elif i == self.current_step:
                # Current - accent color
                circle.setText(str(i + 1))
                circle.setStyleSheet(f"""
                    QLabel {{
                        background-color: {COLORS['accent_primary']};
                        color: white;
                        border-radius: 20px;
                        font-weight: bold;
                        font-size: 16px;
                    }}
                """)
                label.setStyleSheet(f"QLabel {{ color: white; background: transparent; font-size: 12px; font-weight: 700; }}")
            else:
                # Future - muted
                circle.setText(str(i + 1))
                circle.setStyleSheet(f"""
                    QLabel {{
                        background-color: rgba(60, 60, 60, 0.8);
                        color: rgba(255,255,255,0.5);
                        border-radius: 20px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        font-size: 14px;
                    }}
                """)
                label.setStyleSheet(f"QLabel {{ color: rgba(255,255,255,0.5); background: transparent; font-size: 12px; }}")
        
        # Update connector lines
        for i, line in enumerate(self.connectors):
            if i < self.current_step:
                line.setStyleSheet(f"background-color: {COLORS['success']}; border-radius: 1px;")
            else:
                line.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 1px;")


class MainWindow(QMainWindow):
    """Main application window with wizard flow"""
    
    STEPS = ["Welcome", "Connect", "Configure", "Review", "Write"]
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("inCODE NGX Configuration Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        # Core state
        self.can_interface = CANInterface()
        self.configuration = FullConfiguration()
        self.backup_config = None
        
        # Ensure directories exist
        self._ensure_directories()
        
        self._setup_ui()
        self._connect_signals()
    
    def _ensure_directories(self):
        """Create backup and config directories if they don't exist"""
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.backup_dir = os.path.join(base_path, "backups")
        self.config_dir = os.path.join(base_path, "configurations")
        
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header with glass effect
        header = QWidget()
        header.setStyleSheet(f"""
            background-color: rgba(25, 25, 25, 0.85);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 20, 32, 20)
        
        # App title (left side)
        title = QLabel("inCODE NGX")
        title.setFont(QFont("", 24, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Configuration Tool")
        subtitle.setFont(QFont("", 14))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-left: 12px;")
        header_layout.addWidget(subtitle)
        
        header_layout.addStretch()
        
        # Right side - Logo and Infinitybox branding
        logo_container = QWidget()
        logo_container.setStyleSheet("background: transparent;")
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(16)
        
        # Large logo icon
        logo_icon = QLabel("⬡")
        logo_icon.setFont(QFont("", 52))
        logo_icon.setStyleSheet(f"color: {COLORS['accent_primary']}; background: transparent;")
        logo_layout.addWidget(logo_icon)
        
        # Infinitybox text
        brand_name = QLabel("Infinitybox")
        brand_name.setFont(QFont("", 24, QFont.Weight.Bold))
        brand_name.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        logo_layout.addWidget(brand_name)
        
        header_layout.addWidget(logo_container)
        
        main_layout.addWidget(header)
        
        # Step indicator
        self.step_indicator = StepIndicator(self.STEPS)
        main_layout.addWidget(self.step_indicator)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border_default']};")
        main_layout.addWidget(sep)
        
        # Stacked widget for pages
        self.pages = QStackedWidget()
        
        # Create pages
        self.welcome_page = WelcomePage(self.configuration)
        self.connection_page = ConnectionPage(self.can_interface)
        self.inputs_page = InputsPage(self.configuration)
        self.confirmation_page = ConfirmationPage(self.configuration)
        self.write_page = WritePage(self.can_interface, self.configuration, 
                                     self.backup_dir, self.config_dir)
        
        self.pages.addWidget(self.welcome_page)      # 0
        self.pages.addWidget(self.connection_page)   # 1
        self.pages.addWidget(self.inputs_page)       # 2
        self.pages.addWidget(self.confirmation_page) # 3
        self.pages.addWidget(self.write_page)        # 4
        
        main_layout.addWidget(self.pages, 1)
        
        # Bottom navigation with glass effect
        self.nav = WizardNavigation()
        self.nav.setStyleSheet(f"""
            background-color: rgba(25, 25, 25, 0.85);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        """)
        main_layout.addWidget(self.nav)
        
        # Apply stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Initial state
        self._update_navigation()
    
    def _connect_signals(self):
        self.nav.back_clicked.connect(self._go_back)
        self.nav.next_clicked.connect(self._go_next)
        
        # Page-specific signals
        self.welcome_page.config_loaded.connect(self._on_config_loaded)
        self.connection_page.connection_changed.connect(self._on_connection_changed)
        self.write_page.write_complete.connect(self._on_write_complete)
    
    def _update_navigation(self):
        """Update navigation based on current page"""
        current = self.pages.currentIndex()
        self.step_indicator.set_step(current)
        self.nav.set_step(current + 1, len(self.STEPS))
        
        # Update next button text
        if current == 0:
            self.nav.set_next_text("Next →")
            self.nav.set_next_enabled(True)
        elif current == 1:
            self.nav.set_next_text("Next →")
            self.nav.set_next_enabled(self.can_interface.is_connected())
        elif current == 2:
            self.nav.set_next_text("Review Changes →")
            self.nav.set_next_enabled(True)
        elif current == 3:
            self.nav.set_next_text("Write to Device →")
            self.nav.set_next_enabled(True)
        elif current == 4:
            self.nav.set_next_text("Done")
            self.nav.set_next_enabled(self.write_page.is_complete())
    
    def _go_back(self):
        current = self.pages.currentIndex()
        if current > 0:
            self.pages.setCurrentIndex(current - 1)
            self._update_navigation()
    
    def _go_next(self):
        current = self.pages.currentIndex()
        
        if current == 0:
            # Welcome -> Connection
            self.pages.setCurrentIndex(1)
        
        elif current == 1:
            # Connection -> Inputs
            if not self.can_interface.is_connected():
                QMessageBox.warning(self, "Not Connected", 
                    "Please connect to the GridConnect device before continuing.")
                return
            self.pages.setCurrentIndex(2)
        
        elif current == 2:
            # Inputs -> Confirmation
            self.inputs_page.save_current_input()
            self.confirmation_page.refresh()
            self.pages.setCurrentIndex(3)
        
        elif current == 3:
            # Confirmation -> Write
            self.write_page.prepare()
            self.pages.setCurrentIndex(4)
        
        elif current == 4:
            # Write -> Done (close or restart)
            if self.write_page.is_complete():
                reply = QMessageBox.question(self, "Configuration Complete",
                    "Configuration has been written successfully!\n\n"
                    "Would you like to configure another device?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    self._restart_wizard()
                else:
                    self.close()
        
        self._update_navigation()
    
    def _restart_wizard(self):
        """Reset and go back to welcome page"""
        self.configuration = FullConfiguration()
        self.welcome_page.reset()
        self.inputs_page.set_configuration(self.configuration)
        self.confirmation_page.set_configuration(self.configuration)
        self.write_page.set_configuration(self.configuration)  # Update write page too!
        self.write_page.reset()
        self.pages.setCurrentIndex(0)
        self._update_navigation()
    
    def _on_config_loaded(self, config: FullConfiguration):
        """Handle configuration loaded from file or preset"""
        self.configuration = config
        self.inputs_page.set_configuration(config)
        self.confirmation_page.set_configuration(config)
        self.write_page.set_configuration(config)  # Update write page too!
    
    def _on_connection_changed(self, connected: bool):
        """Handle connection state change"""
        self._update_navigation()
    
    def _on_write_complete(self, success: bool):
        """Handle write completion"""
        self._update_navigation()
    
    def closeEvent(self, event):
        """Clean up on close"""
        self.can_interface.disconnect()
        event.accept()


def main():
    # Set high DPI policy before creating app
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Fusion gives consistent cross-platform look
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
