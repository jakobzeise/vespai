#!/usr/bin/env python3
"""
VespAI - Simple Working Version
Based on your working code that properly updates video frames
"""

import argparse
import datetime
import logging
import os
import sys
import threading
import time
import cv2
import numpy as np

# Configure logging with proper Unicode support for Windows
import platform
if platform.system() == 'Windows':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vespai.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vespai.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)

# Global variables for web interface
web_frame = None
web_lock = threading.Lock()

# Statistics
stats = {
    "frame_id": 0,
    "total_velutina": 0,
    "total_crabro": 0,
    "total_detections": 0,
    "fps": 0,
    "start_time": datetime.datetime.now(),
    "detection_log": [],
    "detection_frames": {}
}

def setup_camera(args):
    """Initialize camera with cross-platform compatibility"""
    logger.info("Initializing camera...")
    
    if args.video:
        cap = cv2.VideoCapture(args.video)
        logger.info(f"Using video file: {args.video}")
    else:
        # Cross-platform camera backend selection
        os_name = platform.system()
        if os_name == "Darwin":  # macOS
            backend = cv2.CAP_AVFOUNDATION
        elif os_name == "Windows":
            backend = cv2.CAP_DSHOW  # DirectShow for Windows
        else:  # Linux and others
            backend = cv2.CAP_V4L2
        
        # Try camera with appropriate backend
        cap = cv2.VideoCapture(0, backend)
        
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)  # Fallback to default
        
        if not cap.isOpened():
            logger.error("Failed to open camera")
            return None
        
        # Parse resolution
        resolution_map = {"4k": (3840, 2160), "1080p": (1920, 1080), "720p": (1280, 720)}
        if args.resolution in resolution_map:
            width, height = resolution_map[args.resolution]
        else:
            try:
                width, height = map(int, args.resolution.split('x'))
            except:
                width, height = 1280, 720
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        logger.info(f"Camera resolution: {width}x{height}")
    
    return cap

def load_model():
    """Load YOLOv5 model with fallback options"""
    logger.info("Loading YOLOv5 model...")
    
    # Try different model paths
    model_paths = [
        "models/yolov5s-all-data.pt",  # VespAI hornet model
        "yolov5s.pt",  # Standard YOLOv5
        "models/yolov5s.pt"
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            logger.info(f"Found model at: {path}")
            break
    
    if not model_path:
        logger.info("No local model found, will download yolov5s.pt")
        model_path = "yolov5s.pt"
    
    # Try loading with ultralytics first
    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        logger.info("✓ Model loaded via ultralytics YOLO")
        return model
    except Exception as e:
        logger.warning(f"Ultralytics loading failed: {e}")
    
    # Fallback to torch.hub
    try:
        import torch
        # Force weights_only=False for PyTorch 2.8+ compatibility
        original_load = torch.load
        torch.load = lambda *args, **kwargs: original_load(*args, **kwargs, weights_only=False)
        
        model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path, force_reload=True)
        torch.load = original_load  # Restore
        logger.info("✓ Model loaded via torch.hub")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None

# Flask Web Server
from flask import Flask, Response, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>VespAI Monitor</title>
    <meta http-equiv="refresh" content="0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #0a0a0a; color: white; }
        .header { text-align: center; margin-bottom: 20px; }
        .live-feed { max-width: 100%; height: auto; border: 2px solid #ff6600; }
        .stats { display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; margin: 20px 0; }
        .stat { background: #1a1a1a; padding: 15px; border-radius: 8px; text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐝 VespAI Monitor</h1>
        <p>Live Hornet Detection System</p>
    </div>
    
    <div style="text-align: center;">
        <img src="/video_feed" alt="Live Feed" class="live-feed" id="video-feed">
    </div>
    
    <div class="stats" id="stats">
        <!-- Stats will be loaded here -->
    </div>
    
    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('stats').innerHTML = `
                        <div class="stat">
                            <h3>Frames</h3>
                            <p>${data.frame_id}</p>
                        </div>
                        <div class="stat">
                            <h3>FPS</h3>
                            <p>${data.fps.toFixed(1)}</p>
                        </div>
                        <div class="stat">
                            <h3>Detections</h3>
                            <p>${data.total_detections}</p>
                        </div>
                        <div class="stat">
                            <h3>Asian Hornets</h3>
                            <p style="color: #ff4444;">${data.total_velutina}</p>
                        </div>
                        <div class="stat">
                            <h3>European Hornets</h3>
                            <p style="color: #ffaa44;">${data.total_crabro}</p>
                        </div>
                    `;
                });
        }
        setInterval(updateStats, 2000);
        updateStats();
    </script>
</body>
</html>'''

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    def generate():
        global web_frame
        while True:
            with web_lock:
                if web_frame is None:
                    # Create fallback frame
                    frame = np.zeros((540, 960, 3), dtype=np.uint8)
                    cv2.putText(frame, "VespAI - Camera Initializing...", (200, 270), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 102, 0), 2)
                else:
                    frame = web_frame.copy()

            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    global stats
    return jsonify(stats)

def start_web_server():
    """Start Flask web server"""
    logger.info("Starting web server on http://0.0.0.0:8081")
    app.run(host='0.0.0.0', port=8081, threaded=True, debug=False)

def main():
    global web_frame, stats
    
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--web", action="store_true", help="Enable web interface")
    parser.add_argument("--resolution", default="720p", help="Camera resolution")
    parser.add_argument("--video", help="Video file path")
    parser.add_argument("--motion", action="store_true", help="Enable motion detection")
    parser.add_argument("--conf", type=float, default=0.8, help="Confidence threshold")
    parser.add_argument("--brake", type=float, default=0.1, help="Frame delay")
    args = parser.parse_args()
    
    # Setup camera
    cap = setup_camera(args)
    if cap is None:
        logger.error("Camera setup failed")
        return 1
    
    # Load model
    model = load_model()
    if model is None:
        logger.error("Model loading failed")
        return 1
    
    # Start web server
    if args.web:
        web_thread = threading.Thread(target=start_web_server)
        web_thread.daemon = True
        web_thread.start()
        time.sleep(2)
    
    # Main detection loop
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
                stats["fps"] = fps_counter
                fps_counter = 0
                last_fps_time = time.time()
            
            # Always run detection for now (motion detection can be added later)
            run_detection = True
            
            if run_detection:
                # Run YOLOv5 detection
                results = model(frame)
                
                # Process results
                velutina_count = 0
                crabro_count = 0
                
                if hasattr(results, 'pred') and len(results.pred[0]) > 0:
                    for detection in results.pred[0]:
                        x1, y1, x2, y2, conf, cls = detection
                        cls = int(cls)
                        confidence = float(conf)
                        
                        if cls == 1:  # Vespa velutina
                            velutina_count += 1
                            stats["total_velutina"] += 1
                        elif cls == 0:  # Vespa crabro
                            crabro_count += 1
                            stats["total_crabro"] += 1
                
                # Render results
                if hasattr(results, 'render'):
                    results.render()
                    annotated_frame = results.ims[0]
                    annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)
                else:
                    annotated_frame = frame.copy()
                
                # Add overlay info
                cv2.putText(annotated_frame, f"Frame: {frame_id} | FPS: {stats['fps']:.1f}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"V: {stats['total_velutina']} | C: {stats['total_crabro']}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Update detection counts
                if velutina_count > 0 or crabro_count > 0:
                    stats["total_detections"] += 1
                    logger.info(f"Detection #{stats['total_detections']}: V={velutina_count}, C={crabro_count}")
                
            else:
                annotated_frame = frame.copy()
                cv2.putText(annotated_frame, f"Frame: {frame_id} | FPS: {stats['fps']:.1f}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # CRITICAL: Always update web frame - this is the key fix!
            if args.web:
                display_frame = cv2.resize(annotated_frame, (960, 540))
                with web_lock:
                    web_frame = display_frame.copy()
            
            stats["frame_id"] = frame_id
            frame_id += 1
            
            # Frame rate control
            delay = args.brake - (time.time() - loop_start)
            if delay > 0:
                time.sleep(delay)
                
    except KeyboardInterrupt:
        logger.info("Stopping...")
    
    finally:
        if cap:
            cap.release()
        logger.info("Cleanup complete")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())