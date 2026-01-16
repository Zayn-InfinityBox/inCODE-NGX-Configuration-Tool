#!/usr/bin/env python3
"""
Generate preset configuration files based on the EEPROM init C code.

This script creates front_engine.json and rear_engine.json presets that
match the MASTERCELL firmware's default configurations.

Data byte to output mapping for POWERCELL (per hardware documentation):
Byte 0: bit 7=Out1, bit 6=Out2, bit 5=Out3, bit 4=Out4, bit 3=Out5, bit 2=Out6, bit 1=Out7, bit 0=Out8

Examples from C code:
- 0x20 = 0b00100000 = bit 5 = Output 3
- 0x80 = 0b10000000 = bit 7 = Output 1
- 0x40 = 0b01000000 = bit 6 = Output 2
- 0x10 = 0b00010000 = bit 4 = Output 4
- 0x08 = 0b00001000 = bit 3 = Output 5
- 0x04 = 0b00000100 = bit 2 = Output 6
- 0x02 = 0b00000010 = bit 1 = Output 7
- 0x01 = 0b00000001 = bit 0 = Output 8
- 0xC0 = 0b11000000 = bits 7,6 = Outputs 1,2

Byte 1: bit 7=Out9 Track, bit 6=Out10 Track
- 0x80 = bit 7 = Output 9
- 0x40 = bit 6 = Output 10
"""

import json
from config_data import (
    FullConfiguration, InputConfig, CaseConfig, OutputConfig, OutputMode,
    SystemConfig, INPUTS
)

def byte_to_outputs(data_byte, byte_index=0):
    """
    Convert a data byte value to list of output numbers that are set.
    
    For byte 0: bit 7=Out1, bit 6=Out2, ..., bit 0=Out8
    For byte 1: bit 7=Out9, bit 6=Out10 (Track mode)
    """
    outputs = []
    if byte_index == 0:
        for bit in range(8):
            if data_byte & (1 << (7 - bit)):
                outputs.append(bit + 1)  # Output 1-8
    elif byte_index == 1:
        if data_byte & 0x80:  # bit 7
            outputs.append(9)
        if data_byte & 0x40:  # bit 6
            outputs.append(10)
    return outputs


def create_inmotion_case(device_id, output_num, mode=OutputMode.ON):
    """Create an inMOTION motor control case.
    
    Args:
        device_id: The inMOTION device ID (inmotion_1, inmotion_2, etc.)
        output_num: The output/channel number (1-8)
        mode: OutputMode.ON (for ON cases), OutputMode.OFF (for OFF cases), or OutputMode.ALL_MOTORS
    """
    case = CaseConfig()
    case.enabled = True
    case.mode = "track"
    case.pattern_preset = "none"
    case.pattern_on_time = 0
    case.pattern_off_time = 0
    
    # Create output config for the specified output
    output_configs = {
        output_num: OutputConfig(enabled=True, mode=mode, pwm_duty=0, inmotion_timer=0)
    }
    case.device_outputs = [(device_id, output_configs)]
    
    return case


def create_case(device_id, outputs, mode=OutputMode.TRACK, pattern_on=0, pattern_off=0, 
                must_be_on=None, ignition_mode="normal", 
                timer_on_value=0, timer_on_scale_10s=False,
                timer_delay_value=0, timer_delay_scale_10s=False,
                timer_execution_mode="fire_and_forget",
                can_be_overridden=False, require_ignition=False, require_security_off=False):
    """Create a CaseConfig with the specified outputs.
    
    Args:
        device_id: The device to send messages to
        outputs: List of output numbers to activate
        mode: OutputMode.TRACK or OutputMode.SOFT_START etc
        pattern_on: Pattern ON time (0-15, units of 250ms)
        pattern_off: Pattern OFF time (0-15, units of 250ms)
        must_be_on: List of input numbers that must be ON
        ignition_mode: "normal", "set_ignition", or "track_ignition"
        timer_on_value: Duration value (0-63)
        timer_on_scale_10s: True for 10s increments, False for 0.25s increments
        timer_delay_value: Delay value (0-63)
        timer_delay_scale_10s: True for 10s increments, False for 0.25s increments
        timer_execution_mode: "fire_and_forget" or "track_input"
        can_be_overridden: If True, allows turn signals to override (for brake lights)
        require_ignition: If True, case only activates when ignition is ON
        require_security_off: If True, case is blocked when security is ON
    """
    case = CaseConfig()
    case.enabled = True
    case.mode = "track" if mode == OutputMode.TRACK else "toggle"
    case.pattern_on_time = pattern_on
    case.pattern_off_time = pattern_off
    case.ignition_mode = ignition_mode
    case.set_ignition = (ignition_mode == "set_ignition")  # Legacy field
    case.can_be_overridden = can_be_overridden
    case.require_ignition_on = require_ignition
    case.require_security_off = require_security_off
    # Timer configuration
    case.timer_execution_mode = timer_execution_mode
    case.timer_on_value = timer_on_value
    case.timer_on_scale_10s = timer_on_scale_10s
    case.timer_delay_value = timer_delay_value
    case.timer_delay_scale_10s = timer_delay_scale_10s
    case.must_be_on = must_be_on or []
    
    output_configs = {}
    for out_num in outputs:
        output_configs[out_num] = OutputConfig(enabled=True, mode=mode, pwm_duty=0)
    
    case.device_outputs = [(device_id, output_configs)]
    return case


def create_multi_device_case(device_outputs_list, pattern_on=0, pattern_off=0,
                             must_be_on=None, ignition_mode="normal", 
                             timer_on_value=0, timer_on_scale_10s=False,
                             timer_delay_value=0, timer_delay_scale_10s=False,
                             timer_execution_mode="fire_and_forget",
                             can_be_overridden=False, require_ignition=False, require_security_off=False):
    """Create a CaseConfig with outputs on multiple devices."""
    case = CaseConfig()
    case.enabled = True
    case.mode = "track"
    case.pattern_on_time = pattern_on
    case.pattern_off_time = pattern_off
    case.ignition_mode = ignition_mode
    case.set_ignition = (ignition_mode == "set_ignition")  # Legacy field
    case.require_security_off = require_security_off
    # Timer configuration
    case.timer_execution_mode = timer_execution_mode
    case.timer_on_value = timer_on_value
    case.timer_on_scale_10s = timer_on_scale_10s
    case.timer_delay_value = timer_delay_value
    case.timer_delay_scale_10s = timer_delay_scale_10s
    case.can_be_overridden = can_be_overridden
    case.require_ignition_on = require_ignition
    case.must_be_on = must_be_on or []
    
    case.device_outputs = []
    for device_id, outputs in device_outputs_list:
        output_configs = {}
        for out_num in outputs:
            output_configs[out_num] = OutputConfig(enabled=True, mode=OutputMode.TRACK, pwm_duty=0)
        case.device_outputs.append((device_id, output_configs))
    
    return case


def generate_front_engine():
    """
    Generate Front Engine configuration based on eeprom_init_front_engine.c
    
    Mapping from C code analysis:
    - POWERCELL Front (0xFF01, SA 0x1E): powercell_front
    - POWERCELL Rear (0xFF02, SA 0x1E): powercell_rear
    - inMOTION 1 (0xFF03, SA 0x1A): inmotion_1
    - inMOTION 2 (0xFF04, SA 0x1A): inmotion_2
    - inMOTION 3 (0xFF05, SA 0x1A): inmotion_3
    - inMOTION 4 (0xFF06, SA 0x1A): inmotion_4
    """
    config = FullConfiguration()
    
    # System configuration (from C code bytes 0-22)
    config.system = SystemConfig()
    config.system.bitrate = 1  # 250kbps
    config.system.heartbeat_pgn_high = 0xFF
    config.system.heartbeat_pgn_low = 0x00
    config.system.heartbeat_sa = 0x80
    config.system.write_pgn_high = 0xFF
    config.system.write_pgn_low = 0x10
    config.system.write_sa = 0x80
    config.system.read_pgn_high = 0xFF
    config.system.read_pgn_low = 0x20
    config.system.read_sa = 0x80
    config.system.response_pgn_high = 0xFF
    config.system.response_pgn_low = 0x30
    config.system.response_sa = 0x80
    config.system.diagnostic_pgn_high = 0xFF
    config.system.diagnostic_pgn_low = 0x40
    config.system.diagnostic_sa = 0x80
    config.system.serial_number = 0x42
    
    # =========================================================================
    # FRONT ENGINE STANDARD SYSTEM ASSIGNMENTS - IPM1 Kit REV1
    # =========================================================================
    # Pattern timing 0x33 = on_time=3, off_time=3 (turn signal pattern)
    TURN_PATTERN_ON = 3
    TURN_PATTERN_OFF = 3
    
    # ===== IN01 - Ignition (* Blocked when security is ON) =====
    # Front POWERCELL Output 3, Track mode
    inp = config.inputs[0]
    inp.custom_name = "Ignition"
    inp.on_cases[0] = create_case("powercell_front", [3], ignition_mode="set_ignition", 
                                   require_security_off=True)
    
    # ===== IN02 - Starter (* Blocked when security ON, requires Neutral Safety) =====
    # Front POWERCELL Output 4, Track mode
    inp = config.inputs[1]
    inp.custom_name = "Starter"
    inp.on_cases[0] = create_case("powercell_front", [4], must_be_on=[16], 
                                   require_security_off=True)
    
    # ===== IN03 - Left Turn Signal (** Requires Ignition) =====
    # Front POWERCELL Output 1 (Turn Signal pattern), Rear POWERCELL Output 1 (Track)
    inp = config.inputs[2]
    inp.custom_name = "Left Turn"
    inp.on_cases[0] = create_case("powercell_front", [1], pattern_on=TURN_PATTERN_ON, 
                                   pattern_off=TURN_PATTERN_OFF, require_ignition=True)
    inp.on_cases[1] = create_case("powercell_rear", [1], require_ignition=True)
    
    # ===== IN04 - Right Turn Signal (** Requires Ignition) =====
    # Front POWERCELL Output 2 (Turn Signal pattern), Rear POWERCELL Output 2 (Track)
    inp = config.inputs[3]
    inp.custom_name = "Right Turn"
    inp.on_cases[0] = create_case("powercell_front", [2], pattern_on=TURN_PATTERN_ON, 
                                   pattern_off=TURN_PATTERN_OFF, require_ignition=True)
    inp.on_cases[1] = create_case("powercell_rear", [2], require_ignition=True)
    
    # ===== IN05 - Headlights =====
    # Front POWERCELL Output 5, Track: Soft Start
    inp = config.inputs[4]
    inp.custom_name = "Headlights"
    inp.on_cases[0] = create_case("powercell_front", [5], mode=OutputMode.SOFT_START)
    
    # ===== IN06 - Parking Lights =====
    # Front POWERCELL Output 6 (Track), Rear POWERCELL Output 6 (Track)
    inp = config.inputs[5]
    inp.custom_name = "Parking Lights"
    inp.on_cases[0] = create_case("powercell_front", [6])
    inp.on_cases[1] = create_case("powercell_rear", [6])
    
    # ===== IN07 - High Beams =====
    # Front POWERCELL Output 7, Track: Soft Start
    inp = config.inputs[6]
    inp.custom_name = "High Beams"
    inp.on_cases[0] = create_case("powercell_front", [7], mode=OutputMode.SOFT_START)
    
    # ===== IN08 - 4-Ways/Hazards =====
    # Front POWERCELL Outputs 1,2 (4-Ways pattern), Rear POWERCELL Outputs 1,2 (4-Ways pattern)
    inp = config.inputs[7]
    inp.custom_name = "4-Ways"
    inp.on_cases[0] = create_case("powercell_front", [1, 2], pattern_on=TURN_PATTERN_ON, 
                                   pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [1, 2], pattern_on=TURN_PATTERN_ON, 
                                   pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN09 - Horn =====
    # Front POWERCELL Output 9, Track mode
    inp = config.inputs[8]
    inp.custom_name = "Horn"
    inp.on_cases[0] = create_case("powercell_front", [9])
    
    # ===== IN10 - Cooling Fan (Ground Input) =====
    # Front POWERCELL Output 8, Track: Soft Start
    inp = config.inputs[9]
    inp.custom_name = "Cooling Fan"
    inp.on_cases[0] = create_case("powercell_front", [8], mode=OutputMode.SOFT_START)
    
    # ===== IN11 - Brake Light Single Filament (can be overridden by turns) =====
    # Rear POWERCELL Outputs 1,2, Track mode
    inp = config.inputs[10]
    inp.custom_name = "Brake 1-Fil"
    inp.on_cases[0] = create_case("powercell_rear", [1, 2], can_be_overridden=True)
    
    # ===== IN12 - Brake Light Multi-Filament =====
    # Rear POWERCELL Output 3, Track mode
    inp = config.inputs[11]
    inp.custom_name = "Brake Multi"
    inp.on_cases[0] = create_case("powercell_rear", [3])
    
    # ===== IN13 - Fuel Pump (* Blocked when security ON) =====
    # Rear POWERCELL Output 10, Track mode
    inp = config.inputs[12]
    inp.custom_name = "Fuel Pump"
    inp.on_cases[0] = create_case("powercell_rear", [10], require_security_off=True)
    
    # ===== IN14 - OPEN =====
    inp = config.inputs[13]
    inp.custom_name = "OPEN"
    
    # ===== IN15 - One-Button Start (requires Neutral Safety) =====
    # Front POWERCELL Outputs 3,4 (Ignition + Starter)
    inp = config.inputs[14]
    inp.custom_name = "One-Button Start"
    # Case 1: Ignition (Output 3)
    inp.on_cases[0] = create_case("powercell_front", [3], must_be_on=[16], 
                                   ignition_mode="set_ignition")
    # Case 2: Starter (Output 4) with delay and limited duration
    inp.on_cases[1] = create_case("powercell_front", [4], must_be_on=[16],
                                   timer_delay_value=12, timer_delay_scale_10s=False,
                                   timer_on_value=12, timer_on_scale_10s=False,
                                   timer_execution_mode="fire_and_forget")
    
    # ===== IN16 - Neutral Safety Input (Cannot Be Changed) =====
    inp = config.inputs[15]
    inp.custom_name = "Neutral Safety"
    
    # ===== IN17 - Backup Lights (** Requires Ignition) =====
    # Rear POWERCELL Output 5, Track mode
    inp = config.inputs[16]
    inp.custom_name = "Backup Lights"
    inp.on_cases[0] = create_case("powercell_rear", [5], require_ignition=True)
    
    # ===== IN18 - Interior Lights =====
    # Rear POWERCELL Output 4, Track mode
    inp = config.inputs[17]
    inp.custom_name = "Interior Lights"
    inp.on_cases[0] = create_case("powercell_rear", [4])
    
    # ===== IN19 - Open =====
    # Front POWERCELL Output 10, Track mode
    inp = config.inputs[18]
    inp.custom_name = "Open"
    inp.on_cases[0] = create_case("powercell_front", [10])
    
    # ===== IN20 - Open =====
    # Rear POWERCELL Output 7, Track mode
    inp = config.inputs[19]
    inp.custom_name = "Open"
    inp.on_cases[0] = create_case("powercell_rear", [7])
    
    # ===== IN21 - Open =====
    # Rear POWERCELL Output 8, Track mode
    inp = config.inputs[20]
    inp.custom_name = "Open"
    inp.on_cases[0] = create_case("powercell_rear", [8])
    
    # ===== IN22 - Open or Optional inRESERVE =====
    # Rear POWERCELL Output 9, Track mode
    inp = config.inputs[21]
    inp.custom_name = "Open/inRESERVE"
    inp.on_cases[0] = create_case("powercell_rear", [9])
    
    # ===== IN23 - Door Lock (All Windows UP) =====
    # All inMOTION devices, Output 3 (Data[2]) = 0xA2
    inp = config.inputs[22]
    inp.custom_name = "Door Lock"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 3, OutputMode.ALL_MOTORS)
    inp.on_cases[1] = create_inmotion_case("inmotion_2", 3, OutputMode.ALL_MOTORS)
    inp.on_cases[2] = create_inmotion_case("inmotion_3", 3, OutputMode.ALL_MOTORS)
    inp.on_cases[3] = create_inmotion_case("inmotion_4", 3, OutputMode.ALL_MOTORS)
    
    # ===== IN24 - Door Unlock (All Windows DOWN) =====
    # All inMOTION devices, Output 4 (Data[3]) = 0xA2
    inp = config.inputs[23]
    inp.custom_name = "Door Unlock"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 4, OutputMode.ALL_MOTORS)
    inp.on_cases[1] = create_inmotion_case("inmotion_2", 4, OutputMode.ALL_MOTORS)
    inp.on_cases[2] = create_inmotion_case("inmotion_3", 4, OutputMode.ALL_MOTORS)
    inp.on_cases[3] = create_inmotion_case("inmotion_4", 4, OutputMode.ALL_MOTORS)
    
    # ===== IN25 - Driver Front Window UP =====
    # inMOTION 1 (FF03), Output 1 (Data[0]) = 0x90
    inp = config.inputs[24]
    inp.custom_name = "Window DF Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_1", 1, OutputMode.OFF)
    
    # ===== IN26 - Passenger Front Window UP =====
    # inMOTION 1 (FF03), Output 2 (Data[1]) = 0x90
    inp = config.inputs[25]
    inp.custom_name = "Window PF Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_1", 2, OutputMode.OFF)
    
    # ===== IN27 - Driver Rear Window UP =====
    # inMOTION 2 (FF04), Output 1 (Data[0]) = 0x90
    inp = config.inputs[26]
    inp.custom_name = "Window DR Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_2", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_2", 1, OutputMode.OFF)
    
    # ===== IN28 - Passenger Rear Window UP =====
    # inMOTION 2 (FF04), Output 2 (Data[1]) = 0x90
    inp = config.inputs[27]
    inp.custom_name = "Window PR Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_2", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_2", 2, OutputMode.OFF)
    
    # ===== IN29 - Driver Front Window DOWN =====
    # inMOTION 3 (FF05), Output 1 (Data[0]) = 0x90
    inp = config.inputs[28]
    inp.custom_name = "Window DF Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_3", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_3", 1, OutputMode.OFF)
    
    # ===== IN30 - Passenger Front Window DOWN =====
    # inMOTION 3 (FF05), Output 2 (Data[1]) = 0x90
    inp = config.inputs[29]
    inp.custom_name = "Window PF Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_3", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_3", 2, OutputMode.OFF)
    
    # ===== IN31 - Driver Rear Window DOWN =====
    # inMOTION 4 (FF06), Output 1 (Data[0]) = 0x90
    inp = config.inputs[30]
    inp.custom_name = "Window DR Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_4", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_4", 1, OutputMode.OFF)
    
    # ===== IN32 - Passenger Rear Window DOWN =====
    # inMOTION 4 (FF06), Output 2 (Data[1]) = 0x90
    inp = config.inputs[31]
    inp.custom_name = "Window PR Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_4", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_4", 2, OutputMode.OFF)
    
    # ===== IN33-IN38 - Aux Inputs =====
    for i in range(32, 38):
        config.inputs[i].custom_name = f"AUX {i-31:02d}"
    
    # ===== HSIN01 (IN39) - Cooling Fan 12-Volt Input =====
    # Front POWERCELL Output 8, Track: Soft Start
    inp = config.inputs[38]
    inp.custom_name = "Cooling Fan HS"
    inp.on_cases[0] = create_case("powercell_front", [8], mode=OutputMode.SOFT_START)
    
    # ===== HSIN02 (IN40) - Fuel Pump 12-Volt Input =====
    # Rear POWERCELL Output 10, Track mode
    inp = config.inputs[39]
    inp.custom_name = "Fuel Pump HS"
    inp.on_cases[0] = create_case("powercell_rear", [10])
    
    # ===== HSIN03-HSIN06 (IN41-IN44) - Aux High Side =====
    config.inputs[40].custom_name = "AUX HS03"
    config.inputs[41].custom_name = "AUX HS04"
    config.inputs[42].custom_name = "AUX HS05"
    config.inputs[43].custom_name = "AUX HS06"
    
    return config


def config_to_dict(obj):
    """Convert configuration object to dictionary for JSON serialization."""
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for k, v in obj.__dict__.items():
            result[k] = config_to_dict(v)
        return result
    elif isinstance(obj, list):
        return [config_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): config_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, tuple):
        return list(config_to_dict(item) for item in obj)
    elif hasattr(obj, 'value'):  # Enum
        return obj.value
    else:
        return obj


def save_config(config, filename, name, description):
    """Save configuration to JSON file."""
    data = config_to_dict(config)
    data['name'] = name
    data['description'] = description
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved {filename}")


def generate_rear_engine():
    """
    Generate Rear Engine configuration based on IPM1 Kit REV1 assignments.
    
    Key differences from Front Engine:
    - IN01 (Ignition): POWERCELL Rear Output 4 (instead of Front Output 3)
    - IN02 (Starter): POWERCELL Rear Output 5 (instead of Front Output 4)
    - IN15 (One-Button Start): POWERCELL Rear Outputs 4,5
    - Engine accessories on rear POWERCELL, lighting on front POWERCELL
    """
    config = FullConfiguration()
    
    # System configuration
    config.system = SystemConfig()
    config.system.bitrate = 1
    config.system.heartbeat_pgn_high = 0xFF
    config.system.heartbeat_pgn_low = 0x00
    config.system.heartbeat_sa = 0x80
    config.system.write_pgn_high = 0xFF
    config.system.write_pgn_low = 0x10
    config.system.write_sa = 0x80
    config.system.read_pgn_high = 0xFF
    config.system.read_pgn_low = 0x20
    config.system.read_sa = 0x80
    config.system.response_pgn_high = 0xFF
    config.system.response_pgn_low = 0x30
    config.system.response_sa = 0x80
    config.system.diagnostic_pgn_high = 0xFF
    config.system.diagnostic_pgn_low = 0x40
    config.system.diagnostic_sa = 0x80
    config.system.serial_number = 0x42
    
    # =========================================================================
    # REAR ENGINE STANDARD SYSTEM ASSIGNMENTS - IPM1 Kit REV1
    # =========================================================================
    TURN_PATTERN_ON = 3
    TURN_PATTERN_OFF = 3
    
    # ===== IN01 - Ignition (* Blocked when security is ON) =====
    # Rear POWERCELL Output 4, Track mode
    inp = config.inputs[0]
    inp.custom_name = "Ignition"
    inp.on_cases[0] = create_case("powercell_rear", [4], ignition_mode="set_ignition",
                                   require_security_off=True)
    
    # ===== IN02 - Starter (* Blocked when security ON, requires Neutral Safety) =====
    # Rear POWERCELL Output 5, Track mode
    inp = config.inputs[1]
    inp.custom_name = "Starter"
    inp.on_cases[0] = create_case("powercell_rear", [5], must_be_on=[16],
                                   require_security_off=True)
    
    # ===== IN03 - Left Turn Signal (** Requires Ignition) =====
    # Front POWERCELL Output 1 (Turn Signal pattern), Rear POWERCELL Output 1 (Track)
    inp = config.inputs[2]
    inp.custom_name = "Left Turn"
    inp.on_cases[0] = create_case("powercell_front", [1], pattern_on=TURN_PATTERN_ON,
                                   pattern_off=TURN_PATTERN_OFF, require_ignition=True)
    inp.on_cases[1] = create_case("powercell_rear", [1], require_ignition=True)
    
    # ===== IN04 - Right Turn Signal (** Requires Ignition) =====
    # Front POWERCELL Output 2 (Turn Signal pattern), Rear POWERCELL Output 2 (Track)
    inp = config.inputs[3]
    inp.custom_name = "Right Turn"
    inp.on_cases[0] = create_case("powercell_front", [2], pattern_on=TURN_PATTERN_ON,
                                   pattern_off=TURN_PATTERN_OFF, require_ignition=True)
    inp.on_cases[1] = create_case("powercell_rear", [2], require_ignition=True)
    
    # ===== IN05 - Headlights =====
    # Front POWERCELL Output 5, Track: Soft Start
    inp = config.inputs[4]
    inp.custom_name = "Headlights"
    inp.on_cases[0] = create_case("powercell_front", [5], mode=OutputMode.SOFT_START)
    
    # ===== IN06 - Parking Lights =====
    # Front POWERCELL Output 6 (Track), Rear POWERCELL Output 6 (Track)
    inp = config.inputs[5]
    inp.custom_name = "Parking Lights"
    inp.on_cases[0] = create_case("powercell_front", [6])
    inp.on_cases[1] = create_case("powercell_rear", [6])
    
    # ===== IN07 - High Beams =====
    # Front POWERCELL Output 7, Track: Soft Start
    inp = config.inputs[6]
    inp.custom_name = "High Beams"
    inp.on_cases[0] = create_case("powercell_front", [7], mode=OutputMode.SOFT_START)
    
    # ===== IN08 - 4-Ways/Hazards =====
    # Front POWERCELL Outputs 1,2, Rear POWERCELL Outputs 1,2 (4-Ways pattern)
    inp = config.inputs[7]
    inp.custom_name = "4-Ways"
    inp.on_cases[0] = create_case("powercell_front", [1, 2], pattern_on=TURN_PATTERN_ON,
                                   pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [1, 2], pattern_on=TURN_PATTERN_ON,
                                   pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN09 - Horn =====
    # Front POWERCELL Output 9, Track mode
    inp = config.inputs[8]
    inp.custom_name = "Horn"
    inp.on_cases[0] = create_case("powercell_front", [9])
    
    # ===== IN10 - Cooling Fan (Ground Input) =====
    # Front POWERCELL Output 8, Track: Soft Start
    inp = config.inputs[9]
    inp.custom_name = "Cooling Fan"
    inp.on_cases[0] = create_case("powercell_front", [8], mode=OutputMode.SOFT_START)
    
    # ===== IN11 - Brake Light Single Filament (can be overridden by turns) =====
    # Rear POWERCELL Outputs 1,2, Track mode
    inp = config.inputs[10]
    inp.custom_name = "Brake 1-Fil"
    inp.on_cases[0] = create_case("powercell_rear", [1, 2], can_be_overridden=True)
    
    # ===== IN12 - Brake Light Multi-Filament =====
    # Rear POWERCELL Output 3, Track mode
    inp = config.inputs[11]
    inp.custom_name = "Brake Multi"
    inp.on_cases[0] = create_case("powercell_rear", [3])
    
    # ===== IN13 - Fuel Pump (* Blocked when security ON) =====
    # Rear POWERCELL Output 10, Track mode
    inp = config.inputs[12]
    inp.custom_name = "Fuel Pump"
    inp.on_cases[0] = create_case("powercell_rear", [10], require_security_off=True)
    
    # ===== IN14 - OPEN =====
    inp = config.inputs[13]
    inp.custom_name = "OPEN"
    
    # ===== IN15 - One-Button Start (requires Neutral Safety) =====
    # Rear POWERCELL Outputs 4,5 (Ignition + Starter)
    inp = config.inputs[14]
    inp.custom_name = "One-Button Start"
    # Case 1: Ignition (Output 4)
    inp.on_cases[0] = create_case("powercell_rear", [4], must_be_on=[16],
                                   ignition_mode="set_ignition")
    # Case 2: Starter (Output 5) with delay and limited duration
    inp.on_cases[1] = create_case("powercell_rear", [5], must_be_on=[16],
                                   timer_delay_value=12, timer_delay_scale_10s=False,
                                   timer_on_value=12, timer_on_scale_10s=False,
                                   timer_execution_mode="fire_and_forget")
    
    # ===== IN16 - Neutral Safety Input (Cannot Be Changed) =====
    inp = config.inputs[15]
    inp.custom_name = "Neutral Safety"
    
    # ===== IN17 - Backup Lights (** Requires Ignition) =====
    # Rear POWERCELL Output 7, Track mode
    inp = config.inputs[16]
    inp.custom_name = "Backup Lights"
    inp.on_cases[0] = create_case("powercell_rear", [7], require_ignition=True)
    
    # ===== IN18 - Interior Lights =====
    # Front POWERCELL Output 4, Track mode
    inp = config.inputs[17]
    inp.custom_name = "Interior Lights"
    inp.on_cases[0] = create_case("powercell_front", [4])
    
    # ===== IN19 - Open =====
    # Front POWERCELL Output 10, Track mode
    inp = config.inputs[18]
    inp.custom_name = "Open"
    inp.on_cases[0] = create_case("powercell_front", [10])
    
    # ===== IN20 - Open =====
    # Front POWERCELL Output 3, Track mode
    inp = config.inputs[19]
    inp.custom_name = "Open"
    inp.on_cases[0] = create_case("powercell_front", [3])
    
    # ===== IN21 - Open =====
    # Rear POWERCELL Output 8, Track mode
    inp = config.inputs[20]
    inp.custom_name = "Open"
    inp.on_cases[0] = create_case("powercell_rear", [8])
    
    # ===== IN22 - Open or Optional inRESERVE =====
    # Rear POWERCELL Output 9, Track mode
    inp = config.inputs[21]
    inp.custom_name = "Open/inRESERVE"
    inp.on_cases[0] = create_case("powercell_rear", [9])
    
    # ===== IN23 - Door Lock (All Windows UP) =====
    # All inMOTION devices, Output 3 (Data[2]) = 0xA2
    inp = config.inputs[22]
    inp.custom_name = "Door Lock"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 3, OutputMode.ALL_MOTORS)
    inp.on_cases[1] = create_inmotion_case("inmotion_2", 3, OutputMode.ALL_MOTORS)
    inp.on_cases[2] = create_inmotion_case("inmotion_3", 3, OutputMode.ALL_MOTORS)
    inp.on_cases[3] = create_inmotion_case("inmotion_4", 3, OutputMode.ALL_MOTORS)
    
    # ===== IN24 - Door Unlock (All Windows DOWN) =====
    # All inMOTION devices, Output 4 (Data[3]) = 0xA2
    inp = config.inputs[23]
    inp.custom_name = "Door Unlock"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 4, OutputMode.ALL_MOTORS)
    inp.on_cases[1] = create_inmotion_case("inmotion_2", 4, OutputMode.ALL_MOTORS)
    inp.on_cases[2] = create_inmotion_case("inmotion_3", 4, OutputMode.ALL_MOTORS)
    inp.on_cases[3] = create_inmotion_case("inmotion_4", 4, OutputMode.ALL_MOTORS)
    
    # ===== IN25 - Driver Front Window UP =====
    # inMOTION 1 (FF03), Output 1 (Data[0]) = 0x90
    inp = config.inputs[24]
    inp.custom_name = "Window DF Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_1", 1, OutputMode.OFF)
    
    # ===== IN26 - Passenger Front Window UP =====
    # inMOTION 1 (FF03), Output 2 (Data[1]) = 0x90
    inp = config.inputs[25]
    inp.custom_name = "Window PF Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_1", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_1", 2, OutputMode.OFF)
    
    # ===== IN27 - Driver Rear Window UP =====
    # inMOTION 2 (FF04), Output 1 (Data[0]) = 0x90
    inp = config.inputs[26]
    inp.custom_name = "Window DR Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_2", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_2", 1, OutputMode.OFF)
    
    # ===== IN28 - Passenger Rear Window UP =====
    # inMOTION 2 (FF04), Output 2 (Data[1]) = 0x90
    inp = config.inputs[27]
    inp.custom_name = "Window PR Up"
    inp.on_cases[0] = create_inmotion_case("inmotion_2", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_2", 2, OutputMode.OFF)
    
    # ===== IN29 - Driver Front Window DOWN =====
    # inMOTION 3 (FF05), Output 1 (Data[0]) = 0x90
    inp = config.inputs[28]
    inp.custom_name = "Window DF Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_3", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_3", 1, OutputMode.OFF)
    
    # ===== IN30 - Passenger Front Window DOWN =====
    # inMOTION 3 (FF05), Output 2 (Data[1]) = 0x90
    inp = config.inputs[29]
    inp.custom_name = "Window PF Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_3", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_3", 2, OutputMode.OFF)
    
    # ===== IN31 - Driver Rear Window DOWN =====
    # inMOTION 4 (FF06), Output 1 (Data[0]) = 0x90
    inp = config.inputs[30]
    inp.custom_name = "Window DR Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_4", 1, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_4", 1, OutputMode.OFF)
    
    # ===== IN32 - Passenger Rear Window DOWN =====
    # inMOTION 4 (FF06), Output 2 (Data[1]) = 0x90
    inp = config.inputs[31]
    inp.custom_name = "Window PR Down"
    inp.on_cases[0] = create_inmotion_case("inmotion_4", 2, OutputMode.ON)
    inp.off_cases[0] = create_inmotion_case("inmotion_4", 2, OutputMode.OFF)
    
    # ===== IN33-IN38 - Aux Inputs =====
    for i in range(32, 38):
        config.inputs[i].custom_name = f"AUX {i-31:02d}"
    
    # ===== HSIN01 (IN39) - Cooling Fan 12-Volt Input =====
    # Front POWERCELL Output 8, Track: Soft Start
    inp = config.inputs[38]
    inp.custom_name = "Cooling Fan HS"
    inp.on_cases[0] = create_case("powercell_front", [8], mode=OutputMode.SOFT_START)
    
    # ===== HSIN02 (IN40) - Fuel Pump 12-Volt Input =====
    # Rear POWERCELL Output 10, Track mode
    inp = config.inputs[39]
    inp.custom_name = "Fuel Pump HS"
    inp.on_cases[0] = create_case("powercell_rear", [10])
    
    # ===== HSIN03-HSIN06 (IN41-IN44) - Aux High Side =====
    config.inputs[40].custom_name = "AUX HS03"
    config.inputs[41].custom_name = "AUX HS04"
    config.inputs[42].custom_name = "AUX HS05"
    config.inputs[43].custom_name = "AUX HS06"
    
    return config


if __name__ == "__main__":
    # Generate Front Engine preset
    front_config = generate_front_engine()
    save_config(
        front_config,
        "resources/presets/front_engine.json",
        "Front Engine Configuration",
        "Standard configuration for front-engine vehicles. "
        "Engine accessories (ignition relay, starter, cooling fan) controlled via POWERCELL Front. "
        "Lighting and rear accessories via POWERCELL Rear. Window controls via inMOTION units."
    )
    
    # Generate Rear Engine preset
    rear_config = generate_rear_engine()
    save_config(
        rear_config,
        "resources/presets/rear_engine.json",
        "Rear Engine Configuration",
        "Configuration for rear-engine vehicles (mid-engine, rear-mounted). "
        "Engine accessories (ignition relay, starter, fuel pump) controlled via POWERCELL Rear. "
        "Front lighting via POWERCELL Front. Window controls via inMOTION units."
    )
    
    print("\nPreset files generated successfully!")
    print("\nOutput mappings (POWERCELL byte 0):")
    print("  0x80 (bit 7) = Output 1")
    print("  0x40 (bit 6) = Output 2")
    print("  0x20 (bit 5) = Output 3")
    print("  0x10 (bit 4) = Output 4")
    print("  0x08 (bit 3) = Output 5")
    print("  0x04 (bit 2) = Output 6")
    print("  0x02 (bit 1) = Output 7")
    print("  0x01 (bit 0) = Output 8")
