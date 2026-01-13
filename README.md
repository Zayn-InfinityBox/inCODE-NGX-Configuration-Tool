# inCode NGX Configuration Tool

<p align="center">
  <img src="resources/icon.png" alt="Infinity Box Logo" width="120"/>
</p>

A professional desktop application for configuring **inCode NGX MasterCell** devices via CAN bus. Built with Python and PyQt6, designed for the GridConnect CANUSB COM FD adapter.

## Features

- **🔧 Complete Configuration** - Configure all 32 inputs with up to 5 ON cases and 5 OFF cases each
- **💡 Multi-Device Support** - Control outputs on Front PowerCell and Rear PowerCell simultaneously
- **📁 Template Presets** - Quick setup with Front Engine and Rear Engine configurations
- **🔒 View Modes** - Basic, Advanced, and Admin modes for different user skill levels
- **📤 Import/Export** - Save and load configurations as JSON files
- **⚡ Real-time Communication** - Read from and write to device EEPROM over CAN bus
- **🖥️ Cross-Platform** - Works on Windows and macOS

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
python main.py
```

### Pre-built Application (macOS)

1. Navigate to the `dist/` folder
2. Double-click `inCode NGX Config.app`
3. If macOS blocks the app, right-click and select "Open"

### Building from Source

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Run the build script
python build.py
```

The executable will be created in the `dist/` folder.

## Project Structure

```
inCode NGX Configuration Tool/
├── main.py                 # Application entry point
├── config_data.py          # Data models and configuration structures
├── can_interface.py        # CAN bus communication layer
├── eeprom_protocol.py      # EEPROM read/write protocol
├── styles.py               # UI styling and themes
├── view_mode.py            # View mode management
├── pages/                  # Wizard page components
│   ├── welcome_page.py
│   ├── connection_page.py
│   ├── inputs_page.py
│   ├── confirmation_page.py
│   └── write_page.py
├── widgets/                # Reusable UI widgets
├── resources/              # Application resources
│   ├── icon.png
│   ├── icon.icns
│   └── presets/            # Default configuration templates
├── build.py                # Build script for executables
└── requirements.txt        # Python dependencies
```

## Usage

### Quick Start

1. Connect your GridConnect CANUSB COM FD to your computer
2. Launch the application
3. Select a configuration template (Front Engine or Rear Engine) or load a saved file
4. Navigate through the wizard to configure inputs
5. Review your changes and write to the device

### View Modes

- **Basic Mode** - Simplified interface for common operations
- **Advanced Mode** - Full access to input/output configuration
- **Admin Mode** - Complete access including locked system inputs (password protected)

### Input Configuration

Each input supports:
- Up to 5 ON cases (triggered when input turns ON)
- Up to 5 OFF cases (triggered when input turns OFF)
- Multiple output assignments per case
- Output modes: Track, Soft Start, PWM
- Timer configurations (delay, fire-and-forget, one-shot)
- Ignition tracking and conditions

## Hardware Setup

### CANUSB COM FD Pinout (DB9 Connector)

| Pin | Signal |
|-----|--------|
| 2 | CAN_L |
| 3 | CAN_GND |
| 7 | CAN_H |

### Connection Notes

- Ensure proper CAN bus termination (120Ω resistors at each end)
- CAN bitrate: 250 kbps (Classic CAN)
- Power supplied via USB (no external power needed)

## Troubleshooting

### No COM ports detected
- Ensure the CANUSB COM FD is connected
- On Windows, install drivers from GridConnect website
- On macOS/Linux, detected automatically as virtual COM port

### Connection errors
- Try a different USB port
- Check if another application is using the COM port
- Restart the application

### Write failures
- Verify CAN bus wiring and termination
- Check that the device is powered and responding
- Try reading configuration first to verify communication

## Version

**v0.1.1-alpha.3**

## License

Copyright © 2026 Infinity Box. All rights reserved.

This software is provided for use with inCode NGX MasterCell devices.

## Support

For product support, contact Infinity Box.
