#!/usr/bin/env python3
"""
VespAI Launcher Configuration
This file is part of the repository and controls what gets executed
"""

import os
from datetime import datetime

# Configuration mode: 'monolith' or 'modular'
MODE = 'monolith'

# Additional configuration
CONFIG = {
    'enable_web': True,
    'enable_motion': True,
    'enable_sms': True,
    'resolution': '720p',
    'confidence': 0.7,
    'save_detections': True,
    'debug_mode': False,
}


def get_command(venv_python, repo_dir):
    """
    Generate the command to run based on configuration

    Args:
        venv_python: Path to Python in virtual environment
        repo_dir: Path to repository directory

    Returns:
        Command string to execute
    """

    if MODE == 'monolith':
        # Run the monolithic version
        cmd = f"{venv_python} {repo_dir}/vespai.py"

        # Add command line arguments based on config
        if CONFIG.get('enable_web'):
            cmd += " --web"

        if CONFIG.get('enable_motion'):
            cmd += " --motion"

        if CONFIG.get('resolution'):
            cmd += f" --resolution {CONFIG['resolution']}"

        if CONFIG.get('confidence'):
            cmd += f" --conf {CONFIG['confidence']}"

        if CONFIG.get('save_detections'):
            cmd += " --save"

        if CONFIG.get('debug_mode'):
            cmd += " --print"

    elif MODE == 'modular':
        # Run the modular version (adjust path as needed)
        cmd = f"{venv_python} {repo_dir}/src/vespai/main.py"

        # Add modular-specific configuration
        if CONFIG.get('enable_web'):
            cmd += " --web"

        # Add other modular-specific options

    else:
        # Default fallback
        cmd = f"{venv_python} {repo_dir}/vespai.py --web --motion --resolution 720p"

    # Log configuration for debugging
    print(f"[CONFIG] Mode: {MODE}")
    print(f"[CONFIG] Command: {cmd}")
    print(f"[CONFIG] Time: {datetime.now()}")

    return cmd


# Optional: Add environment-specific settings
def setup_environment():
    """
    Set up any environment variables or system settings needed
    """
    # Example: Set environment variables
    os.environ['PYTHONUNBUFFERED'] = '1'

    # Example: Location-specific settings
    # if in Switzerland:
    #     os.environ['TZ'] = 'Europe/Zurich'

    return True