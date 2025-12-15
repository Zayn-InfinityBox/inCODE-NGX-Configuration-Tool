"""
monitor_tab.py - CAN traffic monitor tab
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QCheckBox, QLineEdit, QGroupBox,
    QGridLayout, QSpinBox
)
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor

from can_interface import CANInterface, CANMessage
from styles import COLORS, ICONS
import time


class MonitorTab(QWidget):
    """CAN traffic monitor with filtering and message sending"""
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.is_paused = False
        self.message_count = 0
        self.start_time = time.time()
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QLabel("CAN Bus Monitor")
        header.setFont(QFont("", 24, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Controls row
        controls_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton(f"⏸ Pause")
        self.pause_btn.clicked.connect(self._toggle_pause)
        controls_layout.addWidget(self.pause_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_log)
        controls_layout.addWidget(self.clear_btn)
        
        controls_layout.addWidget(QLabel("Filter PGN:"))
        self.pgn_filter = QLineEdit()
        self.pgn_filter.setPlaceholderText("e.g., FF00")
        self.pgn_filter.setMaximumWidth(100)
        controls_layout.addWidget(self.pgn_filter)
        
        controls_layout.addWidget(QLabel("Filter SA:"))
        self.sa_filter = QLineEdit()
        self.sa_filter.setPlaceholderText("e.g., 10")
        self.sa_filter.setMaximumWidth(80)
        controls_layout.addWidget(self.sa_filter)
        
        self.show_raw = QCheckBox("Show Raw Hex")
        controls_layout.addWidget(self.show_raw)
        
        controls_layout.addStretch()
        
        self.msg_count_label = QLabel("Messages: 0")
        controls_layout.addWidget(self.msg_count_label)
        
        layout.addLayout(controls_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("JetBrains Mono", 11))
        self.log_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_default']};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self.log_display)
        
        # Send message section
        send_group = QGroupBox("Send CAN Message")
        send_layout = QGridLayout(send_group)
        
        send_layout.addWidget(QLabel("CAN ID (hex):"), 0, 0)
        self.send_id_edit = QLineEdit("18FF0110")
        self.send_id_edit.setMaximumWidth(120)
        send_layout.addWidget(self.send_id_edit, 0, 1)
        
        self.extended_check = QCheckBox("Extended (29-bit)")
        self.extended_check.setChecked(True)
        send_layout.addWidget(self.extended_check, 0, 2)
        
        send_layout.addWidget(QLabel("Data (hex):"), 1, 0)
        self.send_data_edit = QLineEdit("00 00 00 00 00 00 00 00")
        send_layout.addWidget(self.send_data_edit, 1, 1, 1, 2)
        
        self.send_btn = QPushButton("Send Message")
        self.send_btn.setObjectName("primaryButton")
        self.send_btn.clicked.connect(self._send_message)
        send_layout.addWidget(self.send_btn, 0, 3, 2, 1)
        
        layout.addWidget(send_group)
        
        # J1939 Message Builder
        j1939_group = QGroupBox("J1939 Message Builder")
        j1939_layout = QGridLayout(j1939_group)
        
        j1939_layout.addWidget(QLabel("Priority:"), 0, 0)
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 7)
        self.priority_spin.setValue(6)
        j1939_layout.addWidget(self.priority_spin, 0, 1)
        
        j1939_layout.addWidget(QLabel("PGN (hex):"), 0, 2)
        self.pgn_edit = QLineEdit("FF01")
        self.pgn_edit.setMaximumWidth(80)
        j1939_layout.addWidget(self.pgn_edit, 0, 3)
        
        j1939_layout.addWidget(QLabel("SA (hex):"), 0, 4)
        self.sa_edit = QLineEdit("10")
        self.sa_edit.setMaximumWidth(60)
        j1939_layout.addWidget(self.sa_edit, 0, 5)
        
        j1939_layout.addWidget(QLabel("Data:"), 1, 0)
        self.j1939_data_edit = QLineEdit("01 00 00 00 00 00 00 00")
        j1939_layout.addWidget(self.j1939_data_edit, 1, 1, 1, 4)
        
        self.j1939_send_btn = QPushButton("Send J1939")
        self.j1939_send_btn.clicked.connect(self._send_j1939)
        j1939_layout.addWidget(self.j1939_send_btn, 1, 5)
        
        layout.addWidget(j1939_group)
    
    def _connect_signals(self):
        self.can.message_received.connect(self._on_message)
        self.can.raw_received.connect(self._on_raw)
    
    def _toggle_pause(self):
        """Toggle pause state"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("▶ Resume")
        else:
            self.pause_btn.setText("⏸ Pause")
    
    def _clear_log(self):
        """Clear the log display"""
        self.log_display.clear()
        self.message_count = 0
        self.start_time = time.time()
        self.msg_count_label.setText("Messages: 0")
    
    def _on_message(self, msg: CANMessage):
        """Handle received CAN message"""
        if self.is_paused:
            return
        
        # Apply filters
        pgn_filter = self.pgn_filter.text().strip()
        if pgn_filter:
            try:
                filter_pgn = int(pgn_filter, 16)
                if msg.pgn != filter_pgn:
                    return
            except ValueError:
                pass
        
        sa_filter = self.sa_filter.text().strip()
        if sa_filter:
            try:
                filter_sa = int(sa_filter, 16)
                if msg.source_address != filter_sa:
                    return
            except ValueError:
                pass
        
        self.message_count += 1
        self.msg_count_label.setText(f"Messages: {self.message_count}")
        
        # Format message
        elapsed = time.time() - self.start_time
        timestamp = f"[{elapsed:8.3f}]"
        
        if msg.extended:
            id_str = f"EXT 0x{msg.can_id:08X}"
            pgn_str = f"PGN=0x{msg.pgn:04X}"
            sa_str = f"SA=0x{msg.source_address:02X}"
        else:
            id_str = f"STD 0x{msg.can_id:03X}"
            pgn_str = ""
            sa_str = ""
        
        data_str = ' '.join(f"{b:02X}" for b in msg.data)
        
        if msg.extended:
            line = f"{timestamp} RX {id_str} {pgn_str} {sa_str} Data=[{data_str}]"
        else:
            line = f"{timestamp} RX {id_str} Data=[{data_str}]"
        
        self._append_log(line, COLORS['accent_blue'])
    
    def _on_raw(self, data: str):
        """Handle raw data (optional display)"""
        if self.show_raw.isChecked() and not self.is_paused:
            self._append_log(f"RAW: {data}", COLORS['text_muted'])
    
    def _append_log(self, text: str, color: str = None):
        """Append text to log display"""
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if color:
            html = f'<span style="color: {color}">{text}</span><br>'
            cursor.insertHtml(html)
        else:
            cursor.insertText(text + "\n")
        
        self.log_display.setTextCursor(cursor)
        self.log_display.ensureCursorVisible()
        
        # Limit log size
        if self.log_display.document().blockCount() > 1000:
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, 
                              QTextCursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
    
    def _send_message(self):
        """Send CAN message"""
        if not self.can.is_connected():
            self._append_log("ERROR: Not connected", COLORS['accent_red'])
            return
        
        try:
            can_id = int(self.send_id_edit.text().replace(" ", ""), 16)
            data_str = self.send_data_edit.text().replace(" ", "")
            data = bytes.fromhex(data_str)
            extended = self.extended_check.isChecked()
            
            if self.can.send_message(can_id, data, extended):
                elapsed = time.time() - self.start_time
                id_str = f"0x{can_id:08X}" if extended else f"0x{can_id:03X}"
                data_disp = ' '.join(f"{b:02X}" for b in data)
                self._append_log(
                    f"[{elapsed:8.3f}] TX {id_str} Data=[{data_disp}]",
                    COLORS['accent_green']
                )
            else:
                self._append_log("ERROR: Send failed", COLORS['accent_red'])
        except ValueError as e:
            self._append_log(f"ERROR: Invalid input - {e}", COLORS['accent_red'])
    
    def _send_j1939(self):
        """Send J1939 message"""
        if not self.can.is_connected():
            self._append_log("ERROR: Not connected", COLORS['accent_red'])
            return
        
        try:
            priority = self.priority_spin.value()
            pgn = int(self.pgn_edit.text().replace(" ", ""), 16)
            sa = int(self.sa_edit.text().replace(" ", ""), 16)
            data_str = self.j1939_data_edit.text().replace(" ", "")
            data = bytes.fromhex(data_str)
            
            if self.can.send_j1939(priority, pgn, sa, data):
                elapsed = time.time() - self.start_time
                data_disp = ' '.join(f"{b:02X}" for b in data)
                self._append_log(
                    f"[{elapsed:8.3f}] TX J1939 P={priority} PGN=0x{pgn:04X} SA=0x{sa:02X} Data=[{data_disp}]",
                    COLORS['accent_green']
                )
            else:
                self._append_log("ERROR: Send failed", COLORS['accent_red'])
        except ValueError as e:
            self._append_log(f"ERROR: Invalid input - {e}", COLORS['accent_red'])

