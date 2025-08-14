#!/usr/bin/env python3
"""
VespAI Configuration Module

Handles all configuration management including environment variables,
command line arguments, and default settings.

Author: VespAI Team
Version: 1.0
"""

import os
import argparse
import logging
from typing import Tuple, Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class VespAIConfig:
    """
    Central configuration management for VespAI.
    
    Handles environment variables, command line arguments, and default settings
    with proper precedence (CLI args override env vars override defaults).
    """
    
    def __init__(self):
        """Initialize configuration with defaults."""
        # Load environment variables from .env file
        load_dotenv()
        
        # Default configuration
        self.defaults = {
            # Camera settings
            'resolution': '1920x1080',
            'video_file': None,
            
            # Detection settings  
            'confidence_threshold': 0.8,
            'model_path': 'models/yolov5s-all-data.pt',
            'save_detections': False,
            'save_directory': 'data/detections',
            'print_detections': False,
            
            # Motion detection
            'enable_motion_detection': False,
            'min_motion_area': 100,
            'dilation_iterations': 1,
            
            # Performance settings
            'frame_delay': 0.1,
            
            # Web interface
            'enable_web': False,
            'web_host': '0.0.0.0',
            'web_port': 5000,
            
            # SMS settings (disabled by default, use --sms to enable)
            'enable_sms': False,
            'lox24_api_key': '',
            'phone_number': '',
            'lox24_sender': 'VespAI',
            'sms_delay_minutes': 5,
            'domain_name': 'localhost',
            'use_https': False,
        }
        
        # Current configuration (will be populated from env + args)
        self.config = {}
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Map environment variable names to config keys
        env_mapping = {
            'RESOLUTION': 'resolution',
            'CONFIDENCE_THRESHOLD': 'confidence_threshold', 
            'MODEL_PATH': 'model_path',
            'SAVE_DETECTIONS': 'save_detections',
            'SAVE_DIRECTORY': 'save_directory',
            'ENABLE_MOTION_DETECTION': 'enable_motion_detection',
            'MIN_MOTION_AREA': 'min_motion_area',
            'FRAME_DELAY': 'frame_delay',
            'ENABLE_WEB': 'enable_web',
            'WEB_HOST': 'web_host',
            'WEB_PORT': 'web_port',
            'ENABLE_SMS': 'enable_sms',
            'LOX24_API_KEY': 'lox24_api_key',
            'PHONE_NUMBER': 'phone_number',
            'LOX24_SENDER': 'lox24_sender',
            'SMS_DELAY_MINUTES': 'sms_delay_minutes',
            'DOMAIN_NAME': 'domain_name',
            'USE_HTTPS': 'use_https',
        }
        
        # Start with defaults
        self.config = self.defaults.copy()
        
        # Override with environment variables
        for env_key, config_key in env_mapping.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # Convert types based on default value type
                default_value = self.defaults[config_key]
                try:
                    if isinstance(default_value, bool):
                        self.config[config_key] = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(default_value, int):
                        self.config[config_key] = int(env_value)
                    elif isinstance(default_value, float):
                        self.config[config_key] = float(env_value)
                    else:
                        self.config[config_key] = env_value
                        
                    logger.debug("Loaded %s from environment: %s", config_key, env_value)
                except (ValueError, TypeError) as e:
                    logger.warning("Invalid environment value for %s: %s (%s)", env_key, env_value, e)
    
    def parse_args(self, args=None) -> argparse.Namespace:
        """
        Parse command line arguments and update configuration.
        
        Args:
            args: List of arguments to parse (None for sys.argv)
            
        Returns:
            argparse.Namespace: Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description='VespAI Hornet Detection System',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        
        # Camera settings
        parser.add_argument('-r', '--resolution', 
                          default=self.config['resolution'],
                          help='Camera resolution (e.g., 1920x1080, 1080p, 720p)')
        parser.add_argument('-v', '--video',
                          default=self.config['video_file'],
                          help='Video file to process instead of live camera')
        
        # Detection settings
        parser.add_argument('-c', '--conf', '--confidence',
                          type=float,
                          default=self.config['confidence_threshold'], 
                          help='Detection confidence threshold')
        parser.add_argument('--model-path',
                          default=self.config['model_path'],
                          help='Path to YOLOv5 model weights')
        parser.add_argument('-s', '--save',
                          action='store_true',
                          default=self.config['save_detections'],
                          help='Save detection images')
        parser.add_argument('-sd', '--save-dir',
                          default=self.config['save_directory'],
                          help='Directory to save detection images')
        parser.add_argument('-p', '--print',
                          action='store_true', 
                          default=self.config['print_detections'],
                          help='Print detection details to console')
        
        # Motion detection
        parser.add_argument('-m', '--motion',
                          action='store_true',
                          default=self.config['enable_motion_detection'],
                          help='Enable motion detection optimization')
        parser.add_argument('-a', '--min-motion-area',
                          type=int,
                          default=self.config['min_motion_area'],
                          help='Minimum motion area threshold')
        parser.add_argument('-d', '--dilation',
                          type=int,
                          default=self.config['dilation_iterations'],
                          help='Dilation iterations for motion detection')
        
        # Performance settings
        parser.add_argument('-b', '--brake',
                          type=float,
                          default=self.config['frame_delay'],
                          help='Frame processing delay in seconds')
        
        # Web interface
        parser.add_argument('--web',
                          action='store_true',
                          default=self.config['enable_web'],
                          help='Enable web dashboard')
        parser.add_argument('--web-host',
                          default=self.config['web_host'],
                          help='Web server host address')
        parser.add_argument('--web-port',
                          type=int,
                          default=self.config['web_port'],
                          help='Web server port')
        
        # SMS alerts
        parser.add_argument('--sms',
                          action='store_true',
                          default=False,
                          help='Enable SMS alerts (requires LOX24_API_KEY and PHONE_NUMBER)')
        parser.add_argument('--no-sms',
                          action='store_true',
                          default=False,
                          help='Disable SMS alerts')
        
        # Parse arguments
        parsed_args = parser.parse_args(args)
        
        # Update configuration with parsed arguments
        self._update_from_args(parsed_args)
        
        return parsed_args
    
    def _update_from_args(self, args: argparse.Namespace):
        """Update configuration from parsed command line arguments."""
        # Map argument attributes to config keys
        arg_mapping = {
            'resolution': 'resolution',
            'video': 'video_file',
            'conf': 'confidence_threshold',
            'model_path': 'model_path', 
            'save': 'save_detections',
            'save_dir': 'save_directory',
            'print': 'print_detections',
            'motion': 'enable_motion_detection',
            'min_motion_area': 'min_motion_area',
            'dilation': 'dilation_iterations',
            'brake': 'frame_delay',
            'web': 'enable_web',
            'web_host': 'web_host',
            'web_port': 'web_port',
        }
        
        for arg_key, config_key in arg_mapping.items():
            if hasattr(args, arg_key):
                value = getattr(args, arg_key)
                if value is not None:
                    self.config[config_key] = value
        
        # Handle SMS enable/disable flags
        if hasattr(args, 'sms') and args.sms:
            self.config['enable_sms'] = True
        elif hasattr(args, 'no_sms') and args.no_sms:
            self.config['enable_sms'] = False
    
    def get(self, key: str, default=None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value
        logger.debug("Set %s to %s", key, value)
    
    def get_camera_resolution(self) -> Tuple[int, int]:
        """
        Get camera resolution as (width, height) tuple.
        
        Returns:
            Tuple of (width, height)
        """
        from .detection import parse_resolution
        return parse_resolution(self.config['resolution'])
    
    def get_sms_config(self) -> Dict[str, Any]:
        """
        Get SMS configuration dictionary.
        
        Returns:
            Dictionary with SMS configuration
        """
        return {
            'enabled': self.config['enable_sms'],
            'api_key': self.config['lox24_api_key'],
            'phone_number': self.config['phone_number'],
            'sender_name': self.config['lox24_sender'],
            'delay_minutes': self.config['sms_delay_minutes'],
        }
    
    def get_web_config(self) -> Dict[str, Any]:
        """
        Get web server configuration dictionary.
        
        Returns:
            Dictionary with web configuration
        """
        protocol = 'https' if self.config['use_https'] else 'http'
        domain = self.config['domain_name']
        port = self.config['web_port']
        
        if port in (80, 443):
            public_url = f"{protocol}://{domain}"
        else:
            public_url = f"{protocol}://{domain}:{port}"
        
        return {
            'enabled': self.config['enable_web'],
            'host': self.config['web_host'],
            'port': self.config['web_port'],
            'public_url': public_url,
        }
    
    def validate(self) -> bool:
        """
        Validate configuration values.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate confidence threshold
        conf = self.config['confidence_threshold']
        if not (0.0 <= conf <= 1.0):
            raise ValueError(f"Confidence threshold must be between 0.0 and 1.0, got {conf}")
        
        # Validate resolution
        try:
            width, height = self.get_camera_resolution()
            if width <= 0 or height <= 0:
                raise ValueError("Resolution must have positive width and height")
        except Exception as e:
            raise ValueError(f"Invalid resolution format: {e}")
        
        # Validate ports
        web_port = self.config['web_port']
        if not (1 <= web_port <= 65535):
            raise ValueError(f"Web port must be between 1 and 65535, got {web_port}")
        
        # Validate paths
        model_path = self.config['model_path']
        if not model_path:
            raise ValueError("Model path cannot be empty")
        
        logger.info("Configuration validation passed")
        return True
    
    def print_summary(self):
        """Print a summary of the current configuration."""
        print("\n" + "="*60)
        print("VespAI Configuration Summary")
        print("="*60)
        
        print(f"Resolution: {self.config['resolution']}")
        print(f"Confidence threshold: {self.config['confidence_threshold']}")
        print(f"Model path: {self.config['model_path']}")
        print(f"Save detections: {self.config['save_detections']}")
        if self.config['save_detections']:
            print(f"Save directory: {self.config['save_directory']}")
        
        print(f"Motion detection: {self.config['enable_motion_detection']}")
        print(f"Web interface: {self.config['enable_web']}")
        if self.config['enable_web']:
            web_config = self.get_web_config()
            print(f"Web URL: {web_config['public_url']}")
        
        print(f"SMS alerts: {self.config['enable_sms']}")
        if self.config['enable_sms'] and self.config['lox24_api_key']:
            print(f"SMS delay: {self.config['sms_delay_minutes']} minutes")
        
        print("="*60 + "\n")


def create_config_from_args(args=None) -> VespAIConfig:
    """
    Create and configure VespAI configuration from command line arguments.
    
    Args:
        args: Command line arguments (None for sys.argv)
        
    Returns:
        VespAIConfig: Configured instance
    """
    config = VespAIConfig()
    config.parse_args(args)
    config.validate()
    return config