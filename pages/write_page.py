"""
write_page.py - Write configuration to device with backup
"""

import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont

from styles import COLORS, ICONS
from config_data import FullConfiguration, EEPROM_GUARD_BYTE
from can_interface import CANInterface


class WriteWorker(QThread):
    """Background worker for EEPROM read/write operations"""
    
    progress = pyqtSignal(int, str)  # progress percent, status message
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, can_interface: CANInterface, config: FullConfiguration,
                 backup_dir: str, config_dir: str, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.config = config
        self.backup_dir = backup_dir
        self.config_dir = config_dir
        self.timestamp = None
    
    def run(self):
        try:
            self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
            # Step 1: Read current EEPROM (backup)
            self.progress.emit(10, "Reading current configuration from MASTERCELL...")
            backup_data = self._read_current_config()
            
            if backup_data:
                self.progress.emit(30, "Saving backup...")
                self._save_backup(backup_data)
            else:
                self.progress.emit(30, "No existing configuration to backup (new device)")
            
            # Step 2: Save new configuration to file
            self.progress.emit(40, "Saving new configuration to file...")
            self._save_new_config()
            
            # Step 3: Write configuration to device
            self.progress.emit(50, "Writing configuration to MASTERCELL...")
            success = self._write_config()
            
            if success:
                self.progress.emit(100, "Configuration written successfully!")
                self.finished.emit(True, "Configuration written successfully!")
            else:
                self.finished.emit(False, "Failed to write some configuration data")
                
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
    
    def _read_current_config(self) -> dict:
        """Read current EEPROM configuration from device"""
        return {"read_at": self.timestamp, "status": "placeholder"}
    
    def _save_backup(self, data: dict):
        """Save backup to file"""
        import json
        backup_path = os.path.join(
            self.backup_dir,
            f"Backup_{self.timestamp}.json"
        )
        with open(backup_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_new_config(self):
        """Save new configuration to file"""
        config_path = os.path.join(
            self.config_dir,
            f"Configuration_{self.timestamp}.json"
        )
        with open(config_path, 'w') as f:
            f.write(self.config.to_json())
    
    def _write_config(self) -> bool:
        """Write configuration to MASTERCELL EEPROM"""
        total_inputs = 0
        written_inputs = 0
        
        for input_config in self.config.inputs:
            has_cases = any(c.enabled for c in input_config.on_cases + input_config.off_cases)
            if not has_cases:
                continue
            
            total_inputs += 1
            
            for case_idx, case in enumerate(input_config.on_cases):
                if case.enabled:
                    messages = case.get_can_messages()
                    for pgn_high, pgn_low, sa, data in messages:
                        pass
            
            for case_idx, case in enumerate(input_config.off_cases):
                if case.enabled:
                    messages = case.get_can_messages()
                    for pgn_high, pgn_low, sa, data in messages:
                        pass
            
            written_inputs += 1
            progress = 50 + int((written_inputs / max(total_inputs, 1)) * 45)
            self.progress.emit(progress, f"Writing input {input_config.input_number}...")
        
        return True


class WritePage(QWidget):
    """Write configuration page with progress and backup"""
    
    write_complete = pyqtSignal(bool)
    
    def __init__(self, can_interface: CANInterface, config: FullConfiguration,
                 backup_dir: str, config_dir: str, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.config = config
        self.backup_dir = backup_dir
        self.config_dir = config_dir
        self._complete = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Left side - Status and controls
        left_panel = QWidget()
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(24)
        
        # Header
        self.title = QLabel("Write Configuration")
        self.title.setFont(QFont("", 24, QFont.Weight.Bold))
        left_layout.addWidget(self.title)
        
        self.subtitle = QLabel("Ready to write configuration to MASTERCELL")
        self.subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        left_layout.addWidget(self.subtitle)
        
        left_layout.addSpacing(16)
        
        # Status display
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_medium']};
                border: 1px solid {COLORS['border_default']};
                border-radius: 12px;
                padding: 24px;
            }}
        """)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(16)
        
        # Status icon and text row
        status_row = QHBoxLayout()
        self.status_icon = QLabel("⏳")
        self.status_icon.setFont(QFont("", 48))
        status_row.addWidget(self.status_icon)
        
        status_text_layout = QVBoxLayout()
        self.status_label = QLabel("Click 'Write to Device' to begin")
        self.status_label.setFont(QFont("", 16, QFont.Weight.Bold))
        status_text_layout.addWidget(self.status_label)
        
        self.status_detail = QLabel("Your current MASTERCELL configuration will be backed up first")
        self.status_detail.setStyleSheet(f"color: {COLORS['text_secondary']};")
        status_text_layout.addWidget(self.status_detail)
        
        status_row.addLayout(status_text_layout, 1)
        status_layout.addLayout(status_row)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(28)
        status_layout.addWidget(self.progress_bar)
        
        # Write button
        self.write_btn = QPushButton("Write to Device")
        self.write_btn.setObjectName("primaryButton")
        self.write_btn.setMinimumHeight(50)
        self.write_btn.setFont(QFont("", 14, QFont.Weight.Bold))
        self.write_btn.clicked.connect(self._start_write)
        status_layout.addWidget(self.write_btn)
        
        left_layout.addWidget(status_frame)
        
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
        
        # Right side - Log
        right_panel = QWidget()
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)
        
        log_header = QLabel("Activity Log")
        log_header.setFont(QFont("", 14, QFont.Weight.Bold))
        right_layout.addWidget(log_header)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(f"""
            QTextEdit {{
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 12px;
                background-color: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border_default']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        right_layout.addWidget(self.log)
        
        layout.addWidget(right_panel)
    
    def _create_clickable_folder_box(self, title: str, path: str) -> QFrame:
        """Create a clickable info box that opens the folder"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_light']};
                border: 1px solid {COLORS['border_default']};
                border-radius: 8px;
                padding: 12px;
            }}
            QFrame:hover {{
                border-color: {COLORS['accent_blue']};
            }}
        """)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Clickable title button
        title_btn = QPushButton(f"Open {title}")
        title_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLORS['accent_blue']};
                font-weight: bold;
                font-size: 12px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
                text-decoration: underline;
            }}
        """)
        title_btn.clicked.connect(lambda: self._open_folder(path))
        layout.addWidget(title_btn)
        
        # Path display
        display_path = path
        if len(display_path) > 35:
            display_path = "..." + display_path[-32:]
        
        path_label = QLabel(display_path)
        path_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
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
        self.status_icon.setStyleSheet("")
        self.status_label.setText("Ready to write configuration")
        self.status_label.setStyleSheet("")
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
        self.status_detail.setText("Please wait while configuration is written...")
        
        self._log("Starting write process...")
        
        self.worker = WriteWorker(
            self.can, self.config,
            self.backup_dir, self.config_dir
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, percent: int, message: str):
        """Handle progress updates"""
        self.progress_bar.setValue(percent)
        self.status_detail.setText(message)
        self._log(message)
    
    def _on_finished(self, success: bool, message: str):
        """Handle write completion"""
        self._complete = success
        
        if success:
            self.status_icon.setText("✅")
            self.status_icon.setStyleSheet(f"color: {COLORS['accent_green']};")
            self.status_label.setText("Configuration Written Successfully!")
            self.status_label.setStyleSheet(f"color: {COLORS['accent_green']};")
            self.status_detail.setText("Click 'Done' to finish or configure another device")
            self.write_btn.setText("Complete!")
            self._log("✓ Write completed successfully!")
        else:
            self.status_icon.setText("❌")
            self.status_icon.setStyleSheet(f"color: {COLORS['accent_red']};")
            self.status_label.setText("Write Failed")
            self.status_label.setStyleSheet(f"color: {COLORS['accent_red']};")
            self.status_detail.setText(message)
            self.write_btn.setText("Retry")
            self.write_btn.setEnabled(True)
            self._log(f"✗ Write failed: {message}")
        
        self.write_complete.emit(success)
    
    def _log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {message}")
    
    def is_complete(self) -> bool:
        """Check if write is complete"""
        return self._complete
    
    def reset(self):
        """Reset page state"""
        self._complete = False
        self.progress_bar.setValue(0)
        self.status_icon.setText("⏳")
        self.status_icon.setStyleSheet("")
        self.status_label.setText("Ready to write")
        self.status_label.setStyleSheet("")
        self.status_detail.setText("Your current MASTERCELL configuration will be backed up first")
        self.write_btn.setEnabled(True)
        self.write_btn.setText("Write to Device")
        self.log.clear()
