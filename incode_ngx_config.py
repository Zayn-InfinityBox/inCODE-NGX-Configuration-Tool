#!/usr/bin/env python3
"""
inCode NGX Configuration Tool
A Python-based desktop application for configuring MasterCell devices via CAN bus.
Uses GridConnect CANUSB COM FD (USB-C to CAN FD converter) at 250kbps Classic CAN.
"""

import sys
import serial
import serial.tools.list_ports
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QLineEdit, QTextEdit, QGroupBox,
    QGridLayout, QSpinBox, QMessageBox, QFrame, QSplitter, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon


# GridConnect CANUSB COM FD ASCII Protocol
# Based on the official GridConnect CAN232 FD / CANUSB COM FD User Manual
#
# Message Format:
#   :S<ID><TYPE><DATA>;     - Standard 11-bit frame
#   :X<ID><TYPE><DATA>;     - Extended 29-bit frame
#
# Where:
#   ID = 3 hex digits (standard) or 8 hex digits (extended)
#   TYPE = N (normal CAN 2.0), F (CAN FD), H (CAN FD+BRS), R (RTR)
#   DATA = hex byte pairs (e.g., 0102030405060708)
#
# Examples:
#   :S123N12345678;           - Standard ID 0x123, 4 data bytes
#   :X18FF0100N0102030405060708;  - Extended ID, 8 data bytes (J1939)
#   :E;                       - Request error status
#   :CONFIG;                  - Enter config mode (if enabled)

# Configuration is done by pressing the physical CONFIG button on the device
# or by sending :CONFIG; if config cmd is enabled in settings


class SerialReaderThread(QThread):
    """Thread for reading data from serial port without blocking the GUI."""
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.running = True

    def run(self):
        while self.running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    if self.serial_port.in_waiting > 0:
                        data = self.serial_port.read(self.serial_port.in_waiting)
                        try:
                            decoded = data.decode('ascii', errors='replace')
                            self.data_received.emit(decoded)
                        except Exception as e:
                            self.data_received.emit(f"[Decode Error: {e}]")
                    self.msleep(10)  # Small delay to prevent CPU spinning
                else:
                    self.msleep(100)
            except Exception as e:
                self.error_occurred.emit(str(e))
                self.msleep(100)

    def stop(self):
        self.running = False
        self.wait()


class InCodeNGXConfigTool(QMainWindow):
    """Main application window for inCode NGX Configuration Tool."""

    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.reader_thread = None
        self.rx_buffer = ""  # Buffer for receiving CAN frames
        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("inCode NGX Configuration Tool")
        self.setMinimumSize(900, 700)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Connection panel
        connection_group = self.create_connection_panel()
        main_layout.addWidget(connection_group)

        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Vertical)

        # CAN Configuration and Send panel
        config_send_widget = QWidget()
        config_send_layout = QHBoxLayout(config_send_widget)
        config_send_layout.setContentsMargins(0, 0, 0, 0)

        can_config_group = self.create_can_config_panel()
        send_group = self.create_send_panel()

        config_send_layout.addWidget(can_config_group, 1)
        config_send_layout.addWidget(send_group, 2)

        splitter.addWidget(config_send_widget)

        # Log panel
        log_group = self.create_log_panel()
        splitter.addWidget(log_group)

        splitter.setSizes([300, 400])
        main_layout.addWidget(splitter)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Disconnected - Select a COM port and connect")

        # Refresh ports on startup
        self.refresh_ports()

    def create_header(self):
        """Create the application header."""
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel("inCode NGX Configuration Tool")
        title_label.setObjectName("titleLabel")
        title_font = QFont("Segoe UI", 22, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("CAN Bus Configuration Interface • GridConnect CANUSB COM FD")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_font = QFont("Segoe UI", 10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        return header_frame

    def create_connection_panel(self):
        """Create the serial port connection panel."""
        group = QGroupBox("Connection")
        group.setObjectName("connectionGroup")
        layout = QHBoxLayout(group)
        layout.setSpacing(15)

        # Port selection
        port_layout = QVBoxLayout()
        port_label = QLabel("COM Port:")
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)
        layout.addLayout(port_layout)

        # Baud rate (for USB virtual COM port, not CAN)
        baud_layout = QVBoxLayout()
        baud_label = QLabel("Serial Baud:")
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['115200', '230400', '460800', '921600', '1000000'])
        self.baud_combo.setCurrentText('115200')
        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_combo)
        layout.addLayout(baud_layout)

        # Buttons
        button_layout = QVBoxLayout()
        button_layout.addWidget(QLabel(""))  # Spacer for alignment

        btn_container = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.refresh_btn.setObjectName("secondaryButton")
        btn_container.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setObjectName("primaryButton")
        btn_container.addWidget(self.connect_btn)

        button_layout.addLayout(btn_container)
        layout.addLayout(button_layout)

        layout.addStretch()

        return group

    def create_can_config_panel(self):
        """Create the CAN bus configuration panel."""
        group = QGroupBox("Device Setup")
        group.setObjectName("canConfigGroup")
        layout = QGridLayout(group)
        layout.setSpacing(8)

        # Auto Configure button - the main one-click solution
        self.auto_config_btn = QPushButton("🚀 Auto Configure Device")
        self.auto_config_btn.clicked.connect(self.auto_configure_device)
        self.auto_config_btn.setEnabled(False)
        self.auto_config_btn.setObjectName("primaryButton")
        self.auto_config_btn.setMinimumHeight(40)
        layout.addWidget(self.auto_config_btn, 0, 0, 1, 2)

        # First-time setup note
        self.first_time_label = QLabel("First time? Press CONFIG button on device first")
        self.first_time_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.first_time_label, 1, 0, 1, 2)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #333;")
        layout.addWidget(separator, 2, 0, 1, 2)

        # Manual config button
        self.quick_start_btn = QPushButton("📖 Manual Setup Guide")
        self.quick_start_btn.clicked.connect(self.quick_start_can)
        self.quick_start_btn.setEnabled(False)
        layout.addWidget(self.quick_start_btn, 3, 0, 1, 2)

        # Get CAN error status
        self.status_btn = QPushButton("📊 CAN Bus Status")
        self.status_btn.clicked.connect(self.get_status)
        self.status_btn.setEnabled(False)
        layout.addWidget(self.status_btn, 4, 0, 1, 2)

        # Hidden/unused buttons (keep for compatibility)
        self.open_can_btn = QPushButton("")
        self.open_can_btn.hide()
        self.listen_btn = QPushButton("")
        self.listen_btn.hide()
        self.test_btn = QPushButton("")
        self.test_btn.hide()
        self.config_can_btn = QPushButton("")
        self.config_can_btn.hide()
        self.close_can_btn = QPushButton("")
        self.close_can_btn.hide()
        self.version_btn = QPushButton("")
        self.version_btn.hide()
        self.scan_baud_btn = QPushButton("")
        self.scan_baud_btn.hide()
        self.deep_test_btn = QPushButton("")
        self.deep_test_btn.hide()

        layout.setRowStretch(5, 1)

        return group

    def create_send_panel(self):
        """Create the CAN message send panel."""
        group = QGroupBox("Send CAN Message")
        group.setObjectName("sendGroup")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Message ID
        layout.addWidget(QLabel("CAN ID (hex):"), 0, 0)
        self.can_id_input = QLineEdit()
        self.can_id_input.setPlaceholderText("e.g., 123 or 1ABCDEF0")
        self.can_id_input.setMaxLength(8)
        layout.addWidget(self.can_id_input, 0, 1)

        # Extended ID checkbox
        self.extended_id_check = QPushButton("Standard (11-bit)")
        self.extended_id_check.setCheckable(True)
        self.extended_id_check.clicked.connect(self.toggle_id_type)
        layout.addWidget(self.extended_id_check, 0, 2)

        # Data length
        layout.addWidget(QLabel("Data Length:"), 1, 0)
        self.data_length_spin = QSpinBox()
        self.data_length_spin.setRange(0, 8)
        self.data_length_spin.setValue(8)
        self.data_length_spin.valueChanged.connect(self.update_data_fields)
        layout.addWidget(self.data_length_spin, 1, 1)

        # Data bytes
        layout.addWidget(QLabel("Data (hex):"), 2, 0)
        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("e.g., 01 02 03 04 05 06 07 08")
        layout.addWidget(self.data_input, 2, 1, 1, 2)

        # Quick data presets
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Presets:")
        preset_layout.addWidget(preset_label)

        self.preset_zeros_btn = QPushButton("All 00")
        self.preset_zeros_btn.clicked.connect(lambda: self.set_data_preset("00"))
        preset_layout.addWidget(self.preset_zeros_btn)

        self.preset_ff_btn = QPushButton("All FF")
        self.preset_ff_btn.clicked.connect(lambda: self.set_data_preset("FF"))
        preset_layout.addWidget(self.preset_ff_btn)

        self.preset_inc_btn = QPushButton("Increment")
        self.preset_inc_btn.clicked.connect(self.set_increment_preset)
        preset_layout.addWidget(self.preset_inc_btn)

        preset_layout.addStretch()
        layout.addLayout(preset_layout, 3, 0, 1, 3)

        # Send button
        self.send_btn = QPushButton("📤 Send CAN Message")
        self.send_btn.clicked.connect(self.send_can_message)
        self.send_btn.setEnabled(False)
        self.send_btn.setObjectName("sendButton")
        layout.addWidget(self.send_btn, 4, 0, 1, 3)

        # Raw command section
        layout.addWidget(QLabel(""), 5, 0)  # Spacer
        layout.addWidget(QLabel("Raw ASCII Command:"), 6, 0)
        self.raw_cmd_input = QLineEdit()
        self.raw_cmd_input.setPlaceholderText("Enter raw command (e.g., V for version)")
        layout.addWidget(self.raw_cmd_input, 6, 1, 1, 2)

        self.raw_send_btn = QPushButton("📨 Send Raw")
        self.raw_send_btn.clicked.connect(self.send_raw_command)
        self.raw_send_btn.setEnabled(False)
        layout.addWidget(self.raw_send_btn, 7, 0, 1, 3)

        return group

    def create_log_panel(self):
        """Create the message log panel."""
        group = QGroupBox("Communication Log")
        group.setObjectName("logGroup")
        layout = QVBoxLayout(group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)

        # Log control buttons
        btn_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("🗑️ Clear Log")
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        btn_layout.addWidget(self.clear_log_btn)

        self.autoscroll_btn = QPushButton("📜 Auto-scroll: ON")
        self.autoscroll_btn.setCheckable(True)
        self.autoscroll_btn.setChecked(True)
        self.autoscroll_btn.clicked.connect(self.toggle_autoscroll)
        btn_layout.addWidget(self.autoscroll_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def apply_dark_theme(self):
        """Apply a modern dark theme to the application."""
        style = """
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                background-color: #1a1a2e;
                color: #eaeaea;
                font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
            }
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #16213e, stop:1 #0f3460);
                border-radius: 10px;
                border: 1px solid #0f3460;
            }
            #titleLabel {
                color: #e94560;
                background: transparent;
            }
            #subtitleLabel {
                color: #a0a0a0;
                background: transparent;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #16213e;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: #16213e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #e94560;
            }
            QLabel {
                color: #c0c0c0;
                background: transparent;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #0f3460;
                border: 1px solid #1a1a2e;
                border-radius: 5px;
                padding: 8px;
                color: #ffffff;
                selection-background-color: #e94560;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #e94560;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #e94560;
                margin-right: 5px;
            }
            QPushButton {
                background-color: #0f3460;
                border: 1px solid #16213e;
                border-radius: 6px;
                padding: 10px 20px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
                border-color: #e94560;
            }
            QPushButton:pressed {
                background-color: #e94560;
            }
            QPushButton:disabled {
                background-color: #2a2a4e;
                color: #606060;
            }
            #primaryButton {
                background-color: #e94560;
                border: none;
            }
            #primaryButton:hover {
                background-color: #ff6b6b;
            }
            #primaryButton:pressed {
                background-color: #c73e54;
            }
            #sendButton {
                background-color: #00d4aa;
                border: none;
                color: #1a1a2e;
            }
            #sendButton:hover {
                background-color: #00f5c4;
            }
            #sendButton:disabled {
                background-color: #2a4a4e;
                color: #606060;
            }
            QTextEdit {
                background-color: #0a0a1a;
                border: 1px solid #16213e;
                border-radius: 5px;
                color: #00ff88;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QStatusBar {
                background-color: #16213e;
                color: #a0a0a0;
                border-top: 1px solid #0f3460;
            }
            QSplitter::handle {
                background-color: #16213e;
            }
            QScrollBar:vertical {
                background: #16213e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #0f3460;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #e94560;
            }
        """
        self.setStyleSheet(style)

    def refresh_ports(self):
        """Refresh the list of available serial ports."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}", port.device)

        if len(ports) == 0:
            self.port_combo.addItem("No ports found", None)
            self.log_message("No COM ports found. Please connect the CANUSB device.", "warning")
        else:
            self.log_message(f"Found {len(ports)} COM port(s)", "info")

    def toggle_connection(self):
        """Connect or disconnect from the serial port."""
        if self.serial_port and self.serial_port.is_open:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        """Connect to the selected serial port."""
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "Error", "Please select a valid COM port")
            return

        baud = int(self.baud_combo.currentText())

        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )

            # Start reader thread
            self.reader_thread = SerialReaderThread(self.serial_port)
            self.reader_thread.data_received.connect(self.handle_received_data)
            self.reader_thread.error_occurred.connect(self.handle_serial_error)
            self.reader_thread.start()

            self.connect_btn.setText("🔌 Disconnect")
            self.connect_btn.setStyleSheet("background-color: #ff6b6b;")
            self.enable_controls(True)
            self.statusBar.showMessage(f"Connected to {port} at {baud} baud")
            self.log_message(f"Connected to {port} at {baud} baud", "success")

        except serial.SerialException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect:\n{str(e)}")
            self.log_message(f"Connection failed: {e}", "error")

    def disconnect_serial(self):
        """Disconnect from the serial port."""
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread = None

        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

        self.connect_btn.setText("🔌 Connect")
        self.connect_btn.setStyleSheet("")
        self.enable_controls(False)
        self.statusBar.showMessage("Disconnected")
        self.log_message("Disconnected from serial port", "info")

    def enable_controls(self, enabled):
        """Enable or disable CAN controls."""
        self.auto_config_btn.setEnabled(enabled)
        self.quick_start_btn.setEnabled(enabled)
        self.status_btn.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.raw_send_btn.setEnabled(enabled)

    def send_command(self, cmd):
        """Send a command to the CANUSB device."""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message("Not connected to device", "error")
            return False

        try:
            # GridConnect protocol: commands are sent as-is (no CR needed for message commands)
            # But config mode uses CR for line termination
            self.serial_port.write(cmd.encode('ascii'))
            self.log_message(f"TX: {cmd}", "tx")
            return True
        except Exception as e:
            self.log_message(f"Send error: {e}", "error")
            return False

    def configure_can(self):
        """Show configuration instructions."""
        self.log_message("=== CAN Configuration ===", "info")
        self.log_message("To configure the device:", "info")
        self.log_message("1. Press the CONFIG button on the device (< 3 sec)", "info")
        self.log_message("2. You'll see a '>' prompt in the log", "info")
        self.log_message("3. Type commands like:", "info")
        self.log_message("   config", "info")
        self.log_message("   can", "info")
        self.log_message("   baud 250000", "info")
        self.log_message("   save", "info")
        self.log_message("   exit", "info")

    def open_can_channel(self):
        """Try to enter config mode via serial command."""
        self.log_message("Sending :CONFIG; command (requires config cmd enabled)", "info")
        self.send_command(":CONFIG;")

    def close_can_channel(self):
        """Send exit command for config mode."""
        self.log_message("Sending 'exit' command for config mode", "info")
        self.send_command("exit\r")

    def get_device_info(self):
        """Request device info (in config mode: status > show all)."""
        self.log_message("To get device info, enter config mode and run:", "info")
        self.log_message("  status", "info")
        self.log_message("  show all", "info")
        # Try sending show command in case we're in config mode
        self.send_command("show\r")

    def quick_start_can(self):
        """Show quick setup instructions."""
        self.log_message("=== GridConnect CANUSB COM FD Quick Setup ===", "info")
        self.log_message("", "info")
        self.log_message("1. Press CONFIG button on device (< 3 seconds)", "info")
        self.log_message("2. Type these commands in the Raw Command field:", "info")
        self.log_message("   config", "info")
        self.log_message("   can", "info")
        self.log_message("   baud 250000", "info")
        self.log_message("   exit", "info")
        self.log_message("   com", "info")
        self.log_message("   mode command", "info")
        self.log_message("   exit", "info")
        self.log_message("   command", "info")
        self.log_message("   format ascii", "info")
        self.log_message("   exit", "info")
        self.log_message("   save", "info")
        self.log_message("   exit", "info")
        self.log_message("", "info")
        self.log_message("3. Device will restart in command mode", "info")
        self.log_message("4. Now you can send CAN messages!", "info")

    def get_status(self):
        """Request CAN error status."""
        self.log_message("Requesting CAN error status...", "info")
        self.send_command(":E;")

    def auto_configure_device(self):
        """Auto-configure the CANUSB device with one click."""
        self.log_message("═" * 50, "info")
        self.log_message("🚀 AUTO-CONFIGURING DEVICE FOR 250kbps J1939", "info")
        self.log_message("═" * 50, "info")
        
        # Configuration commands to send
        self.config_commands = [
            (":CONFIG;", "Entering config mode via serial..."),
            ("config\r", "Navigating to config level..."),
            ("can\r", "Navigating to CAN settings..."),
            ("baud 250000\r", "Setting CAN baud rate to 250000..."),
            ("exit\r", "Exiting CAN settings..."),
            ("com\r", "Navigating to COM settings..."),
            ("mode command\r", "Setting mode to command..."),
            ("exit\r", "Exiting COM settings..."),
            ("command\r", "Navigating to command settings..."),
            ("format ascii\r", "Setting format to ASCII..."),
            ("config cmd enable\r", "Enabling serial config command..."),
            ("exit\r", "Exiting command settings..."),
            ("save\r", "Saving configuration..."),
            ("exit\r", "Exiting config mode..."),
        ]
        
        self.config_step = 0
        self.config_in_progress = True
        
        # Check if we're already receiving CAN data (device already configured)
        self.log_message("Attempting to enter config mode...", "info")
        self.log_message("(If this fails, press CONFIG button on device)", "warning")
        
        # Start the configuration sequence
        self.send_next_config_command()
    
    def send_next_config_command(self):
        """Send the next command in the auto-config sequence."""
        if not hasattr(self, 'config_commands') or self.config_step >= len(self.config_commands):
            # Configuration complete
            self.log_message("═" * 50, "info")
            self.log_message("✅ AUTO-CONFIGURATION COMPLETE!", "success")
            self.log_message("Device is now configured for 250kbps J1939", "success")
            self.log_message("You should now see CAN traffic in the log", "success")
            self.log_message("═" * 50, "info")
            self.config_in_progress = False
            return
        
        cmd, description = self.config_commands[self.config_step]
        self.log_message(f"Step {self.config_step + 1}/{len(self.config_commands)}: {description}", "info")
        self.send_command(cmd)
        self.config_step += 1
        
        # Schedule next command (give device time to respond)
        delay = 300 if "save" in cmd.lower() else 150
        QTimer.singleShot(delay, self.send_next_config_command)

    def test_communication(self):
        """Test if the adapter responds to commands."""
        self.log_message("=== Testing Communication ===", "info")
        self.log_message("Sending version command (V)...", "info")
        
        # Try sending raw bytes to see what happens
        if self.serial_port and self.serial_port.is_open:
            # Clear any pending data
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # Try V command with just CR
            self.serial_port.write(b'V\r')
            self.log_message("TX: V (with CR)", "tx")
            
            # Wait a bit and try to read
            QTimer.singleShot(500, self.check_test_response)
    
    def check_test_response(self):
        """Check if we got a response from the test."""
        if self.serial_port and self.serial_port.is_open:
            waiting = self.serial_port.in_waiting
            self.log_message(f"Bytes waiting in buffer: {waiting}", "info")
            if waiting > 0:
                data = self.serial_port.read(waiting)
                self.log_message(f"Direct read: {repr(data)}", "success")
            else:
                self.log_message("No response received - adapter may need different settings", "warning")
                self.log_message("Try: Different baud rate, or check if device is in correct mode", "warning")

    def scan_baud_rates(self):
        """Scan through common baud rates to find the correct one."""
        self.log_message("=== Scanning Baud Rates ===", "info")
        self.baud_rates_to_try = [1000000, 921600, 460800, 230400, 115200, 57600, 38400, 19200, 9600]
        self.current_baud_index = 0
        self.try_next_baud_rate()

    def deep_test_communication(self):
        """Comprehensive test with different settings."""
        self.log_message("=== Deep Communication Test ===", "info")
        
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message("Not connected!", "error")
            return
        
        port = self.serial_port.port
        baud = self.serial_port.baudrate
        
        # Close current connection
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread = None
        self.serial_port.close()
        
        # Test different configurations
        test_configs = [
            {"rtscts": False, "dsrdtr": False, "terminator": b'\r', "name": "CR only"},
            {"rtscts": False, "dsrdtr": False, "terminator": b'\n', "name": "LF only"},
            {"rtscts": False, "dsrdtr": False, "terminator": b'\r\n', "name": "CRLF"},
            {"rtscts": True, "dsrdtr": False, "terminator": b'\r', "name": "RTS/CTS + CR"},
            {"rtscts": False, "dsrdtr": True, "terminator": b'\r', "name": "DSR/DTR + CR"},
        ]
        
        commands_to_try = [
            b'V',      # Version
            b'\r',     # Just CR (some devices wake up on this)
            b'\x03',   # Ctrl+C
            b'?',      # Help
            b'v',      # Lowercase version
            b'C',      # Close
            b'\r\r\r', # Multiple CRs
        ]
        
        for config in test_configs:
            self.log_message(f"Testing: {config['name']}...", "info")
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=baud,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.3,
                    rtscts=config['rtscts'],
                    dsrdtr=config['dsrdtr']
                )
                
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                for cmd in commands_to_try:
                    ser.write(cmd + config['terminator'])
                    import time
                    time.sleep(0.1)
                    
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        self.log_message(f"✓ RESPONSE with {config['name']}, cmd={repr(cmd)}: {repr(data)}", "success")
                        ser.close()
                        
                        # Reconnect with working settings
                        self.serial_port = serial.Serial(
                            port=port, baudrate=baud,
                            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE, timeout=0.1,
                            rtscts=config['rtscts'], dsrdtr=config['dsrdtr']
                        )
                        self.reader_thread = SerialReaderThread(self.serial_port)
                        self.reader_thread.data_received.connect(self.handle_received_data)
                        self.reader_thread.error_occurred.connect(self.handle_serial_error)
                        self.reader_thread.start()
                        self.log_message(f"=== Found working config: {config['name']} ===", "success")
                        return
                
                ser.close()
                
            except Exception as e:
                self.log_message(f"Error with {config['name']}: {e}", "error")
        
        self.log_message("=== No working configuration found ===", "error")
        self.log_message("Device may be in a special mode or need firmware update", "warning")
        
        # Reconnect with default settings
        try:
            self.serial_port = serial.Serial(
                port=port, baudrate=baud,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE, timeout=0.1
            )
            self.reader_thread = SerialReaderThread(self.serial_port)
            self.reader_thread.data_received.connect(self.handle_received_data)
            self.reader_thread.error_occurred.connect(self.handle_serial_error)
            self.reader_thread.start()
        except:
            pass

    def passive_listen(self):
        """Just listen for any incoming data for 5 seconds."""
        self.log_message("=== Passive Listen Mode (5 seconds) ===", "info")
        self.log_message("Listening for any data from device...", "info")
        self.log_message("(If device is streaming CAN data, we'll see it)", "info")
        
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message("Not connected!", "error")
            return
        
        port = self.serial_port.port
        
        # Stop current reader
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread = None
        
        self.serial_port.close()
        
        # Test at multiple baud rates with passive listening
        baud_rates = [115200, 1000000, 921600, 460800, 230400, 57600, 9600]
        
        import time
        total_data = b''
        
        for baud in baud_rates:
            self.log_message(f"Listening at {baud} baud...", "info")
            QApplication.processEvents()  # Update UI
            
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=baud,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.5
                )
                
                ser.reset_input_buffer()
                
                # Listen for 1 second at this baud rate
                start = time.time()
                while time.time() - start < 1.0:
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        total_data += data
                        hex_str = ' '.join([f'{b:02X}' for b in data])
                        self.log_message(f"✓ DATA at {baud}: [{hex_str}]", "success")
                        self.log_message(f"  ASCII: {repr(data)}", "success")
                    time.sleep(0.05)
                    QApplication.processEvents()
                
                ser.close()
                
                if total_data:
                    self.log_message(f"=== Found data at {baud} baud! ===", "success")
                    break
                    
            except Exception as e:
                self.log_message(f"Error at {baud}: {e}", "error")
        
        if not total_data:
            self.log_message("=== No data received at any baud rate ===", "warning")
            self.log_message("Possible issues:", "info")
            self.log_message("  1. Device may need initial configuration via Windows tool", "info")
            self.log_message("  2. CAN bus not properly connected (check H/L wiring)", "info")
            self.log_message("  3. CAN bitrate mismatch (device not set to 250kbps)", "info")
            self.log_message("  4. Device in wrong mode (check for mode switch/button)", "info")
        
        # Reconnect
        try:
            self.serial_port = serial.Serial(
                port=port, baudrate=115200,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE, timeout=0.1
            )
            self.reader_thread = SerialReaderThread(self.serial_port)
            self.reader_thread.data_received.connect(self.handle_received_data)
            self.reader_thread.error_occurred.connect(self.handle_serial_error)
            self.reader_thread.start()
        except:
            pass
    
    def try_next_baud_rate(self):
        """Try the next baud rate in the list."""
        if self.current_baud_index >= len(self.baud_rates_to_try):
            self.log_message("=== Baud Rate Scan Complete - No response at any baud rate ===", "error")
            self.log_message("Check: USB cable, device power, or device mode", "warning")
            return
        
        baud = self.baud_rates_to_try[self.current_baud_index]
        port = self.serial_port.port if self.serial_port else None
        
        if not port:
            self.log_message("No port selected", "error")
            return
        
        # Close current connection
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread = None
        if self.serial_port:
            self.serial_port.close()
        
        self.log_message(f"Trying baud rate: {baud}...", "info")
        
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.5
            )
            
            # Clear buffers
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # Send version command
            self.serial_port.write(b'V\r')
            
            # Wait for response
            QTimer.singleShot(300, self.check_baud_response)
            
        except Exception as e:
            self.log_message(f"Error at {baud}: {e}", "error")
            self.current_baud_index += 1
            QTimer.singleShot(100, self.try_next_baud_rate)
    
    def check_baud_response(self):
        """Check if we got a response at this baud rate."""
        if self.serial_port and self.serial_port.is_open:
            waiting = self.serial_port.in_waiting
            if waiting > 0:
                data = self.serial_port.read(waiting)
                baud = self.serial_port.baudrate
                self.log_message(f"✓ RESPONSE at {baud} baud: {repr(data)}", "success")
                self.log_message(f"=== Found working baud rate: {baud} ===", "success")
                
                # Update the UI
                self.baud_combo.setCurrentText(str(baud))
                
                # Restart reader thread
                self.reader_thread = SerialReaderThread(self.serial_port)
                self.reader_thread.data_received.connect(self.handle_received_data)
                self.reader_thread.error_occurred.connect(self.handle_serial_error)
                self.reader_thread.start()
                
                self.statusBar.showMessage(f"Connected at {baud} baud - WORKING!")
                return
            else:
                baud = self.serial_port.baudrate
                self.log_message(f"✗ No response at {baud}", "warning")
        
        self.current_baud_index += 1
        QTimer.singleShot(100, self.try_next_baud_rate)

    def toggle_id_type(self):
        """Toggle between standard and extended CAN ID."""
        if self.extended_id_check.isChecked():
            self.extended_id_check.setText("Extended (29-bit)")
            self.can_id_input.setMaxLength(8)
        else:
            self.extended_id_check.setText("Standard (11-bit)")
            self.can_id_input.setMaxLength(3)

    def update_data_fields(self, length):
        """Update data input placeholder based on length."""
        placeholder = " ".join(["00"] * length)
        self.data_input.setPlaceholderText(f"e.g., {placeholder}")

    def set_data_preset(self, value):
        """Set all data bytes to a preset value."""
        length = self.data_length_spin.value()
        data = " ".join([value] * length)
        self.data_input.setText(data)

    def set_increment_preset(self):
        """Set data bytes to incrementing values."""
        length = self.data_length_spin.value()
        data = " ".join([f"{i:02X}" for i in range(1, length + 1)])
        self.data_input.setText(data)

    def send_can_message(self):
        """Send a CAN message using GridConnect ASCII protocol."""
        # Parse CAN ID
        can_id_str = self.can_id_input.text().strip()
        if not can_id_str:
            QMessageBox.warning(self, "Error", "Please enter a CAN ID")
            return

        try:
            can_id = int(can_id_str, 16)
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid CAN ID. Enter hexadecimal value.")
            return

        # Validate ID range
        extended = self.extended_id_check.isChecked()
        if extended:
            if can_id > 0x1FFFFFFF:
                QMessageBox.warning(self, "Error", "Extended ID must be 0-1FFFFFFF")
                return
        else:
            if can_id > 0x7FF:
                QMessageBox.warning(self, "Error", "Standard ID must be 0-7FF")
                return

        # Parse data
        data_length = self.data_length_spin.value()
        data_str = self.data_input.text().strip()
        data_bytes = []

        if data_length > 0 and data_str:
            # Parse space-separated or continuous hex string
            data_str = data_str.replace(" ", "")
            if len(data_str) % 2 != 0:
                QMessageBox.warning(self, "Error", "Data must be complete byte pairs")
                return

            try:
                for i in range(0, len(data_str), 2):
                    data_bytes.append(int(data_str[i:i+2], 16))
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid data. Enter hexadecimal bytes.")
                return

            if len(data_bytes) != data_length:
                QMessageBox.warning(self, "Error", f"Data length mismatch. Expected {data_length} bytes.")
                return

        # Build GridConnect ASCII command
        # Format: :<S|X><ID><N|F|H|R><DATA>;
        # S = Standard (11-bit), X = Extended (29-bit)
        # N = Normal CAN 2.0, F = CAN FD, H = CAN FD+BRS, R = RTR
        
        if extended:
            id_type = 'X'
            id_str = f"{can_id:08X}"
        else:
            id_type = 'S'
            id_str = f"{can_id:03X}"

        msg_type = 'N'  # Normal CAN 2.0 message
        data_hex = "".join([f"{b:02X}" for b in data_bytes])
        
        # GridConnect format: :X18FF0100N0102030405060708;
        cmd = f":{id_type}{id_str}{msg_type}{data_hex};"

        self.send_command(cmd)

    def send_raw_command(self):
        """Send a raw ASCII command."""
        cmd = self.raw_cmd_input.text().strip()
        if cmd:
            # If it looks like a config mode command (no : prefix), add CR
            if not cmd.startswith(':'):
                cmd = cmd + '\r'
            self.send_command(cmd)
            self.raw_cmd_input.clear()

    def handle_received_data(self, data):
        """Handle data received from the serial port (GridConnect ASCII protocol)."""
        # GridConnect ASCII format: :<S|X><ID><TYPE><DATA>;
        # Messages start with ':' and end with ';'
        
        for char in data:
            if char == ':':
                # Start of a new message
                self.rx_buffer = ':'
            elif char == ';':
                # End of message
                if self.rx_buffer:
                    self.rx_buffer += ';'
                    self.parse_gridconnect_frame(self.rx_buffer)
                    self.rx_buffer = ""
            elif self.rx_buffer:
                # Accumulate message
                self.rx_buffer += char
            elif char == '\r' or char == '\n':
                pass  # Ignore line endings outside of messages
            elif char == '>':
                # Config mode prompt
                self.log_message("RX: Config prompt '>'", "info")
            elif char.strip():
                # Other characters (might be config mode output)
                pass  # Suppress individual character logging
    
    def parse_gridconnect_frame(self, frame):
        """Parse and display a received GridConnect ASCII CAN frame.
        
        Format: :<S|X><ID><N|F|H|R><DATA>;
        Examples:
            :S123N12345678;     - Standard, ID=123, Normal, 4 bytes
            :X18FF0100N01020304; - Extended, ID=18FF0100, Normal, 4 bytes
            :EA;                - Error status: Active
        """
        try:
            if not frame.startswith(':') or not frame.endswith(';'):
                self.log_message(f"RX: Invalid frame format: {frame}", "warning")
                return
            
            # Remove : and ;
            content = frame[1:-1]
            
            if not content:
                return
            
            # Check for error status message
            if content.startswith('E'):
                status_char = content[1] if len(content) > 1 else '?'
                status_map = {
                    'A': 'Active (Normal)',
                    'W': 'Warning',
                    'P': 'Passive (Too many errors)',
                    'B': 'Bus Off'
                }
                status = status_map.get(status_char, f'Unknown ({status_char})')
                self.log_message(f"RX CAN STATUS: {status}", "info")
                return
            
            # Parse CAN message
            id_type = content[0]  # S or X
            
            if id_type == 'S':
                # Standard 11-bit: S<3 hex><type><data>
                can_id = content[1:4]
                msg_type = content[4] if len(content) > 4 else '?'
                data_hex = content[5:] if len(content) > 5 else ''
            elif id_type == 'X':
                # Extended 29-bit: X<8 hex><type><data>
                can_id = content[1:9]
                msg_type = content[9] if len(content) > 9 else '?'
                data_hex = content[10:] if len(content) > 10 else ''
            else:
                self.log_message(f"RX: Unknown ID type: {frame}", "warning")
                return
            
            # Parse data bytes
            data_bytes = ' '.join([data_hex[i:i+2] for i in range(0, len(data_hex), 2)]) if data_hex else '(none)'
            dlc = len(data_hex) // 2
            
            # Message type
            type_map = {'N': 'Normal', 'F': 'CAN-FD', 'H': 'CAN-FD+BRS', 'R': 'RTR'}
            type_str = type_map.get(msg_type, msg_type)
            
            # Format nice output
            id_label = "STD" if id_type == 'S' else "EXT"
            self.log_message(
                f"RX CAN [{id_label} ID=0x{can_id}] {type_str} DLC={dlc} Data=[{data_bytes}]",
                "rx"
            )
            
        except Exception as e:
            self.log_message(f"RX Frame Parse Error: {frame} - {e}", "warning")

    def handle_serial_error(self, error):
        """Handle serial port errors."""
        self.log_message(f"Serial error: {error}", "error")

    def toggle_autoscroll(self):
        """Toggle auto-scroll for the log."""
        if self.autoscroll_btn.isChecked():
            self.autoscroll_btn.setText("📜 Auto-scroll: ON")
        else:
            self.autoscroll_btn.setText("📜 Auto-scroll: OFF")

    def log_message(self, message, msg_type="info"):
        """Add a message to the log with timestamp and color coding."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        color_map = {
            "info": "#a0a0a0",
            "success": "#00ff88",
            "warning": "#ffaa00",
            "error": "#ff4444",
            "tx": "#00d4aa",
            "rx": "#00aaff",
        }
        color = color_map.get(msg_type, "#ffffff")

        formatted = f'<span style="color: #606060">[{timestamp}]</span> ' \
                    f'<span style="color: {color}">{message}</span>'

        self.log_text.append(formatted)

        if self.autoscroll_btn.isChecked():
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )

    def closeEvent(self, event):
        """Clean up when closing the application."""
        self.disconnect_serial()
        event.accept()


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("inCode NGX Configuration Tool")
    app.setOrganizationName("inCode")

    window = InCodeNGXConfigTool()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

