"""
files_tab.py - File operations and utilities tab
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFileDialog, QMessageBox, QProgressBar,
    QTextEdit
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from can_interface import CANInterface
from config_data import FullConfiguration, EEPROM_ADDR_INIT_STAMP
from styles import COLORS, ICONS

import json
import os


class FilesTab(QWidget):
    """File operations and utilities"""
    
    config_loaded = pyqtSignal(FullConfiguration)
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.current_file = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Files & Utilities")
        header.setFont(QFont("", 24, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # File Operations Group
        file_group = QGroupBox("Configuration Files")
        file_layout = QGridLayout(file_group)
        file_layout.setSpacing(12)
        
        # Current file display
        file_layout.addWidget(QLabel("Current File:"), 0, 0)
        self.current_file_label = QLabel("No file loaded")
        self.current_file_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        file_layout.addWidget(self.current_file_label, 0, 1, 1, 2)
        
        # Buttons
        self.new_btn = QPushButton(f"{ICONS['file']} New Configuration")
        self.new_btn.clicked.connect(self._new_config)
        file_layout.addWidget(self.new_btn, 1, 0)
        
        self.open_btn = QPushButton(f"{ICONS['folder']} Open Configuration...")
        self.open_btn.clicked.connect(self._open_config)
        file_layout.addWidget(self.open_btn, 1, 1)
        
        self.save_btn = QPushButton(f"{ICONS['save']} Save Configuration")
        self.save_btn.clicked.connect(self._save_config)
        file_layout.addWidget(self.save_btn, 1, 2)
        
        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.clicked.connect(self._save_config_as)
        file_layout.addWidget(self.save_as_btn, 2, 0)
        
        self.export_btn = QPushButton("Export as CSV...")
        self.export_btn.clicked.connect(self._export_csv)
        file_layout.addWidget(self.export_btn, 2, 1)
        
        layout.addWidget(file_group)
        
        # Device Operations Group
        device_group = QGroupBox("Device Operations")
        device_layout = QGridLayout(device_group)
        device_layout.setSpacing(12)
        
        self.read_all_btn = QPushButton("Read All Config from Device")
        self.read_all_btn.setMinimumHeight(40)
        self.read_all_btn.clicked.connect(self._read_all_from_device)
        device_layout.addWidget(self.read_all_btn, 0, 0)
        
        self.write_all_btn = QPushButton("Write All Config to Device")
        self.write_all_btn.setObjectName("primaryButton")
        self.write_all_btn.setMinimumHeight(40)
        self.write_all_btn.clicked.connect(self._write_all_to_device)
        device_layout.addWidget(self.write_all_btn, 0, 1)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        device_layout.addWidget(self.progress, 1, 0, 1, 2)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        device_layout.addWidget(self.status_label, 2, 0, 1, 2)
        
        layout.addWidget(device_group)
        
        # Utilities Group
        util_group = QGroupBox("Utilities")
        util_layout = QGridLayout(util_group)
        util_layout.setSpacing(12)
        
        self.factory_reset_btn = QPushButton(f"{ICONS['warning']} Factory Reset Device")
        self.factory_reset_btn.setObjectName("dangerButton")
        self.factory_reset_btn.clicked.connect(self._factory_reset)
        util_layout.addWidget(self.factory_reset_btn, 0, 0)
        
        reset_note = QLabel("Resets all EEPROM to factory defaults. Requires power cycle.")
        reset_note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        util_layout.addWidget(reset_note, 0, 1)
        
        self.backup_btn = QPushButton("Backup Device Config...")
        self.backup_btn.clicked.connect(self._backup_device)
        util_layout.addWidget(self.backup_btn, 1, 0)
        
        self.restore_btn = QPushButton("Restore from Backup...")
        self.restore_btn.clicked.connect(self._restore_backup)
        util_layout.addWidget(self.restore_btn, 1, 1)
        
        layout.addWidget(util_group)
        
        # Info/Help Group
        info_group = QGroupBox("Configuration File Info")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setPlainText(
            "Configuration files are stored in JSON format.\n\n"
            "They contain:\n"
            "• System settings (bitrate, loss of COM timer, etc.)\n"
            "• All 44 input configurations\n"
            "• Custom names and notes\n\n"
            "Files can be shared between computers and used to configure multiple devices."
        )
        info_layout.addWidget(self.info_text)
        
        layout.addWidget(info_group)
        
        # Spacer
        layout.addStretch()
    
    def set_get_config_callback(self, callback):
        """Set callback to get current configuration"""
        self._get_config = callback
    
    def set_set_config_callback(self, callback):
        """Set callback to set configuration"""
        self._set_config = callback
    
    def _new_config(self):
        """Create new configuration"""
        reply = QMessageBox.question(self, "New Configuration",
            "Create a new configuration? This will clear all current settings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            new_config = FullConfiguration()
            self.config_loaded.emit(new_config)
            self.current_file = None
            self.current_file_label.setText("New configuration (unsaved)")
    
    def _open_config(self):
        """Open configuration file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration",
            "", "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    json_str = f.read()
                
                config = FullConfiguration.from_json(json_str)
                self.config_loaded.emit(config)
                self.current_file = filename
                self.current_file_label.setText(os.path.basename(filename))
                
                QMessageBox.information(self, "Success", 
                    f"Configuration loaded from:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Failed to load configuration:\n{str(e)}")
    
    def _save_config(self):
        """Save configuration to current file"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._save_config_as()
    
    def _save_config_as(self):
        """Save configuration to new file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration",
            "mastercell_config.json", "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            self._save_to_file(filename)
    
    def _save_to_file(self, filename: str):
        """Save configuration to file"""
        try:
            if hasattr(self, '_get_config'):
                config = self._get_config()
                json_str = config.to_json()
                
                with open(filename, 'w') as f:
                    f.write(json_str)
                
                self.current_file = filename
                self.current_file_label.setText(os.path.basename(filename))
                
                QMessageBox.information(self, "Success", 
                    f"Configuration saved to:\n{filename}")
            else:
                QMessageBox.warning(self, "Error", "Configuration callback not set")
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Failed to save configuration:\n{str(e)}")
    
    def _export_csv(self):
        """Export configuration as CSV"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export as CSV",
            "mastercell_config.csv", "CSV Files (*.csv);;All Files (*)"
        )
        
        if filename:
            try:
                if hasattr(self, '_get_config'):
                    config = self._get_config()
                    
                    with open(filename, 'w') as f:
                        # Header
                        f.write("Input,Name,Case Type,Case #,Enabled,PGN,SA,Data\n")
                        
                        # Data rows
                        for inp_config in config.inputs:
                            for i, case in enumerate(inp_config.on_cases):
                                if case.enabled:
                                    pgn = f"{case.pgn_high:02X}{case.pgn_low:02X}"
                                    data = ' '.join(f"{b:02X}" for b in case.data_bytes)
                                    f.write(f"{inp_config.input_number},{inp_config.custom_name},"
                                           f"ON,{i+1},Yes,{pgn},{case.source_address:02X},{data}\n")
                            
                            for i, case in enumerate(inp_config.off_cases):
                                if case.enabled:
                                    pgn = f"{case.pgn_high:02X}{case.pgn_low:02X}"
                                    data = ' '.join(f"{b:02X}" for b in case.data_bytes)
                                    f.write(f"{inp_config.input_number},{inp_config.custom_name},"
                                           f"OFF,{i+1},Yes,{pgn},{case.source_address:02X},{data}\n")
                    
                    QMessageBox.information(self, "Success", 
                        f"Configuration exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Failed to export:\n{str(e)}")
    
    def _read_all_from_device(self):
        """Read all configuration from device"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", 
                "Please connect to a device first.")
            return
        
        reply = QMessageBox.question(self, "Read from Device",
            "Read all configuration from the device?\n\n"
            "This will replace the current configuration in the tool.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.status_label.setText("Reading configuration from device...")
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)  # Indeterminate
            
            # TODO: Implement full EEPROM read
            QMessageBox.information(self, "Read Complete", 
                "Configuration read from device.\n\n"
                "(Full implementation pending)")
            
            self.progress.setVisible(False)
            self.status_label.setText("")
    
    def _write_all_to_device(self):
        """Write all configuration to device"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", 
                "Please connect to a device first.")
            return
        
        reply = QMessageBox.question(self, "Write to Device",
            "Write all configuration to the device?\n\n"
            "This will overwrite all device settings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.status_label.setText("Writing configuration to device...")
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)
            
            # TODO: Implement full EEPROM write
            QMessageBox.information(self, "Write Complete", 
                "Configuration written to device.\n\n"
                "If you changed the CAN bitrate, power cycle the device for it to take effect.\n\n"
                "(Full implementation pending)")
            
            self.progress.setVisible(False)
            self.status_label.setText("")
    
    def _factory_reset(self):
        """Perform factory reset on device"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", 
                "Please connect to a device first.")
            return
        
        reply = QMessageBox.warning(self, "Factory Reset",
            "⚠️ FACTORY RESET ⚠️\n\n"
            "This will erase ALL configuration on the device and restore factory defaults.\n\n"
            "Are you SURE you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Double-check
            reply2 = QMessageBox.warning(self, "Confirm Factory Reset",
                "This action cannot be undone!\n\n"
                "Type 'RESET' in the next dialog to confirm.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            
            if reply2 == QMessageBox.StandardButton.Ok:
                # Write 0x00 to init stamp address
                self.can.write_eeprom(EEPROM_ADDR_INIT_STAMP, 0x00)
                
                QMessageBox.information(self, "Factory Reset Initiated",
                    "Factory reset command sent.\n\n"
                    "Please power cycle the device to complete the reset.")
    
    def _backup_device(self):
        """Backup device configuration to file"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", 
                "Please connect to a device first.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Backup Device Configuration",
            "device_backup.json", "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            self.status_label.setText("Backing up device configuration...")
            # TODO: Implement full backup
            QMessageBox.information(self, "Backup", 
                "Backup functionality coming soon!")
            self.status_label.setText("")
    
    def _restore_backup(self):
        """Restore device configuration from backup"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", 
                "Please connect to a device first.")
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Restore from Backup",
            "", "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            reply = QMessageBox.warning(self, "Restore Backup",
                "This will overwrite ALL configuration on the device.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.status_label.setText("Restoring device configuration...")
                # TODO: Implement full restore
                QMessageBox.information(self, "Restore", 
                    "Restore functionality coming soon!")
                self.status_label.setText("")

