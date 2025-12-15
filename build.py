#!/usr/bin/env python3
"""
Build script for creating executables for Windows and macOS.
Uses PyInstaller to create standalone executables.
"""

import os
import sys
import subprocess
import platform

def build():
    """Build the executable for the current platform."""
    
    app_name = "inCode NGX Config"
    main_script = "incode_ngx_config.py"
    
    # Common PyInstaller options
    common_opts = [
        "--name", app_name,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
    ]
    
    # Platform-specific options
    if platform.system() == "Darwin":  # macOS
        print("Building for macOS...")
        opts = common_opts + [
            "--osx-bundle-identifier", "com.incode.ngx-config",
        ]
    elif platform.system() == "Windows":
        print("Building for Windows...")
        opts = common_opts + [
            "--uac-admin",  # Request admin privileges if needed
        ]
    else:
        print(f"Building for {platform.system()}...")
        opts = common_opts
    
    # Build command
    cmd = [sys.executable, "-m", "PyInstaller"] + opts + [main_script]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ Build successful!")
        print(f"   Executable located in: dist/")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build()

