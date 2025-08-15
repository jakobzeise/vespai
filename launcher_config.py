#!/usr/bin/env python3
"""
VespAI Launcher Configuration
This file is part of the repository and controls what gets executed
"""

import os
from datetime import datetime
from sms_config import SMS_CONFIG, get_phone_number, get_sender_name, get_delay_minutes, get_domain_name

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
        cmd = f"{venv_python} {repo_dir}/web_preview.py"

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
            
        if CONFIG.get('enable_sms'):
            cmd += " --sms"

    elif MODE == 'modular':
        # Run the modular version (adjust path as needed)
        cmd = f"{venv_python} {repo_dir}/vespai.py --web --motion --resolution 720p"

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
    # Set up basic environment
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Set up SMS configuration from sms_config.py
    phone_number = get_phone_number()
    if phone_number:
        os.environ['PHONE_NUMBER'] = phone_number
        print(f"✓ Phone number configured: {phone_number}")
    else:
        print("⚠️  No phone number configured in sms_config.py")
    
    os.environ['LOX24_SENDER'] = get_sender_name()
    os.environ['SMS_DELAY_MINUTES'] = str(get_delay_minutes())
    os.environ['DOMAIN_NAME'] = get_domain_name()
    
    # Enable SMS if configured in CONFIG
    if CONFIG.get('enable_sms') and phone_number:
        os.environ['ENABLE_SMS'] = 'true'
    else:
        os.environ['ENABLE_SMS'] = 'false'

    return True