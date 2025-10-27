#!/usr/bin/env python3
"""
Setup verification script.
Checks if all required dependencies and tools are available.
"""
import sys
import subprocess
import importlib.util

def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False

def check_command(cmd, name=None):
    """Check if a command-line tool is available."""
    if name is None:
        name = cmd
    
    try:
        result = subprocess.run([cmd, "--version"], 
                              capture_output=True, 
                              timeout=5)
        if result.returncode == 0:
            print(f"✓ {name}")
            return True
        else:
            print(f"✗ {name} (not found in PATH)")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f"✗ {name} (not found in PATH)")
        return False

def main():
    print("=" * 60)
    print("Video Analyzer Setup Check")
    print("=" * 60)
    
    all_ok = True
    
    # Core requirements
    print("\n[Core Requirements]")
    all_ok &= check_python_version()
    all_ok &= check_command("node", "Node.js")
    all_ok &= check_command("npm")
    all_ok &= check_command("cargo", "Rust")
    all_ok &= check_command("ffmpeg", "FFmpeg")

    # Check directories
    print("\n[Directory Structure]")
    import os
    from pathlib import Path
    
    dirs = [
        "backend",
        "backend/protos",
        "backend/agents",
        "frontend",
        "frontend/src-tauri",
        "protos",
        "data"
    ]
    
    for d in dirs:
        if Path(d).exists():
            print(f"✓ {d}/")
        else:
            print(f"✗ {d}/ (missing)")
            all_ok = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ All core requirements met!")
        print("\nYou can run the simple chat server:")
        print("  python test_simple_server.py")
        print("\nThen start the frontend:")
        print("  cd frontend && npm run tauri dev")
    else:
        print("✗ Some core requirements are missing.")
        print("\nInstall missing dependencies:")
        print("  pip install grpcio grpcio-tools protobuf")

    print("=" * 60)
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
