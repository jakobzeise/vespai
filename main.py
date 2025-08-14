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

# Local imports
from config.settings import config
from detection.engine import DetectionEngine
from detection.motion import MotionDetector
from services.sms import SMSAlertService  
from utils.stats import StatsManager
from web.app import create_app, update_web_frame, start_web_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vespai.log'),
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
    
    return parser.parse_args()

def setup_camera(args):
    """Initialize camera or video input"""
    import cv2
    
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
        logger.info("Initializing camera...")
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        if not cap.isOpened():
            cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Cannot open camera!")
        
        # Set camera properties
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
        
        logger.info("Camera initialized successfully")
        time.sleep(2)  # Allow camera to warm up
    
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
    except Exception as e:
        logger.error(f"Camera initialization failed: {e}")
        return 1
    
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
            
            # Read frame
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue
            
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
            if motion_detector:
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
                    update_web_frame(display_frame)
            
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