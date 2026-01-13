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
    QMessageBox, QGraphicsDropShadowEffect, QMenuBar, QMenu, QFileDialog,
    QDialog, QLineEdit, QDialogButtonBox, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QColor, QPalette, QLinearGradient, QPainter, QAction, QKeySequence, QActionGroup

from styles import MAIN_STYLESHEET, COLORS, ICONS, BACKGROUND_GRADIENT
from can_interface import CANInterface
from config_data import FullConfiguration
from view_mode import ViewMode, ViewModeManager, view_mode_manager

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
        
        self._setup_menu()
        self._setup_ui()
        self._connect_signals()
    
    def _ensure_directories(self):
        """Create backup and config directories if they don't exist"""
        # Use visible folder in user's Documents
        docs_dir = os.path.join(os.path.expanduser("~"), "Documents", "inCODE NGX Configs")
        
        self.backup_dir = os.path.join(docs_dir, "Backups")
        self.config_dir = os.path.join(docs_dir, "Configurations")
        
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _setup_menu(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: rgba(25, 25, 25, 0.95);
                color: {COLORS['text_primary']};
                padding: 4px 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QMenuBar::item {{
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: rgba(96, 176, 225, 0.3);
            }}
            QMenu {{
                background-color: rgba(45, 45, 45, 0.98);
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 10px 24px;
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
        """)
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Save Configuration action
        save_action = QAction("Save Configuration...", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_configuration)
        file_menu.addAction(save_action)
        
        # Save Configuration As action
        save_as_action = QAction("Save Configuration As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_configuration_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Test: Read Current Config from device
        read_config_action = QAction("Read Current Config (Test)...", self)
        read_config_action.setShortcut(QKeySequence("Ctrl+R"))
        read_config_action.triggered.connect(self._read_current_config)
        file_menu.addAction(read_config_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu - Mode selection
        view_menu = menubar.addMenu("View")
        
        # Create action group for exclusive selection
        self.view_mode_group = QActionGroup(self)
        self.view_mode_group.setExclusive(True)
        
        # Basic Mode
        self.basic_mode_action = QAction("Basic Mode", self)
        self.basic_mode_action.setCheckable(True)
        self.basic_mode_action.setStatusTip("Simplified interface for standard installations")
        self.basic_mode_action.triggered.connect(lambda: self._set_view_mode(ViewMode.BASIC))
        self.view_mode_group.addAction(self.basic_mode_action)
        view_menu.addAction(self.basic_mode_action)
        
        # Advanced Mode
        self.advanced_mode_action = QAction("Advanced Mode", self)
        self.advanced_mode_action.setCheckable(True)
        self.advanced_mode_action.setChecked(True)  # Default
        self.advanced_mode_action.setStatusTip("Full feature set for experienced users")
        self.advanced_mode_action.triggered.connect(lambda: self._set_view_mode(ViewMode.ADVANCED))
        self.view_mode_group.addAction(self.advanced_mode_action)
        view_menu.addAction(self.advanced_mode_action)
        
        view_menu.addSeparator()
        
        # Admin Mode (password protected)
        self.admin_mode_action = QAction("Admin Mode 🔒", self)
        self.admin_mode_action.setCheckable(True)
        self.admin_mode_action.setStatusTip("Full unrestricted access (password required)")
        self.admin_mode_action.triggered.connect(self._request_admin_mode)
        self.view_mode_group.addAction(self.admin_mode_action)
        view_menu.addAction(self.admin_mode_action)
        
        # Connect to view mode manager to update menu state
        view_mode_manager.view_mode_changed.connect(self._on_view_mode_changed)
    
    def _save_configuration(self):
        """Save configuration to the configurations folder with timestamp"""
        # Save current input first if on inputs page
        if self.pages.currentIndex() == 2:  # Inputs page
            self.inputs_page.save_current_input()
        
        # Generate timestamp filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Configuration_{timestamp}.json"
        filepath = os.path.join(self.config_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write(self.configuration.to_json())
            
            QMessageBox.information(
                self, 
                "Configuration Saved",
                f"Configuration saved successfully!\n\n"
                f"File: {filename}\n"
                f"Location: {self.config_dir}\n\n"
                f"You can load this configuration later from the Welcome page."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save configuration:\n{str(e)}"
            )
    
    def _save_configuration_as(self):
        """Save configuration to a user-specified location"""
        # Save current input first if on inputs page
        if self.pages.currentIndex() == 2:  # Inputs page
            self.inputs_page.save_current_input()
        
        # Generate default filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"Configuration_{timestamp}.json"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            os.path.join(self.config_dir, default_name),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filepath:
            try:
                # Ensure .json extension
                if not filepath.endswith('.json'):
                    filepath += '.json'
                
                with open(filepath, 'w') as f:
                    f.write(self.configuration.to_json())
                
                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    f"Configuration saved successfully!\n\n"
                    f"File: {os.path.basename(filepath)}\n\n"
                    f"You can load this configuration later from the Welcome page."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Save Failed",
                    f"Failed to save configuration:\n{str(e)}"
                )
    
    def _read_current_config(self):
        """Test function: Read current config from connected MASTERCELL and save to backup"""
        from can_interface import ConfigurationManager
        
        # Check if we're connected
        if not self.can_interface.is_connected():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to a MASTERCELL device first.\n\n"
                "Go to the Connection page (Step 2) to establish a connection."
            )
            return
        
        # Create progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        progress = QProgressDialog("Reading EEPROM configuration...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Read Current Config")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        # Create config manager for reading
        self._read_manager = ConfigurationManager(self.can_interface)
        self._read_progress = progress
        self._read_data = {}
        
        # Connect signals
        self._read_manager.progress.connect(self._on_read_progress)
        self._read_manager.read_complete.connect(self._on_read_complete)
        
        # Start reading
        self._read_manager.read_full_configuration()
    
    def _on_read_progress(self, current, total, message):
        """Handle read progress updates"""
        if hasattr(self, '_read_progress') and self._read_progress:
            percent = int((current / total) * 100) if total > 0 else 0
            self._read_progress.setValue(percent)
            self._read_progress.setLabelText(f"Reading EEPROM: {message}\n({current}/{total})")
            
            if self._read_progress.wasCanceled():
                self._read_manager.cancel()
    
    def _on_read_complete(self, success, data):
        """Handle read completion - decode EEPROM and save as configuration"""
        if hasattr(self, '_read_progress') and self._read_progress:
            self._read_progress.close()
            self._read_progress = None
        
        # Even if not fully successful, save whatever data we got
        if data:
            from eeprom_protocol import decode_raw_eeprom_to_config
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            status = "complete" if success else "partial"
            byte_count = len(data)
            
            try:
                # Decode raw EEPROM into a proper configuration
                decoded_config = decode_raw_eeprom_to_config(data)
                
                # Save as a proper configuration JSON (like our presets)
                config_filename = f"Device_Config_{status}_{timestamp}.json"
                config_path = os.path.join(self.backup_dir, config_filename)
                
                with open(config_path, 'w') as f:
                    f.write(decoded_config.to_json())
                
                # Also save raw EEPROM data for debugging
                raw_filename = f"Device_Raw_{status}_{timestamp}.json"
                raw_path = os.path.join(self.backup_dir, raw_filename)
                
                import json
                raw_data = {
                    "timestamp": timestamp,
                    "type": "device_backup_raw",
                    "source": "read_current_config",
                    "complete": success,
                    "byte_count": byte_count,
                    "raw_eeprom": {str(addr): val for addr, val in sorted(data.items())}
                }
                
                with open(raw_path, 'w') as f:
                    json.dump(raw_data, f, indent=2)
                
                # Count configured inputs
                configured_inputs = sum(
                    1 for inp in decoded_config.inputs
                    if any(c.enabled for c in inp.on_cases + inp.off_cases)
                )
                
                if success:
                    QMessageBox.information(
                        self,
                        "Read Complete",
                        f"✅ Successfully read {byte_count} bytes from EEPROM!\n\n"
                        f"Found {configured_inputs} configured inputs.\n\n"
                        f"Configuration saved to:\n{config_filename}\n\n"
                        f"Raw EEPROM saved to:\n{raw_filename}\n\n"
                        f"Location: {self.backup_dir}"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Partial Read",
                        f"⚠️ Read {byte_count} bytes before encountering an error.\n\n"
                        f"Found {configured_inputs} configured inputs (partial).\n\n"
                        f"Partial config saved to:\n{config_filename}\n\n"
                        f"Location: {self.backup_dir}\n\n"
                        f"The device may have stopped responding. Try again."
                    )
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.warning(
                    self,
                    "Decode Failed",
                    f"Read succeeded but failed to decode/save:\n{str(e)}\n\n"
                    f"Read {byte_count} bytes from device."
                )
        else:
            QMessageBox.critical(
                self,
                "Read Failed",
                "Failed to read configuration from device.\n\n"
                "Please check the connection and try again."
            )
    
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
    
    # =========================================================================
    # VIEW MODE METHODS
    # =========================================================================
    
    def _set_view_mode(self, mode: ViewMode):
        """Set view mode (for Basic and Advanced - no password needed)"""
        view_mode_manager.set_mode(mode)
    
    def _request_admin_mode(self):
        """Request admin mode - shows password dialog"""
        # If already in admin mode, just stay there
        if view_mode_manager.is_admin:
            return
        
        # Show password dialog
        password, ok = QInputDialog.getText(
            self,
            "Admin Mode",
            "Enter admin password:",
            QLineEdit.EchoMode.Password
        )
        
        if ok and password:
            if view_mode_manager.set_mode(ViewMode.ADMIN, password):
                QMessageBox.information(
                    self,
                    "Admin Mode Enabled",
                    "Admin mode is now active.\n\n"
                    "You have full access to all settings and features."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Access Denied",
                    "Incorrect password.\n\n"
                    "Admin mode was not enabled."
                )
                # Revert the menu selection to current mode
                self._update_view_mode_menu()
        else:
            # User cancelled - revert menu selection
            self._update_view_mode_menu()
    
    def _on_view_mode_changed(self, mode: ViewMode):
        """Handle view mode change from manager"""
        self._update_view_mode_menu()
        self._update_view_mode_indicator()
        
        # Notify pages of view mode change
        # Pages can connect to view_mode_manager.view_mode_changed directly
        # or we can call methods on them here
        if hasattr(self.inputs_page, 'on_view_mode_changed'):
            self.inputs_page.on_view_mode_changed(mode)
    
    def _update_view_mode_menu(self):
        """Update menu checkmarks to match current mode"""
        mode = view_mode_manager.current_mode
        self.basic_mode_action.setChecked(mode == ViewMode.BASIC)
        self.advanced_mode_action.setChecked(mode == ViewMode.ADVANCED)
        self.admin_mode_action.setChecked(mode == ViewMode.ADMIN)
    
    def _update_view_mode_indicator(self):
        """Update any UI indicators showing current mode"""
        mode = view_mode_manager.current_mode
        mode_names = {
            ViewMode.BASIC: "Basic",
            ViewMode.ADVANCED: "Advanced", 
            ViewMode.ADMIN: "Admin"
        }
        # Could update a status bar or header indicator here
        # For now, just update window title
        base_title = "inCODE NGX Configuration Tool"
        if mode == ViewMode.ADMIN:
            self.setWindowTitle(f"{base_title} [ADMIN MODE]")
        elif mode == ViewMode.BASIC:
            self.setWindowTitle(f"{base_title} [Basic]")
        else:
            self.setWindowTitle(base_title)
    
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
            # Save current input before leaving inputs page
            if current == 2:  # Inputs page
                self.inputs_page.save_current_input()
            
            self.pages.setCurrentIndex(current - 1)
            self._update_navigation()
    
    def _go_next(self):
        current = self.pages.currentIndex()
        
        if current == 0:
            # Welcome -> Connection: Load the selected configuration now
            config, is_preset = self.welcome_page.load_selected_config()
            if config:
                self.configuration = config
                self.inputs_page.set_configuration(config, is_preset=is_preset)
                # Store original config for change comparison BEFORE setting current config
                self.confirmation_page.set_original_configuration(config)
                self.confirmation_page.set_configuration(config)
                self.write_page.set_configuration(config)
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
        self.inputs_page.set_configuration(self.configuration, is_preset=False)
        self.confirmation_page.set_configuration(self.configuration)
        self.write_page.set_configuration(self.configuration)  # Update write page too!
        self.write_page.reset()
        self.pages.setCurrentIndex(0)
        self._update_navigation()
    
    def _on_config_loaded(self, config: FullConfiguration, is_preset: bool = False):
        """Handle configuration loaded from file or preset"""
        self.configuration = config
        self.inputs_page.set_configuration(config, is_preset=is_preset)
        
        # Store original config for change comparison in confirmation page
        self.confirmation_page.set_original_configuration(config)
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
