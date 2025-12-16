"""
eeprom_protocol.py - MASTERCELL NGX EEPROM Configuration Protocol via J1939

This module handles:
- Converting configuration data to EEPROM bytes
- Generating CAN messages for read/write operations
- Parsing responses from the MASTERCELL
- Address calculations for all configuration data
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from enum import IntEnum

from config_data import (
    CaseConfig, InputConfig, FullConfiguration, SystemConfig,
    DEVICES, OutputMode, OutputConfig, PATTERN_PRESETS
)


# =============================================================================
# EEPROM Constants
# =============================================================================

# Guard byte required for all read/write operations
EEPROM_GUARD_BYTE = 0x77

# Default PGNs (can be reconfigured)
DEFAULT_WRITE_PGN = 0xFF10
DEFAULT_READ_PGN = 0xFF20
DEFAULT_RESPONSE_PGN = 0xFF30
DEFAULT_SA = 0x80

# Priority for configuration messages
CAN_PRIORITY = 6  # Default J1939 priority

# Response status codes
class ResponseStatus(IntEnum):
    SUCCESS = 0x01
    BAD_GUARD = 0xE1
    WRITE_VERIFY_FAILED = 0xE5
    ADDRESS_OUT_OF_RANGE = 0xE6


# =============================================================================
# EEPROM Address Map
# =============================================================================

# System configuration addresses (0x0000 - 0x001A)
class SystemAddress(IntEnum):
    BITRATE = 0x00
    HEARTBEAT_PGN_HIGH = 0x01
    HEARTBEAT_PGN_LOW = 0x02
    HEARTBEAT_SA = 0x03
    FW_MAJOR = 0x04
    FW_MINOR = 0x05
    REBROADCAST_MODE = 0x06
    INIT_STAMP = 0x07
    # 0x08-0x09 Reserved
    WRITE_PGN_HIGH = 0x0A
    WRITE_PGN_LOW = 0x0B
    WRITE_SA = 0x0C
    READ_PGN_HIGH = 0x0D
    READ_PGN_LOW = 0x0E
    READ_SA = 0x0F
    RESPONSE_PGN_HIGH = 0x10
    RESPONSE_PGN_LOW = 0x11
    RESPONSE_SA = 0x12
    DIAG_PGN_HIGH = 0x13
    DIAG_PGN_LOW = 0x14
    DIAG_SA = 0x15
    SERIAL_NUMBER = 0x16
    CUSTOMER_NAME_START = 0x17  # 4 bytes: 0x17-0x1A


# Case data constants
CASE_DATA_START = 0x0022  # First case starts here
CASE_SIZE = 32  # Each case is 32 bytes
CASES_PER_INPUT = 10  # 8 ON cases + 2 OFF cases
BYTES_PER_INPUT = CASE_SIZE * CASES_PER_INPUT  # 320 bytes per input

# Total inputs
TOTAL_INPUTS = 44


# =============================================================================
# Case Structure Offsets (within 32-byte case)
# =============================================================================

class CaseOffset(IntEnum):
    PRIORITY = 0
    PGN_HIGH = 1
    PGN_LOW = 2
    SOURCE_ADDRESS = 3
    CONFIG_BYTE = 4
    RESERVED_1 = 5
    RESERVED_2 = 6
    PATTERN_TIMING = 7
    MUST_BE_ON_START = 8   # 8 bytes (8-15)
    MUST_BE_OFF_START = 16  # 8 bytes (16-23)
    CAN_DATA_START = 24    # 8 bytes (24-31)


# Config byte bit masks
class ConfigBits(IntEnum):
    CAN_BE_OVERRIDDEN = 0x04  # Bits 2-3
    ONE_BUTTON_START = 0x10   # Bits 4-5
    TRACK_IGNITION = 0x40     # Bits 6-7


# =============================================================================
# Address Calculation Functions
# =============================================================================

def get_case_address(input_number: int, is_on_case: bool, case_index: int) -> int:
    """
    Calculate the EEPROM address for a specific case.
    
    Args:
        input_number: Input number (1-44)
        is_on_case: True for ON cases, False for OFF cases
        case_index: Index within ON (0-7) or OFF (0-1) cases
    
    Returns:
        EEPROM starting address for this case
    """
    if input_number < 1 or input_number > TOTAL_INPUTS:
        raise ValueError(f"Invalid input number: {input_number}")
    
    if is_on_case:
        if case_index < 0 or case_index > 7:
            raise ValueError(f"Invalid ON case index: {case_index}")
        case_offset = case_index
    else:
        if case_index < 0 or case_index > 1:
            raise ValueError(f"Invalid OFF case index: {case_index}")
        case_offset = 8 + case_index  # OFF cases are after 8 ON cases
    
    input_offset = (input_number - 1) * BYTES_PER_INPUT
    case_byte_offset = case_offset * CASE_SIZE
    
    return CASE_DATA_START + input_offset + case_byte_offset


def get_input_address_range(input_number: int) -> Tuple[int, int]:
    """
    Get the address range for all cases of an input.
    
    Returns:
        (start_address, end_address) tuple
    """
    start = CASE_DATA_START + (input_number - 1) * BYTES_PER_INPUT
    end = start + BYTES_PER_INPUT - 1
    return (start, end)


# =============================================================================
# Case Data Encoding
# =============================================================================

def inputs_to_bitmask(input_numbers: List[int]) -> bytes:
    """
    Convert a list of input numbers to an 8-byte bitmask.
    
    Input 1 = Byte 0, Bit 0
    Input 8 = Byte 0, Bit 7
    Input 9 = Byte 1, Bit 0
    ...
    Input 44 = Byte 5, Bit 3
    
    Special: Byte 5, Bit 5 (0x20) = Ignition condition
    """
    bitmask = [0] * 8
    
    for inp in input_numbers:
        if inp < 1 or inp > 64:  # Allow up to 64 inputs for future expansion
            continue
        byte_index = (inp - 1) // 8
        bit_index = (inp - 1) % 8
        if byte_index < 8:
            bitmask[byte_index] |= (1 << bit_index)
    
    return bytes(bitmask)


def bitmask_to_inputs(bitmask: bytes) -> List[int]:
    """
    Convert an 8-byte bitmask to a list of input numbers.
    """
    inputs = []
    for byte_index, byte_val in enumerate(bitmask):
        for bit_index in range(8):
            if byte_val & (1 << bit_index):
                input_num = byte_index * 8 + bit_index + 1
                inputs.append(input_num)
    return inputs


def encode_pattern_timing(on_time_250ms: int, off_time_250ms: int) -> int:
    """
    Encode pattern timing into a single byte.
    Upper nibble = ON time (0-15, units of 250ms)
    Lower nibble = OFF time (0-15, units of 250ms)
    """
    on_time = min(15, max(0, on_time_250ms))
    off_time = min(15, max(0, off_time_250ms))
    return (on_time << 4) | off_time


def decode_pattern_timing(timing_byte: int) -> Tuple[int, int]:
    """
    Decode pattern timing byte.
    Returns (on_time_250ms, off_time_250ms)
    """
    on_time = (timing_byte >> 4) & 0x0F
    off_time = timing_byte & 0x0F
    return (on_time, off_time)


def case_config_to_eeprom_bytes(case: CaseConfig, input_number: int) -> List[bytes]:
    """
    Convert a CaseConfig to 32-byte EEPROM format.
    
    Returns a list of 32-byte arrays, one for each device output configured.
    If no outputs are configured, returns a single 32-byte array of zeros (disabled case).
    """
    results = []
    
    if not case.enabled or not case.device_outputs:
        # Return a disabled/empty case
        return [bytes(32)]
    
    for device_id, output_configs in case.device_outputs:
        if device_id not in DEVICES:
            continue
        
        device = DEVICES[device_id]
        case_bytes = bytearray(32)
        
        # Byte 0: Priority
        case_bytes[CaseOffset.PRIORITY] = CAN_PRIORITY
        
        # Bytes 1-2: PGN
        case_bytes[CaseOffset.PGN_HIGH] = device.pgn_high
        case_bytes[CaseOffset.PGN_LOW] = device.pgn_low
        
        # Byte 3: Source Address
        case_bytes[CaseOffset.SOURCE_ADDRESS] = DEFAULT_SA
        
        # Byte 4: Config byte
        config_byte = 0
        if case.mode == 'toggle':
            config_byte |= ConfigBits.ONE_BUTTON_START
        # Add other config bits as needed
        case_bytes[CaseOffset.CONFIG_BYTE] = config_byte
        
        # Bytes 5-6: Reserved
        case_bytes[CaseOffset.RESERVED_1] = 0
        case_bytes[CaseOffset.RESERVED_2] = 0
        
        # Byte 7: Pattern timing
        if case.pattern_preset and case.pattern_preset != 'none':
            preset = PATTERN_PRESETS.get(case.pattern_preset, {})
            on_time = preset.get('on_time', 0)
            off_time = preset.get('off_time', 0)
            case_bytes[CaseOffset.PATTERN_TIMING] = encode_pattern_timing(on_time, off_time)
        else:
            case_bytes[CaseOffset.PATTERN_TIMING] = encode_pattern_timing(
                case.pattern_on_time, case.pattern_off_time
            )
        
        # Bytes 8-15: must_be_on bitmask
        must_on_mask = inputs_to_bitmask(case.must_be_on)
        case_bytes[CaseOffset.MUST_BE_ON_START:CaseOffset.MUST_BE_ON_START + 8] = must_on_mask
        
        # Bytes 16-23: must_be_off bitmask
        must_off_mask = inputs_to_bitmask(case.must_be_off)
        case_bytes[CaseOffset.MUST_BE_OFF_START:CaseOffset.MUST_BE_OFF_START + 8] = must_off_mask
        
        # Bytes 24-31: CAN data bytes
        can_data = encode_device_outputs(device, output_configs)
        case_bytes[CaseOffset.CAN_DATA_START:CaseOffset.CAN_DATA_START + 8] = can_data
        
        results.append(bytes(case_bytes))
    
    # If no valid device outputs, return disabled case
    if not results:
        return [bytes(32)]
    
    return results


def encode_device_outputs(device, output_configs: Dict[int, OutputConfig]) -> bytes:
    """
    Encode output configurations into 8 CAN data bytes for a device.
    """
    from config_data import encode_powercell_message, encode_inmotion_message
    
    if device.device_type == "powercell":
        return bytes(encode_powercell_message(output_configs))
    else:
        return bytes(encode_inmotion_message(output_configs))


# =============================================================================
# CAN Message Generation
# =============================================================================

def build_can_id(pgn: int, sa: int = DEFAULT_SA, priority: int = CAN_PRIORITY) -> int:
    """
    Build a 29-bit extended CAN ID from J1939 components.
    
    Format: [Priority(3)] [R(1)] [DP(1)] [PGN(16)] [SA(8)]
    """
    # Priority in bits 26-28
    # Reserved bit 25 = 0
    # Data Page bit 24 = 0
    # PGN in bits 8-23
    # SA in bits 0-7
    can_id = (priority & 0x07) << 26
    can_id |= (pgn & 0xFFFF) << 8
    can_id |= (sa & 0xFF)
    return can_id


def generate_write_message(address: int, value: int, sa: int = DEFAULT_SA) -> Tuple[int, bytes]:
    """
    Generate a CAN write request message.
    
    Returns:
        (can_id, data_bytes) tuple
    """
    can_id = build_can_id(DEFAULT_WRITE_PGN, sa)
    
    data = bytes([
        EEPROM_GUARD_BYTE,       # Byte 0: Guard byte
        address & 0xFF,          # Byte 1: Address LSB
        (address >> 8) & 0xFF,   # Byte 2: Address MSB
        value & 0xFF,            # Byte 3: Value to write
        0xFF, 0xFF, 0xFF, 0xFF   # Bytes 4-7: Padding
    ])
    
    return (can_id, data)


def generate_read_message(address: int, sa: int = DEFAULT_SA) -> Tuple[int, bytes]:
    """
    Generate a CAN read request message.
    
    Returns:
        (can_id, data_bytes) tuple
    """
    can_id = build_can_id(DEFAULT_READ_PGN, sa)
    
    data = bytes([
        EEPROM_GUARD_BYTE,       # Byte 0: Guard byte
        address & 0xFF,          # Byte 1: Address LSB
        (address >> 8) & 0xFF,   # Byte 2: Address MSB
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF  # Bytes 3-7: Padding
    ])
    
    return (can_id, data)


@dataclass
class WriteOperation:
    """Represents a single EEPROM write operation"""
    address: int
    value: int
    description: str = ""
    
    def to_can_message(self, sa: int = DEFAULT_SA) -> Tuple[int, bytes]:
        return generate_write_message(self.address, self.value, sa)


@dataclass
class ReadOperation:
    """Represents a single EEPROM read operation"""
    address: int
    description: str = ""
    
    def to_can_message(self, sa: int = DEFAULT_SA) -> Tuple[int, bytes]:
        return generate_read_message(self.address, sa)


# =============================================================================
# Configuration to Write Operations
# =============================================================================

def generate_case_write_operations(
    case: CaseConfig,
    input_number: int,
    is_on_case: bool,
    case_index: int
) -> List[WriteOperation]:
    """
    Generate all write operations needed to write a case to EEPROM.
    
    Returns:
        List of WriteOperation objects
    """
    operations = []
    base_address = get_case_address(input_number, is_on_case, case_index)
    
    # Get the 32-byte case data
    case_bytes_list = case_config_to_eeprom_bytes(case, input_number)
    
    # Use the first set of bytes (primary device output)
    if case_bytes_list:
        case_bytes = case_bytes_list[0]
        
        case_type = "ON" if is_on_case else "OFF"
        
        for offset, value in enumerate(case_bytes):
            operations.append(WriteOperation(
                address=base_address + offset,
                value=value,
                description=f"Input {input_number} {case_type} Case {case_index}: byte {offset}"
            ))
    
    return operations


def generate_input_write_operations(input_config: InputConfig) -> List[WriteOperation]:
    """
    Generate all write operations for an input's configuration.
    """
    operations = []
    
    # Write all 8 ON cases
    for i, case in enumerate(input_config.on_cases):
        ops = generate_case_write_operations(
            case, input_config.input_number, True, i
        )
        operations.extend(ops)
    
    # Write all 2 OFF cases
    for i, case in enumerate(input_config.off_cases):
        ops = generate_case_write_operations(
            case, input_config.input_number, False, i
        )
        operations.extend(ops)
    
    return operations


def generate_system_write_operations(system: SystemConfig) -> List[WriteOperation]:
    """
    Generate write operations for system configuration.
    """
    operations = [
        WriteOperation(SystemAddress.BITRATE, system.bitrate, "CAN Bitrate"),
        WriteOperation(SystemAddress.HEARTBEAT_PGN_HIGH, system.heartbeat_pgn_high, "Heartbeat PGN High"),
        WriteOperation(SystemAddress.HEARTBEAT_PGN_LOW, system.heartbeat_pgn_low, "Heartbeat PGN Low"),
        WriteOperation(SystemAddress.HEARTBEAT_SA, system.heartbeat_sa, "Heartbeat SA"),
        WriteOperation(SystemAddress.REBROADCAST_MODE, system.rebroadcast_mode, "Rebroadcast Mode"),
        WriteOperation(SystemAddress.WRITE_PGN_HIGH, system.write_pgn_high, "Write PGN High"),
        WriteOperation(SystemAddress.WRITE_PGN_LOW, system.write_pgn_low, "Write PGN Low"),
        WriteOperation(SystemAddress.WRITE_SA, system.write_sa, "Write SA"),
        WriteOperation(SystemAddress.READ_PGN_HIGH, system.read_pgn_high, "Read PGN High"),
        WriteOperation(SystemAddress.READ_PGN_LOW, system.read_pgn_low, "Read PGN Low"),
        WriteOperation(SystemAddress.READ_SA, system.read_sa, "Read SA"),
        WriteOperation(SystemAddress.RESPONSE_PGN_HIGH, system.response_pgn_high, "Response PGN High"),
        WriteOperation(SystemAddress.RESPONSE_PGN_LOW, system.response_pgn_low, "Response PGN Low"),
        WriteOperation(SystemAddress.RESPONSE_SA, system.response_sa, "Response SA"),
    ]
    return operations


def generate_full_config_write_operations(config: FullConfiguration) -> List[WriteOperation]:
    """
    Generate ALL write operations for a complete configuration.
    
    This includes system settings and all input cases.
    """
    operations = []
    
    # System configuration
    operations.extend(generate_system_write_operations(config.system))
    
    # All inputs
    for input_config in config.inputs:
        operations.extend(generate_input_write_operations(input_config))
    
    return operations


# =============================================================================
# Read Operations
# =============================================================================

def generate_system_read_operations() -> List[ReadOperation]:
    """Generate read operations for all system configuration bytes."""
    operations = []
    for addr in range(0x00, 0x1B):  # 0x00 to 0x1A inclusive
        operations.append(ReadOperation(addr, f"System byte 0x{addr:02X}"))
    return operations


def generate_case_read_operations(
    input_number: int,
    is_on_case: bool,
    case_index: int
) -> List[ReadOperation]:
    """Generate read operations for a single case (32 bytes)."""
    operations = []
    base_address = get_case_address(input_number, is_on_case, case_index)
    case_type = "ON" if is_on_case else "OFF"
    
    for offset in range(CASE_SIZE):
        operations.append(ReadOperation(
            base_address + offset,
            f"Input {input_number} {case_type} Case {case_index}: byte {offset}"
        ))
    
    return operations


def generate_input_read_operations(input_number: int) -> List[ReadOperation]:
    """Generate read operations for all cases of an input."""
    operations = []
    
    # Read all 8 ON cases
    for i in range(8):
        operations.extend(generate_case_read_operations(input_number, True, i))
    
    # Read all 2 OFF cases
    for i in range(2):
        operations.extend(generate_case_read_operations(input_number, False, i))
    
    return operations


def generate_full_config_read_operations() -> List[ReadOperation]:
    """Generate read operations for the ENTIRE EEPROM configuration."""
    operations = []
    
    # System configuration
    operations.extend(generate_system_read_operations())
    
    # All 44 inputs
    for input_num in range(1, TOTAL_INPUTS + 1):
        operations.extend(generate_input_read_operations(input_num))
    
    return operations


# =============================================================================
# Response Parsing
# =============================================================================

@dataclass
class EEPROMResponse:
    """Parsed response from MASTERCELL"""
    firmware_major: int
    firmware_minor: int
    value: int
    address: int
    status: ResponseStatus
    success: bool
    
    @classmethod
    def from_can_data(cls, data: bytes) -> 'EEPROMResponse':
        """Parse a response from 8 CAN data bytes."""
        if len(data) < 6:
            raise ValueError("Response data too short")
        
        fw_major = data[0]
        fw_minor = data[1]
        value = data[2]
        addr_lsb = data[3]
        addr_msb = data[4]
        status = data[5]
        
        address = (addr_msb << 8) | addr_lsb
        
        try:
            status_enum = ResponseStatus(status)
        except ValueError:
            status_enum = ResponseStatus.SUCCESS  # Unknown status
        
        return cls(
            firmware_major=fw_major,
            firmware_minor=fw_minor,
            value=value,
            address=address,
            status=status_enum,
            success=(status == ResponseStatus.SUCCESS)
        )


# =============================================================================
# EEPROM Data to Configuration Parsing
# =============================================================================

def parse_case_bytes(case_bytes: bytes) -> Optional[CaseConfig]:
    """
    Parse 32 EEPROM bytes into a CaseConfig.
    Returns None if the case is empty/disabled.
    """
    if len(case_bytes) != 32:
        return None
    
    # Check if case is empty (all zeros or no PGN set)
    pgn_high = case_bytes[CaseOffset.PGN_HIGH]
    pgn_low = case_bytes[CaseOffset.PGN_LOW]
    
    if pgn_high == 0 and pgn_low == 0:
        return CaseConfig(enabled=False)
    
    config = CaseConfig(enabled=True)
    
    # Parse config byte
    config_byte = case_bytes[CaseOffset.CONFIG_BYTE]
    if config_byte & ConfigBits.ONE_BUTTON_START:
        config.mode = 'toggle'
    else:
        config.mode = 'momentary'
    
    # Parse pattern timing
    timing = case_bytes[CaseOffset.PATTERN_TIMING]
    config.pattern_on_time, config.pattern_off_time = decode_pattern_timing(timing)
    
    # Parse must_be_on
    must_on_bytes = case_bytes[CaseOffset.MUST_BE_ON_START:CaseOffset.MUST_BE_ON_START + 8]
    config.must_be_on = bitmask_to_inputs(must_on_bytes)
    
    # Parse must_be_off
    must_off_bytes = case_bytes[CaseOffset.MUST_BE_OFF_START:CaseOffset.MUST_BE_OFF_START + 8]
    config.must_be_off = bitmask_to_inputs(must_off_bytes)
    
    # Parse CAN data and determine device/outputs
    can_data = case_bytes[CaseOffset.CAN_DATA_START:CaseOffset.CAN_DATA_START + 8]
    
    # Find matching device by PGN
    device_id = None
    for did, device in DEVICES.items():
        if device.pgn_high == pgn_high and device.pgn_low == pgn_low:
            device_id = did
            break
    
    if device_id:
        # Decode outputs from CAN data
        output_configs = decode_device_outputs(DEVICES[device_id], can_data)
        if output_configs:
            config.device_outputs = [(device_id, output_configs)]
    
    return config


def decode_device_outputs(device, can_data: bytes) -> Dict[int, OutputConfig]:
    """
    Decode CAN data bytes into output configurations for a device.
    """
    outputs = {}
    
    if device.device_type == "powercell":
        # Decode powercell format
        # Byte 0: outputs 1-8 track bits
        # Byte 1: bits 0-1 = outputs 9-10 track, bits 2-7 = outputs 1-6 soft-start
        # Byte 3: bits 0-3 = outputs 7-10 soft-start, bits 4-7 = outputs 1-4 PWM enable
        # Byte 4: bits 0-3 = outputs 5-8 PWM enable
        # Bytes 5-8: PWM duty cycles (upper/lower nibbles)
        
        track_1_8 = can_data[0]
        track_9_10 = can_data[1] & 0x03
        soft_1_6 = (can_data[1] >> 2) & 0x3F
        soft_7_10 = can_data[3] & 0x0F
        pwm_1_4 = (can_data[3] >> 4) & 0x0F
        pwm_5_8 = can_data[4] & 0x0F
        
        # Outputs 1-8
        for i in range(8):
            out_num = i + 1
            if track_1_8 & (1 << i):
                outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.TRACK)
            elif i < 6 and (soft_1_6 & (1 << i)):
                outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.SOFT_START)
            elif i < 4 and (pwm_1_4 & (1 << i)):
                # Get PWM duty
                byte_idx = 5 + (i // 2)
                if i % 2 == 0:
                    duty = (can_data[byte_idx] >> 4) & 0x0F
                else:
                    duty = can_data[byte_idx] & 0x0F
                outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.PWM, pwm_duty=duty)
            elif i >= 4 and i < 8 and (pwm_5_8 & (1 << (i - 4))):
                byte_idx = 5 + (i // 2)
                if i % 2 == 0:
                    duty = (can_data[byte_idx] >> 4) & 0x0F
                else:
                    duty = can_data[byte_idx] & 0x0F
                outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.PWM, pwm_duty=duty)
        
        # Outputs 9-10
        for i in range(2):
            out_num = 9 + i
            if track_9_10 & (1 << i):
                outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.TRACK)
            elif (soft_7_10 >> (i + 2)) & 1:
                outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.SOFT_START)
    
    else:  # inMotion
        # Simpler format - each bit = one output
        for i in range(min(8, len(device.outputs))):
            if can_data[0] & (1 << i):
                outputs[i + 1] = OutputConfig(enabled=True, mode=OutputMode.TRACK)
    
    return outputs


def parse_system_bytes(system_bytes: bytes) -> SystemConfig:
    """Parse system configuration bytes into SystemConfig."""
    if len(system_bytes) < 0x1B:
        return SystemConfig()
    
    return SystemConfig(
        bitrate=system_bytes[SystemAddress.BITRATE],
        heartbeat_pgn_high=system_bytes[SystemAddress.HEARTBEAT_PGN_HIGH],
        heartbeat_pgn_low=system_bytes[SystemAddress.HEARTBEAT_PGN_LOW],
        heartbeat_sa=system_bytes[SystemAddress.HEARTBEAT_SA],
        rebroadcast_mode=system_bytes[SystemAddress.REBROADCAST_MODE],
        write_pgn_high=system_bytes[SystemAddress.WRITE_PGN_HIGH],
        write_pgn_low=system_bytes[SystemAddress.WRITE_PGN_LOW],
        write_sa=system_bytes[SystemAddress.WRITE_SA],
        read_pgn_high=system_bytes[SystemAddress.READ_PGN_HIGH],
        read_pgn_low=system_bytes[SystemAddress.READ_PGN_LOW],
        read_sa=system_bytes[SystemAddress.READ_SA],
        response_pgn_high=system_bytes[SystemAddress.RESPONSE_PGN_HIGH],
        response_pgn_low=system_bytes[SystemAddress.RESPONSE_PGN_LOW],
        response_sa=system_bytes[SystemAddress.RESPONSE_SA],
    )


# =============================================================================
# Utility Functions
# =============================================================================

def calculate_total_write_bytes(config: FullConfiguration) -> int:
    """Calculate total bytes that need to be written for a configuration."""
    # System config: ~27 bytes
    system_bytes = 0x1B
    
    # Each input: 10 cases × 32 bytes = 320 bytes
    # 44 inputs × 320 = 14,080 bytes
    input_bytes = TOTAL_INPUTS * BYTES_PER_INPUT
    
    return system_bytes + input_bytes


def estimate_write_time(config: FullConfiguration, bytes_per_second: float = 100) -> float:
    """
    Estimate time to write configuration in seconds.
    Assumes ~100 bytes/second (accounting for request/response cycle).
    """
    total_bytes = calculate_total_write_bytes(config)
    return total_bytes / bytes_per_second


def format_can_message(can_id: int, data: bytes) -> str:
    """Format a CAN message for display/logging."""
    data_hex = ' '.join(f'{b:02X}' for b in data)
    return f"0x{can_id:08X}: {data_hex}"

