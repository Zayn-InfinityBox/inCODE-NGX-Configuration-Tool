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
    DEVICES, OutputMode, OutputConfig, PATTERN_PRESETS,
    INPUT_ON_CASE_COUNTS, INPUT_OFF_CASE_COUNTS
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
CASE_SIZE = 32  # Each case is 32 bytes
ON_CASES_START = 0x0022   # ON cases: 0x0022 - 0x0D61
OFF_CASES_START = 0x0D62  # OFF cases: 0x0D62 - 0x0FE1

# Total inputs (38 regular + 6 high-side = 44)
TOTAL_INPUTS = 44

# Case counts are imported from config_data.py (single source of truth)
# Use INPUT_ON_CASE_COUNTS and INPUT_OFF_CASE_COUNTS
ON_CASE_COUNTS = INPUT_ON_CASE_COUNTS
OFF_CASE_COUNTS = INPUT_OFF_CASE_COUNTS

# Pre-calculate ON case start addresses
def _build_on_case_offsets():
    """Build lookup table for ON case start addresses."""
    offsets = {}
    current_addr = ON_CASES_START
    for inp in range(1, TOTAL_INPUTS + 1):
        offsets[inp] = current_addr
        case_count = ON_CASE_COUNTS.get(inp, 0)
        current_addr += case_count * CASE_SIZE
    return offsets

# Pre-calculate OFF case start addresses
def _build_off_case_offsets():
    """Build lookup table for OFF case start addresses."""
    offsets = {}
    current_addr = OFF_CASES_START
    for inp in range(1, TOTAL_INPUTS + 1):
        if inp in OFF_CASE_COUNTS:
            offsets[inp] = current_addr
            current_addr += OFF_CASE_COUNTS[inp] * CASE_SIZE
    return offsets

ON_CASE_OFFSETS = _build_on_case_offsets()
OFF_CASE_OFFSETS = _build_off_case_offsets()

# Legacy compatibility
CASE_DATA_START = ON_CASES_START
CASES_PER_INPUT = 10  # Max cases per input (for UI)
BYTES_PER_INPUT = CASE_SIZE * CASES_PER_INPUT  # Legacy - not used for address calc


# =============================================================================
# Case Structure Offsets (within 32-byte case)
# =============================================================================

class CaseOffset(IntEnum):
    """Case structure byte offsets (32 bytes per case)"""
    PRIORITY = 0           # J1939 priority (0-7)
    PGN_HIGH = 1           # High byte of PGN
    PGN_LOW = 2            # Low byte of PGN
    SOURCE_ADDRESS = 3     # Device SA to send to
    CONFIG_BYTE = 4        # Mode flags (see ConfigBits)
    TIMER_ON = 5           # Timer On byte (see TimerBits for structure)
    TIMER_DELAY = 6        # Timer Delay byte (see TimerBits for structure)
    PATTERN_TIMING = 7     # High nibble=ON time, Low nibble=OFF time (250ms units)
    MUST_BE_ON_START = 8   # 8 bytes (8-15) - inputs that must be ON
    MUST_BE_OFF_START = 16 # 8 bytes (16-23) - inputs that must be OFF
    CAN_DATA_START = 24    # 8 bytes (24-31) - CAN payload to transmit


# Timer/Delay byte bit structure (Bytes 5 and 6)
class TimerBits(IntEnum):
    """
    Timer/Delay byte structure:
    - Bit 0: Execution Mode (0 = Fire-and-Forget, 1 = Track Input)
    - Bit 1: Time Scaling (0 = 0.25s increments, 1 = 10s increments)
    - Bits 2-7: Timer value (0-63)
    
    Fire-and-Forget: Timer continues even if input turns OFF
    Track Input: Timer cancels if input turns OFF
    
    Constraint: If both timer and delay are configured, they MUST use same execution mode
    """
    EXECUTION_MODE_MASK = 0x01   # Bit 0
    SCALE_MASK = 0x02            # Bit 1
    VALUE_MASK = 0xFC            # Bits 2-7
    VALUE_SHIFT = 2


# Config byte bit masks (Byte 4)
# Based on actual C code usage in eeprom_init_front_engine.c
class ConfigBits(IntEnum):
    """
    Config Byte Breakdown (from C code analysis):
    - Bit 0 (0x01): Track ignition flag (sets ignition on)
    - Bit 2 (0x04): Can be overridden (single filament brake)
    - Bits 4-5 (0x30): Mode - 0x00=normal, 0x10=one-button start
    
    Examples from C code:
    - IN01 Ignition: 0x01 (track ignition)
    - IN11 Brake 1-fil: 0x04 (can be overridden)
    - IN15 One-button: 0x11 (one-button + track ignition)
    """
    TRACK_IGNITION = 0x01     # Bit 0 - sets ignition flag
    CAN_BE_OVERRIDDEN = 0x04  # Bit 2 - single filament override
    MODE_MASK = 0x30          # Bits 4-5
    ONE_BUTTON_START = 0x10   # Mode value for one-button start


# =============================================================================
# Address Calculation Functions
# =============================================================================

def get_case_address(input_number: int, is_on_case: bool, case_index: int) -> int:
    """
    Calculate the EEPROM address for a specific case.
    
    Args:
        input_number: Input number (1-44)
        is_on_case: True for ON cases, False for OFF cases
        case_index: Index within the case type
    
    Returns:
        EEPROM starting address for this case, or -1 if invalid
    """
    if input_number < 1 or input_number > TOTAL_INPUTS:
        return -1
    
    if is_on_case:
        max_cases = ON_CASE_COUNTS.get(input_number, 0)
        if case_index < 0 or case_index >= max_cases:
            return -1
        base_addr = ON_CASE_OFFSETS.get(input_number, -1)
        if base_addr < 0:
            return -1
        return base_addr + (case_index * CASE_SIZE)
    else:
        max_cases = OFF_CASE_COUNTS.get(input_number, 0)
        if max_cases == 0 or case_index < 0 or case_index >= max_cases:
            return -1
        base_addr = OFF_CASE_OFFSETS.get(input_number, -1)
        if base_addr < 0:
            return -1
        return base_addr + (case_index * CASE_SIZE)


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

def inputs_to_bitmask(input_numbers: List[int], require_security: bool = False, 
                      require_ignition: bool = False) -> bytes:
    """
    Convert a list of input numbers to an 8-byte bitmask.
    
    Input 1 = Byte 0, Bit 0
    Input 8 = Byte 0, Bit 7
    Input 9 = Byte 1, Bit 0
    ...
    Input 44 = Byte 5, Bit 3
    
    Special bits in Byte 5:
    - Bit 4 (0x10) = Security condition
    - Bit 5 (0x20) = Ignition condition
    """
    bitmask = [0] * 8
    
    for inp in input_numbers:
        if inp < 1 or inp > 44:  # Valid inputs 1-44
            continue
        byte_index = (inp - 1) // 8
        bit_index = (inp - 1) % 8
        if byte_index < 8:
            bitmask[byte_index] |= (1 << bit_index)
    
    # Set special condition bits in byte 5
    if require_security:
        bitmask[5] |= 0x10  # Bit 4 = Security
    if require_ignition:
        bitmask[5] |= 0x20  # Bit 5 = Ignition
    
    return bytes(bitmask)


def bitmask_to_inputs(bitmask: bytes) -> tuple:
    """
    Convert an 8-byte bitmask to a list of input numbers and special flags.
    Treats 0xFF bytes as empty/uninitialized (no inputs set).
    
    Returns:
        (input_list, require_security, require_ignition)
    """
    # Check if all bytes are 0xFF (uninitialized EEPROM)
    if all(b == 0xFF for b in bitmask):
        return ([], False, False)
    
    inputs = []
    require_security = False
    require_ignition = False
    
    for byte_index, byte_val in enumerate(bitmask):
        # Skip 0xFF bytes - likely uninitialized
        if byte_val == 0xFF:
            continue
            
        # Check special bits in byte 5
        if byte_index == 5:
            require_security = bool(byte_val & 0x10)  # Bit 4
            require_ignition = bool(byte_val & 0x20)  # Bit 5
            # Clear these bits before checking input bits
            byte_val &= ~0x30
        
        for bit_index in range(8):
            if byte_val & (1 << bit_index):
                input_num = byte_index * 8 + bit_index + 1
                # Only include valid input numbers (1-44)
                if 1 <= input_num <= 44:
                    inputs.append(input_num)
    
    return (inputs, require_security, require_ignition)


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


def encode_timer_byte(value: int, track_input: bool, scale_10s: bool) -> int:
    """
    Encode a timer/delay byte with control bits.
    
    Args:
        value: Timer value (0-63)
        track_input: True = Track Input mode, False = Fire-and-Forget mode
        scale_10s: True = 10s increments, False = 0.25s increments
    
    Returns:
        Encoded byte with structure:
        - Bit 0: Execution mode (0 = Fire-and-Forget, 1 = Track Input)
        - Bit 1: Scale (0 = 0.25s, 1 = 10s)
        - Bits 2-7: Timer value (0-63)
    """
    byte_val = 0
    
    if track_input:
        byte_val |= TimerBits.EXECUTION_MODE_MASK  # Bit 0
    
    if scale_10s:
        byte_val |= TimerBits.SCALE_MASK  # Bit 1
    
    # Clamp value to 0-63 and shift to bits 2-7
    clamped_value = min(63, max(0, value))
    byte_val |= (clamped_value << TimerBits.VALUE_SHIFT)
    
    return byte_val


def decode_timer_byte(byte_val: int) -> Tuple[int, bool, bool]:
    """
    Decode a timer/delay byte into its components.
    
    Args:
        byte_val: The encoded timer byte
    
    Returns:
        (value, track_input, scale_10s) tuple:
        - value: Timer value (0-63)
        - track_input: True if Track Input mode, False if Fire-and-Forget
        - scale_10s: True if 10s increments, False if 0.25s increments
    """
    # Handle uninitialized EEPROM
    if byte_val == 0xFF:
        return (0, False, False)
    
    track_input = bool(byte_val & TimerBits.EXECUTION_MODE_MASK)
    scale_10s = bool(byte_val & TimerBits.SCALE_MASK)
    value = (byte_val & TimerBits.VALUE_MASK) >> TimerBits.VALUE_SHIFT
    
    return (value, track_input, scale_10s)


def calculate_timer_duration_seconds(value: int, scale_10s: bool) -> float:
    """
    Calculate the actual timer duration in seconds.
    
    Args:
        value: Timer value (0-63)
        scale_10s: True = 10s increments, False = 0.25s increments
    
    Returns:
        Duration in seconds
    """
    if scale_10s:
        return value * 10.0  # Max = 63 * 10 = 630 seconds (10.5 minutes)
    else:
        return value * 0.25  # Max = 63 * 0.25 = 15.75 seconds


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
        if getattr(case, 'set_ignition', False):
            config_byte |= ConfigBits.TRACK_IGNITION
        if getattr(case, 'can_be_overridden', False):
            config_byte |= ConfigBits.CAN_BE_OVERRIDDEN
        case_bytes[CaseOffset.CONFIG_BYTE] = config_byte
        
        # Byte 5: Timer On
        # Bit 0: Execution mode (0=Fire-and-Forget, 1=Track Input)
        # Bit 1: Scale (0=0.25s, 1=10s)
        # Bits 2-7: Timer value (0-63)
        track_input = getattr(case, 'timer_execution_mode', 'fire_and_forget') == 'track_input'
        timer_on_value = getattr(case, 'timer_on_value', 0)
        timer_on_scale_10s = getattr(case, 'timer_on_scale_10s', False)
        case_bytes[CaseOffset.TIMER_ON] = encode_timer_byte(timer_on_value, track_input, timer_on_scale_10s)
        
        # Byte 6: Timer Delay (same bit structure as Timer On)
        # Note: Execution mode (bit 0) must match Timer On per spec
        timer_delay_value = getattr(case, 'timer_delay_value', 0)
        timer_delay_scale_10s = getattr(case, 'timer_delay_scale_10s', False)
        case_bytes[CaseOffset.TIMER_DELAY] = encode_timer_byte(timer_delay_value, track_input, timer_delay_scale_10s)
        
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
        
        # Bytes 8-15: must_be_on bitmask (includes ignition/security flags for "ON" condition)
        # Security bit = case requires security ENABLED
        # Ignition bit = case requires ignition ON
        must_on_mask = inputs_to_bitmask(
            case.must_be_on,
            require_security=getattr(case, 'require_security_on', False),
            require_ignition=getattr(case, 'require_ignition_on', False)
        )
        case_bytes[CaseOffset.MUST_BE_ON_START:CaseOffset.MUST_BE_ON_START + 8] = must_on_mask
        
        # Bytes 16-23: must_be_off bitmask (includes ignition/security flags for "OFF" condition)
        # Security bit = case requires security DISABLED
        # Ignition bit = case requires ignition OFF
        must_off_mask = inputs_to_bitmask(
            case.must_be_off,
            require_security=getattr(case, 'require_security_off', False),
            require_ignition=getattr(case, 'require_ignition_off', False)
        )
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


def generate_full_config_read_operations(max_address: int = 4096) -> List[ReadOperation]:
    """
    Generate read operations for EEPROM configuration.
    
    Args:
        max_address: Maximum address to read (default 4096 = 4KB EEPROM)
    """
    operations = []
    
    # Read all addresses up to max_address
    for addr in range(max_address):
        desc = f"Address 0x{addr:04X}"
        if addr < CASE_DATA_START:
            desc = f"System 0x{addr:04X}"
        else:
            input_offset = addr - CASE_DATA_START
            input_num = input_offset // BYTES_PER_INPUT + 1
            if input_num <= TOTAL_INPUTS:
                case_offset = input_offset % BYTES_PER_INPUT
                case_num = case_offset // CASE_SIZE
                desc = f"IN{input_num:02d} Case{case_num}"
        
        operations.append(ReadOperation(address=addr, description=desc))
    
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
    
    # Check if case is empty
    pgn_high = case_bytes[CaseOffset.PGN_HIGH]
    pgn_low = case_bytes[CaseOffset.PGN_LOW]
    
    # Empty if PGN is 0x0000 (cleared) or 0xFFFF (uninitialized EEPROM)
    if (pgn_high == 0 and pgn_low == 0) or (pgn_high == 0xFF and pgn_low == 0xFF):
        return CaseConfig(enabled=False)
    
    # Also check if all bytes are 0xFF (completely uninitialized)
    if all(b == 0xFF for b in case_bytes):
        return CaseConfig(enabled=False)
    
    config = CaseConfig(enabled=True)
    
    # Parse config byte
    config_byte = case_bytes[CaseOffset.CONFIG_BYTE]
    
    # Check mode (bits 4-5): 0x10 = one-button start (toggle)
    if (config_byte & ConfigBits.MODE_MASK) == ConfigBits.ONE_BUTTON_START:
        config.mode = 'toggle'
    else:
        config.mode = 'track'
    
    # Check track ignition flag (bit 0): 0x01 = track ignition
    config.set_ignition = bool(config_byte & ConfigBits.TRACK_IGNITION)
    
    # Check can be overridden flag (bit 2): 0x04 = can be overridden
    config.can_be_overridden = bool(config_byte & ConfigBits.CAN_BE_OVERRIDDEN)
    
    # Parse Timer On (byte 5)
    # Bit 0: Execution mode (0=Fire-and-Forget, 1=Track Input)
    # Bit 1: Scale (0=0.25s, 1=10s)
    # Bits 2-7: Timer value (0-63)
    timer_on_byte = case_bytes[CaseOffset.TIMER_ON]
    timer_on_value, track_input_on, timer_on_scale_10s = decode_timer_byte(timer_on_byte)
    config.timer_on_value = timer_on_value
    config.timer_on_scale_10s = timer_on_scale_10s
    config.timer_execution_mode = 'track_input' if track_input_on else 'fire_and_forget'
    
    # Parse Timer Delay (byte 6) - same structure as Timer On
    timer_delay_byte = case_bytes[CaseOffset.TIMER_DELAY]
    timer_delay_value, _, timer_delay_scale_10s = decode_timer_byte(timer_delay_byte)
    config.timer_delay_value = timer_delay_value
    config.timer_delay_scale_10s = timer_delay_scale_10s
    # Note: Execution mode is shared between timer and delay, we use value from timer_on
    
    # Parse pattern timing (byte 7: high nibble=ON, low nibble=OFF, 250ms units)
    timing = case_bytes[CaseOffset.PATTERN_TIMING]
    config.pattern_on_time, config.pattern_off_time = decode_pattern_timing(timing)
    
    # Parse must_be_on (includes security/ignition flags for "ON" conditions)
    must_on_bytes = case_bytes[CaseOffset.MUST_BE_ON_START:CaseOffset.MUST_BE_ON_START + 8]
    inputs_on, require_security_on, require_ignition_on = bitmask_to_inputs(must_on_bytes)
    config.must_be_on = inputs_on
    config.require_security_on = require_security_on  # Security must be ENABLED
    config.require_ignition_on = require_ignition_on  # Ignition must be ON
    
    # Parse must_be_off (includes security/ignition flags for "OFF" conditions)
    must_off_bytes = case_bytes[CaseOffset.MUST_BE_OFF_START:CaseOffset.MUST_BE_OFF_START + 8]
    inputs_off, require_security_off, require_ignition_off = bitmask_to_inputs(must_off_bytes)
    config.must_be_off = inputs_off
    config.require_security_off = require_security_off  # Security must be DISABLED
    config.require_ignition_off = require_ignition_off  # Ignition must be OFF
    
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
    
    Powercell message format:
    Byte 0: Outputs 1-8 track (bit 7=out1, bit 0=out8)
    Byte 1: Outputs 9-10 track (bits 7-6), Soft-start 1-6 (bits 5-0)
    Byte 2: Soft-start 7-10 (bits 3-0), PWM enable 1-4 (bits 7-4)
    Byte 3: PWM enable 5-8 (bits 3-0)
    Bytes 4-7: PWM duty cycles (high nibble=odd output, low nibble=even output)
    
    inMotion message format:
    Bytes 0-7: Each byte controls one output
    Bit 0 = modifier (1=change output)
    Bits 2-3 = personality (00=OFF, 01/10=ON, 11=Express)
    """
    outputs = {}
    
    if device.device_type == "powercell":
        # Byte 0: Track outputs 1-8 (bit 7 = output 1, bit 0 = output 8)
        track_byte = can_data[0]
        for out_num in range(1, 9):
            bit_pos = 8 - out_num  # output 1 = bit 7, output 8 = bit 0
            if track_byte & (1 << bit_pos):
                outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.TRACK)
        
        # Byte 1: Outputs 9-10 track (bits 7-6), Soft-start 1-6 (bits 5-0)
        byte1 = can_data[1]
        # Output 9 = bit 7, Output 10 = bit 6
        if byte1 & 0x80:
            outputs[9] = OutputConfig(enabled=True, mode=OutputMode.TRACK)
        if byte1 & 0x40:
            outputs[10] = OutputConfig(enabled=True, mode=OutputMode.TRACK)
        
        # Soft-start 1-6 in bits 5-0 (bit 5 = output 1 soft-start)
        for out_num in range(1, 7):
            bit_pos = 6 - out_num  # output 1 = bit 5, output 6 = bit 0
            if byte1 & (1 << bit_pos):
                if out_num not in outputs:  # Don't override track
                    outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.SOFT_START)
        
        # Byte 2: Soft-start 7-10 (bits 7-4), PWM enable 1-4 (bits 3-0)
        byte2 = can_data[2]
        # Soft-start 7-10 in bits 7-4 (bit 7 = output 7, bit 4 = output 10)
        for out_num in range(7, 11):
            bit_pos = 14 - out_num  # output 7 = bit 7, output 10 = bit 4
            if byte2 & (1 << bit_pos):
                if out_num not in outputs:
                    outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.SOFT_START)
        
        # PWM enable 1-4 in bits 3-0 (bit 3 = output 1, bit 0 = output 4)
        for out_num in range(1, 5):
            bit_pos = 4 - out_num  # output 1 = bit 3, output 4 = bit 0
            if byte2 & (1 << bit_pos):
                if out_num not in outputs:
                    outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.PWM, pwm_duty=0)
        
        # Byte 3: PWM enable 5-8 (bits 7-4)
        byte3 = can_data[3]
        for out_num in range(5, 9):
            bit_pos = 12 - out_num  # output 5 = bit 7, output 8 = bit 4
            if byte3 & (1 << bit_pos):
                if out_num not in outputs:
                    outputs[out_num] = OutputConfig(enabled=True, mode=OutputMode.PWM, pwm_duty=0)
        
        # Bytes 4-7: PWM duty cycles
        # Byte 4: output 1 high nibble, output 2 low nibble
        # Byte 5: output 3 high nibble, output 4 low nibble
        # etc.
        for byte_idx in range(4, 8):
            out_odd = (byte_idx - 4) * 2 + 1   # outputs 1, 3, 5, 7
            out_even = (byte_idx - 4) * 2 + 2  # outputs 2, 4, 6, 8
            if out_odd in outputs and outputs[out_odd].mode == OutputMode.PWM:
                outputs[out_odd].pwm_duty = (can_data[byte_idx] >> 4) & 0x0F
            if out_even in outputs and outputs[out_even].mode == OutputMode.PWM:
                outputs[out_even].pwm_duty = can_data[byte_idx] & 0x0F
    
    else:  # inMotion
        # Each byte controls one output
        # Bit 0 = modifier (must be 1 to change), Bits 2-3 = personality
        for i in range(min(8, len(device.outputs))):
            byte_val = can_data[i] if i < len(can_data) else 0
            modifier = byte_val & 0x01
            personality = (byte_val >> 2) & 0x03
            
            if modifier and personality in (0x01, 0x02, 0x03):  # ON or Express
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


def decode_raw_eeprom_to_config(raw_data: Dict[int, int]) -> FullConfiguration:
    """
    Decode raw EEPROM address->value dict into a FullConfiguration.
    
    Args:
        raw_data: Dict mapping EEPROM address (int) to byte value (int)
    
    Returns:
        FullConfiguration object with decoded data
    """
    config = FullConfiguration()
    
    # Parse system configuration (addresses 0x00-0x1A)
    system_bytes = bytearray(0x1B)
    for addr in range(0x1B):
        if addr in raw_data:
            system_bytes[addr] = raw_data[addr]
    config.system = parse_system_bytes(bytes(system_bytes))
    
    max_addr = max(raw_data.keys(), default=0)
    
    # Parse each input's cases
    for input_num in range(1, TOTAL_INPUTS + 1):
        input_config = InputConfig(input_number=input_num)
        
        # Parse ON cases (variable count per input)
        on_case_count = ON_CASE_COUNTS.get(input_num, 0)
        for case_idx in range(min(on_case_count, 8)):  # Max 8 ON cases in UI
            case_addr = get_case_address(input_num, is_on_case=True, case_index=case_idx)
            
            if case_addr < 0 or case_addr + 32 > max_addr + 1:
                continue
            
            # Extract 32 bytes for this case
            case_bytes = bytearray(32)
            for offset in range(32):
                addr = case_addr + offset
                if addr in raw_data:
                    case_bytes[offset] = raw_data[addr]
            
            parsed_case = parse_case_bytes(bytes(case_bytes))
            if parsed_case:
                input_config.on_cases[case_idx] = parsed_case
        
        # Parse OFF cases (variable count per input)
        off_case_count = OFF_CASE_COUNTS.get(input_num, 0)
        for case_idx in range(min(off_case_count, 2)):  # Max 2 OFF cases in UI
            case_addr = get_case_address(input_num, is_on_case=False, case_index=case_idx)
            
            if case_addr < 0 or case_addr + 32 > max_addr + 1:
                continue
            
            case_bytes = bytearray(32)
            for offset in range(32):
                addr = case_addr + offset
                if addr in raw_data:
                    case_bytes[offset] = raw_data[addr]
            
            parsed_case = parse_case_bytes(bytes(case_bytes))
            if parsed_case:
                input_config.off_cases[case_idx] = parsed_case
        
        config.inputs[input_num - 1] = input_config
    
    return config

