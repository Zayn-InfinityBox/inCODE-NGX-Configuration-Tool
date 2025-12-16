"""
can_interface.py - CAN/Serial communication interface for GridConnect CANUSB COM FD

Handles serial port communication using GridConnect ASCII protocol.
"""

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QWaitCondition
from typing import Optional, List, Tuple
import time
import re
from dataclasses import dataclass

from config_data import (
    EEPROM_GUARD_BYTE, EEPROM_STATUS_SUCCESS,
    SA_MASTERCELL, PGN_EEPROM_WRITE, PGN_EEPROM_READ, PGN_EEPROM_RESPONSE
)

# Import EEPROM protocol for advanced operations
from eeprom_protocol import (
    WriteOperation, ReadOperation, EEPROMResponse, ResponseStatus,
    generate_full_config_write_operations, generate_full_config_read_operations,
    generate_system_read_operations, generate_input_read_operations,
    CASE_DATA_START, CASE_SIZE, CASES_PER_INPUT, BYTES_PER_INPUT, TOTAL_INPUTS,
    SystemAddress
)

# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CANMessage:
    """Represents a CAN message"""
    can_id: int
    extended: bool
    data: bytes
    timestamp: float = 0.0
    
    @property
    def priority(self) -> int:
        """Extract J1939 priority (bits 28-26)"""
        return (self.can_id >> 26) & 0x07
    
    @property
    def pgn(self) -> int:
        """Extract J1939 PGN"""
        pf = (self.can_id >> 16) & 0xFF
        ps = (self.can_id >> 8) & 0xFF
        dp = (self.can_id >> 24) & 0x01
        if pf >= 240:  # PDU2
            return (dp << 16) | (pf << 8) | ps
        else:  # PDU1
            return (dp << 16) | (pf << 8)
    
    @property
    def source_address(self) -> int:
        """Extract J1939 source address"""
        return self.can_id & 0xFF
    
    def to_gridconnect(self) -> str:
        """Convert to GridConnect ASCII format"""
        if self.extended:
            can_id_str = f"{self.can_id:08X}"
            prefix = "X"
        else:
            can_id_str = f"{self.can_id:03X}"
            prefix = "S"
        
        data_str = ''.join(f"{b:02X}" for b in self.data)
        return f":{prefix}{can_id_str}N{data_str};"
    
    @classmethod
    def from_gridconnect(cls, msg: str) -> Optional['CANMessage']:
        """Parse GridConnect ASCII format message"""
        msg = msg.strip()
        if not msg.startswith(':') or not msg.endswith(';'):
            return None
        
        msg = msg[1:-1]  # Remove : and ;
        
        if msg.startswith('X'):  # Extended ID
            extended = True
            msg = msg[1:]
            # Find the N or R separator
            if 'N' in msg:
                id_str, data_str = msg.split('N', 1)
            elif 'R' in msg:
                id_str, data_str = msg.split('R', 1)
            else:
                return None
            try:
                can_id = int(id_str, 16)
            except ValueError:
                return None
        elif msg.startswith('S'):  # Standard ID
            extended = False
            msg = msg[1:]
            if 'N' in msg:
                id_str, data_str = msg.split('N', 1)
            elif 'R' in msg:
                id_str, data_str = msg.split('R', 1)
            else:
                return None
            try:
                can_id = int(id_str, 16)
            except ValueError:
                return None
        else:
            return None
        
        # Parse data bytes
        data = bytes()
        if data_str:
            try:
                data = bytes.fromhex(data_str)
            except ValueError:
                return None
        
        return cls(can_id=can_id, extended=extended, data=data, timestamp=time.time())


# =============================================================================
# Serial Worker Thread
# =============================================================================

class SerialWorker(QThread):
    """Background thread for serial communication"""
    
    # Signals
    message_received = pyqtSignal(CANMessage)
    raw_data_received = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    eeprom_response = pyqtSignal(int, int, int)  # address, value, status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port: Optional[serial.Serial] = None
        self.running = False
        self.rx_buffer = ""
        self.mutex = QMutex()
        
    def connect_port(self, port: str, baudrate: int = 115200) -> bool:
        """Connect to serial port"""
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
                write_timeout=1.0
            )
            self.running = True
            self.connection_changed.emit(True)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {str(e)}")
            return False
    
    def disconnect_port(self):
        """Disconnect from serial port"""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.serial_port = None
        self.connection_changed.emit(False)
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.serial_port is not None and self.serial_port.is_open
    
    def send_raw(self, data: str) -> bool:
        """Send raw string data"""
        if not self.is_connected():
            return False
        try:
            self.serial_port.write(data.encode('ascii'))
            return True
        except Exception as e:
            self.error_occurred.emit(f"Send failed: {str(e)}")
            return False
    
    def send_can_message(self, msg: CANMessage) -> bool:
        """Send CAN message in GridConnect format"""
        return self.send_raw(msg.to_gridconnect())
    
    def run(self):
        """Main thread loop - reads incoming data"""
        while self.running:
            if not self.is_connected():
                self.msleep(100)
                continue
            
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        text = data.decode('ascii', errors='replace')
                        self.rx_buffer += text
                        self._process_buffer()
            except Exception as e:
                if self.running:
                    self.error_occurred.emit(f"Read error: {str(e)}")
                    self.disconnect_port()
                break
            
            self.msleep(10)
    
    def _process_buffer(self):
        """Process received data buffer for complete messages"""
        while ';' in self.rx_buffer:
            # Find message boundaries
            start_idx = self.rx_buffer.find(':')
            end_idx = self.rx_buffer.find(';')
            
            if start_idx == -1 or end_idx == -1:
                break
            
            if start_idx > end_idx:
                # Discard garbage before start
                self.rx_buffer = self.rx_buffer[end_idx + 1:]
                continue
            
            # Extract complete message
            msg_str = self.rx_buffer[start_idx:end_idx + 1]
            self.rx_buffer = self.rx_buffer[end_idx + 1:]
            
            # Emit raw data
            self.raw_data_received.emit(msg_str)
            
            # Parse message
            msg = CANMessage.from_gridconnect(msg_str)
            if msg:
                self.message_received.emit(msg)
                
                # Check for EEPROM response
                if msg.extended and msg.pgn == PGN_EEPROM_RESPONSE:
                    if len(msg.data) >= 6:
                        value = msg.data[2]
                        addr_lsb = msg.data[3]
                        addr_msb = msg.data[4]
                        status = msg.data[5]
                        address = addr_lsb | (addr_msb << 8)
                        self.eeprom_response.emit(address, value, status)


# =============================================================================
# CAN Interface Manager
# =============================================================================

class CANInterface(QObject):
    """High-level CAN interface manager"""
    
    # Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_status_changed = pyqtSignal(bool)  # For connection page
    message_received = pyqtSignal(CANMessage)
    frame_received = pyqtSignal(int, list)  # can_id, data list - simplified for UI
    raw_received = pyqtSignal(str)
    error = pyqtSignal(str)
    eeprom_read_complete = pyqtSignal(int, int)  # address, value
    eeprom_write_complete = pyqtSignal(int, bool)  # address, success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = SerialWorker()
        self.worker.message_received.connect(self._on_message)
        self.worker.raw_data_received.connect(self.raw_received)
        self.worker.connection_changed.connect(self._on_connection_changed)
        self.worker.error_occurred.connect(self.error)
        self.worker.eeprom_response.connect(self._on_eeprom_response)
        
        self._pending_eeprom_ops = {}  # address -> (operation, callback)
        self._target_sa = 0x80  # Default target source address
        self._write_pgn = PGN_EEPROM_WRITE
        self._read_pgn = PGN_EEPROM_READ
    
    def scan_ports(self) -> List[str]:
        """Scan and return list of available serial port names"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return sorted(ports)
    
    @staticmethod
    def list_ports() -> List[Tuple[str, str]]:
        """List available serial ports"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append((port.device, port.description))
        return ports
    
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """Connect to device"""
        if self.worker.connect_port(port, baudrate):
            self.worker.start()
            return True
        return False
    
    def disconnect(self):
        """Disconnect from device"""
        self.worker.disconnect_port()
        self.worker.wait(1000)
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self.worker.is_connected()
    
    def set_target_device(self, source_address: int, 
                          write_pgn: int = PGN_EEPROM_WRITE,
                          read_pgn: int = PGN_EEPROM_READ):
        """Set target device for EEPROM operations"""
        self._target_sa = source_address
        self._write_pgn = write_pgn
        self._read_pgn = read_pgn
    
    def send_message(self, can_id: int, data: bytes, extended: bool = True) -> bool:
        """Send a CAN message"""
        msg = CANMessage(can_id=can_id, extended=extended, data=data)
        return self.worker.send_can_message(msg)
    
    def send_j1939(self, priority: int, pgn: int, sa: int, data: bytes) -> bool:
        """Send J1939 message"""
        # Construct 29-bit CAN ID
        pf = (pgn >> 8) & 0xFF
        ps = pgn & 0xFF
        dp = (pgn >> 16) & 0x01
        
        can_id = ((priority & 0x07) << 26) | (dp << 24) | (pf << 16) | (ps << 8) | (sa & 0xFF)
        return self.send_message(can_id, data, extended=True)
    
    def write_eeprom(self, address: int, value: int) -> bool:
        """Write single byte to EEPROM"""
        if not self.is_connected():
            return False
        
        # Construct write request
        addr_lsb = address & 0xFF
        addr_msb = (address >> 8) & 0xFF
        data = bytes([
            EEPROM_GUARD_BYTE,  # Guard byte
            addr_lsb,
            addr_msb,
            value,
            0xFF, 0xFF, 0xFF, 0xFF  # Padding
        ])
        
        # Track pending operation
        self._pending_eeprom_ops[address] = ('write', value)
        
        # Send on write PGN with default priority 3
        return self.send_j1939(3, self._write_pgn, self._target_sa, data)
    
    def read_eeprom(self, address: int) -> bool:
        """Read single byte from EEPROM"""
        if not self.is_connected():
            return False
        
        addr_lsb = address & 0xFF
        addr_msb = (address >> 8) & 0xFF
        data = bytes([
            EEPROM_GUARD_BYTE,
            addr_lsb,
            addr_msb,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF
        ])
        
        self._pending_eeprom_ops[address] = ('read', None)
        
        return self.send_j1939(3, self._read_pgn, self._target_sa, data)
    
    def _on_connection_changed(self, connected: bool):
        self.connection_status_changed.emit(connected)
        if connected:
            self.connected.emit()
        else:
            self.disconnected.emit()
    
    def _on_message(self, msg: CANMessage):
        self.message_received.emit(msg)
        # Also emit simplified signal for UI
        self.frame_received.emit(msg.can_id, list(msg.data))
    
    def _on_eeprom_response(self, address: int, value: int, status: int):
        """Handle EEPROM response"""
        if address in self._pending_eeprom_ops:
            op_type, expected = self._pending_eeprom_ops.pop(address)
            success = (status == EEPROM_STATUS_SUCCESS)
            
            if op_type == 'read':
                self.eeprom_read_complete.emit(address, value if success else -1)
            else:  # write
                self.eeprom_write_complete.emit(address, success)


# =============================================================================
# Utility Functions
# =============================================================================

def make_j1939_id(priority: int, pgn: int, sa: int) -> int:
    """Construct 29-bit J1939 CAN ID"""
    pf = (pgn >> 8) & 0xFF
    ps = pgn & 0xFF
    dp = (pgn >> 16) & 0x01
    return ((priority & 0x07) << 26) | (dp << 24) | (pf << 16) | (ps << 8) | (sa & 0xFF)


def parse_j1939_id(can_id: int) -> Tuple[int, int, int]:
    """Parse J1939 CAN ID into (priority, pgn, sa)"""
    priority = (can_id >> 26) & 0x07
    dp = (can_id >> 24) & 0x01
    pf = (can_id >> 16) & 0xFF
    ps = (can_id >> 8) & 0xFF
    sa = can_id & 0xFF
    
    if pf >= 240:
        pgn = (dp << 16) | (pf << 8) | ps
    else:
        pgn = (dp << 16) | (pf << 8)
    
    return priority, pgn, sa


# =============================================================================
# EEPROM Batch Operations Worker
# =============================================================================

class EEPROMWorker(QThread):
    """
    Background thread for batch EEPROM read/write operations.
    Handles the request/response protocol with proper timing.
    """
    
    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, description
    operation_complete = pyqtSignal(bool, str)  # success, message
    byte_read = pyqtSignal(int, int)  # address, value
    byte_written = pyqtSignal(int, bool)  # address, success
    
    def __init__(self, can_interface: 'CANInterface', parent=None):
        super().__init__(parent)
        self.can_interface = can_interface
        self.operations: List = []
        self.is_write = False
        self.running = False
        self.read_data: Dict[int, int] = {}  # address -> value
        
        # Timing parameters (milliseconds)
        self.inter_message_delay = 15  # 15ms between messages
        self.response_timeout = 200  # 200ms timeout for response
        self.retry_count = 3
        
        # Response tracking
        self._waiting_for_response = False
        self._response_address = -1
        self._response_received = False
        self._response_value = 0
        self._response_status = 0
    
    def set_operations(self, operations: List, is_write: bool = True):
        """Set the operations to perform"""
        self.operations = operations
        self.is_write = is_write
        self.read_data.clear()
    
    def stop(self):
        """Stop the operation"""
        self.running = False
    
    def on_eeprom_response(self, address: int, value: int, status: int):
        """Called when EEPROM response is received"""
        if self._waiting_for_response and address == self._response_address:
            self._response_value = value
            self._response_status = status
            self._response_received = True
    
    def run(self):
        """Execute all operations"""
        self.running = True
        total = len(self.operations)
        
        if total == 0:
            self.operation_complete.emit(True, "No operations to perform")
            return
        
        # Connect to EEPROM response signal
        self.can_interface.worker.eeprom_response.connect(self.on_eeprom_response)
        
        try:
            for i, op in enumerate(self.operations):
                if not self.running:
                    self.operation_complete.emit(False, "Operation cancelled")
                    return
                
                # Update progress
                desc = op.description if hasattr(op, 'description') else f"Address 0x{op.address:04X}"
                self.progress.emit(i + 1, total, desc)
                
                # Perform operation with retry
                success = False
                for retry in range(self.retry_count):
                    if self.is_write:
                        success = self._do_write(op)
                    else:
                        success = self._do_read(op)
                    
                    if success:
                        break
                    
                    # Wait before retry
                    self.msleep(50)
                
                if not success:
                    error_msg = f"Failed at address 0x{op.address:04X} after {self.retry_count} retries"
                    self.operation_complete.emit(False, error_msg)
                    return
                
                # Inter-message delay
                self.msleep(self.inter_message_delay)
            
            self.operation_complete.emit(True, f"Completed {total} operations")
        
        finally:
            # Disconnect signal
            try:
                self.can_interface.worker.eeprom_response.disconnect(self.on_eeprom_response)
            except:
                pass
    
    def _do_write(self, op: WriteOperation) -> bool:
        """Perform a single write operation"""
        self._waiting_for_response = True
        self._response_address = op.address
        self._response_received = False
        
        # Send write request
        if not self.can_interface.write_eeprom(op.address, op.value):
            self._waiting_for_response = False
            return False
        
        # Wait for response
        start_time = time.time()
        while not self._response_received:
            if (time.time() - start_time) * 1000 > self.response_timeout:
                self._waiting_for_response = False
                return False
            self.msleep(5)
        
        self._waiting_for_response = False
        success = self._response_status == EEPROM_STATUS_SUCCESS
        self.byte_written.emit(op.address, success)
        return success
    
    def _do_read(self, op: ReadOperation) -> bool:
        """Perform a single read operation"""
        self._waiting_for_response = True
        self._response_address = op.address
        self._response_received = False
        
        # Send read request
        if not self.can_interface.read_eeprom(op.address):
            self._waiting_for_response = False
            return False
        
        # Wait for response
        start_time = time.time()
        while not self._response_received:
            if (time.time() - start_time) * 1000 > self.response_timeout:
                self._waiting_for_response = False
                return False
            self.msleep(5)
        
        self._waiting_for_response = False
        
        if self._response_status == EEPROM_STATUS_SUCCESS:
            self.read_data[op.address] = self._response_value
            self.byte_read.emit(op.address, self._response_value)
            return True
        
        return False


# =============================================================================
# Configuration Read/Write Manager
# =============================================================================

class ConfigurationManager(QObject):
    """
    High-level manager for reading and writing full device configurations.
    """
    
    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, description
    read_complete = pyqtSignal(bool, dict)  # success, data_dict
    write_complete = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, can_interface: CANInterface, parent=None):
        super().__init__(parent)
        self.can_interface = can_interface
        self.worker: Optional[EEPROMWorker] = None
        self._operation_type = None
    
    def read_full_configuration(self):
        """
        Start reading the entire device configuration.
        Emits read_complete when done.
        """
        if self.worker and self.worker.isRunning():
            return
        
        # Generate read operations for entire config
        # Note: This is a LOT of bytes - ~14,000 for full config
        # For practical use, you may want to read only modified inputs
        operations = generate_full_config_read_operations()
        
        self.worker = EEPROMWorker(self.can_interface)
        self.worker.set_operations(operations, is_write=False)
        self.worker.progress.connect(self._on_progress)
        self.worker.operation_complete.connect(self._on_read_complete)
        self._operation_type = 'read'
        self.worker.start()
    
    def read_system_config(self):
        """Read only system configuration (much faster)"""
        if self.worker and self.worker.isRunning():
            return
        
        operations = generate_system_read_operations()
        
        self.worker = EEPROMWorker(self.can_interface)
        self.worker.set_operations(operations, is_write=False)
        self.worker.progress.connect(self._on_progress)
        self.worker.operation_complete.connect(self._on_read_complete)
        self._operation_type = 'read_system'
        self.worker.start()
    
    def read_input_config(self, input_number: int):
        """Read configuration for a single input"""
        if self.worker and self.worker.isRunning():
            return
        
        operations = generate_input_read_operations(input_number)
        
        self.worker = EEPROMWorker(self.can_interface)
        self.worker.set_operations(operations, is_write=False)
        self.worker.progress.connect(self._on_progress)
        self.worker.operation_complete.connect(self._on_read_complete)
        self._operation_type = f'read_input_{input_number}'
        self.worker.start()
    
    def write_configuration(self, config):
        """
        Write a FullConfiguration to the device.
        """
        if self.worker and self.worker.isRunning():
            return
        
        from config_data import FullConfiguration
        
        if not isinstance(config, FullConfiguration):
            self.write_complete.emit(False, "Invalid configuration object")
            return
        
        operations = generate_full_config_write_operations(config)
        
        self.worker = EEPROMWorker(self.can_interface)
        self.worker.set_operations(operations, is_write=True)
        self.worker.progress.connect(self._on_progress)
        self.worker.operation_complete.connect(self._on_write_complete)
        self._operation_type = 'write'
        self.worker.start()
    
    def cancel(self):
        """Cancel current operation"""
        if self.worker:
            self.worker.stop()
    
    def _on_progress(self, current: int, total: int, desc: str):
        self.progress.emit(current, total, desc)
    
    def _on_read_complete(self, success: bool, message: str):
        if self.worker:
            data = self.worker.read_data.copy() if success else {}
            self.read_complete.emit(success, data)
    
    def _on_write_complete(self, success: bool, message: str):
        self.write_complete.emit(success, message)

