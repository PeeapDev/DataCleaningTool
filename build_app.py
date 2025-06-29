#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build script for creating distributable packages of the Education Data Cleaning Tool.
Creates standalone executables for Mac (.dmg) and Windows (.exe).
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

# Configuration
APP_NAME = "EducationDataCleaner"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "run.py"
ICON_PATH = os.path.join("resources", "icon.ico")  # Windows icon
MAC_ICON_PATH = os.path.join("resources", "icon.icns")  # Mac icon

# Ensure we have the required directories
def create_build_dirs():
    """Create necessary directories for the build process"""
    dirs = ["dist", "build", "resources"]
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

def build_windows():
    """Build Windows executable (.exe)"""
    print("Building Windows executable...")
    
    # PyInstaller command for Windows
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--windowed",  # GUI mode
        "--onefile",   # Single file executable
        f"--icon={ICON_PATH}" if os.path.exists(ICON_PATH) else "",
        "--add-data", "resources;resources",
        "--clean",  # Clean PyInstaller cache
        MAIN_SCRIPT
    ]
    
    # Run PyInstaller
    subprocess.run([arg for arg in cmd if arg != ""])
    
    print(f"Windows executable created at: dist/{APP_NAME}.exe")

def build_mac():
    """Build macOS application (.app and .dmg)"""
    print("Building macOS application...")
    
    # PyInstaller command for macOS
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--windowed",  # GUI mode
        "--onedir",    # Directory mode for Mac
        f"--icon={MAC_ICON_PATH}" if os.path.exists(MAC_ICON_PATH) else "",
        "--add-data", "resources:resources",
        "--clean",  # Clean PyInstaller cache
        MAIN_SCRIPT
    ]
    
    # Run PyInstaller
    subprocess.run([arg for arg in cmd if arg != ""])
    
    # Create DMG using create-dmg if available
    try:
        app_path = os.path.join("dist", f"{APP_NAME}.app")
        dmg_path = os.path.join("dist", f"{APP_NAME}-{APP_VERSION}.dmg")
        
        # Check if create-dmg is installed
        with open(os.devnull, "w") as devnull:
            if subprocess.call(["which", "create-dmg"], stdout=devnull, stderr=devnull) == 0:
                print("Creating DMG package...")
                
                dmg_cmd = [
                    "create-dmg",
                    "--volname", f"{APP_NAME} Installer",
                    "--volicon", MAC_ICON_PATH if os.path.exists(MAC_ICON_PATH) else "",
                    "--window-pos", "200", "100",
                    "--window-size", "800", "400",
                    "--icon-size", "100",
                    "--icon", f"{APP_NAME}.app", "200", "190",
                    "--hide-extension", f"{APP_NAME}.app",
                    "--app-drop-link", "600", "185",
                    dmg_path,
                    app_path
                ]
                
                subprocess.run([arg for arg in dmg_cmd if arg != ""])
                print(f"DMG package created at: {dmg_path}")
            else:
                print("create-dmg not found. Install it with 'brew install create-dmg' to create DMG files.")
                print(f"Application bundle created at: {app_path}")
    except Exception as e:
        print(f"Error creating DMG: {str(e)}")
        print(f"Application bundle created at: dist/{APP_NAME}.app")

def main():
    """Main entry point for the build script"""
    create_build_dirs()
    
    # Determine which build to run based on platform
    system = platform.system()
    if system == "Windows":
        build_windows()
    elif system == "Darwin":  # macOS
        build_mac()
    else:
        print(f"Building for {system} is not currently supported.")
        sys.exit(1)
    
    print("Build completed successfully!")
    print(f"Application version: {APP_VERSION}")
    print("Remember to test the packaged application before distribution!")

if __name__ == "__main__":
    main()
