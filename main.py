#!/usr/bin/env python3
"""
inCode NGX Configuration Tool

Main application entry point.
A professional configuration tool for MASTERCELL NGX and IOX devices.

Copyright 2024 Infinitybox, LLC
"""

import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon

from styles import MAIN_STYLESHEET, COLORS
from can_interface import CANInterface
from config_data import FullConfiguration, InputConfig
from widgets import ConnectionTab, SystemTab, InputsTab, MonitorTab, FilesTab


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("inCode NGX Configuration Tool")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Initialize CAN interface
        self.can_interface = CANInterface()
        
        # Current configuration
        self.config = FullConfiguration()
        
        # Setup UI
        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._connect_signals()
        
        # Apply dark theme
        self.setStyleSheet(MAIN_STYLESHEET)
    
    def _setup_ui(self):
        """Setup the main UI"""
        # Central widget with tabs
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Create tabs
        self.connection_tab = ConnectionTab(self.can_interface)
        self.system_tab = SystemTab(self.can_interface)
        self.inputs_tab = InputsTab(self.can_interface)
        self.monitor_tab = MonitorTab(self.can_interface)
        self.files_tab = FilesTab(self.can_interface)
        
        # Add tabs with icons/labels
        self.tabs.addTab(self.connection_tab, "🔌 Connection")
        self.tabs.addTab(self.system_tab, "⚙️ System")
        self.tabs.addTab(self.inputs_tab, "🎚️ Inputs")
        self.tabs.addTab(self.monitor_tab, "📊 Monitor")
        self.tabs.addTab(self.files_tab, "💾 Files")
        
        layout.addWidget(self.tabs)
    
    def _setup_menubar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = file_menu.addAction("New Configuration")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_config)
        
        open_action = file_menu.addAction("Open Configuration...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_config)
        
        save_action = file_menu.addAction("Save Configuration")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_config)
        
        save_as_action = file_menu.addAction("Save As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_config_as)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # Device menu
        device_menu = menubar.addMenu("Device")
        
        connect_action = device_menu.addAction("Connect...")
        connect_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.connection_tab))
        
        disconnect_action = device_menu.addAction("Disconnect")
        disconnect_action.triggered.connect(self.can_interface.disconnect)
        
        device_menu.addSeparator()
        
        read_action = device_menu.addAction("Read All from Device")
        read_action.triggered.connect(self._read_from_device)
        
        write_action = device_menu.addAction("Write All to Device")
        write_action.triggered.connect(self._write_to_device)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        connection_action = view_menu.addAction("Connection Tab")
        connection_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.connection_tab))
        
        system_action = view_menu.addAction("System Tab")
        system_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.system_tab))
        
        inputs_action = view_menu.addAction("Inputs Tab")
        inputs_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.inputs_tab))
        
        monitor_action = view_menu.addAction("Monitor Tab")
        monitor_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.monitor_tab))
        
        files_action = view_menu.addAction("Files Tab")
        files_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.files_tab))
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._show_about)
    
    def _setup_statusbar(self):
        """Setup the status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Connection status
        self.conn_status = QLabel("● Disconnected")
        self.conn_status.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 0 10px;")
        self.statusbar.addWidget(self.conn_status)
        
        # Message counter
        self.msg_counter = QLabel("Messages: 0")
        self.msg_counter.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 0 10px;")
        self.statusbar.addPermanentWidget(self.msg_counter)
        
        # Version
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 0 10px;")
        self.statusbar.addPermanentWidget(version_label)
    
    def _connect_signals(self):
        """Connect signals between components"""
        # Connection changes
        self.can_interface.connected.connect(self._on_connected)
        self.can_interface.disconnected.connect(self._on_disconnected)
        self.can_interface.message_received.connect(self._on_message)
        
        # Files tab callbacks
        self.files_tab.set_get_config_callback(self._get_full_config)
        self.files_tab.set_set_config_callback(self._set_full_config)
        self.files_tab.config_loaded.connect(self._set_full_config)
    
    def _on_connected(self):
        """Handle connection established"""
        self.conn_status.setText("● Connected")
        self.conn_status.setStyleSheet(f"color: {COLORS['accent_green']}; padding: 0 10px;")
        self.statusbar.showMessage("Connected to device", 3000)
    
    def _on_disconnected(self):
        """Handle disconnection"""
        self.conn_status.setText("● Disconnected")
        self.conn_status.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 0 10px;")
        self.statusbar.showMessage("Disconnected from device", 3000)
    
    def _on_message(self, msg):
        """Handle received message (update counter)"""
        current = self.msg_counter.text().split(": ")[1]
        try:
            count = int(current) + 1
            self.msg_counter.setText(f"Messages: {count}")
        except:
            pass
    
    def _get_full_config(self) -> FullConfiguration:
        """Get current full configuration from all tabs"""
        config = FullConfiguration()
        config.system = self.system_tab.get_config()
        
        # Get input configs from inputs tab
        input_configs = self.inputs_tab.get_all_configs()
        for i, inp_config in input_configs.items():
            if i <= len(config.inputs):
                config.inputs[i-1] = inp_config
        
        return config
    
    def _set_full_config(self, config: FullConfiguration):
        """Set full configuration to all tabs"""
        self.config = config
        self.system_tab.set_config(config.system)
        
        # Set input configs
        input_configs = {inp.input_number: inp for inp in config.inputs}
        self.inputs_tab.set_all_configs(input_configs)
    
    def _new_config(self):
        """Create new configuration"""
        reply = QMessageBox.question(self, "New Configuration",
            "Create a new configuration? This will clear all current settings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self._set_full_config(FullConfiguration())
    
    def _open_config(self):
        """Open configuration file"""
        self.tabs.setCurrentWidget(self.files_tab)
        self.files_tab._open_config()
    
    def _save_config(self):
        """Save configuration"""
        self.files_tab._save_config()
    
    def _save_config_as(self):
        """Save configuration as"""
        self.files_tab._save_config_as()
    
    def _read_from_device(self):
        """Read all config from device"""
        self.tabs.setCurrentWidget(self.files_tab)
        self.files_tab._read_all_from_device()
    
    def _write_to_device(self):
        """Write all config to device"""
        self.tabs.setCurrentWidget(self.files_tab)
        self.files_tab._write_all_to_device()
    
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About inCode NGX Configuration Tool",
            "<h2>inCode NGX Configuration Tool</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A professional configuration tool for MASTERCELL NGX and IOX devices.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Configure 44 inputs with up to 10 cases each</li>"
            "<li>No-code action templates for easy setup</li>"
            "<li>Real-time CAN bus monitoring</li>"
            "<li>Save/load configurations</li>"
            "<li>Read/write device EEPROM</li>"
            "</ul>"
            "<p>Copyright © 2024 Infinitybox, LLC</p>"
        )
    
    def closeEvent(self, event):
        """Handle window close"""
        # Disconnect if connected
        if self.can_interface.is_connected():
            self.can_interface.disconnect()
        
        event.accept()


def main():
    """Application entry point"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("inCode NGX Configuration Tool")
    app.setOrganizationName("Infinitybox")
    app.setOrganizationDomain("infinitybox.com")
    
    # Set application font (cross-platform)
    font = app.font()
    # Use system-appropriate font
    import platform
    if platform.system() == "Windows":
        font.setFamily("Segoe UI")
    elif platform.system() == "Darwin":
        font.setFamily("SF Pro Display")
    else:
        font.setFamily("Ubuntu")
    font.setPointSize(10)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

