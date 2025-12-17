#!/usr/bin/env python3
"""
Build script for creating executables for Windows and macOS.
Uses PyInstaller to create standalone executables.
"""

import os
import sys
import subprocess
import platform
import shutil

def build():
    """Build the executable for the current platform."""
    
    app_name = "inCode NGX Config"
    spec_file = "inCode NGX Config.spec"
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"\n📦 Building {app_name}...")
    print(f"   Platform: {platform.system()}")
    print(f"   Using spec file: {spec_file}")
    
    # Clean previous build
    print("\n🧹 Cleaning previous build...")
    for folder in ["dist", "build"]:
        path = os.path.join(script_dir, folder)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"   Removed: {folder}/")
    
    # Build command using spec file
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec_file]
    
    print(f"\n🔨 Running PyInstaller...")
    result = subprocess.run(cmd, cwd=script_dir)
    
    if result.returncode != 0:
        print("\n❌ Build failed!")
        sys.exit(1)
    
    # macOS-specific post-processing
    if platform.system() == "Darwin":
        app_path = os.path.join(script_dir, "dist", f"{app_name}.app")
        
        if os.path.exists(app_path):
            print(f"\n🔐 Fixing macOS code signing...")
            
            # Remove extended attributes
            subprocess.run(["xattr", "-cr", app_path], cwd=script_dir)
            
            # Re-sign with ad-hoc signature
            result = subprocess.run(
                ["codesign", "--force", "--deep", "--sign", "-", app_path],
                cwd=script_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("   ✅ Code signing successful")
            else:
                print(f"   ⚠️  Code signing warning: {result.stderr}")
            
            print(f"\n✅ Build successful!")
            print(f"   App bundle: dist/{app_name}.app")
            print(f"\n💡 To run:")
            print(f"   • Double-click the app in Finder")
            print(f"   • Or from terminal: open 'dist/{app_name}.app'")
            print(f"\n⚠️  If macOS blocks the app:")
            print(f"   • Right-click the app and select 'Open'")
            print(f"   • Or go to System Preferences → Security & Privacy → Open Anyway")
        else:
            print(f"\n❌ App bundle not found at: {app_path}")
            sys.exit(1)
    
    elif platform.system() == "Windows":
        exe_path = os.path.join(script_dir, "dist", f"{app_name}.exe")
        if os.path.exists(exe_path):
            print(f"\n✅ Build successful!")
            print(f"   Executable: dist/{app_name}.exe")
        else:
            print(f"\n❌ Executable not found")
            sys.exit(1)
    
    else:
        print(f"\n✅ Build successful!")
        print(f"   Check the dist/ folder for output")

if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build()
