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

def check_python_package(package_name, display_name=None):
    """Check if a Python package is installed."""
    if display_name is None:
        display_name = package_name
    
    spec = importlib.util.find_spec(package_name)
    if spec is not None:
        print(f"✓ {display_name}")
        return True
    else:
        print(f"✗ {display_name} (install with: pip install {package_name})")
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
    
    # Python packages - minimal
    print("\n[Minimal Python Packages - Required for Basic Chat]")
    all_ok &= check_python_package("grpc", "grpcio")
    all_ok &= check_python_package("google.protobuf", "protobuf")
    
    # Python packages - full ML
    print("\n[Full ML Python Packages - Optional for AI Features]")
    ml_ok = True
    ml_ok &= check_python_package("faster_whisper", "faster-whisper")
    ml_ok &= check_python_package("torch", "PyTorch")
    ml_ok &= check_python_package("transformers", "Transformers")
    ml_ok &= check_python_package("cv2", "OpenCV")
    ml_ok &= check_python_package("reportlab", "ReportLab")
    ml_ok &= check_python_package("pptx", "python-pptx")
    ml_ok &= check_python_package("openvino", "OpenVINO")
    
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
    
    if not ml_ok:
        print("\n⚠ ML packages are not fully installed.")
        print("  For full AI features, run: pip install -r requirements.txt")
    else:
        print("\n✓ All ML packages installed!")
        print("  You can run the full system: python main.py")
    
    print("=" * 60)
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
