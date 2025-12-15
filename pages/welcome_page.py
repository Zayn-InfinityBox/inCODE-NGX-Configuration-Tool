"""
welcome_page.py - Welcome/preset selection page
"""

import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QMessageBox, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from styles import COLORS
from config_data import FullConfiguration, DEVICES, OutputConfig, OutputMode, CaseConfig


class PresetCard(QWidget):
    """Clickable card for preset selection"""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, preset_id: str, title: str, description: str, parent=None):
        super().__init__(parent)
        self.preset_id = preset_id
        self.selected = False
        self._setup_ui(title, description)
    
    def _setup_ui(self, title: str, description: str):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 20, 16, 20)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("", 15, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(desc_label)
    
    def _update_style(self):
        if self.selected:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['bg_light']};
                    border: 2px solid {COLORS['accent_blue']};
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['bg_medium']};
                    border: 1px solid {COLORS['border_default']};
                    border-radius: 12px;
                }}
                QWidget:hover {{
                    border-color: {COLORS['accent_blue']};
                    background-color: {COLORS['bg_light']};
                }}
            """)
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.preset_id)
        super().mousePressEvent(event)


class WelcomePage(QWidget):
    """Welcome page with preset selection and file upload"""
    
    config_loaded = pyqtSignal(object)  # Emits FullConfiguration
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.selected_preset = None
        self.preset_cards = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 48, 32, 32)
        
        # Welcome message
        welcome = QLabel("Welcome to inCODE NGX Configuration Tool")
        welcome.setFont(QFont("", 24, QFont.Weight.Bold))
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)
        
        subtitle = QLabel("Select a starting configuration or upload an existing one")
        subtitle.setFont(QFont("", 13))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(32)
        
        # Preset cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(24)
        
        # Front Engine preset
        front_card = PresetCard(
            "front_engine",
            "Front Engine",
            "Standard configuration for front-engine vehicles"
        )
        front_card.clicked.connect(self._on_preset_selected)
        self.preset_cards["front_engine"] = front_card
        cards_layout.addWidget(front_card)
        
        # Rear Engine preset
        rear_card = PresetCard(
            "rear_engine", 
            "Rear Engine",
            "Configuration for rear/mid-engine vehicles"
        )
        rear_card.clicked.connect(self._on_preset_selected)
        self.preset_cards["rear_engine"] = rear_card
        cards_layout.addWidget(rear_card)
        
        # Upload card
        upload_card = PresetCard(
            "upload",
            "Load From File",
            "Upload an existing configuration file"
        )
        upload_card.clicked.connect(self._on_upload_clicked)
        self.preset_cards["upload"] = upload_card
        cards_layout.addWidget(upload_card)
        
        layout.addLayout(cards_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {COLORS['accent_green']};
            font-size: 14px;
            padding: 12px;
        """)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def _on_preset_selected(self, preset_id: str):
        """Handle preset card selection"""
        self.selected_preset = preset_id
        
        # Update card selection state
        for card_id, card in self.preset_cards.items():
            card.set_selected(card_id == preset_id)
        
        # Load preset configuration
        if preset_id == "front_engine":
            self.config = self._create_front_engine_preset()
            self.status_label.setText("Front Engine preset loaded - Click Next to continue")
        elif preset_id == "rear_engine":
            self.config = self._create_rear_engine_preset()
            self.status_label.setText("Rear Engine preset loaded - Click Next to continue")
        
        self.config_loaded.emit(self.config)
    
    def _on_upload_clicked(self, preset_id: str):
        """Handle upload card click"""
        self._upload_config()
    
    def _create_front_engine_preset(self) -> FullConfiguration:
        """Create front engine configuration preset"""
        config = FullConfiguration()
        
        # Input 1: Ignition
        ignition_case = CaseConfig(enabled=True, mode="toggle")
        ignition_case.set_ignition = True
        config.inputs[0].on_cases[0] = ignition_case
        
        return config
    
    def _create_rear_engine_preset(self) -> FullConfiguration:
        """Create rear engine configuration preset"""
        config = FullConfiguration()
        
        ignition_case = CaseConfig(enabled=True, mode="toggle")
        ignition_case.set_ignition = True
        config.inputs[0].on_cases[0] = ignition_case
        
        return config
    
    def _upload_config(self):
        """Upload existing configuration file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Configuration File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    json_str = f.read()
                
                self.config = FullConfiguration.from_json(json_str)
                
                # Update selection
                for card_id, card in self.preset_cards.items():
                    card.set_selected(card_id == "upload")
                self.selected_preset = "upload"
                
                filename = os.path.basename(file_path)
                self.status_label.setText(f"Loaded: {filename} - Click Next to continue")
                self.config_loaded.emit(self.config)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Failed to load configuration:\n{str(e)}")
    
    def reset(self):
        """Reset page to initial state"""
        self.selected_preset = None
        for card in self.preset_cards.values():
            card.set_selected(False)
        self.status_label.setText("")
        self.config = FullConfiguration()
