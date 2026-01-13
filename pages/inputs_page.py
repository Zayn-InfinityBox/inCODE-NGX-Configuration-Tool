"""
inputs_page.py - Input configuration page (simplified, no per-input write)

Supports three view modes:
- BASIC: Simplified interface with scripted presets
- ADVANCED: Full features with some restrictions  
- ADMIN: Full unrestricted access
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

# Import view mode system
from view_mode import ViewMode, view_mode_manager

# Inputs that are fully locked in Basic mode (all cases locked)
# In Advanced mode, only specific cases are locked (see LOCKED_CASES_BY_INPUT)
LOCKED_INPUTS_BASIC = {"IN01", "IN02", "IN03", "IN04", "IN08", "IN15"}

# Number of locked cases per input in Advanced mode
# IN01, IN02: Only case 1 (index 0) is locked
# IN03, IN04, IN08: Cases 1-2 (indices 0-1) are locked
# IN15: Only case 1 (index 0) is locked
LOCKED_CASES_BY_INPUT = {
    "IN01": 1,  # First 1 case locked (case 1)
    "IN02": 1,  # First 1 case locked (case 1)
    "IN03": 2,  # First 2 cases locked (cases 1-2)
    "IN04": 2,  # First 2 cases locked (cases 1-2)
    "IN08": 2,  # First 2 cases locked (cases 1-2)
    "IN15": 1,  # First 1 case locked (case 1)
}


class NoScrollComboBox(QComboBox):
    """
    A QComboBox that ignores scroll wheel events unless it has focus.
    This prevents accidental value changes when scrolling through the page.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def wheelEvent(self, event):
        # Only process wheel events if the combo box has focus
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            # Pass the event to the parent (allows page scrolling)
            event.ignore()


class InfoIcon(QLabel):
    """
    A small info icon (ⓘ) that displays a tooltip on hover.
    """
    def __init__(self, tooltip_text: str, parent=None):
        super().__init__(parent)
        self.setText("ⓘ")
        # Convert newlines to HTML breaks for proper tooltip display
        html_tooltip = tooltip_text.replace('\n', '<br>')
        self.setToolTip(f"<html><body style='white-space: pre-wrap;'>{html_tooltip}</body></html>")
        self.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 14px;
                font-weight: bold;
                padding: 2px 4px;
                border-radius: 8px;
            }}
            QLabel:hover {{
                color: {COLORS['accent_blue']};
                background: rgba(100, 150, 255, 0.15);
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


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
        self.mode_combo = NoScrollComboBox()
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
    
    def set_basic_mode(self, basic_mode: bool):
        """
        Set basic mode - disables add/remove but allows mode changes.
        Only shows configured outputs in basic mode.
        
        Args:
            basic_mode: If True, disable checkbox but keep mode controls enabled.
                       Also hides this widget if output is not enabled.
        """
        if basic_mode:
            # In basic mode: only show if output is enabled
            if not self.enable_check.isChecked():
                self.setVisible(False)
                return
            
            self.setVisible(True)
            # Keep checkbox visible (shows output name) but disable it
            self.enable_check.setEnabled(False)
            # Mode combo should remain enabled
            self.mode_combo.setEnabled(True)
            # PWM slider should stay enabled if in PWM mode
            if self.mode_combo.currentData() == OutputMode.PWM:
                self.pwm_slider.setEnabled(True)
        else:
            # Normal mode: full control, show everything
            self.setVisible(True)
            self.enable_check.setEnabled(True)
            # Mode combo state depends on whether output is enabled
            self.mode_combo.setEnabled(self.enable_check.isChecked())
            self.pwm_slider.setEnabled(self.enable_check.isChecked())
    
    def set_locked_mode(self, locked: bool):
        """
        Set locked mode - shows output info but nothing is editable.
        Used for locked cases where we want to show config but not allow changes.
        
        Args:
            locked: If True, disable ALL controls. If False, restore normal state.
        """
        if locked:
            # Only show if output is enabled
            if not self.enable_check.isChecked():
                self.setVisible(False)
                return
            
            self.setVisible(True)
            # Disable ALL controls
            self.enable_check.setEnabled(False)
            self.mode_combo.setEnabled(False)
            self.pwm_slider.setEnabled(False)
        else:
            # Restore normal state
            self.setVisible(True)
            self.enable_check.setEnabled(True)
            self.mode_combo.setEnabled(self.enable_check.isChecked())
            self.pwm_slider.setEnabled(self.enable_check.isChecked())
    
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
        
        # Header widget (container for device checkbox and PGN label)
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        if self.show_header:
            # Device header with enable checkbox (only if showing header)
            self.device_check = QCheckBox(self.device.name)
            self.device_check.setFont(QFont("", 11, QFont.Weight.Bold))
            self.device_check.stateChanged.connect(self._on_device_toggled)
            header_layout.addWidget(self.device_check)
            
            pgn = f"0x{self.device.pgn_high:02X}{self.device.pgn_low:02X}"
            self.pgn_label = QLabel(f"(PGN {pgn})")
            self.pgn_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            header_layout.addWidget(self.pgn_label)
            header_layout.addStretch()
            layout.addWidget(self.header_widget)
        else:
            # No header - create a hidden checkbox just to track state
            self.device_check = QCheckBox()
            self.header_widget.setVisible(False)
            self.pgn_label = None
        
        # Basic mode device label (shown only in basic mode)
        self.basic_device_label = QLabel(f"{self.device.name}")
        self.basic_device_label.setStyleSheet(f"""
            color: {COLORS['accent_blue']};
            font-size: 12px;
            font-weight: bold;
            background: transparent;
            padding: 4px 0;
        """)
        self.basic_device_label.setVisible(False)  # Hidden by default
        layout.addWidget(self.basic_device_label)
        
        # Outputs container
        self.outputs_container = QWidget()
        self.outputs_container.setStyleSheet("background: transparent;")
        outputs_layout = QVBoxLayout(self.outputs_container)
        outputs_layout.setContentsMargins(0 if not self.show_header else 20, 4, 0, 4)
        outputs_layout.setSpacing(4)
        
        # Label for selecting outputs (hidden in basic mode)
        self.outputs_label = QLabel("Check the outputs you want to control:")
        self.outputs_label.setStyleSheet(f"color: {COLORS['accent_primary']}; font-weight: 700; font-size: 13px; margin-bottom: 8px; background: transparent;")
        outputs_layout.addWidget(self.outputs_label)
        
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
    
    def set_basic_mode(self, basic_mode: bool):
        """
        Set basic mode on all output widgets.
        
        Args:
            basic_mode: If True, disable add/remove but allow mode changes.
                       Hides non-configured outputs and instructional elements.
        """
        if basic_mode:
            # Hide header (device checkbox and PGN label)
            self.header_widget.setVisible(False)
            # Hide instructional label
            self.outputs_label.setVisible(False)
            
            # Check if ANY output is configured - if not, hide entire widget
            has_configured = any(w.enable_check.isChecked() for w in self.output_widgets)
            if not has_configured:
                self.setVisible(False)
                self.basic_device_label.setVisible(False)
                return
            
            self.setVisible(True)
            # Show simplified device name label in basic mode
            self.basic_device_label.setVisible(True)
        else:
            # Normal mode: show everything
            if self.show_header:
                self.header_widget.setVisible(True)
            self.outputs_label.setVisible(True)
            self.basic_device_label.setVisible(False)  # Hide basic mode label
            self.setVisible(True)
        
        # Propagate to all output widgets
        for widget in self.output_widgets:
            widget.set_basic_mode(basic_mode)
    
    def set_locked_mode(self, locked: bool):
        """
        Set locked mode - shows device/output info but nothing is editable.
        Uses same styling as basic mode but with all controls disabled.
        
        Args:
            locked: If True, disable ALL controls. If False, restore normal state.
        """
        if locked:
            # Hide header (device checkbox and PGN label)
            self.header_widget.setVisible(False)
            # Hide instructional label
            self.outputs_label.setVisible(False)
            
            # Check if ANY output is configured - if not, hide entire widget
            has_configured = any(w.enable_check.isChecked() for w in self.output_widgets)
            if not has_configured:
                self.setVisible(False)
                self.basic_device_label.setVisible(False)
                return
            
            self.setVisible(True)
            # Show simplified device name label (same as basic mode)
            self.basic_device_label.setVisible(True)
        else:
            # Restore normal mode visibility
            if self.show_header:
                self.header_widget.setVisible(True)
            self.outputs_label.setVisible(True)
            self.basic_device_label.setVisible(False)
            self.setVisible(True)
        
        # Propagate locked mode to all output widgets
        for widget in self.output_widgets:
            widget.set_locked_mode(locked)


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
        self._current_view_mode = None  # Current view mode (BASIC/ADVANCED/ADMIN)
        self._is_locked = False  # Track if case is locked (non-editable)
        
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
        
        # Device selection row (hidden in Basic mode)
        self.device_row_widget = QWidget()
        device_row = QHBoxLayout(self.device_row_widget)
        device_row.setContentsMargins(0, 0, 0, 0)
        device_row.setSpacing(12)
        
        device_label = QLabel("Device:")
        device_label.setFont(QFont("", 11, QFont.Weight.Bold))
        device_label.setStyleSheet(f"color: {COLORS['accent_blue']};")
        device_row.addWidget(device_label)
        device_row.addWidget(InfoIcon("Select which device (POWERCELL, inMOTION) this case will send CAN messages to."))
        
        self.device_combo = NoScrollComboBox()
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
        content_layout.addWidget(self.device_row_widget)
        
        # Outputs container - shows outputs for selected device (hidden in Basic mode)
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
        
        # Read-only output display (shown in Basic mode instead of device/outputs)
        self.basic_output_display = QFrame()
        self.basic_output_display.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(50, 55, 60, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        basic_output_layout = QVBoxLayout(self.basic_output_display)
        basic_output_layout.setSpacing(6)
        basic_output_layout.setContentsMargins(12, 10, 12, 10)
        
        basic_output_header = QLabel("CONFIGURED OUTPUT")
        basic_output_header.setStyleSheet(f"""
            color: {COLORS['accent_blue']};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        basic_output_layout.addWidget(basic_output_header)
        
        self.basic_output_label = QLabel("No output configured")
        self.basic_output_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 13px;
            padding: 4px 0px;
        """)
        self.basic_output_label.setWordWrap(True)
        basic_output_layout.addWidget(self.basic_output_label)
        
        self.basic_output_display.setVisible(False)  # Hidden by default (shown in Basic mode)
        content_layout.addWidget(self.basic_output_display)
        
        # =====================================================================
        # SECTION 1: OUTPUT BEHAVIOR
        # =====================================================================
        self.behavior_section = QFrame()
        self.behavior_section.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 50, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 8px;
                margin-top: 8px;
            }}
        """)
        behavior_layout = QVBoxLayout(self.behavior_section)
        behavior_layout.setSpacing(8)
        behavior_layout.setContentsMargins(12, 8, 12, 12)
        
        # Section header
        behavior_header = QLabel("OUTPUT BEHAVIOR")
        behavior_header.setStyleSheet(f"""
            color: {COLORS['accent_blue']};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
        """)
        behavior_layout.addWidget(behavior_header)
        
        # Mode and Pattern row
        mode_pattern_row = QHBoxLayout()
        mode_pattern_row.setSpacing(16)
        
        # Mode
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        mode_pattern_row.addWidget(mode_label)
        mode_pattern_row.addWidget(InfoIcon(
            "Track: Output follows input state (ON when input ON, OFF when input OFF)\n"
            "Toggle: Output toggles with each input press\n"
            "Timed: Output turns ON for a set duration"
        ))
        
        self.mode_combo = NoScrollComboBox()
        self.mode_combo.addItem("Track", "track")
        self.mode_combo.addItem("Toggle", "toggle")
        self.mode_combo.addItem("Timed", "timed")
        self.mode_combo.setMinimumWidth(120)
        self.mode_combo.setMinimumHeight(32)
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QComboBox:hover {{ border: 1px solid {COLORS['accent_blue']}; }}
        """)
        self.mode_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        mode_pattern_row.addWidget(self.mode_combo)
        
        mode_pattern_row.addSpacing(24)
        
        # Pattern
        pattern_label = QLabel("Pattern:")
        pattern_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        mode_pattern_row.addWidget(pattern_label)
        mode_pattern_row.addWidget(InfoIcon(
            "Flash pattern for turn signals and hazards.\n"
            "Controls the ON/OFF timing of the output."
        ))
        
        self.pattern_combo = NoScrollComboBox()
        for key, preset in PATTERN_PRESETS.items():
            self.pattern_combo.addItem(preset['name'], key)
        self.pattern_combo.setMinimumWidth(140)
        self.pattern_combo.setMinimumHeight(32)
        self.pattern_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QComboBox:hover {{ border: 1px solid {COLORS['accent_blue']}; }}
        """)
        self.pattern_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        mode_pattern_row.addWidget(self.pattern_combo)
        
        mode_pattern_row.addStretch()
        behavior_layout.addLayout(mode_pattern_row)
        
        # Track Ignition shortcut row (visible in Basic mode, syncs with ignition_mode_combo)
        self.track_ignition_row = QWidget()
        self.track_ignition_row.setStyleSheet("background: transparent;")
        track_ignition_layout = QHBoxLayout(self.track_ignition_row)
        track_ignition_layout.setContentsMargins(0, 4, 0, 0)
        track_ignition_layout.setSpacing(8)
        
        self.track_ignition_check = QCheckBox("Track Ignition")
        self.track_ignition_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: 12px;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
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
        self.track_ignition_check.stateChanged.connect(self._on_track_ignition_changed)
        track_ignition_layout.addWidget(self.track_ignition_check)
        
        track_ignition_layout.addWidget(InfoIcon(
            "Track Ignition: This case will automatically activate when\n"
            "the ignition is ON, and deactivate when ignition is OFF.\n\n"
            "Use for outputs that should follow the vehicle's ignition\n"
            "state, like gauge illumination or accessories."
        ))
        
        track_ignition_layout.addStretch()
        behavior_layout.addWidget(self.track_ignition_row)
        
        # Hide by default (shown in Basic mode)
        self.track_ignition_row.setVisible(False)
        
        # Configure as Popper shortcut row (visible in Basic mode)
        self.popper_row = QWidget()
        self.popper_row.setStyleSheet("background: transparent;")
        popper_layout = QHBoxLayout(self.popper_row)
        popper_layout.setContentsMargins(0, 4, 0, 0)
        popper_layout.setSpacing(8)
        
        self.popper_check = QCheckBox("Configure as Popper")
        self.popper_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: 12px;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
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
        self.popper_check.stateChanged.connect(self._on_popper_changed)
        popper_layout.addWidget(self.popper_check)
        
        popper_layout.addWidget(InfoIcon(
            "Configure as Popper: Sets up a 0.5 second fire-and-forget timer.\n\n"
            "When the input is triggered, the output will turn ON for 0.5 seconds\n"
            "then automatically turn OFF. Perfect for hood/trunk poppers,\n"
            "momentary relays, or any output that needs a quick pulse."
        ))
        
        popper_layout.addStretch()
        behavior_layout.addWidget(self.popper_row)
        
        # Hide by default (shown in Basic mode)
        self.popper_row.setVisible(False)
        
        # Advanced settings warning (shown in Basic mode when advanced settings are active)
        self.advanced_warning_row = QWidget()
        self.advanced_warning_row.setStyleSheet("background: transparent;")
        warning_layout = QHBoxLayout(self.advanced_warning_row)
        warning_layout.setContentsMargins(0, 8, 0, 0)
        warning_layout.setSpacing(6)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 14px; background: transparent;")
        warning_layout.addWidget(warning_icon)
        
        self.advanced_warning_label = QLabel("")
        self.advanced_warning_label.setStyleSheet(f"""
            color: {COLORS['accent_orange']};
            font-size: 11px;
            font-style: italic;
            background: transparent;
        """)
        self.advanced_warning_label.setWordWrap(True)
        warning_layout.addWidget(self.advanced_warning_label, 1)
        
        behavior_layout.addWidget(self.advanced_warning_row)
        self.advanced_warning_row.setVisible(False)  # Hidden by default
        
        content_layout.addWidget(self.behavior_section)
        
        # =====================================================================
        # SECTION 2: TIMER CONFIGURATION
        # =====================================================================
        self.timer_section = QFrame()
        self.timer_section.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 50, 45, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 8px;
                margin-top: 4px;
            }}
        """)
        timer_layout = QVBoxLayout(self.timer_section)
        timer_layout.setSpacing(8)
        timer_layout.setContentsMargins(12, 8, 12, 12)
        
        # Section header
        timer_header = QLabel("TIMER CONFIGURATION")
        timer_header.setStyleSheet(f"""
            color: {COLORS['accent_green']};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
        """)
        timer_layout.addWidget(timer_header)
        
        # Timer behavior row
        exec_row = QHBoxLayout()
        exec_row.setSpacing(12)
        
        exec_label = QLabel("Behavior:")
        exec_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        exec_row.addWidget(exec_label)
        exec_row.addWidget(InfoIcon(
            "Fire-and-Forget: Timer runs to completion even if input turns OFF\n"
            "Track Input: Timer cancels immediately if input turns OFF"
        ))
        
        self.timer_exec_mode_combo = NoScrollComboBox()
        self.timer_exec_mode_combo.addItem("Fire-and-Forget", "fire_and_forget")
        self.timer_exec_mode_combo.addItem("Track Input", "track_input")
        self.timer_exec_mode_combo.setMinimumWidth(140)
        self.timer_exec_mode_combo.setMinimumHeight(32)
        self.timer_exec_mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QComboBox:hover {{ border: 1px solid {COLORS['accent_green']}; }}
        """)
        self.timer_exec_mode_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        exec_row.addWidget(self.timer_exec_mode_combo)
        exec_row.addStretch()
        timer_layout.addLayout(exec_row)
        
        # Delay and Duration row
        delay_duration_row = QHBoxLayout()
        delay_duration_row.setSpacing(12)
        
        # Delay
        delay_label = QLabel("Delay:")
        delay_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        delay_duration_row.addWidget(delay_label)
        delay_duration_row.addWidget(InfoIcon(
            "Delay before sending the ON message.\n"
            "Example: 3 second delay before starter engages."
        ))
        
        self.timer_delay_spin = QSpinBox()
        self.timer_delay_spin.setRange(0, 63)
        self.timer_delay_spin.setValue(0)
        self.timer_delay_spin.setMinimumWidth(60)
        self.timer_delay_spin.setMinimumHeight(32)
        self.timer_delay_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        self.timer_delay_spin.valueChanged.connect(self._update_timer_display)
        delay_duration_row.addWidget(self.timer_delay_spin)
        
        self.timer_delay_scale_combo = NoScrollComboBox()
        self.timer_delay_scale_combo.addItem("× 0.25s", False)
        self.timer_delay_scale_combo.addItem("× 10s", True)
        self.timer_delay_scale_combo.setMinimumWidth(80)
        self.timer_delay_scale_combo.setMinimumHeight(32)
        self.timer_delay_scale_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        self.timer_delay_scale_combo.currentIndexChanged.connect(self._update_timer_display)
        delay_duration_row.addWidget(self.timer_delay_scale_combo)
        
        self.timer_delay_result = QLabel("= 0s")
        self.timer_delay_result.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent;")
        self.timer_delay_result.setMinimumWidth(60)
        delay_duration_row.addWidget(self.timer_delay_result)
        
        delay_duration_row.addSpacing(20)
        
        # Duration
        duration_label = QLabel("Duration:")
        duration_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        delay_duration_row.addWidget(duration_label)
        delay_duration_row.addWidget(InfoIcon(
            "How long output stays ON before auto-OFF.\n"
            "Set to 0 for indefinite (stays ON while input is ON)."
        ))
        
        self.timer_on_spin = QSpinBox()
        self.timer_on_spin.setRange(0, 63)
        self.timer_on_spin.setValue(0)
        self.timer_on_spin.setMinimumWidth(60)
        self.timer_on_spin.setMinimumHeight(32)
        self.timer_on_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        self.timer_on_spin.valueChanged.connect(self._update_timer_display)
        delay_duration_row.addWidget(self.timer_on_spin)
        
        self.timer_on_scale_combo = NoScrollComboBox()
        self.timer_on_scale_combo.addItem("× 0.25s", False)
        self.timer_on_scale_combo.addItem("× 10s", True)
        self.timer_on_scale_combo.setMinimumWidth(80)
        self.timer_on_scale_combo.setMinimumHeight(32)
        self.timer_on_scale_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        self.timer_on_scale_combo.currentIndexChanged.connect(self._update_timer_display)
        delay_duration_row.addWidget(self.timer_on_scale_combo)
        
        self.timer_on_result = QLabel("= 0s (∞)")
        self.timer_on_result.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent;")
        self.timer_on_result.setMinimumWidth(70)
        delay_duration_row.addWidget(self.timer_on_result)
        
        delay_duration_row.addStretch()
        timer_layout.addLayout(delay_duration_row)
        content_layout.addWidget(self.timer_section)
        
        # =====================================================================
        # SECTION 3: CONDITIONS
        # =====================================================================
        self.conditions_section = QFrame()
        self.conditions_section.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(50, 45, 50, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 8px;
                margin-top: 4px;
            }}
        """)
        conditions_main_layout = QVBoxLayout(self.conditions_section)
        conditions_main_layout.setSpacing(10)
        conditions_main_layout.setContentsMargins(12, 8, 12, 12)
        
        # Section header
        conditions_header = QLabel("CONDITIONS & FLAGS")
        conditions_header.setStyleSheet(f"""
            color: {COLORS['accent_orange']};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
        """)
        conditions_main_layout.addWidget(conditions_header)
        
        # Ignition mode and flags row
        flags_row = QHBoxLayout()
        flags_row.setSpacing(16)
        
        # Ignition Mode
        self.ignition_mode_label = QLabel("Ignition Mode:")
        self.ignition_mode_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        flags_row.addWidget(self.ignition_mode_label)
        self.ignition_mode_info = InfoIcon(
            "Normal: No special ignition behavior\n"
            "Sets Ignition: This input IS the ignition source (typically IN01)\n"
            "Tracks Ignition: Case auto-activates when ignition is ON"
        )
        flags_row.addWidget(self.ignition_mode_info)
        
        self.ignition_mode_combo = NoScrollComboBox()
        self.ignition_mode_combo.addItem("Normal", "normal")
        self.ignition_mode_combo.addItem("Sets Ignition", "set_ignition")
        self.ignition_mode_combo.addItem("Tracks Ignition", "track_ignition")
        self.ignition_mode_combo.setMinimumWidth(130)
        self.ignition_mode_combo.setMinimumHeight(32)
        self.ignition_mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(60, 60, 65, 0.95);
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QComboBox:hover {{ border: 1px solid {COLORS['accent_orange']}; }}
        """)
        self.ignition_mode_combo.currentIndexChanged.connect(lambda: self.changed.emit())
        flags_row.addWidget(self.ignition_mode_combo)
        
        flags_row.addSpacing(16)
        
        # Can Be Overridden checkbox
        self.can_override_check = QCheckBox("Can Be Overridden")
        self.can_override_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                spacing: 6px;
                font-size: 12px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                background: rgba(70, 70, 70, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent_orange']};
            }}
        """)
        self.can_override_check.stateChanged.connect(lambda: self.changed.emit())
        flags_row.addWidget(self.can_override_check)
        flags_row.addWidget(InfoIcon(
            "For single-filament brake lights.\n"
            "Allows turn signals to override brake when both are active."
        ))
        
        flags_row.addSpacing(16)
        
        # Requires Ignition checkbox
        self.require_ignition_check = QCheckBox("Requires Ignition")
        self.require_ignition_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                spacing: 6px;
                font-size: 12px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                background: rgba(70, 70, 70, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent_blue']};
            }}
        """)
        self.require_ignition_check.stateChanged.connect(lambda: self.changed.emit())
        flags_row.addWidget(self.require_ignition_check)
        self.require_ignition_info = InfoIcon(
            "Case only activates when the global ignition flag is ON.\n"
            "This sets bit 5 in the must_be_on bitmask (independent of input selection)."
        )
        flags_row.addWidget(self.require_ignition_info)
        
        flags_row.addStretch()
        conditions_main_layout.addLayout(flags_row)
        
        # Must be ON/OFF row
        must_row = QHBoxLayout()
        must_row.setSpacing(24)
        
        # Must be ON
        must_on_layout = QVBoxLayout()
        must_on_label_row = QHBoxLayout()
        must_on_label = QLabel("Must be ON:")
        must_on_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        must_on_label_row.addWidget(must_on_label)
        must_on_label_row.addWidget(InfoIcon(
            "This case only activates if ALL selected inputs are ON.\n"
            "Example: Starter requires Neutral Safety (IN16) to be ON."
        ))
        must_on_label_row.addStretch()
        must_on_layout.addLayout(must_on_label_row)
        
        self.must_on_dropdown = MultiSelectDropdown("None selected")
        self.must_on_dropdown.selection_changed.connect(self.changed)
        must_on_layout.addWidget(self.must_on_dropdown)
        must_row.addLayout(must_on_layout)
        
        # Must be OFF
        must_off_layout = QVBoxLayout()
        must_off_label_row = QHBoxLayout()
        must_off_label = QLabel("Must be OFF:")
        must_off_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        must_off_label_row.addWidget(must_off_label)
        must_off_label_row.addWidget(InfoIcon(
            "This case only activates if ALL selected inputs are OFF.\n"
            "Used for interlocking or mutually exclusive behaviors."
        ))
        must_off_label_row.addStretch()
        must_off_layout.addLayout(must_off_label_row)
        
        self.must_off_dropdown = MultiSelectDropdown("None selected")
        self.must_off_dropdown.selection_changed.connect(self.changed)
        must_off_layout.addWidget(self.must_off_dropdown)
        must_row.addLayout(must_off_layout)
        
        must_row.addStretch()
        conditions_main_layout.addLayout(must_row)
        content_layout.addWidget(self.conditions_section)
        
        self.content.setVisible(False)
        self.main_layout.addWidget(self.content)
        
        # Locked summary display (shown instead of content when case is locked)
        self.locked_summary = QFrame()
        self.locked_summary.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(50, 55, 60, 0.8);
                border-radius: 8px;
                padding: 12px;
                margin: 8px 16px;
            }}
        """)
        locked_summary_layout = QVBoxLayout(self.locked_summary)
        locked_summary_layout.setContentsMargins(12, 8, 12, 8)
        locked_summary_layout.setSpacing(6)
        
        # Lock icon and title
        locked_title_layout = QHBoxLayout()
        locked_icon = QLabel("🔒")
        locked_icon.setStyleSheet("font-size: 14px; background: transparent;")
        locked_title_layout.addWidget(locked_icon)
        locked_title = QLabel("Locked Configuration")
        locked_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic; background: transparent;")
        locked_title_layout.addWidget(locked_title)
        locked_title_layout.addStretch()
        locked_summary_layout.addLayout(locked_title_layout)
        
        # Summary content label
        self.locked_summary_label = QLabel("")
        self.locked_summary_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 12px;
            background: transparent;
        """)
        self.locked_summary_label.setWordWrap(True)
        locked_summary_layout.addWidget(self.locked_summary_label)
        
        self.locked_summary.setVisible(False)
        self.main_layout.addWidget(self.locked_summary)
    
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
            
            # If locked, apply locked visibility (limited UI)
            if self._is_locked:
                self._apply_locked_visibility()
        else:
            # Disabling - just collapse, DON'T clear data
            # User must explicitly click Clear to remove data
            self.is_expanded = False
            self.content.setVisible(False)
        
        self._update_style()
        self._update_clear_button_visibility()
        self.changed.emit()
    
    def _apply_locked_visibility(self):
        """Apply locked UI visibility - shows only device name and outputs, all read-only."""
        # Hide device selection row
        self.device_row_widget.setVisible(False)
        
        # Show outputs container
        self.outputs_container.setVisible(True)
        
        # Show only the selected device widget
        device_id = self.device_combo.currentData()
        for dev_id, device_widget in self.device_widgets.items():
            device_widget.setVisible(dev_id == device_id)
        
        # Hide all editing sections
        self.behavior_section.setVisible(False)
        self.timer_section.setVisible(False)
        self.conditions_section.setVisible(False)
        
        # Hide shortcut rows and warnings
        self.track_ignition_row.setVisible(False)
        self.popper_row.setVisible(False)
        self.advanced_warning_row.setVisible(False)
    
    def _on_track_ignition_changed(self, state):
        """Handle track ignition checkbox - syncs with ignition_mode_combo"""
        if state == Qt.CheckState.Checked.value:
            # Set ignition mode to track_ignition
            idx = self.ignition_mode_combo.findData("track_ignition")
            if idx >= 0:
                self.ignition_mode_combo.blockSignals(True)
                self.ignition_mode_combo.setCurrentIndex(idx)
                self.ignition_mode_combo.blockSignals(False)
        else:
            # Set ignition mode back to normal
            idx = self.ignition_mode_combo.findData("normal")
            if idx >= 0:
                self.ignition_mode_combo.blockSignals(True)
                self.ignition_mode_combo.setCurrentIndex(idx)
                self.ignition_mode_combo.blockSignals(False)
        self.changed.emit()
    
    def _on_popper_changed(self, state):
        """Handle popper checkbox - sets up fire-and-forget timer of 0.5s"""
        if state == Qt.CheckState.Checked.value:
            # Set timer to fire-and-forget, 0.5s (2 × 0.25s)
            self.timer_exec_mode_combo.blockSignals(True)
            self.timer_delay_spin.blockSignals(True)
            self.timer_delay_scale_combo.blockSignals(True)
            self.timer_on_spin.blockSignals(True)
            self.timer_on_scale_combo.blockSignals(True)
            
            self.timer_exec_mode_combo.setCurrentIndex(0)  # Fire-and-Forget
            self.timer_delay_spin.setValue(0)  # No delay
            self.timer_delay_scale_combo.setCurrentIndex(0)  # 0.25s scale
            self.timer_on_spin.setValue(2)  # 2 × 0.25s = 0.5s
            self.timer_on_scale_combo.setCurrentIndex(0)  # 0.25s scale
            
            self.timer_exec_mode_combo.blockSignals(False)
            self.timer_delay_spin.blockSignals(False)
            self.timer_delay_scale_combo.blockSignals(False)
            self.timer_on_spin.blockSignals(False)
            self.timer_on_scale_combo.blockSignals(False)
            
            # Update timer display
            self._update_timer_display()
        # Note: unchecking doesn't clear the timer - user might want to keep it
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
        self.track_ignition_check.blockSignals(True)
        self.track_ignition_check.setChecked(False)
        self.track_ignition_check.blockSignals(False)
        self.popper_check.blockSignals(True)
        self.popper_check.setChecked(False)
        self.popper_check.blockSignals(False)
        self.can_override_check.setChecked(False)
        self.require_ignition_check.setChecked(False)
        self.must_on_dropdown.clear_selection()
        self.must_off_dropdown.clear_selection()
    
    def _on_device_changed(self, index):
        """Show only the outputs for the selected device"""
        self._refresh_device_visibility()
        self.changed.emit()
    
    def _refresh_device_visibility(self):
        """Refresh device widget visibility based on current selection."""
        selected_device_id = self.device_combo.currentData()
        
        # Hide all device widgets, show only the selected one
        for device_id, widget in self.device_widgets.items():
            if device_id == selected_device_id:
                widget.setVisible(True)
                widget.set_enabled(True)  # Auto-enable outputs section
            else:
                widget.setVisible(False)
                # Don't reset here - we want to preserve the data
    
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
                    # Re-apply basic mode if we're in basic mode (to hide unconfigured outputs)
                    if hasattr(self, '_current_view_mode') and self._current_view_mode == ViewMode.BASIC:
                        widget.set_basic_mode(True)
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
            
            # Sync track ignition checkbox with ignition_mode
            self.track_ignition_check.blockSignals(True)
            self.track_ignition_check.setChecked(ignition_mode == "track_ignition")
            self.track_ignition_check.blockSignals(False)
            
            # Sync popper checkbox - check if timer matches popper config (0.5s fire-and-forget)
            exec_mode = getattr(config, 'timer_exec_mode', 'fire_and_forget')
            timer_delay = getattr(config, 'timer_delay_value', 0)
            timer_on = getattr(config, 'timer_on_value', 0)
            timer_on_scale = getattr(config, 'timer_on_scale_10s', False)
            is_popper_config = (
                exec_mode == 'fire_and_forget' and
                timer_delay == 0 and
                timer_on == 2 and
                timer_on_scale == False  # 0.25s scale, so 2 × 0.25s = 0.5s
            )
            self.popper_check.blockSignals(True)
            self.popper_check.setChecked(is_popper_config)
            self.popper_check.blockSignals(False)
            
            self.can_override_check.setChecked(getattr(config, 'can_be_overridden', False))
            self.require_ignition_check.setChecked(getattr(config, 'require_ignition_on', False))
            
            self.must_on_dropdown.set_selected(config.must_be_on or [])
            self.must_off_dropdown.set_selected(config.must_be_off or [])
            
            self._update_style()
            self._update_clear_button_visibility()
            
            # Update basic mode display if in basic mode
            if hasattr(self, '_current_view_mode') and self._current_view_mode == ViewMode.BASIC:
                self._update_basic_output_display()
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
            self.track_ignition_check.setChecked(False)  # Sync with ignition_mode
            self.popper_check.setChecked(False)  # Clear popper shortcut
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
    
    def set_view_mode(self, mode):
        """
        Update UI visibility based on view mode.
        
        Args:
            mode: ViewMode enum (BASIC, ADVANCED, ADMIN)
        """
        self._current_view_mode = mode
        
        if mode == ViewMode.BASIC:
            # BASIC: Simplified interface
            # Hide device selection dropdown (can't change device)
            self.device_row_widget.setVisible(False)
            # Show outputs container (users can change mode but not add/remove)
            self.outputs_container.setVisible(True)
            # Hide the read-only display (we're showing actual controls)
            self.basic_output_display.setVisible(False)
            
            # Enable basic mode on all device widgets (disables checkboxes, keeps mode dropdowns)
            for device_widget in self.device_widgets.values():
                device_widget.set_basic_mode(True)
            
            # Hide timer section
            if hasattr(self, 'timer_section'):
                self.timer_section.setVisible(False)
            # Hide conditions section (must_be_on/off)
            if hasattr(self, 'conditions_section'):
                self.conditions_section.setVisible(False)
            # Hide advanced options - but show shortcuts
            self.can_override_check.setVisible(False)
            self.ignition_mode_combo.setVisible(False)
            self.track_ignition_row.setVisible(True)  # Show track ignition shortcut
            self.popper_row.setVisible(True)  # Show popper shortcut
            
            # Sync shortcuts with current control values
            self._sync_shortcuts_from_controls()
            
            # Keep behavior section visible (mode/pattern)
            if hasattr(self, 'behavior_section'):
                self.behavior_section.setVisible(True)
            
        elif mode == ViewMode.ADVANCED:
            # ADVANCED: Show most settings
            self.device_row_widget.setVisible(True)
            self.outputs_container.setVisible(True)
            self.basic_output_display.setVisible(False)
            
            # Disable basic mode (full control)
            for device_widget in self.device_widgets.values():
                device_widget.set_basic_mode(False)
            
            # Refresh device visibility to show only selected device
            self._refresh_device_visibility()
            
            if hasattr(self, 'timer_section'):
                self.timer_section.setVisible(True)
            if hasattr(self, 'conditions_section'):
                self.conditions_section.setVisible(True)
            if hasattr(self, 'behavior_section'):
                self.behavior_section.setVisible(True)
            self.can_override_check.setVisible(True)
            self.ignition_mode_combo.setVisible(True)
            self.track_ignition_row.setVisible(False)  # Hide in Advanced (use full ignition_mode_combo)
            self.popper_row.setVisible(False)  # Hide in Advanced (use full timer controls)
            self.advanced_warning_row.setVisible(False)  # No warning needed in Advanced
            
        elif mode == ViewMode.ADMIN:
            # ADMIN: Show everything
            self.device_row_widget.setVisible(True)
            self.outputs_container.setVisible(True)
            self.basic_output_display.setVisible(False)
            
            # Disable basic mode (full control)
            for device_widget in self.device_widgets.values():
                device_widget.set_basic_mode(False)
            
            # Refresh device visibility to show only selected device
            self._refresh_device_visibility()
            
            if hasattr(self, 'timer_section'):
                self.timer_section.setVisible(True)
            if hasattr(self, 'conditions_section'):
                self.conditions_section.setVisible(True)
            if hasattr(self, 'behavior_section'):
                self.behavior_section.setVisible(True)
            self.can_override_check.setVisible(True)
            self.ignition_mode_combo.setVisible(True)
            self.track_ignition_row.setVisible(False)  # Hide in Admin (use full ignition_mode_combo)
            self.popper_row.setVisible(False)  # Hide in Admin (use full timer controls)
            self.advanced_warning_row.setVisible(False)  # No warning needed in Admin
        
        # IMPORTANT: Re-apply locked state if this case is locked
        # This ensures view mode changes don't override the locked UI
        if hasattr(self, '_is_locked') and self._is_locked:
            self.set_locked(True)
    
    def set_locked(self, locked: bool):
        """
        Set the locked state for this case editor.
        When locked, shows the same UI as basic mode but fully read-only.
        
        Args:
            locked: True to lock the editor, False to unlock
        """
        self._is_locked = locked
        
        # Disable/enable the main enable checkbox and clear button
        self.enable_check.setEnabled(not locked)
        self.clear_btn.setEnabled(not locked)
        
        if locked:
            # DON'T auto-expand - keep collapsed by default like non-locked cases
            # The locked UI will be applied when user clicks to expand
            
            # Apply locked mode to all device widgets (shows device name + outputs, all disabled)
            device_id = self.device_combo.currentData()
            for dev_id, device_widget in self.device_widgets.items():
                if dev_id == device_id:
                    device_widget.set_locked_mode(True)
                else:
                    device_widget.setVisible(False)
            
            # ALWAYS apply locked visibility settings (even if collapsed)
            # This ensures correct UI if the case is later expanded or view mode changes
            self._apply_locked_visibility()
            
            # Hide the old basic_output_display and locked_summary
            self.basic_output_display.setVisible(False)
            self.locked_summary.setVisible(False)
        else:
            # Unlock - restore visibility based on view mode
            self.locked_summary.setVisible(False)
            self.basic_output_display.setVisible(False)
            
            # Remove locked mode from all device widgets
            for device_widget in self.device_widgets.values():
                device_widget.set_locked_mode(False)
            
            # Re-apply view mode settings to restore proper visibility
            if hasattr(self, '_current_view_mode') and self._current_view_mode:
                self.set_view_mode(self._current_view_mode)
    
    def _update_locked_summary(self):
        """Update the locked summary display with current configuration."""
        # Get device and outputs info
        device_id = self.device_combo.currentData()
        device = DEVICES.get(device_id) if device_id else None
        
        if not device:
            self.locked_summary_label.setText("No output configured")
            return
        
        # Get configured outputs
        device_widget = self.device_widgets.get(device_id)
        if not device_widget:
            self.locked_summary_label.setText(f"<b>{device.name}</b>")
            return
        
        output_lines = []
        for output_widget in device_widget.output_widgets:
            if output_widget.enable_check.isChecked():
                output_name = output_widget.output_name
                mode = output_widget.mode_combo.currentData()
                if mode:
                    mode_str = mode.name.replace('_', ' ').title()
                    output_lines.append(f"• {output_name} — {mode_str}")
                else:
                    output_lines.append(f"• {output_name}")
        
        if output_lines:
            summary_html = f"<b>📦 {device.name}</b><br>"
            summary_html += "<br>".join(output_lines)
        else:
            summary_html = f"<b>{device.name}</b><br>No outputs configured"
        
        self.locked_summary_label.setText(summary_html)
    
    def set_ignition_controls_visible(self, visible: bool):
        """
        Show or hide ignition-related controls.
        Used to hide these controls for IN01 since it IS the ignition input.
        
        Args:
            visible: True to show ignition controls, False to hide them
        """
        # Hide/show ignition mode combo, its label, and info icon
        self.ignition_mode_label.setVisible(visible)
        self.ignition_mode_info.setVisible(visible)
        self.ignition_mode_combo.setVisible(visible)
        
        # Hide/show require ignition checkbox and info icon
        self.require_ignition_check.setVisible(visible)
        self.require_ignition_info.setVisible(visible)
        
        # Hide/show track ignition checkbox (Basic mode shortcut) - only if visible AND in basic mode
        self.track_ignition_row.setVisible(visible and self._current_view_mode == ViewMode.BASIC)
    
    def _update_basic_output_display(self):
        """Update the read-only output display for Basic mode."""
        # Get current device and outputs
        device_id = self.device_combo.currentData()
        if not device_id or device_id not in self.device_widgets:
            self.basic_output_label.setText("No output configured")
            return
        
        device = DEVICES.get(device_id)
        if not device:
            self.basic_output_label.setText("No output configured")
            return
        
        # Get selected outputs from the device widget
        device_widget = self.device_widgets[device_id]
        selected_outputs = []
        
        # Iterate through output_widgets (list of OutputConfigWidget)
        for output_widget in device_widget.output_widgets:
            if output_widget.enable_check.isChecked():
                # Get the output display name
                display_name = output_widget.output_name
                # Check for mode (soft start, PWM, etc.)
                if hasattr(output_widget, 'mode_combo'):
                    mode = output_widget.mode_combo.currentData()
                    if mode and mode != OutputMode.OFF:
                        # mode is an OutputMode enum, use its name
                        mode_str = mode.name.replace('_', ' ').title()
                        display_name += f" ({mode_str})"
                selected_outputs.append(display_name)
        
        if selected_outputs:
            # Format as device name + outputs
            output_text = f"<b>{device.name}</b><br>"
            output_text += ", ".join(selected_outputs)
            self.basic_output_label.setText(output_text)
        else:
            self.basic_output_label.setText("No outputs selected")
    
    def _sync_shortcuts_from_controls(self):
        """
        Sync shortcut checkboxes with current control values.
        Called when switching to Basic mode to reflect any changes made in Advanced/Admin.
        Also detects and warns about advanced settings that aren't visible in Basic mode.
        """
        # Sync Track Ignition checkbox with ignition_mode_combo
        current_ignition_mode = self.ignition_mode_combo.currentData()
        self.track_ignition_check.blockSignals(True)
        self.track_ignition_check.setChecked(current_ignition_mode == "track_ignition")
        self.track_ignition_check.blockSignals(False)
        
        # Sync Popper checkbox with timer settings
        # Popper = Fire-and-Forget, 0 delay, 2 × 0.25s = 0.5s
        exec_mode = self.timer_exec_mode_combo.currentData()
        timer_delay = self.timer_delay_spin.value()
        timer_on = self.timer_on_spin.value()
        timer_on_scale = self.timer_on_scale_combo.currentData()  # False = 0.25s, True = 10s
        
        is_popper_config = (
            exec_mode == 'fire_and_forget' and
            timer_delay == 0 and
            timer_on == 2 and
            timer_on_scale == False  # 0.25s scale
        )
        self.popper_check.blockSignals(True)
        self.popper_check.setChecked(is_popper_config)
        self.popper_check.blockSignals(False)
        
        # Check for advanced settings not visible in Basic mode
        advanced_settings = []
        
        # Check ignition mode (only "normal" and "track_ignition" available in Basic)
        if current_ignition_mode == "set_ignition":
            advanced_settings.append("Sets Ignition mode")
        
        # Check for custom timer (not 0 and not popper config)
        has_custom_timer = (timer_on > 0 or timer_delay > 0) and not is_popper_config
        if has_custom_timer:
            # Calculate actual time for display
            if timer_on_scale:  # 10s scale
                on_time = timer_on * 10
            else:  # 0.25s scale
                on_time = timer_on * 0.25
            advanced_settings.append(f"Custom timer ({on_time}s)")
        
        # Check can be overridden
        if self.can_override_check.isChecked():
            advanced_settings.append("Can be overridden")
        
        # Check require ignition
        if self.require_ignition_check.isChecked():
            advanced_settings.append("Requires ignition")
        
        # Check must be on/off conditions
        must_on = self.must_on_dropdown.get_selected()
        must_off = self.must_off_dropdown.get_selected()
        if must_on:
            must_on_str = ', '.join(f"IN{n:02d}" for n in must_on)
            advanced_settings.append(f"Must be ON: {must_on_str}")
        if must_off:
            must_off_str = ', '.join(f"IN{n:02d}" for n in must_off)
            advanced_settings.append(f"Must be OFF: {must_off_str}")
        
        # Show/hide warning
        if advanced_settings:
            warning_text = "Advanced settings active: " + " • ".join(advanced_settings)
            warning_text += "\nSwitch to Advanced mode to view or modify."
            self.advanced_warning_label.setText(warning_text)
            self.advanced_warning_row.setVisible(True)
        else:
            self.advanced_warning_row.setVisible(False)


class InputConfigPanel(QWidget):
    """Configuration panel for selected input"""
    
    changed = pyqtSignal()
    
    # Maximum case counts (for creating editors)
    MAX_ON_CASES = 6
    MAX_OFF_CASES = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_input = None
        self._current_view_mode = ViewMode.ADVANCED  # Default view mode
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
        
        # Locked input warning (shown when input is locked in Basic/Advanced mode)
        self.locked_warning = QFrame()
        self.locked_warning.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 150, 50, 0.15);
                border: 1px solid {COLORS['accent_orange']};
                border-radius: 8px;
                padding: 8px;
                margin: 8px 0;
            }}
        """)
        locked_layout = QHBoxLayout(self.locked_warning)
        locked_layout.setContentsMargins(12, 8, 12, 8)
        locked_layout.setSpacing(10)
        
        lock_icon = QLabel("🔒")
        lock_icon.setStyleSheet("font-size: 18px; background: transparent;")
        locked_layout.addWidget(lock_icon)
        
        self.locked_label = QLabel(
            "This input is locked and cannot be edited in Basic or Advanced mode."
        )
        self.locked_label.setStyleSheet(f"""
            color: {COLORS['accent_orange']};
            font-size: 12px;
            background: transparent;
        """)
        self.locked_label.setWordWrap(True)
        locked_layout.addWidget(self.locked_label, 1)
        
        layout.addWidget(self.locked_warning)
        self.locked_warning.setVisible(False)  # Hidden by default
        
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
        
        # Update locked state based on current input and view mode
        self._update_locked_state()
        
        # Update ignition controls visibility (hide for IN01 since it IS the ignition)
        self._update_ignition_controls_visibility()
        
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
        
        # Update Basic mode visibility (hide disabled cases in Basic mode)
        self._update_basic_mode_visibility()
        
        # Re-apply locked state after config is set (ensures locked UI is shown)
        self._update_locked_state()
    
    def set_view_mode(self, mode):
        """
        Set view mode on all case editors.
        
        Args:
            mode: ViewMode enum (BASIC, ADVANCED, ADMIN)
        """
        self._current_view_mode = mode
        
        # Propagate to all case editors
        for editor in self.on_case_editors:
            editor.set_view_mode(mode)
        for editor in self.off_case_editors:
            editor.set_view_mode(mode)
        
        # Update case visibility based on mode
        self._update_basic_mode_visibility()
        
        # Update locked state (may change based on mode)
        self._update_locked_state()
        
        # Update ignition controls visibility (needs to be recalculated after view mode change)
        self._update_ignition_controls_visibility()
    
    def _update_ignition_controls_visibility(self):
        """
        Update ignition controls visibility on all case editors.
        
        For IN01, ignition controls should be hidden because IN01 IS the ignition input.
        It doesn't make sense to show "requires ignition", "track ignition", etc. on it.
        """
        if not self.current_input:
            return
        
        # Hide ignition controls for IN01
        show_ignition_controls = self.current_input.number != 1
        
        for editor in self.on_case_editors:
            if hasattr(editor, 'set_ignition_controls_visible'):
                editor.set_ignition_controls_visible(show_ignition_controls)
        
        for editor in self.off_case_editors:
            if hasattr(editor, 'set_ignition_controls_visible'):
                editor.set_ignition_controls_visible(show_ignition_controls)
    
    def _update_basic_mode_visibility(self):
        """
        In Basic mode, hide case editors that are not enabled.
        In Advanced/Admin mode, show all available case editors.
        """
        if not self.current_input:
            return
        
        on_count, off_count = get_case_counts(self.current_input.number)
        is_basic = self._current_view_mode == ViewMode.BASIC
        
        # Track if we have any visible enabled cases
        visible_on_count = 0
        visible_off_count = 0
        
        # Update ON case visibility
        for i, editor in enumerate(self.on_case_editors):
            if i < on_count:
                if is_basic:
                    # In Basic mode, only show enabled cases
                    is_enabled = editor.enable_check.isChecked()
                    editor.setVisible(is_enabled)
                    if is_enabled:
                        visible_on_count += 1
                else:
                    # In Advanced/Admin mode, show all available cases
                    editor.setVisible(True)
                    visible_on_count += 1
        
        # Update OFF case visibility
        for i, editor in enumerate(self.off_case_editors):
            if i < off_count:
                if is_basic:
                    # In Basic mode, only show enabled cases
                    is_enabled = editor.enable_check.isChecked()
                    editor.setVisible(is_enabled)
                    if is_enabled:
                        visible_off_count += 1
                else:
                    # In Advanced/Admin mode, show all available cases
                    editor.setVisible(True)
                    visible_off_count += 1
        
        # Update OFF section label visibility
        if is_basic:
            # In Basic mode, hide OFF label if no OFF cases are enabled
            self.off_label.setVisible(visible_off_count > 0)
        else:
            # In Advanced/Admin mode, show if there are any OFF cases available
            self.off_label.setVisible(off_count > 0)
    
    def _update_locked_state(self):
        """
        Update the locked state based on current input and view mode.
        
        Basic mode: All cases locked for inputs in LOCKED_INPUTS_BASIC
        Advanced mode: Only specific cases locked (based on LOCKED_CASES_BY_INPUT)
        Admin mode: Nothing locked
        """
        if not self.current_input:
            self.locked_warning.setVisible(False)
            return
        
        input_id = f"IN{self.current_input.number:02d}"
        current_mode = getattr(self, '_current_view_mode', ViewMode.ADVANCED)
        
        # Admin mode: nothing is locked
        if current_mode == ViewMode.ADMIN:
            self.locked_warning.setVisible(False)
            self.custom_name_edit.setEnabled(True)
            for editor in self.on_case_editors:
                editor.set_locked(False)
            for editor in self.off_case_editors:
                editor.set_locked(False)
            return
        
        # Basic mode: entire input is locked if in LOCKED_INPUTS_BASIC
        if current_mode == ViewMode.BASIC:
            is_fully_locked = input_id in LOCKED_INPUTS_BASIC
            self.locked_warning.setVisible(is_fully_locked)
            self.custom_name_edit.setEnabled(not is_fully_locked)
            for editor in self.on_case_editors:
                editor.set_locked(is_fully_locked)
            for editor in self.off_case_editors:
                editor.set_locked(is_fully_locked)
            return
        
        # Advanced mode: case-level locking
        locked_case_count = LOCKED_CASES_BY_INPUT.get(input_id, 0)
        has_locked_cases = locked_case_count > 0
        
        # Show warning if any cases are locked
        if has_locked_cases:
            if locked_case_count == 1:
                self.locked_label.setText(
                    f"Case 1 is locked and cannot be edited. Additional cases can be added and configured freely in Advanced Mode."
                )
            else:
                self.locked_label.setText(
                    f"Cases 1 & 2 are locked and cannot be edited. Additional cases can be added and configured freely in Advanced Mode."
                )
            self.locked_warning.setVisible(True)
        else:
            self.locked_warning.setVisible(False)
        
        # Custom name NOT editable for locked inputs in Advanced mode
        self.custom_name_edit.setEnabled(not has_locked_cases)
        
        # Lock only the first N cases based on LOCKED_CASES_BY_INPUT
        for i, editor in enumerate(self.on_case_editors):
            editor.set_locked(i < locked_case_count)
        
        # OFF cases are not locked in Advanced mode (only ON cases have the restriction)
        for editor in self.off_case_editors:
            editor.set_locked(False)


class InputsPage(QWidget):
    """
    Input configuration with master-detail layout.
    
    Supports three view modes:
    - BASIC: Simplified interface with scripted presets
    - ADVANCED: Full features with some restrictions  
    - ADMIN: Full unrestricted access
    """
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_input_number = None
        self.is_preset_loaded = False  # Track if config came from preset
        self._current_view_mode = None  # Will be set when view mode changes
        self._setup_ui()
        
        # Connect to view mode manager
        view_mode_manager.view_mode_changed.connect(self.on_view_mode_changed)
        self._current_view_mode = view_mode_manager.current_mode
    
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
        self.filter_combo = NoScrollComboBox()
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
            
            # Check if input has any locked cases
            input_id = f"IN{inp.number:02d}"
            has_locked_cases = input_id in LOCKED_CASES_BY_INPUT
            lock_icon = "🔒 " if has_locked_cases else ""
            
            item = QListWidgetItem(f"{icon} {lock_icon}IN{inp.number:02d}: {display_name}")
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
                    
                    # Check if input has any locked cases
                    input_id = f"IN{input_number:02d}"
                    has_locked_cases = input_id in LOCKED_CASES_BY_INPUT
                    lock_icon = "🔒 " if has_locked_cases else ""
                    
                    item.setText(f"{icon} {lock_icon}IN{input_number:02d}: {display_name}")
                    
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
    
    # =========================================================================
    # VIEW MODE HANDLING
    # =========================================================================
    
    def on_view_mode_changed(self, mode):
        """
        Handle view mode changes. Updates UI visibility based on mode.
        
        BASIC mode:
        - Hide timer configuration section
        - Hide must_be_on/must_be_off conditions
        - Show simplified "scripted" options
        
        ADVANCED mode:
        - Show all configuration options
        - Some admin-only features may be hidden
        
        ADMIN mode:
        - Full access to all features
        - No restrictions
        """
        self._current_view_mode = mode
        
        # Update the config panel's view mode
        # This internally propagates to all case editors and handles ignition visibility
        if hasattr(self.config_panel, 'set_view_mode'):
            self.config_panel.set_view_mode(mode)

