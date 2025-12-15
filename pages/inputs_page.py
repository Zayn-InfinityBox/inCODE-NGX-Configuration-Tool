"""
inputs_page.py - Input configuration page (simplified, no per-input write)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QSpinBox, QLineEdit,
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QFrame, QCheckBox, QSlider, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from styles import COLORS, ICONS
from config_data import (
    INPUTS, InputDefinition, InputConfig, CaseConfig,
    DEVICES, DeviceDefinition, OutputConfig, OutputMode,
    PATTERN_PRESETS, get_input_definition, FullConfiguration
)


class OutputConfigWidget(QWidget):
    """Widget for configuring a single output on a device"""
    
    changed = pyqtSignal()
    
    def __init__(self, output_num: int, output_name: str, supports_pwm: bool = True, parent=None):
        super().__init__(parent)
        self.output_num = output_num
        self.output_name = output_name
        self.supports_pwm = supports_pwm
        self.config = OutputConfig()
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)
        
        # Enable checkbox
        self.enable_check = QCheckBox(self.output_name)
        self.enable_check.setMinimumWidth(120)
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_check)
        
        # Mode dropdown
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Track", OutputMode.TRACK)
        self.mode_combo.addItem("Soft-Start", OutputMode.SOFT_START)
        if self.supports_pwm:
            self.mode_combo.addItem("PWM", OutputMode.PWM)
        self.mode_combo.setMinimumWidth(120)
        self.mode_combo.setMinimumHeight(32)
        self.mode_combo.setEnabled(False)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)
        
        # PWM duty cycle
        self.pwm_label = QLabel("Duty:")
        self.pwm_label.setVisible(False)
        layout.addWidget(self.pwm_label)
        
        self.pwm_slider = QSlider(Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(0, 15)
        self.pwm_slider.setValue(15)
        self.pwm_slider.setMinimumWidth(120)
        self.pwm_slider.setVisible(False)
        self.pwm_slider.valueChanged.connect(self._on_pwm_changed)
        layout.addWidget(self.pwm_slider)
        
        self.pwm_value = QLabel("100%")
        self.pwm_value.setMinimumWidth(50)
        self.pwm_value.setVisible(False)
        layout.addWidget(self.pwm_value)
        
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
        self.config = config
        self.enable_check.setChecked(config.enabled)
        
        idx = self.mode_combo.findData(config.mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        
        self.pwm_slider.setValue(config.pwm_duty)
    
    def reset(self):
        self.enable_check.setChecked(False)
        self.mode_combo.setCurrentIndex(0)
        self.pwm_slider.setValue(15)


class DeviceOutputsWidget(QWidget):
    """Widget for configuring all outputs on a single device"""
    
    changed = pyqtSignal()
    
    def __init__(self, device: DeviceDefinition, parent=None):
        super().__init__(parent)
        self.device = device
        self.output_widgets = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Device header with enable checkbox
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
        
        # Outputs container
        self.outputs_container = QWidget()
        outputs_layout = QVBoxLayout(self.outputs_container)
        outputs_layout.setContentsMargins(20, 4, 0, 4)
        outputs_layout.setSpacing(2)
        
        # Create output widgets
        for i, output_name in enumerate(self.device.outputs):
            output_num = i + 1
            supports_pwm = (self.device.device_type == "powercell" and output_num <= 8)
            
            widget = OutputConfigWidget(output_num, output_name, supports_pwm)
            widget.changed.connect(self.changed)
            self.output_widgets.append(widget)
            outputs_layout.addWidget(widget)
        
        self.outputs_container.setVisible(False)
        layout.addWidget(self.outputs_container)
    
    def _on_device_toggled(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.outputs_container.setVisible(enabled)
        
        if not enabled:
            for widget in self.output_widgets:
                widget.reset()
        
        self.changed.emit()
    
    def is_enabled(self) -> bool:
        return self.device_check.isChecked()
    
    def get_output_configs(self) -> dict:
        configs = {}
        for widget in self.output_widgets:
            config = widget.get_config()
            if config.enabled:
                configs[widget.output_num] = config
        return configs
    
    def set_output_configs(self, configs: dict):
        has_any = len(configs) > 0
        self.device_check.setChecked(has_any)
        
        for widget in self.output_widgets:
            if widget.output_num in configs:
                widget.set_config(configs[widget.output_num])
            else:
                widget.reset()
    
    def reset(self):
        self.device_check.setChecked(False)
        for widget in self.output_widgets:
            widget.reset()


class CaseEditor(QWidget):
    """Expandable case editor for ON/OFF cases - expands fully when enabled"""
    
    changed = pyqtSignal()
    
    def __init__(self, case_type: str, case_index: int, parent=None):
        super().__init__(parent)
        self.case_type = case_type
        self.case_index = case_index
        self.device_widgets = {}
        self.is_expanded = False
        
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
        header_layout.setContentsMargins(12, 12, 12, 12)
        
        case_label = f"{self.case_type.upper()} Case {self.case_index + 1}"
        self.enable_check = QCheckBox(case_label)
        self.enable_check.setFont(QFont("", 12, QFont.Weight.Bold))
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        header_layout.addWidget(self.enable_check)
        
        header_layout.addStretch()
        
        self.expand_label = QLabel("▶")
        self.expand_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        header_layout.addWidget(self.expand_label)
        
        self.main_layout.addWidget(self.header)
        
        # Content (hidden by default) - full configuration interface
        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(16, 8, 16, 16)
        content_layout.setSpacing(16)
        
        # Device selection section header
        devices_header = QLabel("Select Devices and Outputs to Control:")
        devices_header.setFont(QFont("", 11, QFont.Weight.Bold))
        devices_header.setStyleSheet(f"color: {COLORS['accent_blue']};")
        content_layout.addWidget(devices_header)
        
        # Device widgets - no scroll limit, full expansion
        devices_container = QWidget()
        devices_layout = QVBoxLayout(devices_container)
        devices_layout.setSpacing(8)
        devices_layout.setContentsMargins(0, 0, 0, 0)
        
        for device_id, device in DEVICES.items():
            widget = DeviceOutputsWidget(device)
            widget.changed.connect(self.changed)
            self.device_widgets[device_id] = widget
            devices_layout.addWidget(widget)
        
        content_layout.addWidget(devices_container)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border_default']};")
        content_layout.addWidget(sep)
        
        # Settings row - all in one horizontal layout
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(24)
        
        # Mode
        settings_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Momentary", "momentary")
        self.mode_combo.addItem("Toggle", "toggle")
        self.mode_combo.addItem("Timed", "timed")
        self.mode_combo.setMinimumWidth(120)
        self.mode_combo.setMinimumHeight(32)
        settings_layout.addWidget(self.mode_combo)
        
        # Pattern
        settings_layout.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        for key, preset in PATTERN_PRESETS.items():
            self.pattern_combo.addItem(preset['name'], key)
        self.pattern_combo.setMinimumWidth(150)
        self.pattern_combo.setMinimumHeight(32)
        settings_layout.addWidget(self.pattern_combo)
        
        settings_layout.addStretch()
        content_layout.addLayout(settings_layout)
        
        # Checkboxes row
        checks_layout = QHBoxLayout()
        checks_layout.setSpacing(32)
        
        self.set_ignition_check = QCheckBox("Controls ignition state")
        self.set_ignition_check.setToolTip("This input turns ignition ON/OFF (like the key switch)")
        checks_layout.addWidget(self.set_ignition_check)
        
        self.require_ignition_check = QCheckBox("Requires ignition ON")
        self.require_ignition_check.setToolTip("Only activates when ignition is already ON")
        checks_layout.addWidget(self.require_ignition_check)
        
        self.require_neutral_check = QCheckBox("Requires neutral safety")
        self.require_neutral_check.setToolTip("Only activates when neutral safety is engaged")
        checks_layout.addWidget(self.require_neutral_check)
        
        checks_layout.addStretch()
        content_layout.addLayout(checks_layout)
        
        self.content.setVisible(False)
        self.main_layout.addWidget(self.content)
    
    def _update_style(self):
        """Update visual style based on state"""
        if self.is_expanded:
            self.setStyleSheet(f"""
                CaseEditor {{
                    background-color: {COLORS['bg_medium']};
                    border: 2px solid {COLORS['accent_blue']};
                    border-radius: 8px;
                }}
            """)
            self.expand_label.setText("▼")
            self.header.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_light']};
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }}
            """)
        else:
            if self.enable_check.isChecked():
                self.setStyleSheet(f"""
                    CaseEditor {{
                        background-color: {COLORS['bg_light']};
                        border: 1px solid {COLORS['accent_green']};
                        border-radius: 8px;
                    }}
                """)
            else:
                self.setStyleSheet(f"""
                    CaseEditor {{
                        background-color: {COLORS['bg_dark']};
                        border: 1px solid {COLORS['border_default']};
                        border-radius: 8px;
                    }}
                    CaseEditor:hover {{
                        border-color: {COLORS['text_muted']};
                    }}
                """)
            self.expand_label.setText("▶")
            self.header.setStyleSheet("")
    
    def _on_enable_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.is_expanded = enabled
        self.content.setVisible(enabled)
        self._update_style()
        self.changed.emit()
    
    def mousePressEvent(self, event):
        """Toggle expansion on header click"""
        if self.header.geometry().contains(event.pos()):
            # Toggle the checkbox
            self.enable_check.setChecked(not self.enable_check.isChecked())
        super().mousePressEvent(event)
    
    def get_config(self) -> CaseConfig:
        config = CaseConfig()
        config.enabled = self.enable_check.isChecked()
        
        config.device_outputs = []
        for device_id, widget in self.device_widgets.items():
            if widget.is_enabled():
                output_configs = widget.get_output_configs()
                if output_configs:
                    config.device_outputs.append((device_id, output_configs))
        
        config.mode = self.mode_combo.currentData() or 'momentary'
        config.pattern_preset = self.pattern_combo.currentData() or 'none'
        config.set_ignition = self.set_ignition_check.isChecked()
        config.require_ignition_on = self.require_ignition_check.isChecked()
        config.require_security_on = self.require_neutral_check.isChecked()
        
        return config
    
    def set_config(self, config: CaseConfig):
        self.enable_check.setChecked(config.enabled)
        
        device_output_dict = dict(config.device_outputs) if config.device_outputs else {}
        for device_id, widget in self.device_widgets.items():
            if device_id in device_output_dict:
                widget.set_output_configs(device_output_dict[device_id])
            else:
                widget.reset()
        
        idx = self.mode_combo.findData(config.mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        
        idx = self.pattern_combo.findData(config.pattern_preset)
        if idx >= 0:
            self.pattern_combo.setCurrentIndex(idx)
        
        self.set_ignition_check.setChecked(config.set_ignition)
        self.require_ignition_check.setChecked(config.require_ignition_on)
        self.require_neutral_check.setChecked(config.require_security_on)
    
    def reset(self):
        self.enable_check.setChecked(False)
        for widget in self.device_widgets.values():
            widget.reset()
        self.mode_combo.setCurrentIndex(0)
        self.pattern_combo.setCurrentIndex(0)
        self.set_ignition_check.setChecked(False)
        self.require_ignition_check.setChecked(False)
        self.require_neutral_check.setChecked(False)


class InputConfigPanel(QWidget):
    """Configuration panel for selected input"""
    
    changed = pyqtSignal()
    
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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(8)
        
        # ON Cases
        on_label = QLabel("ON Cases")
        on_label.setFont(QFont("", 12, QFont.Weight.Bold))
        on_label.setStyleSheet(f"color: {COLORS['accent_green']};")
        scroll_layout.addWidget(on_label)
        
        self.on_case_editors = []
        for i in range(8):
            editor = CaseEditor('on', i)
            editor.changed.connect(self.changed)
            self.on_case_editors.append(editor)
            scroll_layout.addWidget(editor)
        
        # OFF Cases
        off_label = QLabel("OFF Cases")
        off_label.setFont(QFont("", 12, QFont.Weight.Bold))
        off_label.setStyleSheet(f"color: {COLORS['accent_red']}; margin-top: 16px;")
        scroll_layout.addWidget(off_label)
        
        self.off_case_editors = []
        for i in range(2):
            editor = CaseEditor('off', i)
            editor.changed.connect(self.changed)
            self.off_case_editors.append(editor)
            scroll_layout.addWidget(editor)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
    
    def set_input(self, input_def: InputDefinition):
        self.current_input = input_def
        self.header_label.setText(f"Input {input_def.number}: {input_def.name}")
        self.subheader_label.setText(
            f"Type: {input_def.input_type.title()} | Connector {input_def.connector}, Pin {input_def.pin}"
        )
        
        self.custom_name_edit.setText("")
        for editor in self.on_case_editors:
            editor.reset()
        for editor in self.off_case_editors:
            editor.reset()
    
    def get_config(self) -> InputConfig:
        if not self.current_input:
            return InputConfig(input_number=1)
        
        config = InputConfig(input_number=self.current_input.number)
        config.custom_name = self.custom_name_edit.text()
        
        for i, editor in enumerate(self.on_case_editors):
            config.on_cases[i] = editor.get_config()
        
        for i, editor in enumerate(self.off_case_editors):
            config.off_cases[i] = editor.get_config()
        
        return config
    
    def set_config(self, config: InputConfig):
        self.custom_name_edit.setText(config.custom_name)
        
        for i, case_config in enumerate(config.on_cases[:8]):
            self.on_case_editors[i].set_config(case_config)
        
        for i, case_config in enumerate(config.off_cases[:2]):
            self.off_case_editors[i].set_config(case_config)


class InputsPage(QWidget):
    """Input configuration with master-detail layout"""
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_input_number = None
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
            self.config_panel.set_input(input_def)
            self.config_panel.set_config(self.config.inputs[input_number - 1])
    
    def _on_config_changed(self):
        if self.current_input_number:
            self.config.inputs[self.current_input_number - 1] = self.config_panel.get_config()
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
    
    def set_configuration(self, config: FullConfiguration):
        """Set the full configuration"""
        self.config = config
        self.current_input_number = None
        self._populate_input_list(self.filter_combo.currentData() or "all")

