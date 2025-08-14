#!/usr/bin/env python3
"""
VespAI Main Application

Modular main application that coordinates all VespAI components for hornet detection.
This replaces the monolithic web_preview.py with a clean, testable architecture.

Author: VespAI Team  
Version: 1.0
"""

import logging
import sys
import time
import threading
import signal
from typing import Optional

# Core modules
from .core.config import create_config_from_args
from .core.detection import CameraManager, ModelManager, DetectionProcessor
from .sms.lox24 import create_sms_manager_from_env
from .web.routes import register_routes

# External dependencies
try:
    from flask import Flask
    import cv2
    import torch
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VespAIApplication:
    """
    Main VespAI application that orchestrates all components.
    
    Provides a clean, modular architecture for hornet detection with
    camera management, model inference, web interface, and SMS alerts.
    """
    
    def __init__(self):
        """Initialize the VespAI application."""
        self.config = None
        self.camera_manager = None
        self.model_manager = None
        self.detection_processor = None
        self.sms_manager = None
        self.flask_app = None
        self.web_thread = None
        self.running = False
        
        # Global state for web interface
        self.web_frame = None
        self.web_lock = threading.Lock()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize(self, args=None):
        """
        Initialize all application components.
        
        Args:
            args: Command line arguments (None for sys.argv)
        """
        logger.info("Initializing VespAI application...")
        
        # Load configuration
        self.config = create_config_from_args(args)
        self.config.print_summary()
        
        # Initialize components
        self._initialize_camera()
        self._initialize_model()
        self._initialize_detection_processor()
        self._initialize_sms()
        
        if self.config.get('enable_web'):
            self._initialize_web_interface()
        
        logger.info("VespAI application initialized successfully")
    
    def _initialize_camera(self):
        """Initialize camera manager."""
        logger.info("Initializing camera...")
        resolution = self.config.get_camera_resolution()
        self.camera_manager = CameraManager(resolution)
        
        video_file = self.config.get('video_file')
        self.camera_manager.initialize_camera(video_file)
    
    def _initialize_model(self):
        """Initialize model manager."""
        logger.info("Initializing detection model...")
        model_path = self.config.get('model_path')
        confidence = self.config.get('confidence_threshold')
        
        self.model_manager = ModelManager(model_path, confidence)
        self.model_manager.load_model()
    
    def _initialize_detection_processor(self):
        """Initialize detection processor."""
        logger.info("Initializing detection processor...")
        self.detection_processor = DetectionProcessor()
    
    def _initialize_sms(self):
        """Initialize SMS manager."""
        if self.config.get('enable_sms'):
            logger.info("Initializing SMS alerts...")
            self.sms_manager = create_sms_manager_from_env()
            if self.sms_manager:
                logger.info("SMS alerts enabled")
            else:
                logger.warning("SMS configuration incomplete - alerts disabled")
        else:
            logger.info("SMS alerts disabled")
    
    def _initialize_web_interface(self):
        """Initialize Flask web interface."""
        logger.info("Initializing web interface...")
        
        # Configure Flask with template and static directories
        import os
        web_dir = os.path.join(os.path.dirname(__file__), 'web')
        template_dir = os.path.join(web_dir, 'templates')
        static_dir = os.path.join(web_dir, 'static')
        
        self.flask_app = Flask(__name__, 
                              template_folder=template_dir,
                              static_folder=static_dir,
                              static_url_path='/static')
        
        # Register web routes
        register_routes(
            self.flask_app,
            self.detection_processor.stats,
            self.detection_processor.hourly_detections,
            self.web_frame,
            self.web_lock
        )
        
        # Start web server in background thread
        web_config = self.config.get_web_config()
        self.web_thread = threading.Thread(
            target=self._run_web_server,
            args=(web_config['host'], web_config['port']),
            daemon=True
        )
        self.web_thread.start()
        
        # Give web server time to start
        time.sleep(2)
        logger.info("Web interface available at %s", web_config['public_url'])
    
    def _run_web_server(self, host: str, port: int):
        """Run Flask web server (called in background thread)."""
        try:
            self.flask_app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            logger.error("Web server error: %s", e)
    
    def run(self):
        """
        Run the main detection loop.
        
        This is the core application loop that processes camera frames,
        runs detection, handles alerts, and updates the web interface.
        """
        if not self._validate_initialization():
            logger.error("Application not properly initialized")
            return False
        
        logger.info("Starting VespAI detection system...")
        logger.info("Press Ctrl+C to stop")
        
        self.running = True
        frame_count = 0
        fps_start_time = time.time()
        fps_counter = 0
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Read frame from camera
                success, frame = self.camera_manager.read_frame()
                if not success or frame is None:
                    time.sleep(0.1)
                    continue
                
                frame_count += 1
                fps_counter += 1
                
                # Update FPS calculation
                if time.time() - fps_start_time >= 1.0:
                    self.detection_processor.stats['fps'] = fps_counter
                    fps_counter = 0
                    fps_start_time = time.time()
                
                # Run detection
                results = self.model_manager.predict(frame)
                velutina_count, crabro_count, annotated_frame = self.detection_processor.process_detections(
                    results, frame, frame_count, self.config.get('confidence_threshold')
                )
                
                # Handle detections
                if velutina_count > 0 or crabro_count > 0:
                    self._handle_detection(velutina_count, crabro_count, frame_count, annotated_frame)
                
                # Update web frame
                if self.config.get('enable_web'):
                    display_frame = cv2.resize(annotated_frame, (960, 540))
                    with self.web_lock:
                        self.web_frame = display_frame.copy()
                
                # Print detection info if enabled
                if self.config.get('print_detections') and (velutina_count > 0 or crabro_count > 0):
                    confidence = self.detection_processor.stats.get('confidence_avg', 0)
                    print(f"Frame {frame_count}: {velutina_count} Velutina, {crabro_count} Crabro "
                          f"(confidence: {confidence:.1f}%)")
                
                # Frame rate control
                frame_delay = self.config.get('frame_delay', 0.1)
                elapsed = time.time() - loop_start
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error("Unexpected error in detection loop: %s", e)
            return False
        finally:
            self._cleanup()
        
        logger.info("VespAI detection system stopped")
        return True
    
    def _handle_detection(self, velutina_count: int, crabro_count: int, frame_id: int, frame):
        """
        Handle a detection event with alerts and logging.
        
        Args:
            velutina_count: Number of Asian hornets detected
            crabro_count: Number of European hornets detected  
            frame_id: Current frame ID
            frame: Detection frame with annotations
        """
        # Save detection image if enabled
        if self.config.get('save_detections'):
            self._save_detection_image(frame, frame_id, velutina_count, crabro_count)
        
        # Send SMS alert if configured
        if self.sms_manager:
            self._send_sms_alert(velutina_count, crabro_count, frame_id)
    
    def _save_detection_image(self, frame, frame_id: int, velutina: int, crabro: int):
        """Save detection image to disk."""
        import os
        from datetime import datetime
        
        save_dir = self.config.get('save_directory', 'data/detections')
        os.makedirs(save_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        species = 'velutina' if velutina > 0 else 'crabro'
        filename = f"{timestamp}_frame{frame_id}_{species}_{velutina}v_{crabro}c.jpg"
        filepath = os.path.join(save_dir, filename)
        
        cv2.imwrite(filepath, frame)
        logger.info("Saved detection image: %s", filepath)
    
    def _send_sms_alert(self, velutina_count: int, crabro_count: int, frame_id: int):
        """Send SMS alert for detection."""
        if not self.sms_manager:
            return
        
        # Create frame URL for SMS
        web_config = self.config.get_web_config()
        current_time = time.strftime('%H%M%S')
        detection_key = f"{frame_id}_{current_time}"
        frame_url = f"{web_config['public_url']}/frame/{detection_key}"
        
        # Determine hornet type and create alert
        if velutina_count > 0:
            hornet_type = 'velutina'
            count = velutina_count
        else:
            hornet_type = 'crabro'
            count = crabro_count
        
        confidence = self.detection_processor.stats.get('confidence_avg', 0)
        message = self.sms_manager.create_hornet_alert(hornet_type, count, confidence, frame_url)
        
        # Send alert
        success, status = self.sms_manager.send_alert(message)
        if success:
            logger.info("SMS alert sent: %s", status)
        else:
            logger.warning("SMS alert failed: %s", status)
    
    def _validate_initialization(self) -> bool:
        """Validate that all required components are initialized."""
        if not self.camera_manager:
            logger.error("Camera manager not initialized")
            return False
        
        if not self.model_manager or not self.model_manager.model:
            logger.error("Model manager not initialized") 
            return False
        
        if not self.detection_processor:
            logger.error("Detection processor not initialized")
            return False
        
        return True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received signal %d, shutting down...", signum)
        self.running = False
    
    def _cleanup(self):
        """Clean up resources on shutdown."""
        logger.info("Cleaning up resources...")
        
        if self.camera_manager:
            self.camera_manager.release()
        
        # Final statistics
        if self.detection_processor:
            stats = self.detection_processor.stats
            logger.info("Final statistics:")
            logger.info("  Total frames processed: %d", stats.get('frame_id', 0))
            logger.info("  Total detections: %d", stats.get('total_detections', 0))
            logger.info("  Asian hornets: %d", stats.get('total_velutina', 0))
            logger.info("  European hornets: %d", stats.get('total_crabro', 0))


def main():
    """Main entry point for the VespAI application."""
    app = VespAIApplication()
    
    try:
        app.initialize()
        success = app.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error("Fatal error: %s", e)
        sys.exit(1)


if __name__ == '__main__':
    main()