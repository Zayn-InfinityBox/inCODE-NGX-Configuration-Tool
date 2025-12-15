# inCode NGX Configuration Tool

A Python-based desktop application for configuring MasterCell devices via CAN bus using the GridConnect CANUSB COM FD (USB to CAN FD converter).

## Features

- **Cross-Platform**: Works on Windows and macOS
- **Easy Connection**: Auto-detects available COM ports
- **CAN Configuration**: Set bitrate (default 250 kbps for Classic CAN)
- **Message Sending**: Send standard (11-bit) and extended (29-bit) CAN frames
- **Raw Commands**: Send raw ASCII commands directly to the adapter
- **Real-time Logging**: View all TX/RX communication with timestamps

## Requirements

- Python 3.9+
- GridConnect CANUSB COM FD (USB-A or USB-C version)
- PyQt6
- pyserial

## Installation

### From Source

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python incode_ngx_config.py
```

### Building Executables

To create a standalone executable:

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Run the build script
python build.py
```

The executable will be created in the `dist/` folder.

## Usage

### Connecting to the Device

1. Connect your GridConnect CANUSB COM FD to your computer via USB
2. Launch the application
3. Click **Refresh** to scan for available COM ports
4. Select the correct COM port from the dropdown
5. Click **Connect**

### Configuring CAN

1. Select the desired CAN bitrate (default: 250 kbps)
2. Click **Configure CAN** to set the bitrate
3. Click **Open CAN Channel** to start CAN communication

### Sending CAN Messages

1. Enter the CAN ID in hexadecimal (e.g., `123` for standard, `1ABCDEF0` for extended)
2. Toggle between Standard (11-bit) and Extended (29-bit) ID types
3. Set the data length (0-8 bytes)
4. Enter the data bytes in hexadecimal, separated by spaces (e.g., `01 02 03 04`)
5. Click **Send CAN Message**

### Raw Commands

You can send raw ASCII commands directly using the "Raw ASCII Command" field. Some common commands:

| Command | Description |
|---------|-------------|
| `V` | Get firmware version |
| `N` | Get serial number |
| `S5` | Set bitrate to 250 kbps |
| `O` | Open CAN channel |
| `C` | Close CAN channel |
| `t1230801020304050607` | Send standard frame (ID=123, 8 bytes) |

## CAN Bitrate Settings

| Setting | Speed |
|---------|-------|
| S0 | 10 kbps |
| S1 | 20 kbps |
| S2 | 50 kbps |
| S3 | 100 kbps |
| S4 | 125 kbps |
| S5 | 250 kbps |
| S6 | 500 kbps |
| S7 | 800 kbps |
| S8 | 1 Mbps |

## Hardware Setup

### CANUSB COM FD Pinout (DB9 Connector)

| Pin | Signal |
|-----|--------|
| 2 | CAN_L |
| 3 | CAN_GND |
| 7 | CAN_H |

### Connection Notes

- Ensure proper CAN bus termination (120Ω resistors at each end of the bus)
- The device provides 3750 Vrms / 1500 VDC isolation
- Power is supplied via USB (no external power needed)

## Troubleshooting

### No COM ports detected
- Make sure the CANUSB COM FD is connected
- On Windows, you may need to install the drivers (available from GridConnect website)
- On macOS/Linux, the device should be detected automatically as a virtual COM port

### Connection errors
- Try a different USB port
- Check if another application is using the COM port
- Restart the application

### No CAN messages received
- Ensure the CAN channel is opened (`O` command)
- Verify the correct bitrate is set
- Check CAN bus wiring and termination

## License

This software is provided as-is for use with inCode MasterCell configuration.

## Support

For hardware support, contact GridConnect:
- Phone: +1 (800) 975-4743 (USA Toll Free)
- Website: https://www.gridconnect.com

