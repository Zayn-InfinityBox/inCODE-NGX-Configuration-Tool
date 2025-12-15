"""
connection_page.py - Device connection page
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from styles import COLORS, ICONS
from can_interface import CANInterface


class ConnectionPage(QWidget):
    """Page for connecting to GridConnect device"""
    
    connection_changed = pyqtSignal(bool)
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self._setup_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_ports)
        self.refresh_timer.start(2000)
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(32)
        layout.setContentsMargins(32, 24, 32, 24)
        
        # Left side - Connection controls
        left_panel = QWidget()
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Connect Your GridConnect Device")
        title.setFont(QFont("", 22, QFont.Weight.Bold))
        left_layout.addWidget(title)
        
        subtitle = QLabel("Plug in your CANUSB COM FD and select it below")
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        left_layout.addWidget(subtitle)
        
        # Port selection row
        port_label = QLabel("Serial Port:")
        port_label.setFont(QFont("", 12, QFont.Weight.Bold))
        left_layout.addWidget(port_label)
        
        port_layout = QHBoxLayout()
        port_layout.setSpacing(12)
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(40)
        port_layout.addWidget(self.port_combo, 1)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setMinimumWidth(80)
        self.refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.refresh_btn)
        
        left_layout.addLayout(port_layout)
        
        # Status row
        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)
        
        self.status_icon = QLabel(ICONS['disconnected'])
        self.status_icon.setFont(QFont("", 24))
        self.status_icon.setStyleSheet(f"color: {COLORS['text_muted']};")
        status_layout.addWidget(self.status_icon)
        
        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(2)
        self.status_label = QLabel("Not connected")
        self.status_label.setFont(QFont("", 13, QFont.Weight.Bold))
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        status_text_layout.addWidget(self.status_label)
        
        self.status_detail = QLabel("Select a port and click Connect")
        self.status_detail.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        status_text_layout.addWidget(self.status_detail)
        
        status_layout.addLayout(status_text_layout)
        status_layout.addStretch()
        left_layout.addLayout(status_layout)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setMinimumHeight(48)
        self.connect_btn.setFont(QFont("", 13, QFont.Weight.Bold))
        self.connect_btn.clicked.connect(self._toggle_connection)
        left_layout.addWidget(self.connect_btn)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border_default']};")
        left_layout.addWidget(sep)
        
        # First-time setup section
        setup_title = QLabel("First-Time Device Setup")
        setup_title.setFont(QFont("", 12, QFont.Weight.Bold))
        left_layout.addWidget(setup_title)
        
        setup_desc = QLabel(
            "New device? Configure it for by pressing the configure button on the device for 3 seconds then click the button below."
        )
        setup_desc.setWordWrap(True)
        setup_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        left_layout.addWidget(setup_desc)
        
        self.setup_btn = QPushButton("Configure")
        self.setup_btn.setMinimumHeight(36)
        self.setup_btn.clicked.connect(self._run_first_time_setup)
        left_layout.addWidget(self.setup_btn)
        
        self.setup_status = QLabel("")
        self.setup_status.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
        left_layout.addWidget(self.setup_status)
        
        left_layout.addStretch()
        layout.addWidget(left_panel)
        
        # Right side - Instructions and traffic log
        right_panel = QWidget()
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Instructions
        instructions_label = QLabel("Setup Instructions")
        instructions_label.setFont(QFont("", 14, QFont.Weight.Bold))
        right_layout.addWidget(instructions_label)
        
        steps = [
            "1. Connect the GridConnect CANUSB COM FD to your computer via USB",
            "2. Connect the DB9 end to your MASTERCELL's CAN network",
            "3. Ensure MASTERCELL is powered on",
            "4. Select the port (usually /dev/cu.usbserial-... on Mac)",
            "5. Click Connect to establish communication",
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding-left: 8px;")
            step_label.setWordWrap(True)
            right_layout.addWidget(step_label)
        
        right_layout.addSpacing(8)
        
        # Traffic log
        log_label = QLabel("CAN Traffic")
        log_label.setFont(QFont("", 14, QFont.Weight.Bold))
        right_layout.addWidget(log_label)
        
        self.traffic_log = QTextEdit()
        self.traffic_log.setReadOnly(True)
        self.traffic_log.setStyleSheet(f"""
            QTextEdit {{
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 11px;
            }}
        """)
        self.traffic_log.setPlaceholderText("CAN traffic will appear here when connected...")
        right_layout.addWidget(self.traffic_log, 1)
        
        layout.addWidget(right_panel)
        
        # Initial port scan
        self._refresh_ports()
        
        # Connect CAN interface signals
        self.can.frame_received.connect(self._on_frame_received)
        self.can.connection_status_changed.connect(self._on_connection_changed)
    
    def _refresh_ports(self):
        """Refresh available serial ports"""
        current = self.port_combo.currentText()
        ports = self.can.scan_ports()
        
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(port)
        
        idx = self.port_combo.findText(current)
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
    
    def _toggle_connection(self):
        """Connect or disconnect"""
        if self.can.is_connected():
            self.can.disconnect()
        else:
            port = self.port_combo.currentText()
            if not port:
                QMessageBox.warning(self, "No Port", 
                    "Please select a serial port first.")
                return
            
            success = self.can.connect(port)
            if not success:
                QMessageBox.warning(self, "Connection Failed",
                    "Could not connect to the device.\n"
                    "Make sure the device is plugged in and not in use by another application.")
    
    def _on_connection_changed(self, connected: bool):
        """Handle connection state change"""
        if connected:
            self.status_icon.setText(ICONS['connected'])
            self.status_icon.setStyleSheet(f"color: {COLORS['accent_green']};")
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet(f"color: {COLORS['accent_green']};")
            self.status_detail.setText("Receiving CAN traffic - Click Next to continue")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setObjectName("dangerButton")
            self.traffic_log.clear()
            self.traffic_log.append("Connected! Waiting for CAN traffic...")
        else:
            self.status_icon.setText(ICONS['disconnected'])
            self.status_icon.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.status_label.setText("Not connected")
            self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.status_detail.setText("Select a port and click Connect")
            self.connect_btn.setText("Connect")
            self.connect_btn.setObjectName("primaryButton")
        
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        
        self.connection_changed.emit(connected)
    
    def _on_frame_received(self, can_id: int, data: list):
        """Display received CAN frame in log"""
        data_hex = ' '.join(f'{b:02X}' for b in data)
        self.traffic_log.append(f"RX: 0x{can_id:08X} [{len(data)}] {data_hex}")
        
        if self.traffic_log.document().blockCount() > 100:
            cursor = self.traffic_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
    
    def _run_first_time_setup(self):
        """Run first-time setup sequence for GridConnect device"""
        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "No Port", 
                "Please select a serial port first.")
            return
        
        reply = QMessageBox.information(self, "First-Time Setup",
            "To configure the GridConnect device for 250kbps CAN:\n\n"
            "1. Press and hold the CONFIG button on the device\n"
            "2. While holding, click OK below\n"
            "3. Release the CONFIG button when prompted\n\n"
            "The device will be configured for 250kbps Classic CAN.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if reply != QMessageBox.StandardButton.Ok:
            return
        
        self.setup_status.setText("Configuring device...")
        self.setup_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        self.setup_btn.setEnabled(False)
        
        try:
            import serial
            import time
            
            ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(0.5)
            
            ser.write(b"C\r")
            time.sleep(0.2)
            ser.write(b"config speed 250000\r")
            time.sleep(0.2)
            ser.write(b"config cmd enable\r")
            time.sleep(0.2)
            ser.write(b"O\r")
            time.sleep(0.2)
            
            ser.close()
            
            self.setup_status.setText("Setup complete! Release CONFIG button and click Connect.")
            self.setup_status.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
            
            QMessageBox.information(self, "Setup Complete",
                "Device configured successfully!\n\n"
                "Release the CONFIG button and click Connect.")
            
        except Exception as e:
            self.setup_status.setText(f"Setup failed: {str(e)}")
            self.setup_status.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 11px;")
            QMessageBox.warning(self, "Setup Failed", f"Could not configure device:\n{str(e)}")
        
        finally:
            self.setup_btn.setEnabled(True)
