#!/usr/bin/env python3
"""
VespAI Launcher Script
Author: Jakob Zeise (Zeise Digital)

This script launches VespAI using the configuration from launcher_config.py
and sets up SMS configuration from sms_config.py
"""

import os
import sys
import subprocess
from launcher_config import get_command, setup_environment, MODE, CONFIG

def main():
    print("="*50)
    print("VespAI Launcher")
    print("="*50)
    
    # Setup environment variables from configuration
    setup_environment()
    
    # Get current directory (repository root)
    repo_dir = os.getcwd()
    
    # Determine Python executable (check for virtual environment)
    venv_python = os.path.join(repo_dir, "venv", "bin", "python")
    if os.name == 'nt':  # Windows
        venv_python = os.path.join(repo_dir, "venv", "Scripts", "python.exe")
    
    if not os.path.exists(venv_python):
        print("⚠️  Virtual environment not found, using system Python")
        venv_python = sys.executable
    else:
        print(f"✓ Using virtual environment: {venv_python}")
    
    # Generate command
    command = get_command(venv_python, repo_dir)
    
    print(f"[LAUNCHING] {command}")
    print("-"*50)
    
    # Execute the command
    try:
        subprocess.run(command, shell=True, check=True)
    except KeyboardInterrupt:
        print("\n\n[STOPPED] VespAI stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] VespAI exited with error code {e.returncode}")
        return e.returncode
    
    return 0

if __name__ == "__main__":
    sys.exit(main())