"""
inputs_page.py - Input configuration page (simplified, no per-input write)
"""

from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QSpinBox, QLineEdit,
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QFrame, QCheckBox, QSlider, QMessageBox, QMenu, QWidgetAction
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from styles import COLORS, ICONS
from config_data import (
    INPUTS, InputDefinition, InputConfig, CaseConfig,
    DEVICES, DeviceDefinition, OutputConfig, OutputMode,
    PATTERN_PRESETS, get_input_definition, FullConfiguration,
    get_case_counts
)


class MultiSelectDropdown(QWidget):
    """Dropdown that allows selecting multiple inputs - 2 column scrollable layout"""
    
    selection_changed = pyqtSignal()
    
    def __init__(self, placeholder: str = "Select inputs...", parent=None):
        super().__init__(parent)
        self.placeholder = placeholder
        self.selected_items = []  # List of input numbers
        self.checkboxes = {}  # input_number -> QCheckBox
        self.popup = None
        self.setStyleSheet("background: transparent;")
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Button that shows selection and opens dropdown
        self.button = QPushButton(self.placeholder)
        self.button.setMinimumHeight(36)
        self.button.setMinimumWidth(200)
        self.button.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 8px 12px;
                padding-right: 24px;
                background-color: rgba(70, 70, 70, 0.9);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_primary']};
            }}
        """)
        self.button.clicked.connect(self._toggle_popup)
        layout.addWidget(self.button)
        
        # Create popup widget (hidden initially)
        self._create_popup()
    
    def _create_popup(self):
        """Create the popup with 2-column scrollable grid"""
        self.popup = QFrame(self.window())
        self.popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.popup.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(55, 55, 55, 0.98);
                border: none;
                border-radius: 12px;
            }}
        """)
        
        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(12, 12, 12, 12)
        popup_layout.setSpacing(8)
        
        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: rgba(40, 40, 40, 0.5);
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(120, 120, 120, 0.8);
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        # Container for grid
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        
        # Add checkboxes in 2 columns
        for i, inp in enumerate(INPUTS):
            row = i // 2
            col = i % 2
            
            # Show input number and name
            label = f"IN{inp.number:02d}: {inp.name}" if inp.name else f"IN{inp.number:02d}"
            checkbox = QCheckBox(label)
            checkbox.setMinimumHeight(44)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    padding: 10px 14px;
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                    background: rgba(70, 70, 70, 0.6);
                    border-radius: 8px;
                }}
                QCheckBox:hover {{
                    background: rgba(90, 90, 90, 0.8);
                }}
                QCheckBox::indicator {{
                    width: 22px;
                    height: 22px;
                    border-radius: 5px;
                    border: none;
                    background: rgba(100, 100, 100, 0.9);
                }}
                QCheckBox::indicator:hover {{
                    background: rgba(120, 120, 120, 1.0);
                }}
                QCheckBox::indicator:checked {{
                    background: {COLORS['accent_primary']};
                }}
            """)
            checkbox.stateChanged.connect(self._on_checkbox_changed)
            self.checkboxes[inp.number] = checkbox
            grid.addWidget(checkbox, row, col)
        
        scroll.setWidget(container)
        popup_layout.addWidget(scroll)
        
        # Initial size - will be resized dynamically when shown
        self.popup.setMinimumWidth(650)
        self.popup.setMinimumHeight(300)
    
    def _toggle_popup(self):
        """Toggle popup visibility"""
        if self.popup.isVisible():
            self.popup.hide()
        else:
            # Get screen geometry
            screen = self.window().screen()
            if screen:
                screen_rect = screen.availableGeometry()
                # Set popup to 50% of screen height, centered vertically
                popup_height = int(screen_rect.height() * 0.5)
                popup_width = 650
                
                self.popup.setFixedHeight(popup_height)
                self.popup.setFixedWidth(popup_width)
                
                # Center horizontally relative to window, center vertically on screen
                window_center = self.window().mapToGlobal(self.window().rect().center())
                x = window_center.x() - popup_width // 2
                y = screen_rect.top() + (screen_rect.height() - popup_height) // 2
                
                self.popup.move(x, y)
            else:
                # Fallback - position below button
                pos = self.button.mapToGlobal(self.button.rect().bottomLeft())
                self.popup.move(pos)
            
            self.popup.show()
    
    def _on_checkbox_changed(self, state):
        """Handle checkbox state change"""
        self._update_selection()
        self._update_button_text()
        self.selection_changed.emit()
    
    def _update_selection(self):
        """Update the selected_items list from checkboxes"""
        self.selected_items = []
        for input_num, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                self.selected_items.append(input_num)
    
    def _update_button_text(self):
        """Update button text to show selection summary"""
        if not self.selected_items:
            self.button.setText(self.placeholder)
        elif len(self.selected_items) == 1:
            inp_num = self.selected_items[0]
            self.button.setText(f"IN{inp_num:02d} selected")
        else:
            self.button.setText(f"{len(self.selected_items)} inputs selected")
    
    def get_selected(self) -> List[int]:
        """Get list of selected input numbers"""
        return self.selected_items.copy()
    
    def set_selected(self, input_numbers: List[int]):
        """Set selected inputs"""
        self.selected_items = input_numbers.copy() if input_numbers else []
        
        # Update checkboxes
        for input_num, checkbox in self.checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(input_num in self.selected_items)
            checkbox.blockSignals(False)
        
        self._update_button_text()
    
    def clear_selection(self):
        """Clear all selections"""
        self.set_selected([])


class OutputConfigWidget(QWidget):
    """Widget for configuring a single output on a device"""
    
    changed = pyqtSignal()
    
    def __init__(self, output_num: int, output_name: str, supports_pwm: bool = True, parent=None):
        super().__init__(parent)
        self.output_num = output_num
        self.output_name = output_name
        self.supports_pwm = supports_pwm
        self.config = OutputConfig()
        self.setStyleSheet("background: transparent;")
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)
        
        # Enable checkbox
        self.enable_check = QCheckBox(self.output_name)
        self.enable_check.setMinimumWidth(140)
        self.enable_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: 13px;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: none;
                background: rgba(80, 80, 80, 0.95);
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent_primary']};
            }}
            QCheckBox::indicator:hover {{
                background: rgba(100, 100, 100, 1.0);
            }}
            QCheckBox::indicator:checked:hover {{
                background: {COLORS['accent_secondary']};
            }}
        """)
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_check)
        
        # Mode card - contains mode dropdown and PWM controls
        self.mode_card = QFrame()
        self.mode_card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(55, 55, 55, 0.95);
                border-radius: 8px;
            }}
        """)
        mode_card_layout = QHBoxLayout(self.mode_card)
        mode_card_layout.setContentsMargins(10, 6, 10, 6)
        mode_card_layout.setSpacing(10)
        
        # Mode dropdown
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Track", OutputMode.TRACK)
        self.mode_combo.addItem("Soft-Start", OutputMode.SOFT_START)
        if self.supports_pwm:
            self.mode_combo.addItem("PWM", OutputMode.PWM)
        self.mode_combo.setMinimumWidth(105)
        self.mode_combo.setMinimumHeight(32)
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 4px 10px;
                font-size: 13px;
            }}
        """)
        self.mode_combo.setEnabled(False)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_card_layout.addWidget(self.mode_combo)
        
        # PWM duty cycle
        self.pwm_label = QLabel("Duty:")
        self.pwm_label.setStyleSheet("background: transparent;")
        self.pwm_label.setVisible(False)
        mode_card_layout.addWidget(self.pwm_label)
        
        self.pwm_slider = QSlider(Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(0, 15)
        self.pwm_slider.setValue(15)
        self.pwm_slider.setMinimumWidth(100)
        self.pwm_slider.setVisible(False)
        self.pwm_slider.valueChanged.connect(self._on_pwm_changed)
        mode_card_layout.addWidget(self.pwm_slider)
        
        self.pwm_value = QLabel("100%")
        self.pwm_value.setMinimumWidth(45)
        self.pwm_value.setStyleSheet("background: transparent;")
        self.pwm_value.setVisible(False)
        mode_card_layout.addWidget(self.pwm_value)
        
        layout.addWidget(self.mode_card)
        layout.addStretch()
    
    def _on_enable_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.config.enabled = enabled
        self.mode_combo.setEnabled(enabled)
        
        if enabled:
            self._on_mode_changed(self.mode_combo.currentIndex())
        else:
            self.pwm_label.setVisible(False)
            self.pwm_slider.setVisible(False)
            self.pwm_value.setVisible(False)
        
        self.changed.emit()
    
    def _on_mode_changed(self, index):
        mode = self.mode_combo.currentData()
        self.config.mode = mode if mode else OutputMode.TRACK
        
        show_pwm = (mode == OutputMode.PWM and self.enable_check.isChecked())
        self.pwm_label.setVisible(show_pwm)
        self.pwm_slider.setVisible(show_pwm)
        self.pwm_value.setVisible(show_pwm)
        
        self.changed.emit()
    
    def _on_pwm_changed(self, value):
        self.config.pwm_duty = value
        percent = int((value / 15) * 100)
        self.pwm_value.setText(f"{percent}%")
        self.changed.emit()
    
    def get_config(self) -> OutputConfig:
        return OutputConfig(
            enabled=self.enable_check.isChecked(),
            mode=self.mode_combo.currentData() if self.enable_check.isChecked() else OutputMode.OFF,
            pwm_duty=self.pwm_slider.value()
        )
    
    def set_config(self, config: OutputConfig):
        """Set configuration. Blocks signals to prevent unwanted change events."""
        # Block signals to prevent cascade of changed events during setup
        self.enable_check.blockSignals(True)
        self.mode_combo.blockSignals(True)
        self.pwm_slider.blockSignals(True)
        
        try:
            self.config = config
            self.enable_check.setChecked(config.enabled)
            self.mode_combo.setEnabled(config.enabled)
            
            idx = self.mode_combo.findData(config.mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            
            self.pwm_slider.setValue(config.pwm_duty)
            
            # Update PWM visibility manually since we blocked signals
            show_pwm = (config.mode == OutputMode.PWM and config.enabled)
            self.pwm_label.setVisible(show_pwm)
            self.pwm_slider.setVisible(show_pwm)
            self.pwm_value.setVisible(show_pwm)
            if show_pwm:
                percent = int((config.pwm_duty / 15) * 100)
                self.pwm_value.setText(f"{percent}%")
        finally:
            self.enable_check.blockSignals(False)
            self.mode_combo.blockSignals(False)
            self.pwm_slider.blockSignals(False)
    
    def reset(self):
        """Reset to default state. Blocks signals to prevent change cascade."""
        self.enable_check.blockSignals(True)
        self.mode_combo.blockSignals(True)
        self.pwm_slider.blockSignals(True)
        try:
            self.enable_check.setChecked(False)
            self.mode_combo.setEnabled(False)
            self.mode_combo.setCurrentIndex(0)
            self.pwm_slider.setValue(15)
            self.pwm_label.setVisible(False)
            self.pwm_slider.setVisible(False)
            self.pwm_value.setVisible(False)
            self.config = OutputConfig()
        finally:
            self.enable_check.blockSignals(False)
            self.mode_combo.blockSignals(False)
            self.pwm_slider.blockSignals(False)


class DeviceOutputsWidget(QWidget):
    """Widget for configuring all outputs on a single device"""
    
    changed = pyqtSignal()
    
    def __init__(self, device: DeviceDefinition, show_header: bool = True, parent=None):
        super().__init__(parent)
        self.device = device
        self.output_widgets = []
        self.show_header = show_header
        self._enabled = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        if self.show_header:
            # Device header with enable checkbox (only if showing header)
            header_layout = QHBoxLayout()
            self.device_check = QCheckBox(self.device.name)
            self.device_check.setFont(QFont("", 11, QFont.Weight.Bold))
            self.device_check.stateChanged.connect(self._on_device_toggled)
            header_layout.addWidget(self.device_check)
            
            pgn = f"0x{self.device.pgn_high:02X}{self.device.pgn_low:02X}"
            pgn_label = QLabel(f"(PGN {pgn})")
            pgn_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            header_layout.addWidget(pgn_label)
            header_layout.addStretch()
            layout.addLayout(header_layout)
        else:
            # No header - create a hidden checkbox just to track state
            self.device_check = QCheckBox()
            self.device_check.setVisible(False)
        
        # Outputs container
        self.outputs_container = QWidget()
        self.outputs_container.setStyleSheet("background: transparent;")
        outputs_layout = QVBoxLayout(self.outputs_container)
        outputs_layout.setContentsMargins(0 if not self.show_header else 20, 4, 0, 4)
        outputs_layout.setSpacing(4)
        
        # Label for selecting outputs
        outputs_label = QLabel("Check the outputs you want to control:")
        outputs_label.setStyleSheet(f"color: {COLORS['accent_primary']}; font-weight: 700; font-size: 13px; margin-bottom: 8px; background: transparent;")
        outputs_layout.addWidget(outputs_label)
        
        # Create output widgets
        for i, output_name in enumerate(self.device.outputs):
            output_num = i + 1
            supports_pwm = (self.device.device_type == "powercell" and output_num <= 8)
            
            widget = OutputConfigWidget(output_num, output_name, supports_pwm)
            widget.changed.connect(self.changed)
            self.output_widgets.append(widget)
            outputs_layout.addWidget(widget)
        
        # Show outputs immediately if no header
        self.outputs_container.setVisible(not self.show_header)
        layout.addWidget(self.outputs_container)
    
    def _on_device_toggled(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self._enabled = enabled
        if self.show_header:
            self.outputs_container.setVisible(enabled)
        
        if not enabled:
            for widget in self.output_widgets:
                widget.reset()
        
        self.changed.emit()
    
    def is_enabled(self) -> bool:
        return self._enabled or self.device_check.isChecked()
    
    def set_enabled(self, enabled: bool):
        """Enable/disable this device (used when no header)"""
        self._enabled = enabled
        # Block signals to prevent change cascade
        self.device_check.blockSignals(True)
        self.device_check.setChecked(enabled)
        self.device_check.blockSignals(False)
        if not self.show_header:
            self.outputs_container.setVisible(enabled)
    
    def get_output_configs(self) -> dict:
        configs = {}
        for widget in self.output_widgets:
            config = widget.get_config()
            if config.enabled:
                configs[widget.output_num] = config
        return configs
    
    def set_output_configs(self, configs: dict):
        """Set output configurations. Blocks signals to prevent change cascade."""
        # Block signals during setup
        self.device_check.blockSignals(True)
        try:
            has_any = len(configs) > 0
            self.device_check.setChecked(has_any)
            
            for widget in self.output_widgets:
                if widget.output_num in configs:
                    widget.set_config(configs[widget.output_num])
                else:
                    widget.reset()
        finally:
            self.device_check.blockSignals(False)
    
    def reset(self):
        """Reset to default state. Blocks signals to prevent change cascade."""
        self.device_check.blockSignals(True)
        try:
            self.device_check.setChecked(False)
            self._enabled = False
            for widget in self.output_widgets:
                widget.reset()
        finally:
            self.device_check.blockSignals(False)


class CaseEditor(QWidget):
    """Expandable case editor for ON/OFF cases - expands fully when enabled"""
    
    changed = pyqtSignal()
    
    # Master stylesheet with all states - set once, never changed
    _MASTER_STYLESHEET = None
    _HEADER_EXPANDED_STYLE = None
    
    @classmethod
    def _init_master_styles(cls):
        """Initialize master stylesheet once - uses property selectors for state"""
        if cls._MASTER_STYLESHEET is None:
            cls._MASTER_STYLESHEET = f"""
                CaseEditor[caseState="disabled"] {{
                    background-color: {COLORS['bg_dark']};
                    border: 1px solid {COLORS['border_default']};
                    border-radius: 8px;
                }}
                CaseEditor[caseState="disabled"]:hover {{
                    border-color: {COLORS['text_muted']};
                }}
                CaseEditor[caseState="enabled"] {{
                    background-color: {COLORS['bg_light']};
                    border: 2px solid {COLORS['accent_green']};
                    border-radius: 8px;
                }}
                CaseEditor[caseState="enabled"]:hover {{
                    border-color: {COLORS['accent_blue']};
                }}
                CaseEditor[caseState="has_data"] {{
                    background-color: {COLORS['bg_dark']};
                    border: 2px solid {COLORS['accent_orange']};
                    border-radius: 8px;
                }}
                CaseEditor[caseState="has_data"]:hover {{
                    border-color: {COLORS['accent_yellow']};
                }}
                CaseEditor[caseState="expanded"] {{
                    background-color: {COLORS['bg_medium']};
                    border: 2px solid {COLORS['accent_blue']};
                    border-radius: 8px;
                }}
            """
            cls._HEADER_EXPANDED_STYLE = f"""
                QFrame {{
                    background-color: {COLORS['bg_light']};
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }}
            """
    
    def __init__(self, case_type: str, case_index: int, parent=None):
        super().__init__(parent)
        self.case_type = case_type
        self.case_index = case_index
        self.device_widgets = {}
        self.is_expanded = False
        self.is_default = False  # Track if case was loaded from preset
        self._stored_config = None  # Store config when enabled
        self._cached_style_state = None  # Track current style state
        
        # Initialize class-level styles once
        CaseEditor._init_master_styles()
        
        # Set master stylesheet once - never changes
        self.setStyleSheet(CaseEditor._MASTER_STYLESHEET)
        
        self._setup_ui()
        self._update_style()
    
    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (always visible) - clickable
        self.header = QFrame()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)
        
        case_label = f"{self.case_type.upper()} Case {self.case_index + 1}"
        self.enable_check = QCheckBox(case_label)
        self.enable_check.setFont(QFont("", 12, QFont.Weight.Bold))
        self.enable_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                spacing: 10px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 5px;
                border: 2px solid rgba(100, 100, 100, 0.8);
                background: rgba(60, 60, 60, 0.9);
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['accent_blue']};
                background: rgba(80, 80, 80, 1.0);
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent_green']};
                border-color: {COLORS['accent_green']};
            }}
            QCheckBox::indicator:checked:hover {{
                background: {COLORS['accent_primary']};
                border-color: {COLORS['accent_primary']};
            }}
        """)
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        header_layout.addWidget(self.enable_check, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # Default label (italicized, shown when case was loaded from preset)
        self.default_label = QLabel("default")
        self.default_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-style: italic;
            font-size: 11px;
            background: transparent;
        """)
        self.default_label.setVisible(False)
        header_layout.addWidget(self.default_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addStretch()
        
        # Clear button - explicitly clears case data
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(70, 70, 70, 0.9);
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                min-width: 50px;
                max-width: 50px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger']};
                color: white;
            }}
        """)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setVisible(False)  # Only show when case has data
        header_layout.addWidget(self.clear_btn)
        
        # Spacer between clear button and expand arrow
        header_layout.addSpacing(16)
        
        self.expand_label = QLabel("▶")
        self.expand_label.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        header_layout.addWidget(self.expand_label)
        
        self.main_layout.addWidget(self.header)
        
        # Content (hidden by default) - full configuration interface
        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(16, 8, 16, 16)
        content_layout.setSpacing(16)
        
        # Device selection row
        device_row = QHBoxLayout()
        device_row.setSpacing(12)
        
        device_label = QLabel("Device:")
        device_label.setFont(QFont("", 11, QFont.Weight.Bold))
        device_label.setStyleSheet(f"color: {COLORS['accent_blue']};")
        device_row.addWidget(device_label)
        
        self.device_combo = QComboBox()
        self.device_combo.addItem("Select a device...", None)
        for device_id, device in DEVICES.items():
            self.device_combo.addItem(f"{device.name}", device_id)
        self.device_combo.setMinimumWidth(220)
        self.device_combo.setMinimumHeight(36)
        self.device_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_row.addWidget(self.device_combo)
        device_row.addStretch()
        content_layout.addLayout(device_row)
        
        # Outputs container - shows outputs for selected device
        self.outputs_container = QWidget()
        self.outputs_layout = QVBoxLayout(self.outputs_container)
        self.outputs_layout.setSpacing(8)
        self.outputs_layout.setContentsMargins(0, 8, 0, 0)
        
        # Create device widgets but keep them hidden initially
        for device_id, device in DEVICES.items():
            widget = DeviceOutputsWidget(device, show_header=False)
            widget.changed.connect(self.changed)
            widget.setVisible(False)
            self.device_widgets[device_id] = widget
            self.outputs_layout.addWidget(widget)
        
        content_layout.addWidget(self.outputs_container)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border_default']};")
        content_layout.addWidget(sep)
        
        # Settings row - all in one horizontal layout
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(16)
        
        # Mode label
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("background: transparent;")
        settings_layout.addWidget(mode_label)
        
        # Mode dropdown with card
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Track", "track")
        self.mode_combo.addItem("Toggle", "toggle")
        self.mode_combo.addItem("Timed", "timed")
        self.mode_combo.setMinimumWidth(130)
        self.mode_combo.setMinimumHeight(36)
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.mode_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        settings_layout.addWidget(self.mode_combo)
        
        settings_layout.addSpacing(16)
        
        # Pattern label
        pattern_label = QLabel("Pattern:")
        pattern_label.setStyleSheet("background: transparent;")
        settings_layout.addWidget(pattern_label)
        
        # Pattern dropdown with card
        self.pattern_combo = QComboBox()
        for key, preset in PATTERN_PRESETS.items():
            self.pattern_combo.addItem(preset['name'], key)
        self.pattern_combo.setMinimumWidth(160)
        self.pattern_combo.setMinimumHeight(36)
        self.pattern_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.pattern_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        settings_layout.addWidget(self.pattern_combo)
        
        settings_layout.addStretch()
        content_layout.addLayout(settings_layout)
        
        # Timer/Delay Configuration Section
        # Each timer byte: Bit 0 = Execution Mode, Bit 1 = Scale, Bits 2-7 = Value (0-63)
        
        # Execution mode row (shared between timer and delay)
        exec_mode_layout = QHBoxLayout()
        exec_mode_layout.setSpacing(12)
        
        exec_label = QLabel("Timer Behavior:")
        exec_label.setStyleSheet("background: transparent;")
        exec_label.setToolTip("How timers respond if input changes before completion")
        exec_mode_layout.addWidget(exec_label)
        
        self.timer_exec_mode_combo = QComboBox()
        self.timer_exec_mode_combo.addItem("Fire-and-Forget", "fire_and_forget")
        self.timer_exec_mode_combo.addItem("Track Input", "track_input")
        self.timer_exec_mode_combo.setMinimumWidth(160)
        self.timer_exec_mode_combo.setMinimumHeight(36)
        self.timer_exec_mode_combo.setToolTip(
            "Fire-and-Forget: Timer runs to completion regardless of input state\n"
            "Track Input: Timer cancels if input turns OFF"
        )
        self.timer_exec_mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.timer_exec_mode_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        exec_mode_layout.addWidget(self.timer_exec_mode_combo)
        
        exec_mode_layout.addStretch()
        content_layout.addLayout(exec_mode_layout)
        
        # Timers row
        timers_layout = QHBoxLayout()
        timers_layout.setSpacing(12)
        
        # Timer Delay (delay before sending ON message)
        delay_label = QLabel("Delay:")
        delay_label.setStyleSheet("background: transparent;")
        delay_label.setToolTip("Delay before sending ON message")
        timers_layout.addWidget(delay_label)
        
        self.timer_delay_spin = QSpinBox()
        self.timer_delay_spin.setRange(0, 63)
        self.timer_delay_spin.setValue(0)
        self.timer_delay_spin.setMinimumWidth(70)
        self.timer_delay_spin.setMinimumHeight(36)
        self.timer_delay_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.timer_delay_spin.valueChanged.connect(self._update_timer_display)
        timers_layout.addWidget(self.timer_delay_spin)
        
        self.timer_delay_scale_combo = QComboBox()
        self.timer_delay_scale_combo.addItem("× 0.25s", False)  # False = 0.25s scale
        self.timer_delay_scale_combo.addItem("× 10s", True)     # True = 10s scale
        self.timer_delay_scale_combo.setMinimumWidth(90)
        self.timer_delay_scale_combo.setMinimumHeight(36)
        self.timer_delay_scale_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.timer_delay_scale_combo.currentIndexChanged.connect(self._update_timer_display)
        timers_layout.addWidget(self.timer_delay_scale_combo)
        
        self.timer_delay_result = QLabel("= 0s")
        self.timer_delay_result.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        self.timer_delay_result.setMinimumWidth(80)
        timers_layout.addWidget(self.timer_delay_result)
        
        timers_layout.addSpacing(24)
        
        # Timer On (how long ON state lasts)
        timer_on_label = QLabel("Duration:")
        timer_on_label.setStyleSheet("background: transparent;")
        timer_on_label.setToolTip("How long to stay ON before auto-OFF (0=indefinite)")
        timers_layout.addWidget(timer_on_label)
        
        self.timer_on_spin = QSpinBox()
        self.timer_on_spin.setRange(0, 63)
        self.timer_on_spin.setValue(0)
        self.timer_on_spin.setMinimumWidth(70)
        self.timer_on_spin.setMinimumHeight(36)
        self.timer_on_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.timer_on_spin.valueChanged.connect(self._update_timer_display)
        timers_layout.addWidget(self.timer_on_spin)
        
        self.timer_on_scale_combo = QComboBox()
        self.timer_on_scale_combo.addItem("× 0.25s", False)  # False = 0.25s scale
        self.timer_on_scale_combo.addItem("× 10s", True)     # True = 10s scale
        self.timer_on_scale_combo.setMinimumWidth(90)
        self.timer_on_scale_combo.setMinimumHeight(36)
        self.timer_on_scale_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(55, 55, 55, 0.95);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
        """)
        self.timer_on_scale_combo.currentIndexChanged.connect(self._update_timer_display)
        timers_layout.addWidget(self.timer_on_scale_combo)
        
        self.timer_on_result = QLabel("= 0s")
        self.timer_on_result.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        self.timer_on_result.setMinimumWidth(80)
        timers_layout.addWidget(self.timer_on_result)
        
        timers_layout.addStretch()
        content_layout.addLayout(timers_layout)
        
        # Options row (dropdowns and checkboxes for special flags)
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)
        
        # Ignition Mode dropdown
        ignition_mode_label = QLabel("Ignition Mode:")
        ignition_mode_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        options_layout.addWidget(ignition_mode_label)
        
        self.ignition_mode_combo = QComboBox()
        self.ignition_mode_combo.setMinimumWidth(140)
        self.ignition_mode_combo.setStyleSheet(f"""
            QComboBox {{
                background: rgba(70, 70, 70, 0.9);
                color: {COLORS['text_primary']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 1px solid {COLORS['accent_blue']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background: rgba(50, 50, 50, 0.95);
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['accent_blue']};
            }}
        """)
        self.ignition_mode_combo.addItem("Normal", "normal")
        self.ignition_mode_combo.addItem("Sets Ignition", "set_ignition")
        self.ignition_mode_combo.addItem("Tracks Ignition", "track_ignition")
        self.ignition_mode_combo.setToolTip(
            "Normal: No special ignition behavior\n"
            "Sets Ignition: This input IS the ignition source (typically IN01)\n"
            "Tracks Ignition: Case auto-activates when ignition is ON"
        )
        self.ignition_mode_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        options_layout.addWidget(self.ignition_mode_combo)
        
        self.can_override_check = QCheckBox("Can Be Overridden")
        self.can_override_check.setToolTip("For single-filament brake lights: allows turn signals to override")
        self.can_override_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                spacing: 6px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                background: rgba(70, 70, 70, 0.9);
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent_orange']};
            }}
        """)
        self.can_override_check.stateChanged.connect(lambda: self.changed.emit())
        options_layout.addWidget(self.can_override_check)
        
        self.require_ignition_check = QCheckBox("Requires Ignition")
        self.require_ignition_check.setToolTip("Case only activates when ignition is ON")
        self.require_ignition_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                spacing: 6px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                background: rgba(70, 70, 70, 0.9);
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent_blue']};
            }}
        """)
        self.require_ignition_check.stateChanged.connect(lambda: self.changed.emit())
        options_layout.addWidget(self.require_ignition_check)
        
        options_layout.addStretch()
        content_layout.addLayout(options_layout)
        
        # Conditions section
        conditions_layout = QHBoxLayout()
        conditions_layout.setSpacing(24)
        
        # Must be ON dropdown
        must_on_layout = QVBoxLayout()
        must_on_label = QLabel("Must be ON:")
        must_on_label.setToolTip("This case only activates if ALL selected inputs are currently ON")
        must_on_layout.addWidget(must_on_label)
        
        self.must_on_dropdown = MultiSelectDropdown("None selected")
        self.must_on_dropdown.selection_changed.connect(self.changed)
        must_on_layout.addWidget(self.must_on_dropdown)
        must_on_layout.addStretch()
        conditions_layout.addLayout(must_on_layout)
        
        # Must be OFF dropdown
        must_off_layout = QVBoxLayout()
        must_off_label = QLabel("Must be OFF:")
        must_off_label.setToolTip("This case only activates if ALL selected inputs are currently OFF")
        must_off_layout.addWidget(must_off_label)
        
        self.must_off_dropdown = MultiSelectDropdown("None selected")
        self.must_off_dropdown.selection_changed.connect(self.changed)
        must_off_layout.addWidget(self.must_off_dropdown)
        must_off_layout.addStretch()
        conditions_layout.addLayout(must_off_layout)
        
        conditions_layout.addStretch()
        content_layout.addLayout(conditions_layout)
        
        self.content.setVisible(False)
        self.main_layout.addWidget(self.content)
    
    def _update_style(self):
        """Update visual style based on state. Uses property selectors for fast switching."""
        is_enabled = self.enable_check.isChecked()
        has_data = self._has_configured_data()
        
        # Determine the style state
        if self.is_expanded:
            new_state = 'expanded'
        elif is_enabled:
            new_state = 'enabled'
        elif has_data:
            new_state = 'has_data'
        else:
            new_state = 'disabled'
        
        # Only update if state changed
        if self._cached_style_state != new_state:
            self._cached_style_state = new_state
            
            # Update property - this triggers style refresh via property selectors
            self.setProperty('caseState', new_state)
            self.style().unpolish(self)
            self.style().polish(self)
            
            # Update expand arrow and header
            if new_state == 'expanded':
                self.expand_label.setText("▼")
                self.header.setStyleSheet(CaseEditor._HEADER_EXPANDED_STYLE)
            else:
                self.expand_label.setText("▶")
                self.header.setStyleSheet("")
    
    def _on_enable_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        
        if enabled:
            # Expanding - show content
            self.is_expanded = True
            self.content.setVisible(True)
        else:
            # Disabling - just collapse, DON'T clear data
            # User must explicitly click Clear to remove data
            self.is_expanded = False
            self.content.setVisible(False)
        
        self._update_style()
        self._update_clear_button_visibility()
        self.changed.emit()
    
    def _on_clear_clicked(self):
        """Explicitly clear all case data when user clicks Clear button"""
        reply = QMessageBox.question(
            self, 
            "Clear Case", 
            f"Are you sure you want to clear all data for {self.case_type.upper()} Case {self.case_index + 1}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Disable and clear
            self.enable_check.blockSignals(True)
            self.enable_check.setChecked(False)
            self.enable_check.blockSignals(False)
            
            self.is_expanded = False
            self.content.setVisible(False)
            self._clear_to_empty()
            self.is_default = False
            self.default_label.setVisible(False)
            
            self._update_style()
            self._update_clear_button_visibility()
            self.changed.emit()
    
    def _update_clear_button_visibility(self):
        """Show Clear button only when case has data configured"""
        has_data = self._has_configured_data()
        self.clear_btn.setVisible(has_data)
    
    def _has_configured_data(self) -> bool:
        """Check if this case has any data configured"""
        # Check if any device has configured outputs
        selected_device_id = self.device_combo.currentData()
        if selected_device_id and selected_device_id in self.device_widgets:
            widget = self.device_widgets[selected_device_id]
            output_configs = widget.get_output_configs()
            if output_configs:
                return True
        
        # Check if conditions are set
        if self.must_on_dropdown.get_selected() or self.must_off_dropdown.get_selected():
            return True
        
        return False
    
    def _clear_to_empty(self):
        """Clear all configuration to empty state"""
        self.device_combo.setCurrentIndex(0)  # "Select a device..."
        for widget in self.device_widgets.values():
            widget.setVisible(False)
            widget.reset()
        self.mode_combo.setCurrentIndex(0)
        self.pattern_combo.setCurrentIndex(0)
        # Clear timer configuration
        self.timer_exec_mode_combo.setCurrentIndex(0)  # Fire-and-Forget
        self.timer_delay_spin.setValue(0)
        self.timer_delay_scale_combo.setCurrentIndex(0)  # 0.25s
        self.timer_on_spin.setValue(0)
        self.timer_on_scale_combo.setCurrentIndex(0)  # 0.25s
        self.timer_delay_result.setText("= 0s")
        self.timer_on_result.setText("= 0s (∞)")
        # Clear option flags
        self.ignition_mode_combo.setCurrentIndex(0)  # Normal
        self.can_override_check.setChecked(False)
        self.require_ignition_check.setChecked(False)
        self.must_on_dropdown.clear_selection()
        self.must_off_dropdown.clear_selection()
    
    def _on_device_changed(self, index):
        """Show only the outputs for the selected device"""
        selected_device_id = self.device_combo.currentData()
        
        # Hide all device widgets, show only the selected one
        for device_id, widget in self.device_widgets.items():
            if device_id == selected_device_id:
                widget.setVisible(True)
                widget.set_enabled(True)  # Auto-enable outputs section
            else:
                widget.setVisible(False)
                widget.reset()  # Reset hidden devices
        
        self.changed.emit()
    
    def _update_timer_display(self):
        """Update the calculated timer duration labels"""
        # Calculate delay duration
        delay_value = self.timer_delay_spin.value()
        delay_scale_10s = self.timer_delay_scale_combo.currentData()
        if delay_scale_10s:
            delay_seconds = delay_value * 10.0
        else:
            delay_seconds = delay_value * 0.25
        
        if delay_seconds == 0:
            self.timer_delay_result.setText("= 0s")
        elif delay_seconds >= 60:
            minutes = delay_seconds / 60
            self.timer_delay_result.setText(f"= {minutes:.1f}m")
        else:
            self.timer_delay_result.setText(f"= {delay_seconds:.2g}s")
        
        # Calculate timer on duration
        on_value = self.timer_on_spin.value()
        on_scale_10s = self.timer_on_scale_combo.currentData()
        if on_scale_10s:
            on_seconds = on_value * 10.0
        else:
            on_seconds = on_value * 0.25
        
        if on_seconds == 0:
            self.timer_on_result.setText("= 0s (∞)")
        elif on_seconds >= 60:
            minutes = on_seconds / 60
            self.timer_on_result.setText(f"= {minutes:.1f}m")
        else:
            self.timer_on_result.setText(f"= {on_seconds:.2g}s")
        
        self.changed.emit()
    
    def mousePressEvent(self, event):
        """Toggle expansion on header click"""
        if self.header.geometry().contains(event.pos()):
            # Only expand/collapse if already enabled, otherwise toggle enable
            if self.enable_check.isChecked():
                # Toggle expansion only
                self.is_expanded = not self.is_expanded
                self.content.setVisible(self.is_expanded)
                self._update_style()
            else:
                # Enable and expand
                self.enable_check.setChecked(True)
        super().mousePressEvent(event)
    
    def get_config(self) -> CaseConfig:
        config = CaseConfig()
        config.enabled = self.enable_check.isChecked()
        
        # Save ALL current values regardless of whether they've been "changed"
        config.device_outputs = []
        
        # Get the currently selected device
        selected_device_id = self.device_combo.currentData()
        if selected_device_id and selected_device_id in self.device_widgets:
            widget = self.device_widgets[selected_device_id]
            output_configs = widget.get_output_configs()
            # Save the device with its outputs (even if empty, save empty dict)
            config.device_outputs.append((selected_device_id, output_configs))
        
        # Always save mode and pattern
        config.mode = self.mode_combo.currentData() or 'track'
        config.pattern_preset = self.pattern_combo.currentData() or 'none'
        
        # Save timer configuration
        # Execution mode (shared between timer and delay)
        config.timer_execution_mode = self.timer_exec_mode_combo.currentData() or 'fire_and_forget'
        
        # Timer On (duration)
        config.timer_on_value = self.timer_on_spin.value()
        config.timer_on_scale_10s = self.timer_on_scale_combo.currentData() or False
        
        # Timer Delay
        config.timer_delay_value = self.timer_delay_spin.value()
        config.timer_delay_scale_10s = self.timer_delay_scale_combo.currentData() or False
        
        # Save option flags
        config.ignition_mode = self.ignition_mode_combo.currentData() or "normal"
        config.set_ignition = (config.ignition_mode == "set_ignition")  # Legacy field
        config.can_be_overridden = self.can_override_check.isChecked()
        config.require_ignition_on = self.require_ignition_check.isChecked()
        
        # Always save conditions
        config.must_be_on = self.must_on_dropdown.get_selected()
        config.must_be_off = self.must_off_dropdown.get_selected()
        
        return config
    
    def set_config(self, config: CaseConfig, is_default: bool = False):
        """Set configuration. is_default=True when loaded from preset file."""
        # Block signals during setup to prevent change cascade
        self.enable_check.blockSignals(True)
        self.device_combo.blockSignals(True)
        self.mode_combo.blockSignals(True)
        self.pattern_combo.blockSignals(True)
        self.timer_exec_mode_combo.blockSignals(True)
        self.timer_delay_spin.blockSignals(True)
        self.timer_delay_scale_combo.blockSignals(True)
        self.timer_on_spin.blockSignals(True)
        self.timer_on_scale_combo.blockSignals(True)
        self.ignition_mode_combo.blockSignals(True)
        self.can_override_check.blockSignals(True)
        self.require_ignition_check.blockSignals(True)
        
        try:
            self.enable_check.setChecked(config.enabled)
            
            # Set default flag and show label if this is a preset-loaded config
            self.is_default = is_default and config.enabled
            self.default_label.setVisible(self.is_default)
            
            # Keep collapsed when loading - user clicks to expand
            self.is_expanded = False
            self.content.setVisible(False)
            
            device_output_dict = dict(config.device_outputs) if config.device_outputs else {}
            
            # Set device dropdown and show appropriate widget
            if device_output_dict:
                # Get the first (and only) device
                selected_device_id = list(device_output_dict.keys())[0]
                idx = self.device_combo.findData(selected_device_id)
                if idx >= 0:
                    self.device_combo.setCurrentIndex(idx)
            else:
                self.device_combo.setCurrentIndex(0)  # "Select a device..."
            
            for device_id, widget in self.device_widgets.items():
                if device_id in device_output_dict:
                    widget.setVisible(True)
                    widget.set_enabled(True)
                    widget.set_output_configs(device_output_dict[device_id])
                else:
                    widget.setVisible(False)
                    widget.reset()
            
            idx = self.mode_combo.findData(config.mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            
            idx = self.pattern_combo.findData(config.pattern_preset)
            if idx >= 0:
                self.pattern_combo.setCurrentIndex(idx)
            
            # Set timer configuration
            # Execution mode
            exec_mode = getattr(config, 'timer_execution_mode', 'fire_and_forget')
            idx = self.timer_exec_mode_combo.findData(exec_mode)
            if idx >= 0:
                self.timer_exec_mode_combo.setCurrentIndex(idx)
            
            # Timer Delay
            self.timer_delay_spin.setValue(getattr(config, 'timer_delay_value', 0))
            delay_scale_10s = getattr(config, 'timer_delay_scale_10s', False)
            idx = self.timer_delay_scale_combo.findData(delay_scale_10s)
            if idx >= 0:
                self.timer_delay_scale_combo.setCurrentIndex(idx)
            
            # Timer On (duration)
            self.timer_on_spin.setValue(getattr(config, 'timer_on_value', 0))
            on_scale_10s = getattr(config, 'timer_on_scale_10s', False)
            idx = self.timer_on_scale_combo.findData(on_scale_10s)
            if idx >= 0:
                self.timer_on_scale_combo.setCurrentIndex(idx)
            
            # Update timer display labels
            self._update_timer_labels_only()
            
            # Set option flags
            ignition_mode = getattr(config, 'ignition_mode', 'normal')
            # Handle legacy set_ignition field
            if ignition_mode == 'normal' and getattr(config, 'set_ignition', False):
                ignition_mode = 'set_ignition'
            idx = self.ignition_mode_combo.findData(ignition_mode)
            if idx >= 0:
                self.ignition_mode_combo.setCurrentIndex(idx)
            else:
                self.ignition_mode_combo.setCurrentIndex(0)  # Default to Normal
            
            self.can_override_check.setChecked(getattr(config, 'can_be_overridden', False))
            self.require_ignition_check.setChecked(getattr(config, 'require_ignition_on', False))
            
            self.must_on_dropdown.set_selected(config.must_be_on or [])
            self.must_off_dropdown.set_selected(config.must_be_off or [])
            
            self._update_style()
            self._update_clear_button_visibility()
        finally:
            # Always unblock signals
            self.enable_check.blockSignals(False)
            self.device_combo.blockSignals(False)
            self.mode_combo.blockSignals(False)
            self.pattern_combo.blockSignals(False)
            self.timer_exec_mode_combo.blockSignals(False)
            self.timer_delay_spin.blockSignals(False)
            self.timer_delay_scale_combo.blockSignals(False)
            self.timer_on_spin.blockSignals(False)
            self.timer_on_scale_combo.blockSignals(False)
            self.ignition_mode_combo.blockSignals(False)
            self.can_override_check.blockSignals(False)
            self.require_ignition_check.blockSignals(False)
    
    def _update_timer_labels_only(self):
        """Update timer display labels without emitting changed signal"""
        # Calculate delay duration
        delay_value = self.timer_delay_spin.value()
        delay_scale_10s = self.timer_delay_scale_combo.currentData()
        if delay_scale_10s:
            delay_seconds = delay_value * 10.0
        else:
            delay_seconds = delay_value * 0.25
        
        if delay_seconds == 0:
            self.timer_delay_result.setText("= 0s")
        elif delay_seconds >= 60:
            minutes = delay_seconds / 60
            self.timer_delay_result.setText(f"= {minutes:.1f}m")
        else:
            self.timer_delay_result.setText(f"= {delay_seconds:.2g}s")
        
        # Calculate timer on duration
        on_value = self.timer_on_spin.value()
        on_scale_10s = self.timer_on_scale_combo.currentData()
        if on_scale_10s:
            on_seconds = on_value * 10.0
        else:
            on_seconds = on_value * 0.25
        
        if on_seconds == 0:
            self.timer_on_result.setText("= 0s (∞)")
        elif on_seconds >= 60:
            minutes = on_seconds / 60
            self.timer_on_result.setText(f"= {minutes:.1f}m")
        else:
            self.timer_on_result.setText(f"= {on_seconds:.2g}s")
    
    def reset(self):
        """Reset to empty disabled state. Blocks signals to prevent change cascade."""
        # Block signals during reset
        self.enable_check.blockSignals(True)
        self.device_combo.blockSignals(True)
        self.mode_combo.blockSignals(True)
        self.pattern_combo.blockSignals(True)
        self.timer_exec_mode_combo.blockSignals(True)
        self.timer_delay_spin.blockSignals(True)
        self.timer_delay_scale_combo.blockSignals(True)
        self.timer_on_spin.blockSignals(True)
        self.timer_on_scale_combo.blockSignals(True)
        self.ignition_mode_combo.blockSignals(True)
        self.can_override_check.blockSignals(True)
        self.require_ignition_check.blockSignals(True)
        
        try:
            self.enable_check.setChecked(False)
            
            self.is_default = False
            self.default_label.setVisible(False)
            self.is_expanded = False
            self.content.setVisible(False)
            
            self.device_combo.setCurrentIndex(0)  # "Select a device..."
            for widget in self.device_widgets.values():
                widget.setVisible(False)
                widget.reset()
            self.mode_combo.setCurrentIndex(0)
            self.pattern_combo.setCurrentIndex(0)
            
            # Reset timer configuration
            self.timer_exec_mode_combo.setCurrentIndex(0)  # Fire-and-Forget
            self.timer_delay_spin.setValue(0)
            self.timer_delay_scale_combo.setCurrentIndex(0)  # 0.25s
            self.timer_on_spin.setValue(0)
            self.timer_on_scale_combo.setCurrentIndex(0)  # 0.25s
            self.timer_delay_result.setText("= 0s")
            self.timer_on_result.setText("= 0s (∞)")
            
            # Reset option flags
            self.ignition_mode_combo.setCurrentIndex(0)  # Normal
            self.can_override_check.setChecked(False)
            self.require_ignition_check.setChecked(False)
            
            self.must_on_dropdown.clear_selection()
            self.must_off_dropdown.clear_selection()
            
            self._update_style()
            self._update_clear_button_visibility()
        finally:
            self.enable_check.blockSignals(False)
            self.device_combo.blockSignals(False)
            self.mode_combo.blockSignals(False)
            self.pattern_combo.blockSignals(False)
            self.timer_exec_mode_combo.blockSignals(False)
            self.timer_delay_spin.blockSignals(False)
            self.timer_delay_scale_combo.blockSignals(False)
            self.timer_on_spin.blockSignals(False)
            self.timer_on_scale_combo.blockSignals(False)
            self.ignition_mode_combo.blockSignals(False)
            self.can_override_check.blockSignals(False)
            self.require_ignition_check.blockSignals(False)


class InputConfigPanel(QWidget):
    """Configuration panel for selected input"""
    
    changed = pyqtSignal()
    
    # Maximum case counts (for creating editors)
    MAX_ON_CASES = 6
    MAX_OFF_CASES = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_input = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        self.header_label = QLabel("Select an input to configure")
        self.header_label.setFont(QFont("", 16, QFont.Weight.Bold))
        layout.addWidget(self.header_label)
        
        self.subheader_label = QLabel("")
        self.subheader_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.subheader_label)
        
        # Case count info
        self.case_count_label = QLabel("")
        self.case_count_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(self.case_count_label)
        
        # Custom name
        name_layout = QHBoxLayout()
        name_layout.setSpacing(12)
        name_label = QLabel("Custom Name:")
        name_label.setMinimumWidth(100)
        name_layout.addWidget(name_label)
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("Optional custom name...")
        self.custom_name_edit.setMinimumHeight(36)
        self.custom_name_edit.textChanged.connect(self.changed)
        name_layout.addWidget(self.custom_name_edit, 1)
        layout.addLayout(name_layout)
        
        # Scroll area for cases
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(8)
        
        # ON Cases section
        self.on_label = QLabel("ON Cases")
        self.on_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.on_label.setStyleSheet(f"color: {COLORS['accent_green']};")
        self.scroll_layout.addWidget(self.on_label)
        
        self.on_case_editors = []
        for i in range(self.MAX_ON_CASES):
            editor = CaseEditor('on', i)
            editor.changed.connect(self.changed)
            self.on_case_editors.append(editor)
            self.scroll_layout.addWidget(editor)
        
        # OFF Cases section
        self.off_label = QLabel("OFF Cases")
        self.off_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.off_label.setStyleSheet(f"color: {COLORS['accent_red']}; margin-top: 16px;")
        self.scroll_layout.addWidget(self.off_label)
        
        self.off_case_editors = []
        for i in range(self.MAX_OFF_CASES):
            editor = CaseEditor('off', i)
            editor.changed.connect(self.changed)
            self.off_case_editors.append(editor)
            self.scroll_layout.addWidget(editor)
        
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
    
    def _update_case_visibility(self, input_number: int):
        """Show/hide case editors based on the input's actual case counts."""
        on_count, off_count = get_case_counts(input_number)
        
        # Update case count label
        if off_count > 0:
            self.case_count_label.setText(f"Available: {on_count} ON case(s), {off_count} OFF case(s)")
        else:
            self.case_count_label.setText(f"Available: {on_count} ON case(s)")
        
        # Show/hide ON case editors
        for i, editor in enumerate(self.on_case_editors):
            editor.setVisible(i < on_count)
            if i >= on_count:
                editor.reset()  # Clear hidden cases
        
        # Show/hide OFF section and editors
        has_off_cases = off_count > 0
        self.off_label.setVisible(has_off_cases)
        
        for i, editor in enumerate(self.off_case_editors):
            editor.setVisible(i < off_count)
            if i >= off_count:
                editor.reset()  # Clear hidden cases
    
    def set_input(self, input_def: InputDefinition):
        """Set the input definition. Updates labels and case visibility."""
        self.current_input = input_def
        self.header_label.setText(f"Input {input_def.number}: {input_def.name}")
        self.subheader_label.setText(
            f"Type: {input_def.input_type.title()} | Connector {input_def.connector}, Pin {input_def.pin}"
        )
        
        # Update which case editors are visible for this input
        self._update_case_visibility(input_def.number)
        
        # Note: Don't reset editors here - set_config() will set all values directly
        # This avoids double-updating (reset then set)
    
    def get_config(self) -> InputConfig:
        if not self.current_input:
            return InputConfig(input_number=1)
        
        config = InputConfig(input_number=self.current_input.number)
        config.custom_name = self.custom_name_edit.text()
        
        # Get case counts for this input
        on_count, off_count = get_case_counts(self.current_input.number)
        
        # Only get configs from visible case editors
        for i in range(min(on_count, len(self.on_case_editors))):
            config.on_cases[i] = self.on_case_editors[i].get_config()
        
        for i in range(min(off_count, len(self.off_case_editors))):
            config.off_cases[i] = self.off_case_editors[i].get_config()
        
        return config
    
    def set_config(self, config: InputConfig, is_default: bool = False):
        """Set configuration. is_default=True marks cases loaded from preset."""
        self.custom_name_edit.blockSignals(True)
        self.custom_name_edit.setText(config.custom_name)
        self.custom_name_edit.blockSignals(False)
        
        # Get case counts for this input
        input_number = config.input_number
        on_count, off_count = get_case_counts(input_number)
        
        # Set case configs for visible editors only
        for i in range(min(on_count, len(self.on_case_editors), len(config.on_cases))):
            self.on_case_editors[i].set_config(config.on_cases[i], is_default=is_default)
        
        for i in range(min(off_count, len(self.off_case_editors), len(config.off_cases))):
            self.off_case_editors[i].set_config(config.off_cases[i], is_default=is_default)


class InputsPage(QWidget):
    """Input configuration with master-detail layout"""
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_input_number = None
        self.is_preset_loaded = False  # Track if config came from preset
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Input list
        left_panel = QWidget()
        left_panel.setObjectName("inputListPanel")
        left_panel.setMinimumWidth(260)
        left_panel.setMaximumWidth(320)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(12, 12, 12, 12)
        
        header = QLabel("Inputs")
        header.setFont(QFont("", 16, QFont.Weight.Bold))
        left_layout.addWidget(header)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        filter_label = QLabel("Filter:")
        filter_label.setMinimumWidth(40)
        filter_layout.addWidget(filter_label)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Inputs", "all")
        self.filter_combo.addItem("Ground Switched", "ground")
        self.filter_combo.addItem("High-Side", "high_side")
        self.filter_combo.addItem("Configured Only", "configured")
        self.filter_combo.setMinimumHeight(32)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_combo, 1)
        left_layout.addLayout(filter_layout)
        
        self.input_list = QListWidget()
        self.input_list.currentRowChanged.connect(self._on_input_selected)
        left_layout.addWidget(self.input_list)
        
        self._populate_input_list()
        splitter.addWidget(left_panel)
        
        # Right panel
        self.config_panel = InputConfigPanel()
        self.config_panel.setObjectName("inputConfigPanel")
        self.config_panel.changed.connect(self._on_config_changed)
        splitter.addWidget(self.config_panel)
        
        splitter.setSizes([280, 720])
        layout.addWidget(splitter)
        
        # Auto-select first input (Input 1)
        if self.input_list.count() > 0:
            self.input_list.setCurrentRow(0)
    
    def _populate_input_list(self, filter_type: str = "all"):
        self.input_list.clear()
        
        for inp in INPUTS:
            if filter_type == "ground" and inp.input_type != "ground":
                continue
            if filter_type == "high_side" and inp.input_type != "high_side":
                continue
            if filter_type == "configured":
                input_config = self.config.inputs[inp.number - 1]
                if not any(c.enabled for c in input_config.on_cases + input_config.off_cases):
                    continue
            
            input_config = self.config.inputs[inp.number - 1]
            has_config = any(c.enabled for c in input_config.on_cases + input_config.off_cases)
            
            icon = ICONS['input_configured'] if has_config else ICONS['input_empty']
            display_name = input_config.custom_name if input_config.custom_name else inp.name
            
            item = QListWidgetItem(f"{icon} IN{inp.number:02d}: {display_name}")
            item.setData(Qt.ItemDataRole.UserRole, inp.number)
            
            if has_config:
                item.setForeground(Qt.GlobalColor.white)
            else:
                item.setForeground(Qt.GlobalColor.gray)
            
            self.input_list.addItem(item)
    
    def _apply_filter(self, index):
        filter_type = self.filter_combo.currentData()
        self._populate_input_list(filter_type)
    
    def _on_input_selected(self, row):
        # Save current before switching
        self.save_current_input()
        
        if row < 0:
            return
        
        item = self.input_list.item(row)
        if not item:
            return
        
        input_number = item.data(Qt.ItemDataRole.UserRole)
        input_def = get_input_definition(input_number)
        
        if input_def:
            self.current_input_number = input_number
            # Disable UI updates during the switch to prevent lag
            self.config_panel.setUpdatesEnabled(False)
            try:
                self.config_panel.set_input(input_def)
                self.config_panel.set_config(
                    self.config.inputs[input_number - 1],
                    is_default=self.is_preset_loaded
                )
            finally:
                self.config_panel.setUpdatesEnabled(True)
    
    def _on_config_changed(self):
        if self.current_input_number:
            config = self.config_panel.get_config()
            self.config.inputs[self.current_input_number - 1] = config
            self._update_list_item(self.current_input_number)
    
    def _update_list_item(self, input_number: int):
        for i in range(self.input_list.count()):
            item = self.input_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == input_number:
                input_config = self.config.inputs[input_number - 1]
                input_def = get_input_definition(input_number)
                
                if input_def:
                    has_config = any(c.enabled for c in input_config.on_cases + input_config.off_cases)
                    icon = ICONS['input_configured'] if has_config else ICONS['input_empty']
                    display_name = input_config.custom_name if input_config.custom_name else input_def.name
                    
                    item.setText(f"{icon} IN{input_number:02d}: {display_name}")
                    
                    if has_config:
                        item.setForeground(Qt.GlobalColor.white)
                    else:
                        item.setForeground(Qt.GlobalColor.gray)
                break
    
    def save_current_input(self):
        """Save current input configuration"""
        if self.current_input_number:
            self.config.inputs[self.current_input_number - 1] = self.config_panel.get_config()
    
    def set_configuration(self, config: FullConfiguration, is_preset: bool = False):
        """Set the full configuration. is_preset=True marks cases as 'default'."""
        # Store the new configuration
        self.config = config
        self.current_input_number = None
        self.is_preset_loaded = is_preset
        
        # Reset the config panel to clear any stale state from previous configuration
        self._reset_config_panel()
        
        # Repopulate the list with new configuration data
        self._populate_input_list(self.filter_combo.currentData() or "all")
        
        # Auto-select first input (Input 1) - this will load the new config for input 1
        if self.input_list.count() > 0:
            self.input_list.setCurrentRow(0)
    
    def _reset_config_panel(self):
        """Reset all editors in the config panel to clear stale state"""
        # Reset custom name
        self.config_panel.custom_name_edit.setText("")
        
        # Reset all case editors
        for editor in self.config_panel.on_case_editors:
            editor.reset()
        for editor in self.config_panel.off_case_editors:
            editor.reset()

