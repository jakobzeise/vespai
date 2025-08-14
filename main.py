
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VespAI - Hornet Detection & SMS Alert System
Main entry point for the application
"""
import argparse
import cv2
import datetime
import logging
import os
import sys
import threading
import time
import warnings

# Suppress PyTorch/YOLOv5 deprecation warnings for cleaner output
warnings.filterwarnings("ignore", category=FutureWarning, message=".*torch.cuda.amp.autocast.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*torch.cuda.amp.*")

# Local imports
from config.settings import config
from detection.engine import DetectionEngine
from detection.motion import MotionDetector
from services.sms import SMSAlertService  
from vespai_utils.stats import StatsManager
from web.app import create_app, update_web_frame, start_web_server

# Configure logging with proper Unicode support for Windows
import platform
if platform.system() == 'Windows':
    # For Windows, use UTF-8 encoding to handle Unicode characters
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/vespai.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Set console to UTF-8 mode for Windows
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except Exception:
        # Fallback: Remove Unicode characters from log messages
        class UnicodeFilterHandler(logging.StreamHandler):
            def emit(self, record):
                try:
                    record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
                    if hasattr(record, 'args') and record.args:
                        record.args = tuple(str(arg).encode('ascii', 'ignore').decode('ascii') 
                                          for arg in record.args)
                    super().emit(record)
                except Exception:
                    pass
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/vespai.log', encoding='utf-8'),
                UnicodeFilterHandler(sys.stdout)
            ]
        )
else:
    # For non-Windows systems, use standard configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/vespai.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="VespAI Hornet Detection System")
    
    # Detection arguments
    parser.add_argument("-c", "--conf", type=float, default=config.CONFIDENCE_THRESHOLD,
                       help="Detection confidence threshold")
    parser.add_argument("-s", "--save", action="store_true", default=config.SAVE_DETECTIONS,
                       help="Save detection images")
    parser.add_argument("-sd", "--save-dir", default=config.SAVE_DIRECTORY,
                       help="Directory for saved images")
    
    # Camera arguments
    parser.add_argument("-v", "--video", help="Use video file instead of camera")
    parser.add_argument("-r", "--resolution", default=config.CAMERA_RESOLUTION,
                       help="Camera resolution (e.g., 1920x1080)")
    
    # Motion detection arguments
    parser.add_argument("-m", "--motion", action="store_true", 
                       default=config.ENABLE_MOTION_DETECTION,
                       help="Enable motion detection")
    parser.add_argument("-a", "--min-motion-area", type=int, default=config.MIN_MOTION_AREA,
                       help="Minimum motion area threshold")
    parser.add_argument("-d", "--dilation", type=int, default=config.MOTION_DILATION,
                       help="Motion detection dilation iterations")
    
    # Other arguments  
    parser.add_argument("-b", "--brake", type=float, default=0.1,
                       help="Frame processing delay")
    parser.add_argument("-p", "--print", action="store_true",
                       help="Print detection details to console")
    parser.add_argument("--web", action="store_true", default=True,
                       help="Enable web server")
    parser.add_argument("--demo", action="store_true",
                       help="Run in demo mode without camera")
    
    return parser.parse_args()

def setup_camera(args):
    """Initialize camera or video input"""
    import cv2
    
    # Demo mode - create a synthetic video feed
    if args.demo:
        logger.info("Running in demo mode - no camera required")
        return None
    
    # Parse resolution
    resolution_map = {
        "4k": (3840, 2160),
        "1080p": (1920, 1080),
        "720p": (1280, 720)
    }
    
    if args.resolution in resolution_map:
        width, height = resolution_map[args.resolution]
    else:
        try:
            width, height = map(int, args.resolution.split('x'))
        except:
            width, height = 1920, 1080
    
    logger.info(f"Using resolution: {width}x{height}")
    
    # Initialize camera or video
    if args.video:
        cap = cv2.VideoCapture(args.video)
        logger.info(f"Using video file: {args.video}")
    else:
        import platform
        os_name = platform.system()
        logger.info(f"Initializing camera on {os_name}...")
        # Try to find built-in camera specifically
        cap = None
        
        # Use appropriate backend for the operating system
        if os_name == "Darwin":  # macOS
            backend = cv2.CAP_AVFOUNDATION
        elif os_name == "Windows":
            backend = cv2.CAP_DSHOW  # DirectShow for Windows
        else:  # Linux and others
            backend = cv2.CAP_V4L2
        
        # Try different camera indices to find the built-in one
        for camera_id in range(5):  # Check cameras 0-4
            logger.info(f"Trying camera index {camera_id}...")
            test_cap = cv2.VideoCapture(camera_id, backend)
            if test_cap.isOpened():
                # Test if we can read a frame
                ret, test_frame = test_cap.read()
                if ret and test_frame is not None:
                    logger.info(f"Camera {camera_id} is available, frame shape: {test_frame.shape}")
                    # Check if this is a lower resolution camera (likely built-in vs iPhone)
                    if test_frame.shape[1] <= 1280:  # Width <= 1280 suggests built-in camera
                        logger.info(f"Using camera {camera_id} (appears to be built-in)")
                        cap = test_cap
                        break
                    else:
                        logger.info(f"Camera {camera_id} has high resolution ({test_frame.shape}), might be iPhone")
                        test_cap.release()
                else:
                    test_cap.release()
            else:
                logger.info(f"Camera {camera_id} not available")
        
        # If no suitable camera found, use camera 0 as fallback
        if cap is None:
            logger.warning("No built-in camera detected, trying default camera...")
            cap = cv2.VideoCapture(0, backend)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise RuntimeError("Cannot open any camera!")
        
        # Set camera properties
        logger.info(f"Setting camera resolution to {width}x{height}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
        
        # Get actual values
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Camera initialized successfully:")
        logger.info(f"  Resolution: {actual_width}x{actual_height} (requested {width}x{height})")
        logger.info(f"  FPS: {actual_fps} (requested {config.CAMERA_FPS})")
        
        # Test read a frame
        ret, test_frame = cap.read()
        if ret and test_frame is not None:
            logger.info(f"Test frame read successfully, shape: {test_frame.shape}")
        else:
            logger.warning("Failed to read test frame")
        
        time.sleep(1)  # Allow camera to warm up
    
    return cap

def setup_save_directories(args):
    """Create directories for saving detection images"""
    if args.save:
        frame_dir = os.path.join(args.save_dir, "frames")
        label_dir = os.path.join(args.save_dir, "labels")
        result_dir = os.path.join(args.save_dir, "results")
        
        for directory in (frame_dir, label_dir, result_dir):
            os.makedirs(directory, exist_ok=True)
            
        logger.info(f"Save directories created: {args.save_dir}")
        return frame_dir, label_dir, result_dir
    
    return None, None, None

def save_detection_images(frame, annotated_frame, result_dir, frame_dir, stats_manager):
    """Save detection images to disk"""
    try:
        timestamp = datetime.datetime.now().strftime("%d.%m.%Y-%H:%M:%S")
        result_path = os.path.join(result_dir, f"{timestamp}.jpeg")
        frame_path = os.path.join(frame_dir, f"{timestamp}.jpeg")
        
        import cv2
        cv2.imwrite(result_path, annotated_frame)
        cv2.imwrite(frame_path, frame)
        
        stats_manager.increment_saved_images()
        logger.info(f"Saved detection images: {timestamp}")
        
    except Exception as e:
        logger.error(f"Error saving images: {e}")

def create_detection_log_entry(detection_result, detection_key, current_time):
    """Create log entry for detection"""
    velutina_count = detection_result['velutina_count']
    crabro_count = detection_result['crabro_count']
    
    if velutina_count > 0 and crabro_count > 0:
        return {
            "time": current_time.strftime("%H:%M:%S"),
            "message": f"Detected: {velutina_count} Velutina, {crabro_count} Crabro",
            "type": "both",
            "frame_id": detection_key
        }
    elif velutina_count > 0:
        return {
            "time": current_time.strftime("%H:%M:%S"),
            "message": f"⚠️ Asian Hornet! {velutina_count} Vespa Velutina detected",
            "type": "velutina",
            "frame_id": detection_key
        }
    else:
        return {
            "time": current_time.strftime("%H:%M:%S"),
            "message": f"European Hornet: {crabro_count} Vespa Crabro detected",
            "type": "crabro",
            "frame_id": detection_key
        }

def send_detection_alerts(detection_result, detection_key, sms_service):
    """Send SMS alerts for detections"""
    velutina_count = detection_result['velutina_count']
    crabro_count = detection_result['crabro_count']
    current_time = datetime.datetime.now().strftime('%H:%M')
    
    frame_url = f"{config.public_url}/frame/{detection_key}"
    
    if velutina_count > 0:  # Asian hornet - high priority
        sms_text = f"⚠️ ALERT: {velutina_count} Asian Hornet(s) detected at {current_time}! View: {frame_url}"
        sms_service.send_alert(sms_text)
    elif crabro_count > 0:  # European hornet - lower priority
        sms_text = f"ℹ️ Info: {crabro_count} European Hornet(s) detected at {current_time}. View: {frame_url}"
        sms_service.send_alert(sms_text)

def main():
    """Main application loop"""
    # Show configuration warnings
    warnings = config.validate_config()
    for warning in warnings:
        logger.warning(warning)
    
    # Parse arguments
    args = parse_arguments()
    
    # Initialize components
    logger.info("Initializing VespAI components...")
    
    # Statistics manager
    stats_manager = StatsManager()
    
    # Detection engine
    try:
        detection_engine = DetectionEngine(confidence=args.conf)
    except Exception as e:
        logger.error(f"Failed to initialize detection engine: {e}")
        return 1
    
    # Motion detector (optional)
    motion_detector = None
    if args.motion:
        motion_detector = MotionDetector(
            min_area=args.min_motion_area,
            dilation_iterations=args.dilation
        )
        logger.info("Motion detection enabled")
    
    # SMS service
    sms_service = SMSAlertService(stats_manager)
    
    # Setup camera
    try:
        cap = setup_camera(args)
        if cap is None and not args.demo:
            logger.error("Camera initialization failed and not in demo mode")
            return 1
    except Exception as e:
        logger.error(f"Camera initialization failed: {e}")
        if not args.demo:
            return 1
        cap = None
    
    # Setup save directories
    frame_dir, label_dir, result_dir = setup_save_directories(args)
    
    # Start web server
    if args.web:
        app = create_app(stats_manager)
        web_thread = threading.Thread(target=start_web_server, args=(app,))
        web_thread.daemon = True
        web_thread.start()
        time.sleep(2)  # Allow server to start
    
    # Detection loop variables
    frame_id = 1
    last_fps_time = time.time()
    fps_counter = 0
    
    logger.info("Starting detection loop...")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            loop_start = time.time()
            
            # Read frame or create demo frame
            if args.demo:
                # Create a synthetic demo frame with dynamic content
                import numpy as np
                frame = np.zeros((540, 960, 3), dtype=np.uint8)
                current_time = time.time()
                
                cv2.putText(frame, "VespAI Demo Mode - LIVE", (300, 180), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Frame: {frame_id}", (50, 220), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, f"Time: {current_time:.1f}", (50, 250), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, "Web interface: http://localhost:8080", 
                           (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, "Connect a camera to enable live detection", 
                           (170, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                ret = True
            else:
                # Read multiple frames to ensure we get the latest
                for _ in range(2):  # Skip one frame to get fresher data
                    ret, frame = cap.read()
                    if not ret:
                        break
                
                if not ret or frame is None:
                    logger.warning(f"Failed to read frame at frame {frame_id}: ret={ret}, frame is None={frame is None}")
                    time.sleep(0.1)
                    continue
                    
                if frame_id % 30 == 0:  # Debug every 30 frames
                    logger.info(f"Successfully read camera frame {frame_id}, shape: {frame.shape}")
                    # Add timestamp to verify frames are truly different
                    current_time_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    logger.info(f"Camera frame timestamp: {current_time_str}")
                    # Calculate a simple hash to verify frame content is changing
                    import hashlib
                    frame_hash = hashlib.md5(frame.tobytes()).hexdigest()[:8]
                    logger.info(f"Frame content hash: {frame_hash}")
            
            # Update FPS
            fps_counter += 1
            if time.time() - last_fps_time >= 1.0:
                fps = fps_counter
                stats_manager.update_frame_stats(frame_id, fps)
                fps_counter = 0
                last_fps_time = time.time()
            
            # Check for hour change
            stats_manager.check_hour_change()
            
            # Motion detection check
            run_detection = True
            if motion_detector and not args.demo:  # Skip motion detection in demo mode
                run_detection = motion_detector.detect_motion(frame)
            
            if run_detection:
                # Run hornet detection
                detection_result = detection_engine.detect(frame)
                annotated_frame = detection_result['annotated_frame']
                
                # Update web frame
                if args.web:
                    display_frame = cv2.resize(annotated_frame, (960, 540))
                    detection_engine.add_overlay_text(
                        display_frame, frame_id, stats_manager.get_stats()['fps'],
                        stats_manager.get_stats()['total_velutina'],
                        stats_manager.get_stats()['total_crabro']
                    )
                    update_web_frame(display_frame)
                    if frame_id % 30 == 0:  # Debug output every 30 frames
                        logger.info(f"Updated web frame {frame_id} - detection path")
                
                # Process detections
                if detection_result['has_detections']:
                    current_time = datetime.datetime.now()
                    
                    # Add detections to stats
                    velutina_count = detection_result['velutina_count']
                    crabro_count = detection_result['crabro_count']
                    
                    detection_key = None
                    for _ in range(velutina_count):
                        detection_key = stats_manager.add_detection(
                            "velutina", 
                            detection_result['confidences'][0] if detection_result['confidences'] else 0.8,
                            frame_id, 
                            annotated_frame
                        )
                    
                    for _ in range(crabro_count):
                        detection_key = stats_manager.add_detection(
                            "crabro",
                            detection_result['confidences'][0] if detection_result['confidences'] else 0.8,
                            frame_id,
                            annotated_frame
                        )
                    
                    # Create log entry
                    if detection_key:
                        log_entry = create_detection_log_entry(detection_result, detection_key, current_time)
                        stats_manager.add_log_entry(log_entry)
                    
                    # Print detection info
                    if args.print:
                        logger.info(f"Detection #{stats_manager.get_stats()['total_detections']} at frame {frame_id}")
                        logger.info(f"  Velutina: {velutina_count}, Crabro: {crabro_count}")
                    
                    # Save images
                    if args.save and result_dir:
                        save_detection_images(frame, annotated_frame, result_dir, frame_dir, stats_manager)
                    
                    # Send SMS alerts
                    if detection_key:
                        send_detection_alerts(detection_result, detection_key, sms_service)
                
                # Update confidence average
                if detection_result['confidences']:
                    avg_confidence = sum(detection_result['confidences']) / len(detection_result['confidences'])
                    stats_manager.update_confidence(avg_confidence * 100)
            
            else:
                # No motion detected, just update web frame with original
                if args.web:
                    display_frame = cv2.resize(frame, (960, 540))
                    # In demo mode, still add basic overlay info
                    if args.demo:
                        cv2.putText(display_frame, f"Demo Frame: {frame_id}", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(display_frame, f"FPS: {stats_manager.get_stats()['fps']:.1f}", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        # Add basic overlay for live camera
                        cv2.putText(display_frame, f"Live Camera - Frame: {frame_id}", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(display_frame, f"FPS: {stats_manager.get_stats()['fps']:.1f}", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    update_web_frame(display_frame)
                    if frame_id % 30 == 0:  # Debug output every 30 frames
                        logger.info(f"Updated web frame {frame_id} - no motion path")
            
            # Update system stats periodically
            if frame_id % 30 == 0:  # Every 30 frames
                stats_manager.update_system_stats()
            
            frame_id += 1
            
            # Frame rate limiting
            delay = args.brake - (time.time() - loop_start)
            if delay > 0:
                time.sleep(delay)
                
    except KeyboardInterrupt:
        logger.info("Stopping detection...")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        if cap is not None:
            cap.release()
        
        # Print final statistics
        final_stats = stats_manager.get_stats()
        logger.info("Final Statistics:")
        logger.info(f"  Frames: {frame_id}")
        logger.info(f"  Total Detections: {final_stats['total_detections']}")
        logger.info(f"  Velutina: {final_stats['total_velutina']}")
        logger.info(f"  Crabro: {final_stats['total_crabro']}")
        logger.info(f"  SMS Sent: {final_stats['sms_sent']}")
        logger.info(f"  SMS Cost: {final_stats['sms_cost']:.3f}€")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())