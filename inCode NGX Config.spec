# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for inCode NGX Configuration Tool
Cross-platform configuration for macOS and Windows.
"""

import os
import sys
import platform

# Get the directory of this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# Determine platform
is_windows = platform.system() == 'Windows'
is_macos = platform.system() == 'Darwin'

# Data files to include
datas = [
    (os.path.join(spec_dir, 'resources', 'presets'), 'presets'),
]

# Icon file - use correct format per platform
if is_windows:
    icon_file = os.path.join(spec_dir, 'resources', 'icon.ico')
else:
    icon_file = os.path.join(spec_dir, 'resources', 'icon.icns')

# Hidden imports - include both POSIX and Windows serial port support
hiddenimports = [
    'PyQt6.QtWidgets',
    'PyQt6.QtCore', 
    'PyQt6.QtGui',
    'PyQt6.sip',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'serial.tools.list_ports_common',
]

# Add platform-specific serial imports
if is_windows:
    hiddenimports.append('serial.tools.list_ports_windows')
else:
    hiddenimports.append('serial.tools.list_ports_posix')

# Exclude PyQt6 modules we don't need to reduce size and avoid issues
excludes = [
    'PyQt6.QtBluetooth',
    'PyQt6.QtNfc',
    'PyQt6.QtWebEngine',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtPositioning',
    'PyQt6.QtLocation',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.Qt3DCore',
    'PyQt6.Qt3DRender',
    'PyQt6.Qt3DInput',
    'PyQt6.Qt3DLogic',
    'PyQt6.Qt3DAnimation',
    'PyQt6.Qt3DExtras',
    'PyQt6.QtQuick',
    'PyQt6.QtQuick3D',
    'PyQt6.QtQml',
    'PyQt6.QtQmlModels',
    'PyQt6.QtQuickWidgets',
    'PyQt6.QtDesigner',
    'PyQt6.QtHelp',
    'PyQt6.QtOpenGL',
    'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtPdf',
    'PyQt6.QtPdfWidgets',
    'PyQt6.QtSvg',
    'PyQt6.QtSvgWidgets',
    'PyQt6.QtTest',
    'PyQt6.QtXml',
    'PyQt6.QtNetwork',
    'PyQt6.QtSql',
    'PyQt6.QtRemoteObjects',
    'PyQt6.QtHttpServer',
    'PyQt6.QtSpatialAudio',
    'PyQt6.QtTextToSpeech',
    'PyQt6.QtWebChannel',
    'PyQt6.QtWebSockets',
]

# Add platform-specific excludes
if not is_macos:
    excludes.append('PyQt6.QtDBus')  # DBus is Unix/macOS only

a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# EXE options - platform aware
exe_options = {
    'name': 'inCode NGX Config',
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': False,
    'upx': False,
    'runtime_tmpdir': None,
    'console': False,
    'disable_windowed_traceback': False,
    'argv_emulation': False,
    'target_arch': None,
    'icon': icon_file,
}

# Add macOS-specific options
if is_macos:
    exe_options['codesign_identity'] = '-'
    exe_options['entitlements_file'] = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    **exe_options,
)

# macOS app bundle (only on macOS)
if is_macos:
    app = BUNDLE(
        exe,
        name='inCode NGX Config.app',
        icon=icon_file,
        bundle_identifier='com.infinitybox.incode-ngx-config',
        info_plist={
            'CFBundleName': 'inCode NGX Config',
            'CFBundleDisplayName': 'inCode NGX Configuration Tool',
            'CFBundleVersion': '0.1.1',
            'CFBundleShortVersionString': '0.1.1-alpha.6',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13.0',
        },
    )
