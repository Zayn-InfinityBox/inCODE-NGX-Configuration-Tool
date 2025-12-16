"""
connection_page.py - Device connection page with clean glass design
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
        layout.setSpacing(24)
        layout.setContentsMargins(40, 24, 40, 24)
        
        # === LEFT PANEL - Connection controls ===
        left_panel = QWidget()
        left_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(55, 55, 55, 0.85);
                border: none;
                border-radius: 16px;
            }
        """)
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(28, 28, 28, 28)
        
        # Title
        title = QLabel("Connect Your Device")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent; border: none;")
        left_layout.addWidget(title)
        
        subtitle = QLabel("Plug in your GridConnect CANUSB COM FD")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.85); background: transparent; border: none; font-size: 13px;")
        left_layout.addWidget(subtitle)
        
        left_layout.addSpacing(12)
        
        # Port selection label
        port_label = QLabel("Serial Port")
        port_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        port_label.setStyleSheet("color: white; background: transparent; border: none;")
        left_layout.addWidget(port_label)
        
        # Port selection row
        port_row = QHBoxLayout()
        port_row.setSpacing(10)
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(44)
        self.port_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(30, 30, 30, 0.95);
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                color: white;
            }}
            QComboBox:hover {{
                background-color: rgba(40, 40, 40, 0.95);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid rgba(255,255,255,0.6);
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: rgba(45, 45, 45, 0.98);
                border: none;
                border-radius: 8px;
                selection-background-color: {COLORS['accent_primary']};
                color: white;
            }}
        """)
        port_row.addWidget(self.port_combo, 1)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMinimumWidth(80)
        self.refresh_btn.setMinimumHeight(44)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(70, 70, 70, 0.9);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 12px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_primary']};
            }}
        """)
        self.refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(self.refresh_btn)
        
        left_layout.addLayout(port_row)
        
        left_layout.addSpacing(8)
        
        # Status display - simple horizontal layout
        status_container = QWidget()
        status_container.setStyleSheet("""
            QWidget {
                background-color: rgba(35, 35, 35, 0.9);
                border: none;
                border-radius: 10px;
            }
        """)
        status_h = QHBoxLayout(status_container)
        status_h.setContentsMargins(16, 14, 16, 14)
        status_h.setSpacing(12)
        
        self.status_icon = QLabel(ICONS['disconnected'])
        self.status_icon.setFont(QFont("Arial", 24))
        self.status_icon.setStyleSheet("color: rgba(180,180,180,1.0); background: transparent; border: none;")
        self.status_icon.setFixedWidth(36)
        status_h.addWidget(self.status_icon)
        
        status_text_container = QWidget()
        status_text_container.setStyleSheet("background: transparent; border: none;")
        status_v = QVBoxLayout(status_text_container)
        status_v.setContentsMargins(0, 0, 0, 0)
        status_v.setSpacing(2)
        
        self.status_label = QLabel("Not connected")
        self.status_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: rgba(180,180,180,1.0); background: transparent; border: none;")
        status_v.addWidget(self.status_label)
        
        self.status_detail = QLabel("Select a port and click Connect")
        self.status_detail.setStyleSheet("color: rgba(200,200,200,1.0); font-size: 12px; background: transparent; border: none;")
        status_v.addWidget(self.status_detail)
        
        status_h.addWidget(status_text_container, 1)
        left_layout.addWidget(status_container)
        
        left_layout.addSpacing(8)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumHeight(50)
        self.connect_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_primary']};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_secondary']};
            }}
            QPushButton:disabled {{
                background-color: rgba(96, 176, 225, 0.4);
            }}
        """)
        self.connect_btn.clicked.connect(self._toggle_connection)
        left_layout.addWidget(self.connect_btn)
        
        # Separator line
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: rgba(255,255,255,0.1); border: none;")
        left_layout.addSpacing(12)
        left_layout.addWidget(separator)
        left_layout.addSpacing(12)
        
        # First-time setup section
        setup_title = QLabel("First-Time Device Setup")
        setup_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        setup_title.setStyleSheet("color: white; background: transparent; border: none;")
        left_layout.addWidget(setup_title)
        
        setup_desc = QLabel(
            "New device? Press the configure button on device for 3 seconds, then click below."
        )
        setup_desc.setWordWrap(True)
        setup_desc.setStyleSheet("color: rgba(200,200,200,1.0); font-size: 12px; background: transparent; border: none; line-height: 1.4;")
        left_layout.addWidget(setup_desc)
        
        left_layout.addSpacing(6)
        
        self.setup_btn = QPushButton("Configure for 250kbps")
        self.setup_btn.setMinimumHeight(42)
        self.setup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(70, 70, 70, 0.9);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_primary']};
            }}
        """)
        self.setup_btn.clicked.connect(self._run_first_time_setup)
        left_layout.addWidget(self.setup_btn)
        
        self.setup_status = QLabel("")
        self.setup_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; background: transparent; border: none;")
        self.setup_status.setMinimumHeight(20)
        left_layout.addWidget(self.setup_status)
        
        left_layout.addStretch()
        layout.addWidget(left_panel)
        
        # === RIGHT PANEL - Instructions and traffic log ===
        right_panel = QWidget()
        right_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(55, 55, 55, 0.85);
                border: none;
                border-radius: 16px;
            }
        """)
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(28, 28, 28, 28)
        
        # Instructions title
        instructions_label = QLabel("Setup Instructions")
        instructions_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        instructions_label.setStyleSheet("color: white; background: transparent; border: none;")
        right_layout.addWidget(instructions_label)
        
        # Steps - simple list
        steps = [
            "1. Connect the GridConnect CANUSB COM FD via USB",
            "2. Connect DB9 to your MASTERCELL's CAN network",
            "3. Ensure MASTERCELL is powered on",
            "4. Select the port (usually /dev/cu.usbserial-...)",
            "5. Click Connect to establish communication",
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet("color: rgba(210,210,210,1.0); font-size: 12px; background: transparent; border: none; padding: 4px 0;")
            step_label.setWordWrap(True)
            right_layout.addWidget(step_label)
        
        right_layout.addSpacing(12)
        
        # Traffic log title
        log_label = QLabel("CAN Traffic")
        log_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        log_label.setStyleSheet("color: white; background: transparent; border: none;")
        right_layout.addWidget(log_label)
        
        # Traffic log
        self.traffic_log = QTextEdit()
        self.traffic_log.setReadOnly(True)
        self.traffic_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(25, 25, 25, 0.95);
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 11px;
                color: rgba(255,255,255,0.7);
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
            self.status_icon.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none;")
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none;")
            self.status_detail.setText("Receiving CAN traffic")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border: none;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: #dc2626;
                }}
            """)
            self.traffic_log.clear()
            self.traffic_log.append("Connected! Waiting for CAN traffic...")
        else:
            self.status_icon.setText(ICONS['disconnected'])
            self.status_icon.setStyleSheet("color: rgba(180,180,180,1.0); background: transparent; border: none;")
            self.status_label.setText("Not connected")
            self.status_label.setStyleSheet("color: rgba(180,180,180,1.0); background: transparent; border: none;")
            self.status_detail.setText("Select a port and click Connect")
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent_primary']};
                    color: white;
                    border: none;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_secondary']};
                }}
            """)
        
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
        self.setup_status.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 12px; background: transparent; border: none;")
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
            
            self.setup_status.setText("✓ Setup complete! Click Connect to continue.")
            self.setup_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; background: transparent; border: none;")
            
            QMessageBox.information(self, "Setup Complete",
                "Device configured successfully!\n\n"
                "Release the CONFIG button and click Connect.")
            
        except Exception as e:
            self.setup_status.setText(f"Setup failed: {str(e)}")
            self.setup_status.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px; background: transparent; border: none;")
            QMessageBox.warning(self, "Setup Failed", f"Could not configure device:\n{str(e)}")
        
        finally:
            self.setup_btn.setEnabled(True)
