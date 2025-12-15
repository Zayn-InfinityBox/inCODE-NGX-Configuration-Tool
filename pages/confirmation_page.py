"""
confirmation_page.py - Review and confirm configuration changes
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from styles import COLORS, ICONS
from config_data import (
    FullConfiguration, INPUTS, DEVICES, get_input_definition,
    OutputMode
)


class ConfirmationPage(QWidget):
    """Review page showing all configured inputs and cases"""
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(48, 32, 48, 32)
        
        # Header
        title = QLabel("Review Your Configuration")
        title.setFont(QFont("", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Please review all changes before writing to the device")
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Summary stats
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet(f"""
            background-color: {COLORS['bg_light']};
            padding: 12px 24px;
            border-radius: 8px;
            color: {COLORS['accent_blue']};
            font-weight: bold;
        """)
        layout.addWidget(self.stats_label)
        
        # Tree view of configuration
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabels(["Configuration Item", "Details"])
        self.config_tree.setColumnWidth(0, 400)
        self.config_tree.setAlternatingRowColors(True)
        self.config_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_dark']};
                alternate-background-color: {COLORS['bg_medium']};
            }}
            QTreeWidget::item {{
                padding: 8px 4px;
            }}
        """)
        layout.addWidget(self.config_tree)
        
        # Warning note
        warning = QLabel(
            "⚠️  The current MASTERCELL configuration will be backed up before any changes are written."
        )
        warning.setStyleSheet(f"""
            color: {COLORS['accent_yellow']};
            background-color: {COLORS['bg_light']};
            padding: 12px;
            border-radius: 8px;
        """)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)
    
    def refresh(self):
        """Refresh the configuration display"""
        self.config_tree.clear()
        
        configured_inputs = 0
        total_cases = 0
        
        for input_config in self.config.inputs:
            # Count enabled cases
            on_cases = [c for c in input_config.on_cases if c.enabled]
            off_cases = [c for c in input_config.off_cases if c.enabled]
            
            if not on_cases and not off_cases:
                continue
            
            configured_inputs += 1
            total_cases += len(on_cases) + len(off_cases)
            
            input_def = get_input_definition(input_config.input_number)
            if not input_def:
                continue
            
            # Create input tree item
            display_name = input_config.custom_name if input_config.custom_name else input_def.name
            input_item = QTreeWidgetItem([
                f"{ICONS['input_configured']} Input {input_config.input_number}: {display_name}",
                f"{len(on_cases)} ON, {len(off_cases)} OFF cases"
            ])
            input_item.setFont(0, QFont("", 11, QFont.Weight.Bold))
            
            # Add ON cases
            for i, case in enumerate(on_cases):
                case_item = QTreeWidgetItem([
                    f"  {ICONS['arrow_right']} ON Case {i + 1}",
                    self._get_case_summary(case)
                ])
                case_item.setForeground(0, Qt.GlobalColor.green)
                
                # Add device outputs
                for device_id, outputs in case.device_outputs:
                    if device_id in DEVICES:
                        device = DEVICES[device_id]
                        output_text = self._get_outputs_text(outputs)
                        device_item = QTreeWidgetItem([
                            f"      {device.name}",
                            output_text
                        ])
                        case_item.addChild(device_item)
                
                input_item.addChild(case_item)
            
            # Add OFF cases
            for i, case in enumerate(off_cases):
                case_item = QTreeWidgetItem([
                    f"  {ICONS['arrow_right']} OFF Case {i + 1}",
                    self._get_case_summary(case)
                ])
                case_item.setForeground(0, Qt.GlobalColor.red)
                
                for device_id, outputs in case.device_outputs:
                    if device_id in DEVICES:
                        device = DEVICES[device_id]
                        output_text = self._get_outputs_text(outputs)
                        device_item = QTreeWidgetItem([
                            f"      {device.name}",
                            output_text
                        ])
                        case_item.addChild(device_item)
                
                input_item.addChild(case_item)
            
            self.config_tree.addTopLevelItem(input_item)
            input_item.setExpanded(True)
        
        # Update stats
        self.stats_label.setText(
            f"📊  {configured_inputs} inputs configured  •  {total_cases} total cases"
        )
        
        if configured_inputs == 0:
            empty_item = QTreeWidgetItem([
                "No inputs configured",
                "Go back and configure at least one input"
            ])
            empty_item.setForeground(0, Qt.GlobalColor.gray)
            self.config_tree.addTopLevelItem(empty_item)
    
    def _get_case_summary(self, case) -> str:
        """Get a text summary of case behavior"""
        parts = []
        
        if case.mode == 'toggle':
            parts.append("Toggle")
        elif case.mode == 'timed':
            parts.append("Timed")
        else:
            parts.append("Momentary")
        
        if case.pattern_preset and case.pattern_preset != 'none':
            parts.append(f"Pattern: {case.pattern_preset}")
        
        if case.set_ignition:
            parts.append("Sets Ignition")
        
        return " | ".join(parts) if parts else "Default behavior"
    
    def _get_outputs_text(self, outputs: dict) -> str:
        """Get a text description of output configurations"""
        parts = []
        
        for out_num, config in sorted(outputs.items()):
            if config.mode == OutputMode.TRACK:
                parts.append(f"Out{out_num}:Track")
            elif config.mode == OutputMode.SOFT_START:
                parts.append(f"Out{out_num}:SoftStart")
            elif config.mode == OutputMode.PWM:
                percent = int((config.pwm_duty / 15) * 100)
                parts.append(f"Out{out_num}:PWM@{percent}%")
        
        return ", ".join(parts) if parts else "No outputs"
    
    def set_configuration(self, config: FullConfiguration):
        """Update the configuration reference"""
        self.config = config
        self.refresh()

