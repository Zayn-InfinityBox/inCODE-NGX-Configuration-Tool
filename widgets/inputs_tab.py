"""
inputs_tab.py - Input configuration tab with master-detail layout
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QSpinBox, QLineEdit,
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QFrame, QCheckBox, QSlider, QTabWidget, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont

from can_interface import CANInterface
from config_data import (
    INPUTS, InputDefinition, InputConfig, CaseConfig, 
    DEVICES, DeviceDefinition, OutputConfig, OutputMode,
    PATTERN_PRESETS, get_input_definition,
    calculate_case_address, EEPROM_BYTES_PER_CASE
)
from styles import COLORS, ICONS


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
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)
        
        # Enable checkbox
        self.enable_check = QCheckBox(self.output_name)
        self.enable_check.setMinimumWidth(100)
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_check)
        
        # Mode dropdown
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Track", OutputMode.TRACK)
        self.mode_combo.addItem("Soft-Start", OutputMode.SOFT_START)
        if self.supports_pwm:
            self.mode_combo.addItem("PWM", OutputMode.PWM)
        self.mode_combo.setMinimumWidth(100)
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
        self.pwm_slider.setMaximumWidth(100)
        self.pwm_slider.setVisible(False)
        self.pwm_slider.valueChanged.connect(self._on_pwm_changed)
        layout.addWidget(self.pwm_slider)
        
        self.pwm_value = QLabel("100%")
        self.pwm_value.setMinimumWidth(40)
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
            # PWM only supported for outputs 1-8 on POWERCELL
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
            # Clear all output selections when device is disabled
            for widget in self.output_widgets:
                widget.reset()
        
        self.changed.emit()
    
    def is_enabled(self) -> bool:
        return self.device_check.isChecked()
    
    def get_output_configs(self) -> dict:
        """Get all output configurations as dict[output_num] -> OutputConfig"""
        configs = {}
        for widget in self.output_widgets:
            config = widget.get_config()
            if config.enabled:
                configs[widget.output_num] = config
        return configs
    
    def set_output_configs(self, configs: dict):
        """Set output configurations from dict"""
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
    """Editor widget for a single ON or OFF case"""
    
    changed = pyqtSignal()
    
    def __init__(self, case_type: str, case_index: int, parent=None):
        super().__init__(parent)
        self.case_type = case_type  # 'on' or 'off'
        self.case_index = case_index
        self.config = CaseConfig()
        self.device_widgets = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Header with enable checkbox
        header_layout = QHBoxLayout()
        
        case_label = f"{self.case_type.upper()} Case {self.case_index + 1}"
        self.enable_check = QCheckBox(case_label)
        self.enable_check.setFont(QFont("", 12, QFont.Weight.Bold))
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        header_layout.addWidget(self.enable_check)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Main content (hidden when disabled)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(0, 8, 0, 0)
        
        # Device outputs section
        devices_label = QLabel("Select devices and outputs to control:")
        devices_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        content_layout.addWidget(devices_label)
        
        # Scroll area for devices
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        devices_container = QWidget()
        devices_layout = QVBoxLayout(devices_container)
        devices_layout.setSpacing(8)
        devices_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create device widgets
        for device_id, device in DEVICES.items():
            widget = DeviceOutputsWidget(device)
            widget.changed.connect(self.changed)
            self.device_widgets[device_id] = widget
            devices_layout.addWidget(widget)
        
        devices_layout.addStretch()
        scroll.setWidget(devices_container)
        content_layout.addWidget(scroll)
        
        # Behavior Settings (collapsible)
        behavior_group = QGroupBox("Behavior Settings")
        behavior_layout = QGridLayout(behavior_group)
        behavior_layout.setSpacing(8)
        
        behavior_layout.addWidget(QLabel("Mode:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Track (follows input state)", "track")
        self.mode_combo.addItem("Toggle (flip each press)", "toggle")
        self.mode_combo.addItem("Timed (on for duration)", "timed")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        behavior_layout.addWidget(self.mode_combo, 0, 1, 1, 2)
        
        # Timer settings
        behavior_layout.addWidget(QLabel("On-Time:"), 1, 0)
        self.timer_on_spin = QSpinBox()
        self.timer_on_spin.setRange(0, 127)
        self.timer_on_spin.setSuffix(" × 500ms")
        self.timer_on_spin.valueChanged.connect(self.changed)
        behavior_layout.addWidget(self.timer_on_spin, 1, 1)
        
        self.timer_on_label = QLabel("= 0.0s")
        behavior_layout.addWidget(self.timer_on_label, 1, 2)
        self.timer_on_spin.valueChanged.connect(
            lambda v: self.timer_on_label.setText(f"= {v * 0.5:.1f}s")
        )
        
        behavior_layout.addWidget(QLabel("Delay:"), 2, 0)
        self.timer_delay_spin = QSpinBox()
        self.timer_delay_spin.setRange(0, 127)
        self.timer_delay_spin.setSuffix(" × 500ms")
        self.timer_delay_spin.valueChanged.connect(self.changed)
        behavior_layout.addWidget(self.timer_delay_spin, 2, 1)
        
        self.timer_delay_label = QLabel("= 0.0s")
        behavior_layout.addWidget(self.timer_delay_label, 2, 2)
        self.timer_delay_spin.valueChanged.connect(
            lambda v: self.timer_delay_label.setText(f"= {v * 0.5:.1f}s")
        )
        
        # Pattern
        behavior_layout.addWidget(QLabel("Pattern:"), 3, 0)
        self.pattern_combo = QComboBox()
        for key, preset in PATTERN_PRESETS.items():
            self.pattern_combo.addItem(preset['name'], key)
        self.pattern_combo.currentIndexChanged.connect(self._on_pattern_changed)
        behavior_layout.addWidget(self.pattern_combo, 3, 1, 1, 2)
        
        # Set Ignition
        self.set_ignition_check = QCheckBox("This input sets IGNITION state")
        self.set_ignition_check.stateChanged.connect(self.changed)
        behavior_layout.addWidget(self.set_ignition_check, 4, 0, 1, 3)
        
        content_layout.addWidget(behavior_group)
        
        layout.addWidget(self.content_widget)
        self.content_widget.setVisible(False)
    
    def _on_enable_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.content_widget.setVisible(enabled)
        self.config.enabled = enabled
        self.changed.emit()
    
    def _on_mode_changed(self, index):
        mode = self.mode_combo.currentData()
        self.config.mode = mode
        self.timer_on_spin.setEnabled(mode == 'timed')
        self.timer_delay_spin.setEnabled(mode in ['track', 'timed'])
        self.changed.emit()
    
    def _on_pattern_changed(self, index):
        preset_key = self.pattern_combo.currentData()
        self.config.pattern_preset = preset_key
        self.changed.emit()
    
    def get_config(self) -> CaseConfig:
        config = CaseConfig()
        config.enabled = self.enable_check.isChecked()
        
        # Collect device outputs
        config.device_outputs = []
        for device_id, widget in self.device_widgets.items():
            if widget.is_enabled():
                output_configs = widget.get_output_configs()
                if output_configs:
                    config.device_outputs.append((device_id, output_configs))
        
        config.mode = self.mode_combo.currentData() or 'track'
        config.timer_on = self.timer_on_spin.value()
        config.timer_delay = self.timer_delay_spin.value()
        config.pattern_preset = self.pattern_combo.currentData() or 'none'
        config.set_ignition = self.set_ignition_check.isChecked()
        
        return config
    
    def set_config(self, config: CaseConfig):
        self.config = config
        self.enable_check.setChecked(config.enabled)
        
        # Set device outputs
        device_output_dict = dict(config.device_outputs) if config.device_outputs else {}
        for device_id, widget in self.device_widgets.items():
            if device_id in device_output_dict:
                widget.set_output_configs(device_output_dict[device_id])
            else:
                widget.reset()
        
        idx = self.mode_combo.findData(config.mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        
        self.timer_on_spin.setValue(config.timer_on)
        self.timer_delay_spin.setValue(config.timer_delay)
        
        idx = self.pattern_combo.findData(config.pattern_preset)
        if idx >= 0:
            self.pattern_combo.setCurrentIndex(idx)
        
        self.set_ignition_check.setChecked(config.set_ignition)
    
    def reset(self):
        self.enable_check.setChecked(False)
        for widget in self.device_widgets.values():
            widget.reset()
        self.mode_combo.setCurrentIndex(0)
        self.timer_on_spin.setValue(0)
        self.timer_delay_spin.setValue(0)
        self.pattern_combo.setCurrentIndex(0)
        self.set_ignition_check.setChecked(False)


class InputConfigPanel(QWidget):
    """Configuration panel for a single input (right side of splitter)"""
    
    changed = pyqtSignal()
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.current_input: InputDefinition = None
        self.config = InputConfig(input_number=1)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        self.header_label = QLabel("Select an input to configure")
        self.header_label.setFont(QFont("", 18, QFont.Weight.Bold))
        layout.addWidget(self.header_label)
        
        self.subheader_label = QLabel("")
        self.subheader_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.subheader_label)
        
        # Custom name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Custom Name:"))
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("Enter a custom name for this input...")
        self.custom_name_edit.textChanged.connect(self.changed)
        name_layout.addWidget(self.custom_name_edit)
        layout.addLayout(name_layout)
        
        # Scroll area for cases
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        
        # ON Cases section
        on_label = QLabel("ON Cases (triggered when input activates)")
        on_label.setFont(QFont("", 14, QFont.Weight.Bold))
        on_label.setStyleSheet(f"color: {COLORS['accent_green']};")
        scroll_layout.addWidget(on_label)
        
        self.on_case_editors = []
        for i in range(8):
            editor = CaseEditor('on', i)
            editor.changed.connect(self.changed)
            self.on_case_editors.append(editor)
            scroll_layout.addWidget(editor)
        
        # OFF Cases section
        off_label = QLabel("OFF Cases (triggered when input deactivates)")
        off_label.setFont(QFont("", 14, QFont.Weight.Bold))
        off_label.setStyleSheet(f"color: {COLORS['accent_red']}; margin-top: 20px;")
        scroll_layout.addWidget(off_label)
        
        off_note = QLabel("Note: Most applications only need ON cases. OFF cases are for special scenarios.")
        off_note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        off_note.setWordWrap(True)
        scroll_layout.addWidget(off_note)
        
        self.off_case_editors = []
        for i in range(2):
            editor = CaseEditor('off', i)
            editor.changed.connect(self.changed)
            self.off_case_editors.append(editor)
            scroll_layout.addWidget(editor)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.read_btn = QPushButton("Read from Device")
        self.read_btn.clicked.connect(self._read_from_device)
        btn_layout.addWidget(self.read_btn)
        
        self.write_btn = QPushButton("Write to Device")
        self.write_btn.setObjectName("primaryButton")
        self.write_btn.clicked.connect(self._write_to_device)
        btn_layout.addWidget(self.write_btn)
        
        self.clear_btn = QPushButton("Clear All Cases")
        self.clear_btn.clicked.connect(self._clear_cases)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
    
    def set_input(self, input_def: InputDefinition):
        """Set the input to configure"""
        self.current_input = input_def
        self.config = InputConfig(input_number=input_def.number)
        
        self.header_label.setText(f"Input {input_def.number}: {input_def.name}")
        self.subheader_label.setText(
            f"Type: {input_def.input_type.title()} | "
            f"Connector: {input_def.connector} Pin {input_def.pin}"
        )
        
        self.custom_name_edit.setText("")
        
        # Reset all case editors
        for editor in self.on_case_editors:
            editor.reset()
        for editor in self.off_case_editors:
            editor.reset()
    
    def get_config(self) -> InputConfig:
        """Get current input configuration"""
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
        """Load input configuration"""
        self.config = config
        self.custom_name_edit.setText(config.custom_name)
        
        for i, case_config in enumerate(config.on_cases[:8]):
            self.on_case_editors[i].set_config(case_config)
        
        for i, case_config in enumerate(config.off_cases[:2]):
            self.off_case_editors[i].set_config(case_config)
    
    def _read_from_device(self):
        """Read this input's config from device"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a device first.")
            return
        
        if not self.current_input:
            return
        
        QMessageBox.information(self, "Read", 
            f"Reading configuration for Input {self.current_input.number}...")
    
    def _write_to_device(self):
        """Write this input's config to device"""
        if not self.can.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a device first.")
            return
        
        if not self.current_input:
            return
        
        config = self.get_config()
        
        # Show what will be sent
        messages = []
        for case in config.on_cases:
            if case.enabled:
                messages.extend(case.get_can_messages())
        
        if messages:
            msg_text = "\n".join([
                f"PGN 0x{m[0]:02X}{m[1]:02X}, SA 0x{m[2]:02X}, Data: {' '.join(f'{b:02X}' for b in m[3])}"
                for m in messages
            ])
            QMessageBox.information(self, "Messages to Write", 
                f"Input {self.current_input.number} will send:\n\n{msg_text}")
        else:
            QMessageBox.information(self, "No Messages", 
                "No enabled cases with configured outputs.")
    
    def _clear_cases(self):
        """Clear all cases for this input"""
        reply = QMessageBox.question(self, "Clear Cases",
            "Clear all case configurations for this input?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            for editor in self.on_case_editors:
                editor.reset()
            for editor in self.off_case_editors:
                editor.reset()
            self.changed.emit()


class InputsTab(QWidget):
    """Input configuration with master-detail layout"""
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can = can_interface
        self.input_configs = {i+1: InputConfig(input_number=i+1) for i in range(44)}
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Splitter for master-detail layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Input list
        left_panel = QWidget()
        left_panel.setObjectName("inputListPanel")
        left_panel.setMinimumWidth(280)
        left_panel.setMaximumWidth(350)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        list_header = QLabel("Inputs")
        list_header.setFont(QFont("", 18, QFont.Weight.Bold))
        left_layout.addWidget(list_header)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Inputs", "all")
        self.filter_combo.addItem("Ground Switched", "ground")
        self.filter_combo.addItem("High-Side Switched", "high_side")
        self.filter_combo.addItem("Configured Only", "configured")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_combo)
        left_layout.addLayout(filter_layout)
        
        # Input list
        self.input_list = QListWidget()
        self.input_list.currentRowChanged.connect(self._on_input_selected)
        left_layout.addWidget(self.input_list)
        
        # Populate list
        self._populate_input_list()
        
        splitter.addWidget(left_panel)
        
        # Right panel - Configuration
        self.config_panel = InputConfigPanel(self.can)
        self.config_panel.setObjectName("inputConfigPanel")
        self.config_panel.changed.connect(self._on_config_changed)
        splitter.addWidget(self.config_panel)
        
        # Set splitter sizes
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
    
    def _populate_input_list(self, filter_type: str = "all"):
        """Populate the input list"""
        self.input_list.clear()
        
        for inp in INPUTS:
            # Apply filter
            if filter_type == "ground" and inp.input_type != "ground":
                continue
            if filter_type == "high_side" and inp.input_type != "high_side":
                continue
            if filter_type == "configured":
                config = self.input_configs.get(inp.number)
                if not config or not any(c.enabled for c in config.on_cases + config.off_cases):
                    continue
            
            # Create list item
            config = self.input_configs.get(inp.number)
            has_config = config and any(c.enabled for c in config.on_cases + config.off_cases)
            
            icon = ICONS['input_configured'] if has_config else ICONS['input_empty']
            display_name = config.custom_name if config and config.custom_name else inp.name
            
            item = QListWidgetItem(f"{icon} IN{inp.number:02d}: {display_name}")
            item.setData(Qt.ItemDataRole.UserRole, inp.number)
            
            if has_config:
                item.setForeground(Qt.GlobalColor.white)
            else:
                item.setForeground(Qt.GlobalColor.gray)
            
            self.input_list.addItem(item)
    
    def _apply_filter(self, index):
        """Apply filter to input list"""
        filter_type = self.filter_combo.currentData()
        self._populate_input_list(filter_type)
    
    def _on_input_selected(self, row):
        """Handle input selection"""
        if row < 0:
            return
        
        item = self.input_list.item(row)
        if not item:
            return
        
        input_number = item.data(Qt.ItemDataRole.UserRole)
        input_def = get_input_definition(input_number)
        
        if input_def:
            self.config_panel.set_input(input_def)
            
            # Load saved config if exists
            if input_number in self.input_configs:
                self.config_panel.set_config(self.input_configs[input_number])
    
    def _on_config_changed(self):
        """Handle configuration change"""
        if self.config_panel.current_input:
            input_number = self.config_panel.current_input.number
            self.input_configs[input_number] = self.config_panel.get_config()
            self._update_list_item(input_number)
    
    def _update_list_item(self, input_number: int):
        """Update list item appearance based on config state"""
        for i in range(self.input_list.count()):
            item = self.input_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == input_number:
                config = self.input_configs.get(input_number)
                input_def = get_input_definition(input_number)
                
                if input_def:
                    has_config = config and any(c.enabled for c in config.on_cases + config.off_cases)
                    icon = ICONS['input_configured'] if has_config else ICONS['input_empty']
                    display_name = config.custom_name if config and config.custom_name else input_def.name
                    
                    item.setText(f"{icon} IN{input_number:02d}: {display_name}")
                    
                    if has_config:
                        item.setForeground(Qt.GlobalColor.white)
                    else:
                        item.setForeground(Qt.GlobalColor.gray)
                break
    
    def get_all_configs(self) -> dict:
        """Get all input configurations"""
        return self.input_configs
    
    def set_all_configs(self, configs: dict):
        """Set all input configurations"""
        self.input_configs = configs
        self._populate_input_list(self.filter_combo.currentData() or "all")
