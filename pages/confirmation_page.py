"""
confirmation_page.py - Review and confirm configuration changes
Shows only cases that have been modified from the original template.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from copy import deepcopy

from styles import COLORS
from config_data import (
    FullConfiguration, CaseConfig, DEVICES, get_input_definition,
    OutputMode
)


class ConfirmationPage(QWidget):
    """Review page showing only modified inputs and cases"""
    
    def __init__(self, config: FullConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.original_config = None  # Store the original template config
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 32, 40, 32)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(55, 55, 55, 0.6);
                border-radius: 16px;
                padding: 24px;
            }}
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(12)
        
        title = QLabel("Review Your Changes")
        title.setFont(QFont("", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Only modified cases are shown below")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; background: transparent;")
        header_layout.addWidget(subtitle)
        
        # Summary stats
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet(f"""
            background-color: rgba(107, 197, 248, 0.15);
            padding: 12px 28px;
            border-radius: 10px;
            color: {COLORS['accent_primary']};
            font-weight: 600;
            font-size: 14px;
        """)
        header_layout.addWidget(self.stats_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(header_frame)
        
        # Scroll area for changes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { 
                background: transparent; 
                border: none; 
            }
            QScrollBar:vertical {
                background: rgba(40, 40, 40, 0.5);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(120, 120, 120, 0.8);
                border-radius: 4px;
                min-height: 30px;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setSpacing(16)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll, 1)
        
        # Warning note
        warning_frame = QFrame()
        warning_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(251, 191, 36, 0.12);
                border: 1px solid rgba(251, 191, 36, 0.3);
                border-radius: 10px;
            }}
        """)
        warning_layout = QHBoxLayout(warning_frame)
        warning_layout.setContentsMargins(16, 12, 16, 12)
        
        warning_icon = QLabel("⚠")
        warning_icon.setStyleSheet(f"font-size: 18px; color: {COLORS['warning']}; background: transparent;")
        warning_layout.addWidget(warning_icon)
        
        warning_text = QLabel(
            "The current MASTERCELL configuration will be backed up before any changes are written."
        )
        warning_text.setStyleSheet(f"""
            color: {COLORS['warning']};
            font-size: 13px;
            background: transparent;
        """)
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text, 1)
        
        layout.addWidget(warning_frame)
    
    def set_original_configuration(self, config: FullConfiguration):
        """Store the original template configuration for comparison"""
        self.original_config = deepcopy(config)
    
    def _normalize_value(self, value, default):
        """Normalize a value - treat None/empty as the default"""
        if value is None or value == "":
            return default
        return value
    
    def _case_has_changed(self, current_case: CaseConfig, original_case: CaseConfig) -> bool:
        """Check if a case has been modified from the original"""
        # Compare enabled state
        if current_case.enabled != original_case.enabled:
            return True
        
        # If both disabled, no change (don't compare other fields for disabled cases)
        if not current_case.enabled and not original_case.enabled:
            return False
        
        # Compare mode (normalize defaults)
        curr_mode = self._normalize_value(current_case.mode, "track")
        orig_mode = self._normalize_value(original_case.mode, "track")
        if curr_mode != orig_mode:
            return True
        
        # Compare pattern (normalize defaults)
        curr_pattern = self._normalize_value(current_case.pattern_preset, "none")
        orig_pattern = self._normalize_value(original_case.pattern_preset, "none")
        if curr_pattern != orig_pattern:
            return True
        
        # Compare timer settings (normalize defaults)
        curr_exec = self._normalize_value(current_case.timer_execution_mode, "fire_and_forget")
        orig_exec = self._normalize_value(original_case.timer_execution_mode, "fire_and_forget")
        if curr_exec != orig_exec:
            return True
        
        if ((current_case.timer_delay_value or 0) != (original_case.timer_delay_value or 0) or
            (current_case.timer_delay_scale_10s or False) != (original_case.timer_delay_scale_10s or False) or
            (current_case.timer_on_value or 0) != (original_case.timer_on_value or 0) or
            (current_case.timer_on_scale_10s or False) != (original_case.timer_on_scale_10s or False)):
            return True
        
        # Compare ignition mode (normalize defaults)
        curr_ign = self._normalize_value(current_case.ignition_mode, "normal")
        orig_ign = self._normalize_value(original_case.ignition_mode, "normal")
        if curr_ign != orig_ign:
            return True
        
        # Compare flags (normalize to False if None)
        if ((current_case.can_be_overridden or False) != (original_case.can_be_overridden or False) or
            (current_case.require_ignition_on or False) != (original_case.require_ignition_on or False) or
            (current_case.require_ignition_off or False) != (original_case.require_ignition_off or False) or
            (current_case.require_security_off or False) != (original_case.require_security_off or False)):
            return True
        
        # Compare must_be_on/off (normalize empty to set())
        if set(current_case.must_be_on or []) != set(original_case.must_be_on or []):
            return True
        if set(current_case.must_be_off or []) != set(original_case.must_be_off or []):
            return True
        
        # Compare device outputs - only compare outputs that have enabled configs
        current_outputs = current_case.device_outputs or []
        original_outputs = original_case.device_outputs or []
        
        # Create dicts and filter to only enabled outputs
        def get_enabled_outputs(outputs_list):
            result = {}
            for dev_id, outputs in outputs_list:
                enabled_outs = {k: v for k, v in (outputs or {}).items() if v and v.enabled}
                if enabled_outs:
                    result[dev_id] = enabled_outs
            return result
        
        current_dict = get_enabled_outputs(current_outputs)
        original_dict = get_enabled_outputs(original_outputs)
        
        if set(current_dict.keys()) != set(original_dict.keys()):
            return True
        
        for dev_id in current_dict:
            curr_outs = current_dict[dev_id]
            orig_outs = original_dict.get(dev_id, {})
            
            if set(curr_outs.keys()) != set(orig_outs.keys()):
                return True
            
            for out_num in curr_outs:
                curr_cfg = curr_outs[out_num]
                orig_cfg = orig_outs.get(out_num)
                
                if not orig_cfg:
                    return True
                
                if (curr_cfg.mode != orig_cfg.mode or
                    (curr_cfg.pwm_duty or 0) != (orig_cfg.pwm_duty or 0)):
                    return True
        
        return False
    
    def refresh(self):
        """Refresh the configuration display - show only changed cases"""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        modified_inputs = 0
        modified_cases = 0
        total_outputs = 0
        
        for idx, input_config in enumerate(self.config.inputs):
            original_input = None
            if self.original_config:
                original_input = self.original_config.inputs[idx]
            
            # Find changed cases
            changed_on_cases = []
            changed_off_cases = []
            
            for i, case in enumerate(input_config.on_cases):
                original_case = original_input.on_cases[i] if original_input and i < len(original_input.on_cases) else CaseConfig()
                if self._case_has_changed(case, original_case):
                    changed_on_cases.append((i, case))
            
            for i, case in enumerate(input_config.off_cases):
                original_case = original_input.off_cases[i] if original_input and i < len(original_input.off_cases) else CaseConfig()
                if self._case_has_changed(case, original_case):
                    changed_off_cases.append((i, case))
            
            if not changed_on_cases and not changed_off_cases:
                continue
            
            modified_inputs += 1
            modified_cases += len(changed_on_cases) + len(changed_off_cases)
            
            input_def = get_input_definition(input_config.input_number)
            if not input_def:
                continue
            
            # Create input section
            display_name = input_config.custom_name if input_config.custom_name else input_def.name
            
            # Input card
            input_card = QFrame()
            input_card.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(55, 55, 55, 0.7);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                }}
            """)
            input_layout = QVBoxLayout(input_card)
            input_layout.setSpacing(12)
            input_layout.setContentsMargins(20, 16, 20, 16)
            
            # Input header
            input_header = QHBoxLayout()
            
            input_title = QLabel(f"IN{input_config.input_number:02d}")
            input_title.setFont(QFont("", 16, QFont.Weight.Bold))
            input_title.setStyleSheet(f"color: {COLORS['accent_primary']}; background: transparent;")
            input_header.addWidget(input_title)
            
            input_name = QLabel(display_name)
            input_name.setFont(QFont("", 14))
            input_name.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")
            input_header.addWidget(input_name)
            
            input_header.addStretch()
            
            change_count = len(changed_on_cases) + len(changed_off_cases)
            change_badge = QLabel(f"{change_count} change{'s' if change_count != 1 else ''}")
            change_badge.setStyleSheet(f"""
                background-color: rgba(107, 197, 248, 0.2);
                color: {COLORS['accent_primary']};
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            """)
            input_header.addWidget(change_badge)
            
            input_layout.addLayout(input_header)
            
            # Separator
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
            input_layout.addWidget(sep)
            
            # ON cases
            for i, case in changed_on_cases:
                case_frame = self._create_case_frame(f"ON Case {i+1}", case, COLORS['accent_green'])
                input_layout.addWidget(case_frame)
                for _, outputs in (case.device_outputs or []):
                    total_outputs += len(outputs)
            
            # OFF cases  
            for i, case in changed_off_cases:
                case_frame = self._create_case_frame(f"OFF Case {i+1}", case, COLORS['accent_red'])
                input_layout.addWidget(case_frame)
                for _, outputs in (case.device_outputs or []):
                    total_outputs += len(outputs)
            
            self.content_layout.addWidget(input_card)
        
        # Update stats
        if modified_inputs > 0:
            self.stats_label.setText(
                f"✓  {modified_inputs} input{'s' if modified_inputs != 1 else ''}  •  "
                f"{modified_cases} case{'s' if modified_cases != 1 else ''}  •  "
                f"{total_outputs} output{'s' if total_outputs != 1 else ''}"
            )
            self.stats_label.setStyleSheet(f"""
                background-color: rgba(52, 211, 153, 0.15);
                padding: 12px 28px;
                border-radius: 10px;
                color: {COLORS['accent_green']};
                font-weight: 600;
                font-size: 14px;
            """)
        else:
            self.stats_label.setText("No changes detected")
            self.stats_label.setStyleSheet(f"""
                background-color: rgba(107, 197, 248, 0.15);
                padding: 12px 28px;
                border-radius: 10px;
                color: {COLORS['text_muted']};
                font-weight: 600;
                font-size: 14px;
            """)
        
        if modified_inputs == 0:
            empty_frame = QFrame()
            empty_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(55, 55, 55, 0.5);
                    border: 1px dashed rgba(255, 255, 255, 0.15);
                    border-radius: 12px;
                }}
            """)
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setContentsMargins(40, 60, 40, 60)
            
            empty_icon = QLabel("📋")
            empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_icon.setStyleSheet("font-size: 48px; background: transparent;")
            empty_layout.addWidget(empty_icon)
            
            empty_label = QLabel("No Changes Detected")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setFont(QFont("", 16, QFont.Weight.Bold))
            empty_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")
            empty_layout.addWidget(empty_label)
            
            empty_sub = QLabel("The configuration matches the loaded template.\nMake changes on the Configure page to see them here.")
            empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_sub.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; background: transparent;")
            empty_layout.addWidget(empty_sub)
            
            self.content_layout.addWidget(empty_frame)
        
        self.content_layout.addStretch()
    
    def _create_case_frame(self, case_name: str, case: CaseConfig, color: str) -> QFrame:
        """Create a frame showing case details with improved styling"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(40, 40, 45, 0.8);
                border-left: 3px solid {color};
                border-radius: 8px;
                margin-left: 4px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Case header
        header = QHBoxLayout()
        
        name_label = QLabel(case_name)
        name_label.setFont(QFont("", 13, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {color}; background: transparent;")
        header.addWidget(name_label)
        
        # Status badge
        if case.enabled:
            status = QLabel("ENABLED")
            status.setStyleSheet(f"""
                background-color: rgba(52, 211, 153, 0.2);
                color: {COLORS['accent_green']};
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            """)
        else:
            status = QLabel("DISABLED")
            status.setStyleSheet(f"""
                background-color: rgba(248, 113, 113, 0.2);
                color: {COLORS['accent_red']};
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            """)
        header.addWidget(status)
        
        header.addStretch()
        
        # Mode badge
        mode_text = {"track": "Track", "toggle": "Toggle", "timed": "Timed"}.get(case.mode, "Track")
        mode_label = QLabel(mode_text)
        mode_label.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.1);
            color: {COLORS['text_secondary']};
            padding: 2px 10px;
            border-radius: 4px;
            font-size: 11px;
        """)
        header.addWidget(mode_label)
        
        layout.addLayout(header)
        
        # Only show details if case is enabled
        if case.enabled:
            # Details section
            details_frame = QFrame()
            details_frame.setStyleSheet("background: transparent;")
            details_layout = QVBoxLayout(details_frame)
            details_layout.setSpacing(4)
            details_layout.setContentsMargins(0, 4, 0, 0)
            
            # Extract colors for use in HTML strings
            c_blue = COLORS['accent_blue']
            c_secondary = COLORS['text_secondary']
            c_primary = COLORS['text_primary']
            c_purple = COLORS['accent_purple']
            c_orange = COLORS['accent_orange']
            c_green = COLORS['accent_green']
            c_red = COLORS['accent_red']
            
            # Device & Outputs
            if case.device_outputs:
                for device_id, outputs in case.device_outputs:
                    if device_id in DEVICES and outputs:
                        device = DEVICES[device_id]
                        output_parts = []
                        for out_num, out_config in sorted(outputs.items()):
                            mode_str = "Track"
                            if out_config.mode == OutputMode.SOFT_START:
                                mode_str = "Soft-Start"
                            elif out_config.mode == OutputMode.PWM:
                                pct = int((out_config.pwm_duty / 15) * 100)
                                mode_str = f"PWM {pct}%"
                            output_parts.append(f"<b>Out{out_num}</b> ({mode_str})")
                        
                        outputs_str = ', '.join(output_parts)
                        detail_label = QLabel(
                            f"<span style='color: {c_blue};'>📦</span> "
                            f"<span style='color: {c_secondary};'>{device.name}:</span> "
                            f"{outputs_str}"
                        )
                        detail_label.setTextFormat(Qt.TextFormat.RichText)
                        detail_label.setStyleSheet(f"color: {c_primary}; background: transparent; font-size: 12px;")
                        detail_label.setWordWrap(True)
                        details_layout.addWidget(detail_label)
            
            # Pattern
            if case.pattern_preset and case.pattern_preset != 'none':
                pattern_name = case.pattern_preset.replace('_', ' ').title()
                pattern_label = QLabel(
                    f"<span style='color: {c_purple};'>✨</span> "
                    f"<span style='color: {c_secondary};'>Pattern:</span> {pattern_name}"
                )
                pattern_label.setTextFormat(Qt.TextFormat.RichText)
                pattern_label.setStyleSheet(f"color: {c_primary}; background: transparent; font-size: 12px;")
                details_layout.addWidget(pattern_label)
            
            # Ignition mode
            if case.ignition_mode and case.ignition_mode != "normal":
                ign_text = "Sets Ignition" if case.ignition_mode == "set_ignition" else "Tracks Ignition"
                ign_label = QLabel(
                    f"<span style='color: {c_orange};'>⚡</span> "
                    f"<span style='color: {c_secondary};'>Ignition:</span> {ign_text}"
                )
                ign_label.setTextFormat(Qt.TextFormat.RichText)
                ign_label.setStyleSheet(f"color: {c_primary}; background: transparent; font-size: 12px;")
                details_layout.addWidget(ign_label)
            
            # Must be ON
            if case.must_be_on:
                names = [f"IN{n:02d}" for n in case.must_be_on]
                names_str = ', '.join(names)
                on_label = QLabel(
                    f"<span style='color: {c_green};'>✓</span> "
                    f"<span style='color: {c_secondary};'>Requires ON:</span> {names_str}"
                )
                on_label.setTextFormat(Qt.TextFormat.RichText)
                on_label.setStyleSheet(f"color: {c_primary}; background: transparent; font-size: 12px;")
                details_layout.addWidget(on_label)
            
            # Must be OFF
            if case.must_be_off:
                names = [f"IN{n:02d}" for n in case.must_be_off]
                names_str = ', '.join(names)
                off_label = QLabel(
                    f"<span style='color: {c_red};'>✕</span> "
                    f"<span style='color: {c_secondary};'>Requires OFF:</span> {names_str}"
                )
                off_label.setTextFormat(Qt.TextFormat.RichText)
                off_label.setStyleSheet(f"color: {c_primary}; background: transparent; font-size: 12px;")
                details_layout.addWidget(off_label)
            
            layout.addWidget(details_frame)
        
        return frame
    
    def set_configuration(self, config: FullConfiguration):
        """Update the configuration reference"""
        self.config = config
        self.refresh()
