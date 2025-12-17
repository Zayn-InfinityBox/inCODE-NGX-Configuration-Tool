"""
confirmation_page.py - Review and confirm configuration changes
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from styles import COLORS
from config_data import (
    FullConfiguration, DEVICES, get_input_definition,
    OutputMode
)


class ConfirmationPage(QWidget):
    """Review page showing all configured inputs and cases"""
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 24, 32, 24)
        
        # Header
        title = QLabel("Review Your Configuration")
        title.setFont(QFont("", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(title)
        
        # Summary stats
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet(f"""
            background-color: rgba(96, 176, 225, 0.2);
            padding: 10px 24px;
            border-radius: 12px;
            color: {COLORS['accent_primary']};
            font-weight: 600;
            font-size: 14px;
        """)
        layout.addWidget(self.stats_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll, 1)
        
        # Warning note
        warning = QLabel(
            "⚠  The current MASTERCELL configuration will be backed up before any changes are written."
        )
        warning.setStyleSheet(f"""
            color: {COLORS['warning']};
            background-color: rgba(245, 158, 11, 0.15);
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
        """)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)
    
    def refresh(self):
        """Refresh the configuration display"""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        configured_inputs = 0
        total_cases = 0
        total_outputs = 0
        
        for input_config in self.config.inputs:
            on_cases = [c for c in input_config.on_cases if c.enabled]
            off_cases = [c for c in input_config.off_cases if c.enabled]
            
            if not on_cases and not off_cases:
                continue
            
            configured_inputs += 1
            total_cases += len(on_cases) + len(off_cases)
            
            input_def = get_input_definition(input_config.input_number)
            if not input_def:
                continue
            
            # Create input section
            display_name = input_config.custom_name if input_config.custom_name else input_def.name
            
            # Input header card
            input_card = QFrame()
            input_card.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(60, 60, 60, 0.95);
                    border-radius: 10px;
                }}
            """)
            input_layout = QVBoxLayout(input_card)
            input_layout.setSpacing(10)
            input_layout.setContentsMargins(16, 14, 16, 14)
            
            # Input title
            input_title = QLabel(f"IN{input_config.input_number:02d}: {display_name}")
            input_title.setFont(QFont("", 14, QFont.Weight.Bold))
            input_title.setStyleSheet(f"color: {COLORS['accent_primary']}; background: transparent;")
            input_layout.addWidget(input_title)
            
            # ON cases
            for i, case in enumerate(on_cases):
                case_frame = self._create_case_frame(f"ON Case {i+1}", case, "#22C55E")
                input_layout.addWidget(case_frame)
                for _, outputs in case.device_outputs:
                    total_outputs += len(outputs)
            
            # OFF cases  
            for i, case in enumerate(off_cases):
                case_frame = self._create_case_frame(f"OFF Case {i+1}", case, "#EF4444")
                input_layout.addWidget(case_frame)
                for _, outputs in case.device_outputs:
                    total_outputs += len(outputs)
            
            self.content_layout.addWidget(input_card)
        
        # Update stats
        self.stats_label.setText(
            f"{configured_inputs} inputs  •  {total_cases} cases  •  {total_outputs} outputs"
        )
        
        if configured_inputs == 0:
            empty_label = QLabel("No inputs configured yet\n\nGo back to the Configure page and enable at least one case")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #888; font-size: 15px; padding: 60px 20px;")
            self.content_layout.addWidget(empty_label)
        
        self.content_layout.addStretch()
    
    def _create_case_frame(self, case_name: str, case, color: str) -> QFrame:
        """Create a frame showing all case details"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 45, 0.95);
                border-left: 3px solid {color};
                border-radius: 6px;
                margin-left: 8px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 10, 12, 10)
        
        # Case header
        header = QHBoxLayout()
        
        name_label = QLabel(case_name)
        name_label.setFont(QFont("", 12, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {color}; background: transparent;")
        header.addWidget(name_label)
        
        # Mode
        mode_text = {"track": "Track", "toggle": "Toggle", "timed": "Timed"}.get(case.mode, "Track")
        mode_label = QLabel(f"[{mode_text}]")
        mode_label.setStyleSheet("color: #AAA; background: transparent;")
        header.addWidget(mode_label)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Details section
        details = []
        
        # Device & Outputs
        if case.device_outputs:
            for device_id, outputs in case.device_outputs:
                if device_id in DEVICES:
                    device = DEVICES[device_id]
                    if outputs:
                        output_parts = []
                        for out_num, out_config in sorted(outputs.items()):
                            mode_str = "Track"
                            if out_config.mode == OutputMode.SOFT_START:
                                mode_str = "Soft-Start"
                            elif out_config.mode == OutputMode.PWM:
                                pct = int((out_config.pwm_duty / 15) * 100)
                                mode_str = f"PWM {pct}%"
                            output_parts.append(f"Out{out_num}={mode_str}")
                        details.append(f"<span style='color: {COLORS['accent_blue']};'>Device:</span> {device.name} → {', '.join(output_parts)}")
                    else:
                        details.append(f"<span style='color: {COLORS['accent_blue']};'>Device:</span> {device.name} <span style='color: {COLORS['warning']};'>(no outputs selected)</span>")
        else:
            details.append(f"<span style='color: {COLORS['warning']};'>⚠ No device selected</span>")
        
        # Pattern
        if case.pattern_preset and case.pattern_preset != 'none':
            pattern_name = case.pattern_preset.replace('_', ' ').title()
            details.append(f"<span style='color: {COLORS['accent_purple']};'>Pattern:</span> {pattern_name}")
        
        # Must be ON
        if case.must_be_on:
            names = []
            for n in case.must_be_on:
                inp = get_input_definition(n)
                names.append(f"IN{n:02d}" + (f" ({inp.name})" if inp else ""))
            details.append(f"<span style='color: #22C55E;'>Must be ON:</span> {', '.join(names)}")
        
        # Must be OFF
        if case.must_be_off:
            names = []
            for n in case.must_be_off:
                inp = get_input_definition(n)
                names.append(f"IN{n:02d}" + (f" ({inp.name})" if inp else ""))
            details.append(f"<span style='color: #F87171;'>Must be OFF:</span> {', '.join(names)}")
        
        # Add all details
        for detail in details:
            label = QLabel(detail)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet("color: white; background: transparent; padding-left: 8px;")
            label.setWordWrap(True)
            layout.addWidget(label)
        
        return frame
    
    def set_configuration(self, config: FullConfiguration):
        """Update the configuration reference"""
        self.config = config
        self.refresh()
