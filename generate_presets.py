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


def create_case(device_id, outputs, mode=OutputMode.TRACK, pattern_on=0, pattern_off=0, 
                must_be_on=None, set_ignition=False, timer_delay=0):
    """Create a CaseConfig with the specified outputs."""
    case = CaseConfig()
    case.enabled = True
    case.mode = "track" if mode == OutputMode.TRACK else "toggle"
    case.pattern_on_time = pattern_on
    case.pattern_off_time = pattern_off
    case.set_ignition = set_ignition
    case.timer_delay = timer_delay
    case.must_be_on = must_be_on or []
    
    output_configs = {}
    for out_num in outputs:
        output_configs[out_num] = OutputConfig(enabled=True, mode=mode, pwm_duty=0)
    
    case.device_outputs = [(device_id, output_configs)]
    return case


def create_multi_device_case(device_outputs_list, pattern_on=0, pattern_off=0,
                             must_be_on=None, set_ignition=False):
    """Create a CaseConfig with outputs on multiple devices."""
    case = CaseConfig()
    case.enabled = True
    case.mode = "track"
    case.pattern_on_time = pattern_on
    case.pattern_off_time = pattern_off
    case.set_ignition = set_ignition
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
    
    # Pattern timing 0x33 = on_time=3, off_time=3 (turn signal pattern)
    TURN_PATTERN_ON = 3
    TURN_PATTERN_OFF = 3
    
    # ===== IN01 - Ignition =====
    # C: data[0] = 0x20 on PGN 0xFF01 -> Output 3 Track
    # Also sets ignition flag
    inp = config.inputs[0]
    inp.custom_name = "Ignition"
    inp.on_cases[0] = create_case("powercell_front", [3], set_ignition=True)
    
    # ===== IN02 - Starter (requires IN16 Neutral Safety) =====
    # C: data[0] = 0x10 on PGN 0xFF01, must_be_on[1] = 0x80 (IN16)
    # 0x10 = bit 4 = Output 4
    inp = config.inputs[1]
    inp.custom_name = "Starter"
    inp.on_cases[0] = create_case("powercell_front", [4], must_be_on=[16])
    
    # ===== IN03 - Left Turn Signal =====
    # C: data[0] = 0x80 on PGN 0xFF01 + 0xFF02, pattern 0x33, requires ignition
    # 0x80 = bit 7 = Output 1
    inp = config.inputs[2]
    inp.custom_name = "Left Turn"
    inp.on_cases[0] = create_case("powercell_front", [1], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [1], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN04 - Right Turn Signal =====
    # C: data[0] = 0x40 on PGN 0xFF01 + 0xFF02, pattern 0x33
    # 0x40 = bit 6 = Output 2
    inp = config.inputs[3]
    inp.custom_name = "Right Turn"
    inp.on_cases[0] = create_case("powercell_front", [2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN05 - Headlights =====
    # C: data[0] = 0x08 on PGN 0xFF01 -> Output 5
    inp = config.inputs[4]
    inp.custom_name = "Head Lights"
    inp.on_cases[0] = create_case("powercell_front", [5])
    
    # ===== IN06 - Parking Lights =====
    # C: data[0] = 0x04 on PGN 0xFF01 + 0xFF02 -> Output 6
    inp = config.inputs[5]
    inp.custom_name = "Parking Lights"
    inp.on_cases[0] = create_case("powercell_front", [6])
    inp.on_cases[1] = create_case("powercell_rear", [6])
    
    # ===== IN07 - High Beams =====
    # C: data[0] = 0x02 on PGN 0xFF01 -> Output 7
    inp = config.inputs[6]
    inp.custom_name = "High Beams"
    inp.on_cases[0] = create_case("powercell_front", [7])
    
    # ===== IN08 - Hazards/4-Way =====
    # C: data[0] = 0xC0 on PGN 0xFF01 + 0xFF02, pattern 0x33 -> Outputs 1,2
    inp = config.inputs[7]
    inp.custom_name = "4-Ways"
    inp.on_cases[0] = create_case("powercell_front", [1, 2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [1, 2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN09 - Horn =====
    # C: data[1] = 0x80 on PGN 0xFF01 -> Output 9
    inp = config.inputs[8]
    inp.custom_name = "Horn"
    inp.on_cases[0] = create_case("powercell_front", [9])
    
    # ===== IN10 - Cooling Fan =====
    # C: data[1] = 0x40 on PGN 0xFF01 -> Output 10
    inp = config.inputs[9]
    inp.custom_name = "Cooling Fan"
    inp.on_cases[0] = create_case("powercell_front", [10])
    
    # ===== IN11 - Brake Light (1-Filament, can be overridden by turns) =====
    # C: data[0] = 0xC0 on PGN 0xFF02, config_byte=0x04 -> Outputs 1,2
    inp = config.inputs[10]
    inp.custom_name = "1-Filament Brake"
    inp.on_cases[0] = create_case("powercell_rear", [1, 2])
    
    # ===== IN12 - Brake Light (Multi-Filament) =====
    # C: data[0] = 0x20 on PGN 0xFF02 -> Output 3
    inp = config.inputs[11]
    inp.custom_name = "Multi-Filament Brake"
    inp.on_cases[0] = create_case("powercell_rear", [3])
    
    # ===== IN13 - Fuel Pump =====
    # C: data[1] = 0x40 on PGN 0xFF02 -> Output 10
    inp = config.inputs[12]
    inp.custom_name = "Fuel Pump"
    inp.on_cases[0] = create_case("powercell_rear", [10])
    
    # ===== IN14 - Alternating Headlight =====
    # C: INVALID (no cases configured)
    inp = config.inputs[13]
    inp.custom_name = "Alt Headlight"
    
    # ===== IN15 - One-Button Start (requires IN16 Neutral Safety) =====
    # C: Complex one-button start with multiple cases
    # Case 1: data[0]=0x20, data[7]=0x80, config_byte=0x11 (ignition + starter trigger)
    # Case 2: data[0]=0x02, pattern_timing=0x1E (30x100ms delay for starter)
    inp = config.inputs[14]
    inp.custom_name = "One-Button Start"
    # First case: Enable ignition outputs (Output 3) and trigger flag
    inp.on_cases[0] = create_case("powercell_front", [3], must_be_on=[16], set_ignition=True)
    # Second case: Starter (Output 7) with delay
    inp.on_cases[1] = create_case("powercell_front", [7], must_be_on=[16], timer_delay=30)
    
    # ===== IN16 - Neutral Safety Input =====
    # C: INVALID (this is a condition input, not an output trigger)
    inp = config.inputs[15]
    inp.custom_name = "Neutral Safety"
    
    # ===== IN17 - Backup Lights =====
    # C: data[0] = 0x08 on PGN 0xFF02 -> Output 5
    inp = config.inputs[16]
    inp.custom_name = "Backup Lights"
    inp.on_cases[0] = create_case("powercell_rear", [5])
    
    # ===== IN18 - Interior Lights =====
    # C: data[0] = 0x10 on PGN 0xFF02 -> Output 4
    inp = config.inputs[17]
    inp.custom_name = "Interior Lights"
    inp.on_cases[0] = create_case("powercell_rear", [4])
    
    # ===== IN19-IN22 - Aux Inputs (configured but open) =====
    # C: data[0] = 0x01 on PGN 0xFF01 -> Output 8
    inp = config.inputs[18]
    inp.custom_name = "AUX 01"
    inp.on_cases[0] = create_case("powercell_front", [8])
    
    # C: data[0] = 0x02 on PGN 0xFF02 -> Output 7
    inp = config.inputs[19]
    inp.custom_name = "AUX 02"
    inp.on_cases[0] = create_case("powercell_rear", [7])
    
    # C: data[0] = 0x01 on PGN 0xFF02 -> Output 8
    inp = config.inputs[20]
    inp.custom_name = "AUX 03"
    inp.on_cases[0] = create_case("powercell_rear", [8])
    
    # C: data[1] = 0x80 on PGN 0xFF02 -> Output 9
    inp = config.inputs[21]
    inp.custom_name = "AUX 04"
    inp.on_cases[0] = create_case("powercell_rear", [9])
    
    # ===== IN23 - HSIN01 Cooling Fan (High Side) =====
    # C: data[1] = 0x40 on PGN 0xFF01 -> Output 10
    inp = config.inputs[22]
    inp.custom_name = "Cooling Fan HS"
    inp.on_cases[0] = create_case("powercell_front", [10])
    
    # ===== IN24 - HSIN02 Fuel Pump (High Side) =====
    # C: data[1] = 0x40 on PGN 0xFF02 -> Output 10
    inp = config.inputs[23]
    inp.custom_name = "Fuel Pump HS"
    inp.on_cases[0] = create_case("powercell_rear", [10])
    
    # ===== IN25-IN32 - Window Controls (inMOTION) =====
    # IN25 - Window Driver Front UP
    # C: data[0] = 0x90 on PGN 0xFF03 (inmotion_1)
    # 0x90 = modifier + ON + timer (Relay 1A UP direction)
    inp = config.inputs[24]
    inp.custom_name = "Window DF Up"
    inp.on_cases[0] = create_case("inmotion_1", [1])  # Relay 1A
    
    # IN26 - Window Passenger Front UP
    # C: data[1] = 0x90 on PGN 0xFF03 (inmotion_1)
    inp = config.inputs[25]
    inp.custom_name = "Window PF Up"
    inp.on_cases[0] = create_case("inmotion_1", [2])  # Relay 1B
    
    # IN27 - Window Driver Rear UP
    # C: data[0] = 0x90 on PGN 0xFF04 (inmotion_2)
    inp = config.inputs[26]
    inp.custom_name = "Window DR Up"
    inp.on_cases[0] = create_case("inmotion_2", [1])  # Relay 1A
    
    # IN28 - Window Passenger Rear UP
    # C: data[1] = 0x90 on PGN 0xFF04 (inmotion_2)
    inp = config.inputs[27]
    inp.custom_name = "Window PR Up"
    inp.on_cases[0] = create_case("inmotion_2", [2])  # Relay 1B
    
    # IN29 - Window Driver Front DOWN
    # C: data[0] = 0x90 on PGN 0xFF05 (inmotion_3)
    inp = config.inputs[28]
    inp.custom_name = "Window DF Down"
    inp.on_cases[0] = create_case("inmotion_3", [1])  # Relay 1A
    
    # IN30 - Window Passenger Front DOWN
    # C: data[1] = 0x90 on PGN 0xFF05 (inmotion_3)
    inp = config.inputs[29]
    inp.custom_name = "Window PF Down"
    inp.on_cases[0] = create_case("inmotion_3", [2])  # Relay 1B
    
    # IN31 - Window Driver Rear DOWN
    # C: data[0] = 0x90 on PGN 0xFF06 (inmotion_4)
    inp = config.inputs[30]
    inp.custom_name = "Window DR Down"
    inp.on_cases[0] = create_case("inmotion_4", [1])  # Relay 1A
    
    # IN32 - Window Passenger Rear DOWN
    # C: data[1] = 0x90 on PGN 0xFF06 (inmotion_4)
    inp = config.inputs[31]
    inp.custom_name = "Window PR Down"
    inp.on_cases[0] = create_case("inmotion_4", [2])  # Relay 1B
    
    # ===== IN33-IN38 - Aux Inputs (not configured) =====
    for i in range(32, 38):
        config.inputs[i].custom_name = f"AUX B{i-31:02d}"
    
    # ===== IN39-IN42 - High Side Aux (not configured) =====
    for i in range(38, 42):
        config.inputs[i].custom_name = f"AUX HS{i-35:02d}"
    
    # ===== IN43-IN44 - Tach/VSS =====
    config.inputs[42].custom_name = "Tachometer"
    config.inputs[43].custom_name = "Speed Sensor"
    
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
    Generate Rear Engine configuration based on eeprom_init_rear_engine.c
    
    Key differences from Front Engine:
    - IN01 (Ignition): POWERCELL Rear Output 4 (instead of Front Output 3)
    - IN02 (Starter): POWERCELL Rear Output 5 (instead of Front Output 4)
    - Engine accessories on rear POWERCELL, lighting on front POWERCELL
    """
    config = FullConfiguration()
    
    # System configuration (same as front engine)
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
    
    TURN_PATTERN_ON = 3
    TURN_PATTERN_OFF = 3
    
    # ===== IN01 - Ignition (REAR ENGINE: on POWERCELL Rear) =====
    # C: data[0] = 0x10 on PGN 0xFF02 -> Output 4 Track
    inp = config.inputs[0]
    inp.custom_name = "Ignition"
    inp.on_cases[0] = create_case("powercell_rear", [4], set_ignition=True)
    
    # ===== IN02 - Starter (REAR ENGINE: on POWERCELL Rear, requires IN16) =====
    # C: data[0] = 0x08 on PGN 0xFF02, must_be_on[1] = 0x80 (IN16)
    # 0x08 = bit 3 = Output 5
    inp = config.inputs[1]
    inp.custom_name = "Starter"
    inp.on_cases[0] = create_case("powercell_rear", [5], must_be_on=[16])
    
    # ===== IN03 - Left Turn Signal (same as front) =====
    inp = config.inputs[2]
    inp.custom_name = "Left Turn"
    inp.on_cases[0] = create_case("powercell_front", [1], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [1], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN04 - Right Turn Signal (same as front) =====
    inp = config.inputs[3]
    inp.custom_name = "Right Turn"
    inp.on_cases[0] = create_case("powercell_front", [2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN05 - Headlights (same as front) =====
    inp = config.inputs[4]
    inp.custom_name = "Head Lights"
    inp.on_cases[0] = create_case("powercell_front", [5])
    
    # ===== IN06 - Parking Lights (same as front) =====
    inp = config.inputs[5]
    inp.custom_name = "Parking Lights"
    inp.on_cases[0] = create_case("powercell_front", [6])
    inp.on_cases[1] = create_case("powercell_rear", [6])
    
    # ===== IN07 - High Beams (same as front) =====
    inp = config.inputs[6]
    inp.custom_name = "High Beams"
    inp.on_cases[0] = create_case("powercell_front", [7])
    
    # ===== IN08 - Hazards (same as front) =====
    inp = config.inputs[7]
    inp.custom_name = "4-Ways"
    inp.on_cases[0] = create_case("powercell_front", [1, 2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    inp.on_cases[1] = create_case("powercell_rear", [1, 2], pattern_on=TURN_PATTERN_ON, pattern_off=TURN_PATTERN_OFF)
    
    # ===== IN09 - Horn (same as front) =====
    inp = config.inputs[8]
    inp.custom_name = "Horn"
    inp.on_cases[0] = create_case("powercell_front", [9])
    
    # ===== IN10 - Cooling Fan (same as front - on Front POWERCELL for rad) =====
    inp = config.inputs[9]
    inp.custom_name = "Cooling Fan"
    inp.on_cases[0] = create_case("powercell_front", [10])
    
    # ===== IN11 - Brake Light 1-Filament (same as front) =====
    inp = config.inputs[10]
    inp.custom_name = "1-Filament Brake"
    inp.on_cases[0] = create_case("powercell_rear", [1, 2])
    
    # ===== IN12 - Brake Light Multi (same as front) =====
    inp = config.inputs[11]
    inp.custom_name = "Multi-Filament Brake"
    inp.on_cases[0] = create_case("powercell_rear", [3])
    
    # ===== IN13 - Fuel Pump (REAR ENGINE: on POWERCELL Rear) =====
    inp = config.inputs[12]
    inp.custom_name = "Fuel Pump"
    inp.on_cases[0] = create_case("powercell_rear", [10])
    
    # ===== IN14 - Alternating Headlight (not configured) =====
    inp = config.inputs[13]
    inp.custom_name = "Alt Headlight"
    
    # ===== IN15 - One-Button Start (on Front POWERCELL, requires IN16) =====
    inp = config.inputs[14]
    inp.custom_name = "One-Button Start"
    inp.on_cases[0] = create_case("powercell_front", [3], must_be_on=[16], set_ignition=True)
    inp.on_cases[1] = create_case("powercell_front", [7], must_be_on=[16], timer_delay=30)
    
    # ===== IN16 - Neutral Safety (condition input) =====
    inp = config.inputs[15]
    inp.custom_name = "Neutral Safety"
    
    # ===== IN17 - Backup Lights (same as front) =====
    inp = config.inputs[16]
    inp.custom_name = "Backup Lights"
    inp.on_cases[0] = create_case("powercell_rear", [5])
    
    # ===== IN18 - Interior Lights (same as front) =====
    inp = config.inputs[17]
    inp.custom_name = "Interior Lights"
    inp.on_cases[0] = create_case("powercell_rear", [4])
    
    # ===== IN19-IN22 - Aux Inputs =====
    inp = config.inputs[18]
    inp.custom_name = "AUX 01"
    inp.on_cases[0] = create_case("powercell_front", [8])
    
    inp = config.inputs[19]
    inp.custom_name = "AUX 02"
    inp.on_cases[0] = create_case("powercell_rear", [7])
    
    inp = config.inputs[20]
    inp.custom_name = "AUX 03"
    inp.on_cases[0] = create_case("powercell_rear", [8])
    
    inp = config.inputs[21]
    inp.custom_name = "AUX 04"
    inp.on_cases[0] = create_case("powercell_rear", [9])
    
    # ===== IN23-24 - High Side Inputs =====
    inp = config.inputs[22]
    inp.custom_name = "Cooling Fan HS"
    inp.on_cases[0] = create_case("powercell_front", [10])
    
    inp = config.inputs[23]
    inp.custom_name = "Fuel Pump HS"
    inp.on_cases[0] = create_case("powercell_rear", [10])
    
    # ===== IN25-IN32 - Window Controls (same as front) =====
    inp = config.inputs[24]
    inp.custom_name = "Window DF Up"
    inp.on_cases[0] = create_case("inmotion_1", [1])
    
    inp = config.inputs[25]
    inp.custom_name = "Window PF Up"
    inp.on_cases[0] = create_case("inmotion_1", [2])
    
    inp = config.inputs[26]
    inp.custom_name = "Window DR Up"
    inp.on_cases[0] = create_case("inmotion_2", [1])
    
    inp = config.inputs[27]
    inp.custom_name = "Window PR Up"
    inp.on_cases[0] = create_case("inmotion_2", [2])
    
    inp = config.inputs[28]
    inp.custom_name = "Window DF Down"
    inp.on_cases[0] = create_case("inmotion_3", [1])
    
    inp = config.inputs[29]
    inp.custom_name = "Window PF Down"
    inp.on_cases[0] = create_case("inmotion_3", [2])
    
    inp = config.inputs[30]
    inp.custom_name = "Window DR Down"
    inp.on_cases[0] = create_case("inmotion_4", [1])
    
    inp = config.inputs[31]
    inp.custom_name = "Window PR Down"
    inp.on_cases[0] = create_case("inmotion_4", [2])
    
    # ===== IN33-IN38 - Aux Inputs B =====
    for i in range(32, 38):
        config.inputs[i].custom_name = f"AUX B{i-31:02d}"
    
    # ===== IN39-IN42 - High Side Aux =====
    for i in range(38, 42):
        config.inputs[i].custom_name = f"AUX HS{i-35:02d}"
    
    # ===== IN43-IN44 - Tach/VSS =====
    config.inputs[42].custom_name = "Tachometer"
    config.inputs[43].custom_name = "Speed Sensor"
    
    return config


if __name__ == "__main__":
    # Generate Front Engine preset
    front_config = generate_front_engine()
    save_config(
        front_config,
        "presets/front_engine.json",
        "Front Engine Configuration",
        "Standard configuration for front-engine vehicles. "
        "Engine accessories (ignition relay, starter, cooling fan) controlled via POWERCELL Front. "
        "Lighting and rear accessories via POWERCELL Rear. Window controls via inMOTION units."
    )
    
    # Generate Rear Engine preset
    rear_config = generate_rear_engine()
    save_config(
        rear_config,
        "presets/rear_engine.json",
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
