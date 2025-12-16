"""
welcome_page.py - Welcome/preset selection page with glassmorphism design
"""

import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QMessageBox, QGridLayout, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from styles import COLORS
from config_data import FullConfiguration, DEVICES, OutputConfig, OutputMode, CaseConfig


class PresetCard(QFrame):
    """Clickable card for preset selection - with proper hover states"""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, preset_id: str, title: str, description: str,
                 accent_color: str = None, parent=None):
        super().__init__(parent)
        self.preset_id = preset_id
        self.selected = False
        self.hovered = False
        self.accent_color = accent_color or COLORS['accent_primary']
        self._setup_ui(title, description)
    
    def _setup_ui(self, title: str, description: str):
        self.setFixedHeight(280)
        self.setFixedWidth(260)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 36, 28, 36)
        
        layout.addStretch()
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("", 18, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"color: white; background: transparent;")
        layout.addWidget(self.title_label)
        
        # Description
        self.desc_label = QLabel(description)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(f"color: rgba(210,210,210,1.0); font-size: 13px; background: transparent;")
        layout.addWidget(self.desc_label)
        
        layout.addStretch()
        
        # Apply initial style after labels are created
        self._update_style()
    
    def _update_style(self):
        if self.selected:
            # Selected state - brighter background
            self.setStyleSheet(f"""
                PresetCard {{
                    background-color: rgba(90, 90, 90, 0.95);
                    border: none;
                    border-radius: 16px;
                }}
            """)
            self.title_label.setStyleSheet(f"color: {self.accent_color}; background: transparent;")
        elif self.hovered:
            # Hover state - medium background
            self.setStyleSheet(f"""
                PresetCard {{
                    background-color: rgba(70, 70, 70, 0.9);
                    border: none;
                    border-radius: 16px;
                }}
            """)
            self.title_label.setStyleSheet(f"color: {self.accent_color}; background: transparent;")
        else:
            # Default state - subtle background
            self.setStyleSheet(f"""
                PresetCard {{
                    background-color: rgba(55, 55, 55, 0.85);
                    border: none;
                    border-radius: 16px;
                }}
            """)
            self.title_label.setStyleSheet(f"color: white; background: transparent;")
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()
    
    def enterEvent(self, event):
        self.hovered = True
        self._update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.hovered = False
        self._update_style()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.preset_id)
        super().mousePressEvent(event)


class WelcomePage(QWidget):
    """Welcome page with preset selection and file upload - Glass style"""
    
    config_loaded = pyqtSignal(object)  # Emits FullConfiguration
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.selected_preset = None
        self.preset_cards = {}
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(48, 48, 48, 48)
        
        layout.addStretch()
        
        # Welcome message
        welcome = QLabel("Choose Your Starting Point")
        welcome.setFont(QFont("", 36, QFont.Weight.Bold))
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        layout.addWidget(welcome)
        
        subtitle = QLabel("Select a preset configuration or load an existing file")
        subtitle.setFont(QFont("", 15))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(48)
        
        # Preset cards - centered container
        cards_container = QWidget()
        cards_container.setStyleSheet("background-color: transparent;")
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setSpacing(32)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Front Engine preset
        front_card = PresetCard(
            "front_engine",
            "Front Engine",
            "Standard configuration for\nfront-engine vehicles",
            accent_color="#60B0E1"  # Primary accent
        )
        front_card.clicked.connect(self._on_preset_selected)
        self.preset_cards["front_engine"] = front_card
        cards_layout.addWidget(front_card)
        
        # Rear Engine preset
        rear_card = PresetCard(
            "rear_engine", 
            "Rear Engine",
            "Configuration for rear or\nmid-engine vehicles",
            accent_color="#8B5CF6"  # Purple
        )
        rear_card.clicked.connect(self._on_preset_selected)
        self.preset_cards["rear_engine"] = rear_card
        cards_layout.addWidget(rear_card)
        
        # Upload card
        upload_card = PresetCard(
            "upload",
            "Load From File",
            "Import an existing\nconfiguration file",
            accent_color="#10B981"  # Green
        )
        upload_card.clicked.connect(self._on_upload_clicked)
        self.preset_cards["upload"] = upload_card
        cards_layout.addWidget(upload_card)
        
        # Center the cards
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(cards_container)
        center_layout.addStretch()
        layout.addLayout(center_layout)
        
        layout.addSpacing(24)
        
        # Status label with pill style
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {COLORS['success']};
            font-size: 15px;
            font-weight: 600;
            padding: 16px 32px;
            background-color: rgba(16, 185, 129, 0.2);
            border-radius: 20px;
            border: none;
        """)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
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
            self.status_label.setText("✓ Front Engine preset loaded")
        elif preset_id == "rear_engine":
            self.config = self._create_rear_engine_preset()
            self.status_label.setText("✓ Rear Engine preset loaded")
        
        self.status_label.setVisible(True)
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
                self.status_label.setText(f"✓ Loaded: {filename}")
                self.status_label.setVisible(True)
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
        self.status_label.setVisible(False)
        self.config = FullConfiguration()
