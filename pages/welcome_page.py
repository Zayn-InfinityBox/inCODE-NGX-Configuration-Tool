"""
welcome_page.py - Welcome/preset selection page with glassmorphism design
"""

import os
import sys
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


def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource, works for dev and PyInstaller bundle.
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in normal Python environment
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


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
    
    config_loaded = pyqtSignal(object, bool)  # Emits (FullConfiguration, is_preset)
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.selected_preset = None
        self.loaded_file_path = None  # Path to uploaded config file
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
        """Handle preset card selection - just updates visual state, doesn't load yet"""
        self.selected_preset = preset_id
        self.loaded_file_path = None  # Clear any previously loaded file
        
        # Update card selection state
        for card_id, card in self.preset_cards.items():
            card.set_selected(card_id == preset_id)
        
        # Update status label to show selection (not loaded yet)
        if preset_id == "front_engine":
            self.status_label.setText("Front Engine selected")
        elif preset_id == "rear_engine":
            self.status_label.setText("Rear Engine selected")
        
        self.status_label.setStyleSheet(f"""
            color: {COLORS['accent_primary']};
            font-size: 15px;
            font-weight: 600;
            padding: 16px 32px;
            background-color: rgba(59, 130, 246, 0.2);
            border-radius: 20px;
            border: none;
        """)
        self.status_label.setVisible(True)
    
    def _on_upload_clicked(self, preset_id: str):
        """Handle upload card click"""
        self._upload_config()
    
    def _load_preset_file(self, preset_name: str) -> FullConfiguration:
        """Load preset configuration from JSON file"""
        # Find the presets directory (works in dev and PyInstaller bundle)
        preset_path = get_resource_path(os.path.join("presets", f"{preset_name}.json"))
        
        try:
            with open(preset_path, 'r') as f:
                preset_data = json.load(f)
            
            # Create configuration from preset data
            config = FullConfiguration()
            
            # Load system config
            if 'system' in preset_data:
                for key, value in preset_data['system'].items():
                    if hasattr(config.system, key):
                        setattr(config.system, key, value)
            
            # Load input configs
            if 'inputs' in preset_data:
                for input_data in preset_data['inputs']:
                    input_num = input_data.get('input_number', 0)
                    if 1 <= input_num <= 44:
                        idx = input_num - 1
                        config.inputs[idx].custom_name = input_data.get('custom_name', '')
                        
                        # Load ON cases
                        for j, case_data in enumerate(input_data.get('on_cases', [])):
                            if j < 8:
                                self._load_case_data(config.inputs[idx].on_cases[j], case_data)
                        
                        # Load OFF cases
                        for j, case_data in enumerate(input_data.get('off_cases', [])):
                            if j < 2:
                                self._load_case_data(config.inputs[idx].off_cases[j], case_data)
            
            return config
            
        except FileNotFoundError:
            print(f"Preset file not found: {preset_path}")
            return FullConfiguration()
        except Exception as e:
            print(f"Error loading preset: {e}")
            return FullConfiguration()
    
    def _load_case_data(self, case: CaseConfig, case_data: dict):
        """Load case configuration from dict"""
        case.enabled = case_data.get('enabled', False)
        case.mode = case_data.get('mode', 'track')
        case.timer_on = case_data.get('timer_on', 0)
        case.timer_delay = case_data.get('timer_delay', 0)
        case.pattern_preset = case_data.get('pattern_preset', 'none')
        case.pattern_on_time = case_data.get('pattern_on_time', 0)
        case.pattern_off_time = case_data.get('pattern_off_time', 0)
        case.set_ignition = case_data.get('set_ignition', False)
        case.must_be_on = case_data.get('must_be_on', [])
        case.must_be_off = case_data.get('must_be_off', [])
        
        # Load device outputs
        case.device_outputs = []
        for device_output in case_data.get('device_outputs', []):
            if len(device_output) == 2:
                device_id = device_output[0]
                outputs_dict = device_output[1]
                # Convert output configs
                output_configs = {}
                for out_num_str, out_data in outputs_dict.items():
                    out_num = int(out_num_str)
                    output_configs[out_num] = OutputConfig(
                        enabled=out_data.get('enabled', False),
                        mode=OutputMode(out_data.get('mode', 0)),
                        pwm_duty=out_data.get('pwm_duty', 0)
                    )
                case.device_outputs.append((device_id, output_configs))
    
    def _create_front_engine_preset(self) -> FullConfiguration:
        """Create front engine configuration preset"""
        return self._load_preset_file("front_engine")
    
    def _create_rear_engine_preset(self) -> FullConfiguration:
        """Create rear engine configuration preset"""
        return self._load_preset_file("rear_engine")
    
    def _upload_config(self):
        """Upload existing configuration file - just stores the path, doesn't load yet"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Configuration File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            # Just store the path and update visual state
            self.loaded_file_path = file_path
            self.selected_preset = "upload"
            
            # Update selection
            for card_id, card in self.preset_cards.items():
                card.set_selected(card_id == "upload")
            
            filename = os.path.basename(file_path)
            self.status_label.setText(f"File selected: {filename}")
            self.status_label.setStyleSheet(f"""
                color: {COLORS['accent_primary']};
                font-size: 15px;
                font-weight: 600;
                padding: 16px 32px;
                background-color: rgba(59, 130, 246, 0.2);
                border-radius: 20px;
                border: none;
            """)
            self.status_label.setVisible(True)
    
    def load_selected_config(self) -> tuple:
        """
        Actually load the selected configuration when Next is pressed.
        Returns (FullConfiguration, is_preset) tuple, or (None, False) if nothing selected.
        """
        if self.selected_preset == "front_engine":
            self.config = self._load_preset_file("front_engine")
            self.status_label.setText("✓ Front Engine preset loaded")
            self.status_label.setStyleSheet(f"""
                color: {COLORS['success']};
                font-size: 15px;
                font-weight: 600;
                padding: 16px 32px;
                background-color: rgba(16, 185, 129, 0.2);
                border-radius: 20px;
                border: none;
            """)
            return (self.config, True)
        
        elif self.selected_preset == "rear_engine":
            self.config = self._load_preset_file("rear_engine")
            self.status_label.setText("✓ Rear Engine preset loaded")
            self.status_label.setStyleSheet(f"""
                color: {COLORS['success']};
                font-size: 15px;
                font-weight: 600;
                padding: 16px 32px;
                background-color: rgba(16, 185, 129, 0.2);
                border-radius: 20px;
                border: none;
            """)
            return (self.config, True)
        
        elif self.selected_preset == "upload" and self.loaded_file_path:
            try:
                with open(self.loaded_file_path, 'r') as f:
                    json_str = f.read()
                
                self.config = FullConfiguration.from_json(json_str)
                filename = os.path.basename(self.loaded_file_path)
                self.status_label.setText(f"✓ Loaded: {filename}")
                self.status_label.setStyleSheet(f"""
                    color: {COLORS['success']};
                    font-size: 15px;
                    font-weight: 600;
                    padding: 16px 32px;
                    background-color: rgba(16, 185, 129, 0.2);
                    border-radius: 20px;
                    border: none;
                """)
                return (self.config, False)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Failed to load configuration:\n{str(e)}")
                return (None, False)
        
        # Nothing selected - return empty config
        return (FullConfiguration(), False)
    
    def has_selection(self) -> bool:
        """Check if user has made a selection"""
        return self.selected_preset is not None
    
    def reset(self):
        """Reset page to initial state"""
        self.selected_preset = None
        self.loaded_file_path = None
        for card in self.preset_cards.values():
            card.set_selected(False)
        self.status_label.setText("")
        self.status_label.setVisible(False)
        self.config = FullConfiguration()
