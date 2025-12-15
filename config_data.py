"""
config_data.py - Data models and constants for inCode NGX Configuration Tool

Defines all EEPROM addresses, PGNs, input definitions, and configuration structures.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import IntEnum
import json

# =============================================================================
# J1939 / CAN Constants
# =============================================================================

class BitrateCode(IntEnum):
    KBPS_250 = 0x01
    KBPS_500 = 0x02
    MBPS_1 = 0x03

class LossOfComTimer(IntEnum):
    SEC_10 = 10
    SEC_30 = 30
    SEC_60 = 60

class RebroadcastMode(IntEnum):
    EDGE_TRIGGERED = 0x01
    PERIODIC = 0x02

class OutputMode(IntEnum):
    OFF = 0
    TRACK = 1
    SOFT_START = 2
    PWM = 3

# Source Address ranges by device type
SA_MASTERCELL = 0x0E
SA_POWERCELL_BASE = 0x10  # 0x10-0x1F
SA_INMOTION_BASE = 0x20   # 0x20-0x2F
SA_INLINK_BASE = 0x30     # 0x30-0x3F

# Common PGNs
PGN_HEARTBEAT = 0xFF00
PGN_EEPROM_WRITE = 0xFF10
PGN_EEPROM_READ = 0xFF20
PGN_EEPROM_RESPONSE = 0xFF30
PGN_DIAGNOSTIC = 0xFF40

# EEPROM Protocol
EEPROM_GUARD_BYTE = 0x77
EEPROM_STATUS_SUCCESS = 0x01
EEPROM_STATUS_BAD_GUARD = 0xE1
EEPROM_STATUS_INVALID_ADDR = 0xE2
EEPROM_STATUS_TX_BUSY = 0xE4
EEPROM_STATUS_VERIFY_FAIL = 0xE5

# =============================================================================
# EEPROM Address Map (System Configuration)
# =============================================================================

EEPROM_ADDR_BITRATE = 0x00
EEPROM_ADDR_HB_PGN_HIGH = 0x01
EEPROM_ADDR_HB_PGN_LOW = 0x02
EEPROM_ADDR_HB_SA = 0x03
EEPROM_ADDR_FW_MAJOR = 0x04
EEPROM_ADDR_FW_MINOR = 0x05
EEPROM_ADDR_REBROADCAST = 0x06
EEPROM_ADDR_INIT_STAMP = 0x07
EEPROM_ADDR_RESERVED_8 = 0x08
EEPROM_ADDR_RESERVED_9 = 0x09
EEPROM_ADDR_WR_PGN_HIGH = 0x0A
EEPROM_ADDR_WR_PGN_LOW = 0x0B
EEPROM_ADDR_WR_SA = 0x0C
EEPROM_ADDR_RD_PGN_HIGH = 0x0D
EEPROM_ADDR_RD_PGN_LOW = 0x0E
EEPROM_ADDR_RD_SA = 0x0F
EEPROM_ADDR_RSP_PGN_HIGH = 0x10
EEPROM_ADDR_RSP_PGN_LOW = 0x11
EEPROM_ADDR_RSP_SA = 0x12
EEPROM_ADDR_DIAG_PGN_HIGH = 0x13
EEPROM_ADDR_DIAG_PGN_LOW = 0x14
EEPROM_ADDR_DIAG_SA = 0x15
EEPROM_ADDR_SERIAL = 0x16

# Input configuration starts at address 23
EEPROM_ADDR_INPUT_START = 23
EEPROM_BYTES_PER_CASE = 11
EEPROM_ON_CASES_PER_INPUT = 8
EEPROM_OFF_CASES_PER_INPUT = 2
EEPROM_BYTES_PER_INPUT = EEPROM_BYTES_PER_CASE * (EEPROM_ON_CASES_PER_INPUT + EEPROM_OFF_CASES_PER_INPUT)  # 110

# =============================================================================
# Device Definitions
# =============================================================================

@dataclass
class DeviceDefinition:
    """Definition of a controllable device on the network"""
    id: str
    name: str
    pgn_high: int
    pgn_low: int
    device_type: str  # 'powercell' or 'inmotion'
    outputs: List[str]  # List of output names

# All controllable devices
DEVICES = {
    "powercell_front": DeviceDefinition(
        id="powercell_front",
        name="POWERCELL Front",
        pgn_high=0xFF, pgn_low=0x01,
        device_type="powercell",
        outputs=["Output 1", "Output 2", "Output 3", "Output 4", "Output 5",
                 "Output 6", "Output 7", "Output 8", "Output 9", "Output 10"]
    ),
    "powercell_rear": DeviceDefinition(
        id="powercell_rear",
        name="POWERCELL Rear",
        pgn_high=0xFF, pgn_low=0x02,
        device_type="powercell",
        outputs=["Output 1", "Output 2", "Output 3", "Output 4", "Output 5",
                 "Output 6", "Output 7", "Output 8", "Output 9", "Output 10"]
    ),
    "powercell_3": DeviceDefinition(
        id="powercell_3",
        name="POWERCELL 3",
        pgn_high=0xFF, pgn_low=0x07,
        device_type="powercell",
        outputs=["Output 1", "Output 2", "Output 3", "Output 4", "Output 5",
                 "Output 6", "Output 7", "Output 8", "Output 9", "Output 10"]
    ),
    "powercell_4": DeviceDefinition(
        id="powercell_4",
        name="POWERCELL 4",
        pgn_high=0xFF, pgn_low=0x08,
        device_type="powercell",
        outputs=["Output 1", "Output 2", "Output 3", "Output 4", "Output 5",
                 "Output 6", "Output 7", "Output 8", "Output 9", "Output 10"]
    ),
    "inmotion_1": DeviceDefinition(
        id="inmotion_1",
        name="inMOTION 1",
        pgn_high=0xFF, pgn_low=0x03,
        device_type="inmotion",
        outputs=["Relay 1A", "Relay 1B", "Relay 2A", "Relay 2B",
                 "Output 1", "Output 2", "Output 3", "Output 4"]
    ),
    "inmotion_2": DeviceDefinition(
        id="inmotion_2",
        name="inMOTION 2",
        pgn_high=0xFF, pgn_low=0x04,
        device_type="inmotion",
        outputs=["Relay 1A", "Relay 1B", "Relay 2A", "Relay 2B",
                 "Output 1", "Output 2", "Output 3", "Output 4"]
    ),
    "inmotion_3": DeviceDefinition(
        id="inmotion_3",
        name="inMOTION 3",
        pgn_high=0xFF, pgn_low=0x05,
        device_type="inmotion",
        outputs=["Relay 1A", "Relay 1B", "Relay 2A", "Relay 2B",
                 "Output 1", "Output 2", "Output 3", "Output 4"]
    ),
    "inmotion_4": DeviceDefinition(
        id="inmotion_4",
        name="inMOTION 4",
        pgn_high=0xFF, pgn_low=0x06,
        device_type="inmotion",
        outputs=["Relay 1A", "Relay 1B", "Relay 2A", "Relay 2B",
                 "Output 1", "Output 2", "Output 3", "Output 4"]
    ),
}

# =============================================================================
# POWERCELL Message Encoding
# =============================================================================
#
# POWERCELL NGX 8-byte message format:
#
# Byte 0: bits 0-7 = Track mode outputs 1-8
# Byte 1: bits 0-1 = Track mode outputs 9-10
#         bits 2-7 = Soft-start outputs 1-6
# Byte 2: bits 0-3 = Soft-start outputs 7-10
#         bits 4-7 = PWM enable outputs 1-4
# Byte 3: bits 0-3 = PWM enable outputs 5-8
# Byte 4: upper nibble = Output 1 PWM duty (0-15)
#         lower nibble = Output 2 PWM duty (0-15)
# Byte 5: upper nibble = Output 3 PWM duty
#         lower nibble = Output 4 PWM duty
# Byte 6: upper nibble = Output 5 PWM duty
#         lower nibble = Output 6 PWM duty
# Byte 7: upper nibble = Output 7 PWM duty
#         lower nibble = Output 8 PWM duty
#
# Priority: Track > Soft-Start > PWM

@dataclass
class OutputConfig:
    """Configuration for a single output"""
    enabled: bool = False
    mode: OutputMode = OutputMode.OFF
    pwm_duty: int = 0  # 0-15 (4-bit)

@dataclass
class DeviceOutputConfig:
    """Configuration for all outputs on a device"""
    device_id: str = ""
    outputs: Dict[int, OutputConfig] = field(default_factory=dict)


def encode_powercell_message(output_configs: Dict[int, OutputConfig]) -> List[int]:
    """
    Encode POWERCELL output configurations into 8-byte CAN message.
    
    Args:
        output_configs: Dict mapping output number (1-10) to OutputConfig
    
    Returns:
        List of 8 bytes
    """
    data = [0, 0, 0, 0, 0, 0, 0, 0]
    
    for out_num, config in output_configs.items():
        if not config.enabled or config.mode == OutputMode.OFF:
            continue
        
        if out_num < 1 or out_num > 10:
            continue
        
        if config.mode == OutputMode.TRACK:
            # Track mode: outputs 1-8 in byte 0, outputs 9-10 in byte 1 bits 0-1
            if out_num <= 8:
                data[0] |= (1 << (out_num - 1))
            else:
                data[1] |= (1 << (out_num - 9))  # Outputs 9-10 -> bits 0-1
        
        elif config.mode == OutputMode.SOFT_START:
            # Soft-start: outputs 1-6 in byte 1 bits 2-7, outputs 7-10 in byte 2 bits 0-3
            if out_num <= 6:
                data[1] |= (1 << (out_num - 1 + 2))  # Outputs 1-6 -> bits 2-7
            else:
                data[2] |= (1 << (out_num - 7))  # Outputs 7-10 -> bits 0-3
        
        elif config.mode == OutputMode.PWM:
            # PWM enable: outputs 1-4 in byte 2 bits 4-7, outputs 5-8 in byte 3 bits 0-3
            duty = max(0, min(15, config.pwm_duty))
            
            if out_num <= 4:
                data[2] |= (1 << (out_num - 1 + 4))  # Enable bits 4-7
            elif out_num <= 8:
                data[3] |= (1 << (out_num - 5))  # Enable bits 0-3
            # Note: PWM doesn't support outputs 9-10
            
            # PWM duty cycle in bytes 4-7
            # Byte 4: Output 1 (upper nibble), Output 2 (lower nibble)
            # Byte 5: Output 3 (upper nibble), Output 4 (lower nibble)
            # Byte 6: Output 5 (upper nibble), Output 6 (lower nibble)
            # Byte 7: Output 7 (upper nibble), Output 8 (lower nibble)
            if out_num <= 8:
                byte_idx = 4 + ((out_num - 1) // 2)
                if (out_num - 1) % 2 == 0:  # Odd outputs (1,3,5,7) -> upper nibble
                    data[byte_idx] |= (duty << 4)
                else:  # Even outputs (2,4,6,8) -> lower nibble
                    data[byte_idx] |= duty
    
    return data


def decode_powercell_message(data: List[int]) -> Dict[int, OutputConfig]:
    """
    Decode 8-byte CAN message into POWERCELL output configurations.
    
    Args:
        data: List of 8 bytes
    
    Returns:
        Dict mapping output number (1-10) to OutputConfig
    """
    configs = {}
    
    for out_num in range(1, 11):
        config = OutputConfig(enabled=False, mode=OutputMode.OFF, pwm_duty=0)
        
        # Check Track mode first (highest priority)
        if out_num <= 8:
            if data[0] & (1 << (out_num - 1)):
                config.enabled = True
                config.mode = OutputMode.TRACK
        else:
            if data[1] & (1 << (out_num - 9)):
                config.enabled = True
                config.mode = OutputMode.TRACK
        
        # Check Soft-start if not Track
        if not config.enabled:
            if out_num <= 6:
                if data[1] & (1 << (out_num - 1 + 2)):
                    config.enabled = True
                    config.mode = OutputMode.SOFT_START
            elif out_num <= 10:
                if data[2] & (1 << (out_num - 7)):
                    config.enabled = True
                    config.mode = OutputMode.SOFT_START
        
        # Check PWM if not Track or Soft-start
        if not config.enabled and out_num <= 8:
            if out_num <= 4:
                if data[2] & (1 << (out_num - 1 + 4)):
                    config.enabled = True
                    config.mode = OutputMode.PWM
            else:
                if data[3] & (1 << (out_num - 5)):
                    config.enabled = True
                    config.mode = OutputMode.PWM
            
            if config.mode == OutputMode.PWM:
                byte_idx = 4 + ((out_num - 1) // 2)
                if (out_num - 1) % 2 == 0:  # Odd outputs -> upper nibble
                    config.pwm_duty = (data[byte_idx] >> 4) & 0x0F
                else:  # Even outputs -> lower nibble
                    config.pwm_duty = data[byte_idx] & 0x0F
        
        if config.enabled:
            configs[out_num] = config
    
    return configs


def encode_inmotion_message(output_configs: Dict[int, OutputConfig]) -> List[int]:
    """
    Encode inMOTION output configurations into 8-byte CAN message.
    
    inMOTION outputs:
    - 1-4: Relay outputs (1A, 1B, 2A, 2B)
    - 5-8: Regular outputs (Output 1-4)
    
    Simple bit mapping: output N is bit (N-1) in byte 0
    """
    data = [0, 0, 0, 0, 0, 0, 0, 0]
    
    for out_num, config in output_configs.items():
        if not config.enabled or config.mode == OutputMode.OFF:
            continue
        
        if 1 <= out_num <= 8:
            data[0] |= (1 << (out_num - 1))
    
    return data


# =============================================================================
# Input Definitions
# =============================================================================

@dataclass
class InputDefinition:
    """Definition of a physical input on the MASTERCELL"""
    number: int
    name: str
    default_name: str
    input_type: str  # 'ground', 'high_side', 'analog', 'pulse'
    connector: str   # 'A' or 'B'
    pin: int

# Define all 44 inputs based on the project scope
INPUTS = [
    # Connector A - Ground Switched (IN01-IN22)
    InputDefinition(1, "Ignition", "Ignition", "ground", "A", 1),
    InputDefinition(2, "Starter", "Starter", "ground", "A", 2),
    InputDefinition(3, "Left Turn", "Left Turn", "ground", "A", 3),
    InputDefinition(4, "Right Turn", "Right Turn", "ground", "A", 4),
    InputDefinition(5, "Head Lights", "Head Lights", "ground", "A", 5),
    InputDefinition(6, "Parking Lights", "Parking Lights", "ground", "A", 6),
    InputDefinition(7, "High Beams", "High Beams", "ground", "A", 7),
    InputDefinition(8, "4-Ways", "4-Ways", "ground", "A", 8),
    InputDefinition(9, "Horn", "Horn", "ground", "A", 9),
    InputDefinition(10, "Cooling Fan (GND)", "Cooling Fan", "ground", "A", 10),
    InputDefinition(11, "1-Filament Brake", "Brake Light", "ground", "A", 11),
    InputDefinition(12, "Multi-Filament Brake", "Brake Multi", "ground", "A", 12),
    InputDefinition(13, "Fuel Pump (GND)", "Fuel Pump", "ground", "A", 13),
    InputDefinition(14, "Alternating Headlight", "Alt Headlight", "ground", "A", 14),
    InputDefinition(15, "One-Button Start", "Push Start", "ground", "A", 15),
    InputDefinition(16, "Neutral Safety Input", "Neutral Safety", "ground", "A", 16),
    InputDefinition(17, "AUX Input 01", "AUX 01", "ground", "A", 17),
    InputDefinition(18, "AUX Input 02", "AUX 02", "ground", "A", 18),
    InputDefinition(19, "AUX Input 03", "AUX 03", "ground", "A", 19),
    InputDefinition(20, "AUX Input 04", "AUX 04", "ground", "A", 20),
    InputDefinition(21, "AUX Input 05", "AUX 05", "ground", "A", 21),
    InputDefinition(22, "AUX Input 06", "AUX 06", "ground", "A", 22),
    # Connector A - High Side (HSIN01-HSIN02)
    InputDefinition(23, "Cooling Fan (HS)", "Cooling Fan HS", "high_side", "A", 23),
    InputDefinition(24, "Fuel Pump (HS)", "Fuel Pump HS", "high_side", "A", 24),
    # Connector B - Ground Switched (IN23-IN38)
    InputDefinition(25, "AUX Input B01", "AUX B01", "ground", "B", 1),
    InputDefinition(26, "AUX Input B02", "AUX B02", "ground", "B", 2),
    InputDefinition(27, "AUX Input B03", "AUX B03", "ground", "B", 3),
    InputDefinition(28, "AUX Input B04", "AUX B04", "ground", "B", 4),
    InputDefinition(29, "AUX Input B05", "AUX B05", "ground", "B", 5),
    InputDefinition(30, "AUX Input B06", "AUX B06", "ground", "B", 6),
    InputDefinition(31, "AUX Input B07", "AUX B07", "ground", "B", 7),
    InputDefinition(32, "AUX Input B08", "AUX B08", "ground", "B", 8),
    InputDefinition(33, "AUX Input B09", "AUX B09", "ground", "B", 9),
    InputDefinition(34, "AUX Input B10", "AUX B10", "ground", "B", 10),
    InputDefinition(35, "AUX Input B11", "AUX B11", "ground", "B", 11),
    InputDefinition(36, "AUX Input B12", "AUX B12", "ground", "B", 12),
    InputDefinition(37, "AUX Input B13", "AUX B13", "ground", "B", 13),
    InputDefinition(38, "AUX Input B14", "AUX B14", "ground", "B", 14),
    # Connector B - High Side (HSIN03-HSIN06)
    InputDefinition(39, "AUX Input HS03", "AUX HS03", "high_side", "B", 17),
    InputDefinition(40, "AUX Input HS04", "AUX HS04", "high_side", "B", 18),
    InputDefinition(41, "AUX Input HS05", "AUX HS05", "high_side", "B", 19),
    InputDefinition(42, "AUX Input HS06", "AUX HS06", "high_side", "B", 20),
    # Analog/Pulse inputs (virtual input numbers for condition tracking)
    InputDefinition(43, "Tach Input", "Tachometer", "pulse", "B", 26),
    InputDefinition(44, "VSS Input", "Speed Sensor", "pulse", "B", 27),
]

# Pattern presets for flashing/blinking
PATTERN_PRESETS = {
    "none": {"name": "No Pattern (Solid)", "on_time": 0, "off_time": 0},
    "turn_signal": {"name": "Turn Signal (500ms)", "on_time": 1, "off_time": 1},
    "hazard": {"name": "Hazard (500ms)", "on_time": 1, "off_time": 1},
    "slow_flash": {"name": "Slow Flash (1s)", "on_time": 2, "off_time": 2},
    "custom": {"name": "Custom Pattern", "on_time": 1, "off_time": 1},
}

# =============================================================================
# Configuration Data Classes
# =============================================================================

@dataclass
class CaseConfig:
    """Configuration for a single ON or OFF case"""
    enabled: bool = False
    # Device outputs configuration - list of (device_id, output_configs) tuples
    device_outputs: List[Tuple[str, Dict[int, OutputConfig]]] = field(default_factory=list)
    # Behavior flags
    mode: str = "momentary"  # momentary, toggle, timed
    timer_on: int = 0        # 0-255, each count = 500ms
    timer_delay: int = 0     # 0-255, each count = 500ms
    pattern_preset: str = "none"
    pattern_on_time: int = 0   # 0-15, upper nibble
    pattern_off_time: int = 0  # 0-15, lower nibble
    set_ignition: bool = False
    # Conditions
    must_be_on: List[int] = field(default_factory=list)
    must_be_off: List[int] = field(default_factory=list)
    require_ignition_on: bool = False
    require_ignition_off: bool = False
    require_security_on: bool = False
    require_security_off: bool = False
    rpm_above: int = 0
    rpm_below: int = 0
    speed_above: int = 0
    speed_below: int = 0
    
    def get_can_messages(self) -> List[Tuple[int, int, int, List[int]]]:
        """
        Generate CAN messages for this case.
        
        Returns:
            List of (pgn_high, pgn_low, sa, data_bytes) tuples
        """
        messages = []
        
        for device_id, output_configs in self.device_outputs:
            if device_id not in DEVICES:
                continue
            
            device = DEVICES[device_id]
            
            if device.device_type == "powercell":
                data = encode_powercell_message(output_configs)
            else:  # inmotion
                data = encode_inmotion_message(output_configs)
            
            # Only add message if any outputs are configured
            if any(b != 0 for b in data):
                messages.append((device.pgn_high, device.pgn_low, 0x80, data))
        
        return messages

@dataclass
class InputConfig:
    """Configuration for a single input with all its cases"""
    input_number: int
    custom_name: str = ""
    on_cases: List[CaseConfig] = field(default_factory=lambda: [CaseConfig() for _ in range(8)])
    off_cases: List[CaseConfig] = field(default_factory=lambda: [CaseConfig() for _ in range(2)])

    def get_eeprom_base_address(self) -> int:
        """Calculate the EEPROM base address for this input"""
        return EEPROM_ADDR_INPUT_START + ((self.input_number - 1) * EEPROM_BYTES_PER_INPUT)

@dataclass
class SystemConfig:
    """System-wide configuration settings"""
    bitrate: int = BitrateCode.KBPS_250
    loss_of_com_timer: int = LossOfComTimer.SEC_30
    rebroadcast_mode: int = RebroadcastMode.EDGE_TRIGGERED
    heartbeat_pgn_high: int = 0xFF
    heartbeat_pgn_low: int = 0x06
    heartbeat_sa: int = 0x80
    write_pgn_high: int = 0xFF
    write_pgn_low: int = 0x16
    write_sa: int = 0x80
    read_pgn_high: int = 0xFF
    read_pgn_low: int = 0x26
    read_sa: int = 0x80
    response_pgn_high: int = 0xFF
    response_pgn_low: int = 0x36
    response_sa: int = 0x80
    diagnostic_pgn_high: int = 0xFF
    diagnostic_pgn_low: int = 0x46
    diagnostic_sa: int = 0x80
    serial_number: int = 0x42

@dataclass 
class FullConfiguration:
    """Complete device configuration"""
    system: SystemConfig = field(default_factory=SystemConfig)
    inputs: List[InputConfig] = field(default_factory=lambda: [InputConfig(input_number=i+1) for i in range(44)])

    def to_json(self) -> str:
        """Serialize configuration to JSON"""
        def config_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                result = {}
                for k, v in obj.__dict__.items():
                    result[k] = config_to_dict(v)
                return result
            elif isinstance(obj, list):
                return [config_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: config_to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, tuple):
                return list(config_to_dict(item) for item in obj)
            elif isinstance(obj, OutputMode):
                return obj.value
            else:
                return obj
        return json.dumps(config_to_dict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'FullConfiguration':
        """Deserialize configuration from JSON"""
        data = json.loads(json_str)
        config = cls()
        # Populate system config
        if 'system' in data:
            for key, value in data['system'].items():
                if hasattr(config.system, key):
                    setattr(config.system, key, value)
        # Populate input configs
        if 'inputs' in data:
            for i, input_data in enumerate(data['inputs']):
                if i < len(config.inputs):
                    for key, value in input_data.items():
                        if key == 'on_cases':
                            for j, case_data in enumerate(value):
                                if j < len(config.inputs[i].on_cases):
                                    for ck, cv in case_data.items():
                                        if hasattr(config.inputs[i].on_cases[j], ck):
                                            setattr(config.inputs[i].on_cases[j], ck, cv)
                        elif key == 'off_cases':
                            for j, case_data in enumerate(value):
                                if j < len(config.inputs[i].off_cases):
                                    for ck, cv in case_data.items():
                                        if hasattr(config.inputs[i].off_cases[j], ck):
                                            setattr(config.inputs[i].off_cases[j], ck, cv)
                        elif hasattr(config.inputs[i], key):
                            setattr(config.inputs[i], key, value)
        return config


def get_input_definition(input_number: int) -> Optional[InputDefinition]:
    """Get input definition by number (1-44)"""
    for inp in INPUTS:
        if inp.number == input_number:
            return inp
    return None


def calculate_case_address(input_number: int, case_type: str, case_index: int) -> int:
    """
    Calculate EEPROM address for a specific case
    
    Args:
        input_number: 1-44
        case_type: 'on' or 'off'
        case_index: 0-7 for ON cases, 0-1 for OFF cases
    
    Returns:
        EEPROM address
    """
    base = EEPROM_ADDR_INPUT_START + ((input_number - 1) * EEPROM_BYTES_PER_INPUT)
    if case_type == 'on':
        return base + (case_index * EEPROM_BYTES_PER_CASE)
    else:  # off
        on_section = EEPROM_ON_CASES_PER_INPUT * EEPROM_BYTES_PER_CASE  # 88 bytes
        return base + on_section + (case_index * EEPROM_BYTES_PER_CASE)
