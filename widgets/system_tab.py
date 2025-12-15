"""
system_tab.py - System configuration tab
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QSpinBox, QLineEdit,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from can_interface import CANInterface
from config_data import (
    SystemConfig, BitrateCode, LossOfComTimer, RebroadcastMode,
    EEPROM_ADDR_BITRATE, EEPROM_ADDR_HB_PGN_HIGH, EEPROM_ADDR_HB_PGN_LOW,
    EEPROM_ADDR_HB_SA, EEPROM_ADDR_REBROADCAST, EEPROM_ADDR_SERIAL,
    EEPROM_ADDR_WR_PGN_HIGH, EEPROM_ADDR_WR_PGN_LOW, EEPROM_ADDR_WR_SA,
    EEPROM_ADDR_RD_PGN_HIGH, EEPROM_ADDR_RD_PGN_LOW, EEPROM_ADDR_RD_SA,
    EEPROM_ADDR_RSP_PGN_HIGH, EEPROM_ADDR_RSP_PGN_LOW, EEPROM_ADDR_RSP_SA,
    EEPROM_ADDR_DIAG_PGN_HIGH, EEPROM_ADDR_DIAG_PGN_LOW, EEPROM_ADDR_DIAG_SA
)
from styles import COLORS


class SystemTab(QWidget):
    """System configuration settings"""
    
    config_changed = pyqtSignal()
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.config = SystemConfig()
        self._pending_reads = []
        self._pending_writes = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("System Configuration")
        header.setFont(QFont("", 24, QFont.Weight.Bold))
        layout.addWidget(header)
        
        subtitle = QLabel("Configure CAN bus settings and device parameters")
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # CAN Settings Group
        can_group = QGroupBox("CAN Bus Settings")
        can_layout = QGridLayout(can_group)
        can_layout.setSpacing(12)
        
        # Bitrate
        can_layout.addWidget(QLabel("CAN Bitrate:"), 0, 0)
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItem("250 kbps (Standard J1939)", BitrateCode.KBPS_250)
        self.bitrate_combo.addItem("500 kbps (High Speed)", BitrateCode.KBPS_500)
        self.bitrate_combo.addItem("1 Mbps (Maximum)", BitrateCode.MBPS_1)
        can_layout.addWidget(self.bitrate_combo, 0, 1)
        
        bitrate_note = QLabel("⚠ Requires power cycle to take effect")
        bitrate_note.setStyleSheet(f"color: {COLORS['accent_yellow']}; font-size: 11px;")
        can_layout.addWidget(bitrate_note, 0, 2)
        
        # Rebroadcast Mode
        can_layout.addWidget(QLabel("Rebroadcast Mode:"), 1, 0)
        self.rebroadcast_combo = QComboBox()
        self.rebroadcast_combo.addItem("Edge-Triggered (on state change)", RebroadcastMode.EDGE_TRIGGERED)
        self.rebroadcast_combo.addItem("Periodic (every 1 second)", RebroadcastMode.PERIODIC)
        can_layout.addWidget(self.rebroadcast_combo, 1, 1)
        
        rebroadcast_note = QLabel("Edge-triggered minimizes bus load")
        rebroadcast_note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        can_layout.addWidget(rebroadcast_note, 1, 2)
        
        layout.addWidget(can_group)
        
        # Heartbeat Message Group
        hb_group = QGroupBox("Heartbeat Message Configuration")
        hb_layout = QGridLayout(hb_group)
        hb_layout.setSpacing(12)
        
        hb_layout.addWidget(QLabel("Heartbeat PGN:"), 0, 0)
        self.hb_pgn_high = QLineEdit("FF")
        self.hb_pgn_high.setMaximumWidth(60)
        self.hb_pgn_high.setPlaceholderText("High")
        hb_layout.addWidget(self.hb_pgn_high, 0, 1)
        
        self.hb_pgn_low = QLineEdit("06")
        self.hb_pgn_low.setMaximumWidth(60)
        self.hb_pgn_low.setPlaceholderText("Low")
        hb_layout.addWidget(self.hb_pgn_low, 0, 2)
        
        hb_pgn_note = QLabel("Default: FF06 (65286)")
        hb_pgn_note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        hb_layout.addWidget(hb_pgn_note, 0, 3)
        
        hb_layout.addWidget(QLabel("Heartbeat SA:"), 1, 0)
        self.hb_sa = QSpinBox()
        self.hb_sa.setRange(0, 253)
        self.hb_sa.setValue(0x80)
        self.hb_sa.setDisplayIntegerBase(16)
        self.hb_sa.setPrefix("0x")
        hb_layout.addWidget(self.hb_sa, 1, 1, 1, 2)
        
        layout.addWidget(hb_group)
        
        # Diagnostic Message Group
        diag_group = QGroupBox("Diagnostic Message Configuration")
        diag_layout = QGridLayout(diag_group)
        diag_layout.setSpacing(12)
        
        diag_layout.addWidget(QLabel("Diagnostic PGN:"), 0, 0)
        self.diag_pgn_high = QLineEdit("FF")
        self.diag_pgn_high.setMaximumWidth(60)
        diag_layout.addWidget(self.diag_pgn_high, 0, 1)
        
        self.diag_pgn_low = QLineEdit("46")
        self.diag_pgn_low.setMaximumWidth(60)
        diag_layout.addWidget(self.diag_pgn_low, 0, 2)
        
        diag_layout.addWidget(QLabel("Diagnostic SA:"), 1, 0)
        self.diag_sa = QSpinBox()
        self.diag_sa.setRange(0, 253)
        self.diag_sa.setValue(0x80)
        self.diag_sa.setDisplayIntegerBase(16)
        self.diag_sa.setPrefix("0x")
        diag_layout.addWidget(self.diag_sa, 1, 1, 1, 2)
        
        layout.addWidget(diag_group)
        
        # EEPROM Command Configuration (Advanced)
        eeprom_group = QGroupBox("EEPROM Command Configuration (Advanced)")
        eeprom_layout = QGridLayout(eeprom_group)
        eeprom_layout.setSpacing(12)
        
        # Write PGN
        eeprom_layout.addWidget(QLabel("Write Request PGN:"), 0, 0)
        self.wr_pgn_high = QLineEdit("FF")
        self.wr_pgn_high.setMaximumWidth(60)
        eeprom_layout.addWidget(self.wr_pgn_high, 0, 1)
        self.wr_pgn_low = QLineEdit("16")
        self.wr_pgn_low.setMaximumWidth(60)
        eeprom_layout.addWidget(self.wr_pgn_low, 0, 2)
        self.wr_sa = QSpinBox()
        self.wr_sa.setRange(0, 253)
        self.wr_sa.setValue(0x80)
        self.wr_sa.setDisplayIntegerBase(16)
        self.wr_sa.setPrefix("0x")
        eeprom_layout.addWidget(self.wr_sa, 0, 3)
        
        # Read PGN
        eeprom_layout.addWidget(QLabel("Read Request PGN:"), 1, 0)
        self.rd_pgn_high = QLineEdit("FF")
        self.rd_pgn_high.setMaximumWidth(60)
        eeprom_layout.addWidget(self.rd_pgn_high, 1, 1)
        self.rd_pgn_low = QLineEdit("26")
        self.rd_pgn_low.setMaximumWidth(60)
        eeprom_layout.addWidget(self.rd_pgn_low, 1, 2)
        self.rd_sa = QSpinBox()
        self.rd_sa.setRange(0, 253)
        self.rd_sa.setValue(0x80)
        self.rd_sa.setDisplayIntegerBase(16)
        self.rd_sa.setPrefix("0x")
        eeprom_layout.addWidget(self.rd_sa, 1, 3)
        
        # Response PGN
        eeprom_layout.addWidget(QLabel("Response PGN:"), 2, 0)
        self.rsp_pgn_high = QLineEdit("FF")
        self.rsp_pgn_high.setMaximumWidth(60)
        eeprom_layout.addWidget(self.rsp_pgn_high, 2, 1)
        self.rsp_pgn_low = QLineEdit("36")
        self.rsp_pgn_low.setMaximumWidth(60)
        eeprom_layout.addWidget(self.rsp_pgn_low, 2, 2)
        self.rsp_sa = QSpinBox()
        self.rsp_sa.setRange(0, 253)
        self.rsp_sa.setValue(0x80)
        self.rsp_sa.setDisplayIntegerBase(16)
        self.rsp_sa.setPrefix("0x")
        eeprom_layout.addWidget(self.rsp_sa, 2, 3)
        
        warning_label = QLabel("⚠ Changing these values affects how you communicate with the device!")
        warning_label.setStyleSheet(f"color: {COLORS['accent_orange']}; font-size: 11px; padding: 8px;")
        eeprom_layout.addWidget(warning_label, 3, 0, 1, 4)
        
        layout.addWidget(eeprom_group)
        
        # Device Info Group
        info_group = QGroupBox("Device Identification")
        info_layout = QGridLayout(info_group)
        info_layout.setSpacing(12)
        
        info_layout.addWidget(QLabel("Serial Number:"), 0, 0)
        self.serial_num = QSpinBox()
        self.serial_num.setRange(0, 255)
        self.serial_num.setValue(0x42)
        info_layout.addWidget(self.serial_num, 0, 1)
        
        layout.addWidget(info_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.read_btn = QPushButton("Read from Device")
        self.read_btn.clicked.connect(self._read_from_device)
        btn_layout.addWidget(self.read_btn)
        
        self.write_btn = QPushButton("Write to Device")
        self.write_btn.setObjectName("primaryButton")
        self.write_btn.clicked.connect(self._write_to_device)
        btn_layout.addWidget(self.write_btn)
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(self.reset_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Spacer
        layout.addStretch()
    
    def _connect_signals(self):
        self.can.eeprom_read_complete.connect(self._on_eeprom_read)
        self.can.eeprom_write_complete.connect(self._on_eeprom_write)
    
    def _read_from_device(self):
        """Read all system config from device"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a device first.")
            return
        
        # Queue read operations
        self._pending_reads = [
            EEPROM_ADDR_BITRATE,
            EEPROM_ADDR_REBROADCAST,
            EEPROM_ADDR_HB_PGN_HIGH,
            EEPROM_ADDR_HB_PGN_LOW,
            EEPROM_ADDR_HB_SA,
            EEPROM_ADDR_DIAG_PGN_HIGH,
            EEPROM_ADDR_DIAG_PGN_LOW,
            EEPROM_ADDR_DIAG_SA,
            EEPROM_ADDR_WR_PGN_HIGH,
            EEPROM_ADDR_WR_PGN_LOW,
            EEPROM_ADDR_WR_SA,
            EEPROM_ADDR_RD_PGN_HIGH,
            EEPROM_ADDR_RD_PGN_LOW,
            EEPROM_ADDR_RD_SA,
            EEPROM_ADDR_RSP_PGN_HIGH,
            EEPROM_ADDR_RSP_PGN_LOW,
            EEPROM_ADDR_RSP_SA,
            EEPROM_ADDR_SERIAL,
        ]
        
        self.progress.setMaximum(len(self._pending_reads))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        
        # Start reading
        self._read_next()
    
    def _read_next(self):
        """Read next pending address"""
        if self._pending_reads:
            addr = self._pending_reads[0]
            self.can.read_eeprom(addr)
    
    def _on_eeprom_read(self, address: int, value: int):
        """Handle EEPROM read response"""
        if address in self._pending_reads:
            self._pending_reads.remove(address)
            self.progress.setValue(self.progress.maximum() - len(self._pending_reads))
            
            # Update UI based on address
            if value >= 0:
                self._update_field_from_eeprom(address, value)
            
            # Read next or finish
            if self._pending_reads:
                QTimer.singleShot(50, self._read_next)
            else:
                self.progress.setVisible(False)
    
    def _update_field_from_eeprom(self, address: int, value: int):
        """Update UI field from EEPROM value"""
        if address == EEPROM_ADDR_BITRATE:
            idx = self.bitrate_combo.findData(value)
            if idx >= 0:
                self.bitrate_combo.setCurrentIndex(idx)
        elif address == EEPROM_ADDR_REBROADCAST:
            idx = self.rebroadcast_combo.findData(value)
            if idx >= 0:
                self.rebroadcast_combo.setCurrentIndex(idx)
        elif address == EEPROM_ADDR_HB_PGN_HIGH:
            self.hb_pgn_high.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_HB_PGN_LOW:
            self.hb_pgn_low.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_HB_SA:
            self.hb_sa.setValue(value)
        elif address == EEPROM_ADDR_DIAG_PGN_HIGH:
            self.diag_pgn_high.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_DIAG_PGN_LOW:
            self.diag_pgn_low.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_DIAG_SA:
            self.diag_sa.setValue(value)
        elif address == EEPROM_ADDR_WR_PGN_HIGH:
            self.wr_pgn_high.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_WR_PGN_LOW:
            self.wr_pgn_low.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_WR_SA:
            self.wr_sa.setValue(value)
        elif address == EEPROM_ADDR_RD_PGN_HIGH:
            self.rd_pgn_high.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_RD_PGN_LOW:
            self.rd_pgn_low.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_RD_SA:
            self.rd_sa.setValue(value)
        elif address == EEPROM_ADDR_RSP_PGN_HIGH:
            self.rsp_pgn_high.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_RSP_PGN_LOW:
            self.rsp_pgn_low.setText(f"{value:02X}")
        elif address == EEPROM_ADDR_RSP_SA:
            self.rsp_sa.setValue(value)
        elif address == EEPROM_ADDR_SERIAL:
            self.serial_num.setValue(value)
    
    def _write_to_device(self):
        """Write system config to device"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a device first.")
            return
        
        # Build write list
        self._pending_writes = [
            (EEPROM_ADDR_BITRATE, self.bitrate_combo.currentData()),
            (EEPROM_ADDR_REBROADCAST, self.rebroadcast_combo.currentData()),
            (EEPROM_ADDR_HB_PGN_HIGH, int(self.hb_pgn_high.text(), 16)),
            (EEPROM_ADDR_HB_PGN_LOW, int(self.hb_pgn_low.text(), 16)),
            (EEPROM_ADDR_HB_SA, self.hb_sa.value()),
            (EEPROM_ADDR_DIAG_PGN_HIGH, int(self.diag_pgn_high.text(), 16)),
            (EEPROM_ADDR_DIAG_PGN_LOW, int(self.diag_pgn_low.text(), 16)),
            (EEPROM_ADDR_DIAG_SA, self.diag_sa.value()),
            (EEPROM_ADDR_SERIAL, self.serial_num.value()),
        ]
        
        self.progress.setMaximum(len(self._pending_writes))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        
        self._write_next()
    
    def _write_next(self):
        """Write next pending value"""
        if self._pending_writes:
            addr, value = self._pending_writes[0]
            self.can.write_eeprom(addr, value)
    
    def _on_eeprom_write(self, address: int, success: bool):
        """Handle EEPROM write response"""
        if self._pending_writes and self._pending_writes[0][0] == address:
            self._pending_writes.pop(0)
            self.progress.setValue(self.progress.maximum() - len(self._pending_writes))
            
            if not success:
                QMessageBox.warning(self, "Write Failed", 
                    f"Failed to write to address 0x{address:04X}")
            
            if self._pending_writes:
                QTimer.singleShot(50, self._write_next)
            else:
                self.progress.setVisible(False)
                QMessageBox.information(self, "Success", 
                    "Configuration written successfully!\n\n"
                    "Note: If you changed the bitrate, power cycle the device for it to take effect.")
    
    def _reset_to_defaults(self):
        """Reset UI to default values"""
        reply = QMessageBox.question(self, "Reset to Defaults",
            "Reset all system settings to factory defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.bitrate_combo.setCurrentIndex(0)  # 250 kbps
            self.rebroadcast_combo.setCurrentIndex(0)  # Edge-triggered
            self.hb_pgn_high.setText("FF")
            self.hb_pgn_low.setText("06")
            self.hb_sa.setValue(0x80)
            self.diag_pgn_high.setText("FF")
            self.diag_pgn_low.setText("46")
            self.diag_sa.setValue(0x80)
            self.wr_pgn_high.setText("FF")
            self.wr_pgn_low.setText("16")
            self.wr_sa.setValue(0x80)
            self.rd_pgn_high.setText("FF")
            self.rd_pgn_low.setText("26")
            self.rd_sa.setValue(0x80)
            self.rsp_pgn_high.setText("FF")
            self.rsp_pgn_low.setText("36")
            self.rsp_sa.setValue(0x80)
            self.serial_num.setValue(0x42)
    
    def get_config(self) -> SystemConfig:
        """Get current configuration from UI"""
        return SystemConfig(
            bitrate=self.bitrate_combo.currentData(),
            rebroadcast_mode=self.rebroadcast_combo.currentData(),
            heartbeat_pgn_high=int(self.hb_pgn_high.text(), 16),
            heartbeat_pgn_low=int(self.hb_pgn_low.text(), 16),
            heartbeat_sa=self.hb_sa.value(),
            diagnostic_pgn_high=int(self.diag_pgn_high.text(), 16),
            diagnostic_pgn_low=int(self.diag_pgn_low.text(), 16),
            diagnostic_sa=self.diag_sa.value(),
            write_pgn_high=int(self.wr_pgn_high.text(), 16),
            write_pgn_low=int(self.wr_pgn_low.text(), 16),
            write_sa=self.wr_sa.value(),
            read_pgn_high=int(self.rd_pgn_high.text(), 16),
            read_pgn_low=int(self.rd_pgn_low.text(), 16),
            read_sa=self.rd_sa.value(),
            response_pgn_high=int(self.rsp_pgn_high.text(), 16),
            response_pgn_low=int(self.rsp_pgn_low.text(), 16),
            response_sa=self.rsp_sa.value(),
            serial_number=self.serial_num.value(),
        )
    
    def set_config(self, config: SystemConfig):
        """Load configuration into UI"""
        idx = self.bitrate_combo.findData(config.bitrate)
        if idx >= 0:
            self.bitrate_combo.setCurrentIndex(idx)
        
        idx = self.rebroadcast_combo.findData(config.rebroadcast_mode)
        if idx >= 0:
            self.rebroadcast_combo.setCurrentIndex(idx)
        
        self.hb_pgn_high.setText(f"{config.heartbeat_pgn_high:02X}")
        self.hb_pgn_low.setText(f"{config.heartbeat_pgn_low:02X}")
        self.hb_sa.setValue(config.heartbeat_sa)
        
        self.diag_pgn_high.setText(f"{config.diagnostic_pgn_high:02X}")
        self.diag_pgn_low.setText(f"{config.diagnostic_pgn_low:02X}")
        self.diag_sa.setValue(config.diagnostic_sa)
        
        self.wr_pgn_high.setText(f"{config.write_pgn_high:02X}")
        self.wr_pgn_low.setText(f"{config.write_pgn_low:02X}")
        self.wr_sa.setValue(config.write_sa)
        
        self.rd_pgn_high.setText(f"{config.read_pgn_high:02X}")
        self.rd_pgn_low.setText(f"{config.read_pgn_low:02X}")
        self.rd_sa.setValue(config.read_sa)
        
        self.rsp_pgn_high.setText(f"{config.response_pgn_high:02X}")
        self.rsp_pgn_low.setText(f"{config.response_pgn_low:02X}")
        self.rsp_sa.setValue(config.response_sa)
        
        self.serial_num.setValue(config.serial_number)

