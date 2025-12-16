"""
write_page.py - Write configuration to device with backup - glassmorphism design

Uses the EEPROM protocol to read/write configuration to the MASTERCELL NGX.
"""

import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont

from styles import COLORS, ICONS
from config_data import FullConfiguration, EEPROM_GUARD_BYTE
from can_interface import CANInterface, ConfigurationManager
from eeprom_protocol import (
    generate_full_config_write_operations,
    generate_system_read_operations,
    estimate_write_time,
    CASE_DATA_START, BYTES_PER_INPUT, TOTAL_INPUTS
)


class WritePage(QWidget):
    """Write configuration page with progress and backup - Glass style"""
    
    write_complete = pyqtSignal(bool)
    
    def __init__(self, can_interface: CANInterface, config: FullConfiguration,
                 backup_dir: str, config_dir: str, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.config = config
        self.backup_dir = backup_dir
        self.config_dir = config_dir
        self._complete = False
        self._config_manager: ConfigurationManager = None
        self._timestamp = None
        self._write_operations = []
        self._current_phase = ""  # 'backup', 'save', 'write'
        self._backup_data = {}
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setSpacing(32)
        layout.setContentsMargins(48, 32, 48, 32)
        
        # Left side - Status and controls (glass panel)
        left_panel = QFrame()
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(55, 55, 55, 0.85);
                border: none;
                border-radius: 16px;
            }}
        """)
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(24)
        left_layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        self.title = QLabel("Write Configuration")
        self.title.setFont(QFont("", 24, QFont.Weight.Bold))
        self.title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        left_layout.addWidget(self.title)
        
        self.subtitle = QLabel("Ready to write configuration to MASTERCELL")
        self.subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; background: transparent;")
        left_layout.addWidget(self.subtitle)
        
        left_layout.addSpacing(8)
        
        # Status display (inner glass panel)
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(35, 35, 35, 0.9);
                border: none;
                border-radius: 12px;
            }}
        """)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(24, 24, 24, 24)
        status_layout.setSpacing(20)
        
        # Status icon and text row
        status_row = QHBoxLayout()
        status_row.setSpacing(20)
        
        self.status_icon = QLabel("⏳")
        self.status_icon.setFont(QFont("", 48))
        self.status_icon.setStyleSheet("background: transparent;")
        status_row.addWidget(self.status_icon)
        
        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(6)
        
        self.status_label = QLabel("Click 'Write to Device' to begin")
        self.status_label.setFont(QFont("", 17, QFont.Weight.Bold))
        self.status_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        status_text_layout.addWidget(self.status_label)
        
        self.status_detail = QLabel("Your current MASTERCELL configuration will be backed up first")
        self.status_detail.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; background: transparent;")
        status_text_layout.addWidget(self.status_detail)
        
        status_row.addLayout(status_text_layout, 1)
        status_layout.addLayout(status_row)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(32)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(40, 40, 40, 0.9);
                border: none;
                border-radius: 6px;
                text-align: center;
                color: white;
                font-weight: 700;
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_primary']};
                border-radius: 6px;
            }}
        """)
        status_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(status_frame)
        
        # Write button
        self.write_btn = QPushButton("Write to Device")
        self.write_btn.setObjectName("primaryButton")
        self.write_btn.setMinimumHeight(56)
        self.write_btn.setFont(QFont("", 15, QFont.Weight.Bold))
        self.write_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_primary']};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_secondary']};
            }}
            QPushButton:disabled {{
                background-color: rgba(96, 176, 225, 0.4);
            }}
        """)
        self.write_btn.clicked.connect(self._start_write)
        left_layout.addWidget(self.write_btn)
        
        # Info boxes (clickable to open folder)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        
        backup_info = self._create_clickable_folder_box("Backup Location", self.backup_dir)
        info_layout.addWidget(backup_info)
        
        config_info = self._create_clickable_folder_box("Config Location", self.config_dir)
        info_layout.addWidget(config_info)
        
        left_layout.addLayout(info_layout)
        
        left_layout.addStretch()
        
        layout.addWidget(left_panel)
        
        # Right side - Log (glass panel)
        right_panel = QFrame()
        right_panel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(55, 55, 55, 0.85);
                border: none;
                border-radius: 16px;
            }}
        """)
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(32, 32, 32, 32)
        
        log_header = QLabel("Activity Log")
        log_header.setFont(QFont("", 16, QFont.Weight.Bold))
        log_header.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        right_layout.addWidget(log_header)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(f"""
            QTextEdit {{
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 12px;
                background-color: rgba(25, 25, 25, 0.95);
                border: none;
                border-radius: 10px;
                padding: 16px;
                color: {COLORS['text_secondary']};
            }}
        """)
        right_layout.addWidget(self.log)
        
        layout.addWidget(right_panel)
    
    def _create_clickable_folder_box(self, title: str, path: str) -> QFrame:
        """Create a clickable info box that opens the folder"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(35, 35, 35, 0.9);
                border: none;
                border-radius: 10px;
            }}
            QFrame:hover {{
                background-color: rgba(50, 50, 50, 0.95);
            }}
        """)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 14, 16, 14)
        
        # Clickable title button
        title_btn = QPushButton(f"Open {title}")
        title_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLORS['accent_primary']};
                font-weight: 700;
                font-size: 13px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        title_btn.clicked.connect(lambda: self._open_folder(path))
        layout.addWidget(title_btn)
        
        # Path display
        display_path = path
        if len(display_path) > 35:
            display_path = "..." + display_path[-32:]
        
        path_label = QLabel(display_path)
        path_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; background: transparent;")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        return frame
    
    def _open_folder(self, path: str):
        """Open folder in system file browser"""
        import subprocess
        import platform
        
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open folder:\n{str(e)}")
    
    def prepare(self):
        """Prepare page for writing"""
        self._complete = False
        self.progress_bar.setValue(0)
        self.status_icon.setText("⏳")
        self.status_icon.setStyleSheet("background: transparent;")
        self.status_label.setText("Ready to write configuration")
        self.status_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        self.status_detail.setText("Your current MASTERCELL configuration will be backed up first")
        self.write_btn.setEnabled(True)
        self.write_btn.setText("Write to Device")
        self.log.clear()
        
        self._log("Ready to write configuration")
        self._log(f"Backup folder: {self.backup_dir}")
        self._log(f"Config folder: {self.config_dir}")
    
    def _start_write(self):
        """Start the write process"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected",
                "Please ensure the GridConnect device is connected.")
            return
        
        self.write_btn.setEnabled(False)
        self.write_btn.setText("Writing...")
        self.status_icon.setText("⏳")
        self.status_detail.setText("Please wait...")
        
        self._timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._log("Starting write process...")
        
        # Create configuration manager
        self._config_manager = ConfigurationManager(self.can)
        self._config_manager.progress.connect(self._on_eeprom_progress)
        self._config_manager.read_complete.connect(self._on_backup_read_complete)
        self._config_manager.write_complete.connect(self._on_write_complete)
        
        # Phase 1: Read current configuration for backup
        self._current_phase = "backup"
        self._log("Phase 1: Reading current configuration from MASTERCELL for backup...")
        self.status_detail.setText("Reading current configuration for backup...")
        self.progress_bar.setValue(5)
        
        # Read system config (fast backup - full backup would take too long)
        self._config_manager.read_system_config()
    
    def _on_eeprom_progress(self, current: int, total: int, description: str):
        """Handle EEPROM operation progress"""
        if self._current_phase == "backup":
            # Backup phase: 5-20%
            percent = 5 + int((current / max(total, 1)) * 15)
        elif self._current_phase == "write":
            # Write phase: 40-95%
            percent = 40 + int((current / max(total, 1)) * 55)
        else:
            percent = int((current / max(total, 1)) * 100)
        
        self.progress_bar.setValue(percent)
        self.status_detail.setText(f"{description} ({current}/{total})")
    
    def _on_backup_read_complete(self, success: bool, data: dict):
        """Handle backup read completion"""
        if success:
            self._backup_data = data
            self._log(f"✓ Read {len(data)} bytes from MASTERCELL")
            
            # Save backup
            self._current_phase = "save"
            self.progress_bar.setValue(25)
            self._log("Saving backup file...")
            self._save_backup()
            
            # Save new config file
            self.progress_bar.setValue(35)
            self._log("Saving new configuration file...")
            self._save_new_config()
            
            # Phase 2: Write new configuration
            self._current_phase = "write"
            self.progress_bar.setValue(40)
            self._log("Phase 2: Writing new configuration to MASTERCELL...")
            self.status_detail.setText("Writing configuration to MASTERCELL...")
            
            # Generate write operations for only modified/enabled cases
            # (For now, write the full config - could optimize later)
            self._config_manager.write_configuration(self.config)
        else:
            # Continue anyway - new device may not have config
            self._log("⚠ Could not read existing configuration (new device?)")
            self._backup_data = {}
            
            # Save new config
            self._current_phase = "save"
            self.progress_bar.setValue(35)
            self._save_new_config()
            
            # Write new configuration
            self._current_phase = "write"
            self.progress_bar.setValue(40)
            self._log("Phase 2: Writing new configuration to MASTERCELL...")
            self._config_manager.write_configuration(self.config)
    
    def _on_write_complete(self, success: bool, message: str):
        """Handle write completion"""
        self._complete = success
        
        if success:
            self.progress_bar.setValue(100)
            self.status_icon.setText("✓")
            self.status_icon.setStyleSheet(f"color: {COLORS['success']}; font-size: 56px; background: transparent;")
            self.status_label.setText("Configuration Written Successfully!")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent;")
            self.status_detail.setText("Click 'Done' to finish or configure another device")
            self.write_btn.setText("Complete!")
            self._log("✓ Write completed successfully!")
        else:
            self.status_icon.setText("✕")
            self.status_icon.setStyleSheet(f"color: {COLORS['danger']}; font-size: 56px; background: transparent;")
            self.status_label.setText("Write Failed")
            self.status_label.setStyleSheet(f"color: {COLORS['danger']}; background: transparent;")
            self.status_detail.setText(message)
            self.write_btn.setText("Retry")
            self.write_btn.setEnabled(True)
            self._log(f"✕ Write failed: {message}")
        
        self.write_complete.emit(success)
    
    def _save_backup(self):
        """Save backup data to file"""
        if not self._backup_data:
            return
        
        backup_path = os.path.join(
            self.backup_dir,
            f"Backup_{self._timestamp}.json"
        )
        
        backup_content = {
            "timestamp": self._timestamp,
            "type": "eeprom_backup",
            "bytes": {f"0x{addr:04X}": value for addr, value in self._backup_data.items()}
        }
        
        with open(backup_path, 'w') as f:
            json.dump(backup_content, f, indent=2)
        
        self._log(f"✓ Backup saved: {os.path.basename(backup_path)}")
    
    def _save_new_config(self):
        """Save new configuration to file"""
        config_path = os.path.join(
            self.config_dir,
            f"Configuration_{self._timestamp}.json"
        )
        with open(config_path, 'w') as f:
            f.write(self.config.to_json())
        self._log(f"✓ Configuration saved: {os.path.basename(config_path)}")
    
    def _log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {message}")
    
    def is_complete(self) -> bool:
        """Check if write is complete"""
        return self._complete
    
    def set_configuration(self, config: FullConfiguration):
        """Update the configuration reference"""
        self.config = config
    
    def reset(self):
        """Reset page state"""
        self._complete = False
        self.progress_bar.setValue(0)
        self.status_icon.setText("⏳")
        self.status_icon.setStyleSheet("background: transparent;")
        self.status_label.setText("Ready to write")
        self.status_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        self.status_detail.setText("Your current MASTERCELL configuration will be backed up first")
        self.write_btn.setEnabled(True)
        self.write_btn.setText("Write to Device")
        self.log.clear()
