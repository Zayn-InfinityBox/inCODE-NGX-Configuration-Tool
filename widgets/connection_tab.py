"""
connection_tab.py - Connection and device status tab
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QGroupBox, QGridLayout, QFrame
)
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from can_interface import CANInterface, CANMessage
from styles import COLORS, ICONS


class ConnectionTab(QWidget):
    """Connection management and device status display"""
    
    connection_changed = pyqtSignal(bool)
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.message_count = 0
        self.last_heartbeat_time = 0
        self.device_info = {
            'fw_major': 0,
            'fw_minor': 0,
            'uptime': 0,
            'status': 0
        }
        
        self._setup_ui()
        self._connect_signals()
        
        # Refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._update_status)
        self.refresh_timer.start(1000)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Connection")
        header.setObjectName("headerLabel")
        header.setFont(QFont("", 24, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Connection Group
        conn_group = QGroupBox("Serial Port Connection")
        conn_layout = QGridLayout(conn_group)
        conn_layout.setSpacing(12)
        
        # Port selection
        conn_layout.addWidget(QLabel("COM Port:"), 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(300)
        conn_layout.addWidget(self.port_combo, 0, 1)
        
        self.refresh_btn = QPushButton(f"{ICONS['refresh']} Refresh Ports")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        conn_layout.addWidget(self.refresh_btn, 0, 2)
        
        # Baud rate (informational - USB CDC doesn't use this)
        conn_layout.addWidget(QLabel("Baud Rate:"), 1, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["115200", "230400", "460800", "921600", "1000000"])
        self.baud_combo.setCurrentText("115200")
        conn_layout.addWidget(self.baud_combo, 1, 1)
        
        baud_note = QLabel("(USB CDC - baud rate is informational only)")
        baud_note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        conn_layout.addWidget(baud_note, 1, 2)
        
        # Connect button
        self.connect_btn = QPushButton(f"{ICONS['power']} Connect")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.clicked.connect(self._toggle_connection)
        conn_layout.addWidget(self.connect_btn, 2, 0, 1, 3)
        
        layout.addWidget(conn_group)
        
        # Status Group
        status_group = QGroupBox("Connection Status")
        status_layout = QGridLayout(status_group)
        status_layout.setSpacing(12)
        
        # Status indicator
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        self.status_label = QLabel(f"{ICONS['disconnected']} Disconnected")
        self.status_label.setObjectName("connectionStatusDisconnected")
        status_layout.addWidget(self.status_label, 0, 1)
        
        # Message count
        status_layout.addWidget(QLabel("Messages Received:"), 1, 0)
        self.msg_count_label = QLabel("0")
        status_layout.addWidget(self.msg_count_label, 1, 1)
        
        # Last activity
        status_layout.addWidget(QLabel("Last Activity:"), 2, 0)
        self.last_activity_label = QLabel("---")
        status_layout.addWidget(self.last_activity_label, 2, 1)
        
        layout.addWidget(status_group)
        
        # Device Info Group
        device_group = QGroupBox("Device Information")
        device_layout = QGridLayout(device_group)
        device_layout.setSpacing(12)
        
        # Firmware version
        device_layout.addWidget(QLabel("Firmware Version:"), 0, 0)
        self.fw_version_label = QLabel("---")
        device_layout.addWidget(self.fw_version_label, 0, 1)
        
        # Device uptime
        device_layout.addWidget(QLabel("Device Uptime:"), 1, 0)
        self.uptime_label = QLabel("---")
        device_layout.addWidget(self.uptime_label, 1, 1)
        
        # CAN traffic indicator
        device_layout.addWidget(QLabel("CAN Traffic:"), 2, 0)
        self.traffic_label = QLabel("---")
        device_layout.addWidget(self.traffic_label, 2, 1)
        
        layout.addWidget(device_group)
        
        # Quick Actions Group
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setSpacing(12)
        
        self.read_config_btn = QPushButton("Read Device Config")
        self.read_config_btn.setEnabled(False)
        actions_layout.addWidget(self.read_config_btn)
        
        self.write_config_btn = QPushButton("Write Device Config")
        self.write_config_btn.setEnabled(False)
        actions_layout.addWidget(self.write_config_btn)
        
        self.factory_reset_btn = QPushButton("Factory Reset")
        self.factory_reset_btn.setObjectName("dangerButton")
        self.factory_reset_btn.setEnabled(False)
        actions_layout.addWidget(self.factory_reset_btn)
        
        layout.addWidget(actions_group)
        
        # Spacer
        layout.addStretch()
        
        # Initial port refresh
        self._refresh_ports()
    
    def _connect_signals(self):
        self.can.connected.connect(self._on_connected)
        self.can.disconnected.connect(self._on_disconnected)
        self.can.message_received.connect(self._on_message)
        self.can.error.connect(self._on_error)
    
    def _refresh_ports(self):
        """Refresh available COM ports"""
        self.port_combo.clear()
        ports = CANInterface.list_ports()
        for device, description in ports:
            self.port_combo.addItem(f"{device} - {description}", device)
        
        if ports:
            self.port_combo.setCurrentIndex(0)
    
    def _toggle_connection(self):
        """Connect or disconnect"""
        if self.can.is_connected():
            self.can.disconnect()
        else:
            port = self.port_combo.currentData()
            if port:
                baudrate = int(self.baud_combo.currentText())
                if self.can.connect(port, baudrate):
                    pass  # Signal will update UI
                else:
                    self._on_error("Failed to connect")
    
    def _on_connected(self):
        """Handle connection established"""
        self.status_label.setText(f"{ICONS['connected']} Connected")
        self.status_label.setObjectName("connectionStatusConnected")
        self.status_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-weight: 600;")
        
        self.connect_btn.setText(f"{ICONS['power']} Disconnect")
        self.connect_btn.setObjectName("dangerButton")
        self.connect_btn.setStyleSheet(f"""
            background-color: {COLORS['status_error']};
            border-color: {COLORS['status_error']};
        """)
        
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        
        self.read_config_btn.setEnabled(True)
        self.write_config_btn.setEnabled(True)
        self.factory_reset_btn.setEnabled(True)
        
        self.connection_changed.emit(True)
    
    def _on_disconnected(self):
        """Handle disconnection"""
        self.status_label.setText(f"{ICONS['disconnected']} Disconnected")
        self.status_label.setObjectName("connectionStatusDisconnected")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: 600;")
        
        self.connect_btn.setText(f"{ICONS['power']} Connect")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setStyleSheet(f"""
            background-color: {COLORS['status_success']};
            border-color: {COLORS['status_success']};
        """)
        
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        
        self.read_config_btn.setEnabled(False)
        self.write_config_btn.setEnabled(False)
        self.factory_reset_btn.setEnabled(False)
        
        self.connection_changed.emit(False)
    
    def _on_message(self, msg: CANMessage):
        """Handle received CAN message"""
        self.message_count += 1
        
        import time
        self.last_heartbeat_time = time.time()
        
        # Try to extract device info from heartbeat messages
        if msg.extended and len(msg.data) >= 6:
            # Check if this might be a heartbeat (common patterns)
            pgn = msg.pgn
            if pgn in [0xFF00, 0xFF06]:  # Heartbeat PGNs
                self.device_info['fw_major'] = msg.data[0]
                self.device_info['fw_minor'] = msg.data[1]
                if len(msg.data) >= 6:
                    self.device_info['uptime'] = msg.data[5] * 10
    
    def _on_error(self, error: str):
        """Handle error"""
        self.status_label.setText(f"{ICONS['warning']} Error: {error}")
        self.status_label.setStyleSheet(f"color: {COLORS['accent_red']};")
    
    def _update_status(self):
        """Update status display"""
        self.msg_count_label.setText(str(self.message_count))
        
        if self.can.is_connected():
            import time
            if self.last_heartbeat_time > 0:
                elapsed = time.time() - self.last_heartbeat_time
                if elapsed < 2:
                    self.last_activity_label.setText("Just now")
                    self.traffic_label.setText(f"{ICONS['connected']} Active")
                    self.traffic_label.setStyleSheet(f"color: {COLORS['accent_green']};")
                elif elapsed < 10:
                    self.last_activity_label.setText(f"{int(elapsed)}s ago")
                    self.traffic_label.setText(f"{ICONS['connected']} Active")
                    self.traffic_label.setStyleSheet(f"color: {COLORS['accent_green']};")
                else:
                    self.last_activity_label.setText(f"{int(elapsed)}s ago")
                    self.traffic_label.setText(f"{ICONS['warning']} No recent traffic")
                    self.traffic_label.setStyleSheet(f"color: {COLORS['accent_yellow']};")
            
            # Update device info
            if self.device_info['fw_major'] > 0:
                self.fw_version_label.setText(
                    f"v{self.device_info['fw_major']}.{self.device_info['fw_minor']}"
                )
            
            if self.device_info['uptime'] > 0:
                uptime = self.device_info['uptime']
                if uptime < 60:
                    self.uptime_label.setText(f"{uptime}s")
                elif uptime < 3600:
                    self.uptime_label.setText(f"{uptime // 60}m {uptime % 60}s")
                else:
                    self.uptime_label.setText(
                        f"{uptime // 3600}h {(uptime % 3600) // 60}m"
                    )

