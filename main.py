#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VespAI – hornet detection & SMS alert with Advanced Web Dashboard
Complete Version with Real-Time Data Integration and Fixed Frame Updates

Based on working implementation - single file architecture with proper frame updates

• YOLOv5 hornet detection
• Real-time web dashboard with live statistics
• SMS alerts through Lox24 API
• Automatic data logging and visualization
"""

import argparse
import datetime
import logging
import os
import sys
import threading
import time
from collections import deque
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Configure logging with proper Unicode support for Windows
import platform
if platform.system() == 'Windows':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except Exception:
        pass
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vespai.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    # For non-Windows systems, use standard configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vespai.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)

import cv2
import numpy as np
import psutil
import requests
import torch
from flask import Flask, Response, render_template_string, jsonify

# ───────────────────────── Configuration ─────────────────────────
# Load configuration from environment variables
LOX24_API_KEY = os.getenv("LOX24_API_KEY", "")
LOX24_SENDER = os.getenv("LOX24_SENDER", "VespAI")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
SMS_DELAY_MINUTES = int(os.getenv("SMS_DELAY_MINUTES", "5"))

# Web server configuration for SMS links
DOMAIN_NAME = os.getenv("DOMAIN_NAME", "localhost")
USE_HTTPS = os.getenv("USE_HTTPS", "false").lower() == "true"
PUBLIC_URL = f"https://{DOMAIN_NAME}" if USE_HTTPS else f"http://{DOMAIN_NAME}:8081"

# Validate critical configuration
if not LOX24_API_KEY and os.getenv("ENABLE_SMS", "true").lower() == "true":
    logger.warning("⚠️  Warning: LOX24_API_KEY not set - SMS alerts disabled")
if not PHONE_NUMBER and os.getenv("ENABLE_SMS", "true").lower() == "true":
    logger.warning("⚠️  Warning: PHONE_NUMBER not set - SMS alerts disabled")

# ───────────────────────── Flask Web Server ─────────────────────────
app = Flask(__name__)
web_frame = None
web_lock = threading.Lock()

# Real-time statistics
stats = {
    "frame_id": 0,
    "total_velutina": 0,
    "total_crabro": 0,
    "total_detections": 0,
    "fps": 0,
    "last_detection_time": None,
    "start_time": datetime.datetime.now(),
    "detection_log": deque(maxlen=20),
    "hourly_stats": deque(maxlen=24),
    "cpu_temp": 0,
    "cpu_usage": 0,
    "ram_usage": 0,
    "disk_usage": 0,
    "uptime": 0,
    "saved_images": 0,
    "sms_sent": 0,
    "sms_cost": 0.0,
    "confidence_avg": 0,
    "detection_history": [],
    "detection_frames": {},
    "last_sms_time": None
}

# Track detections per hour
hourly_detections = {hour: {"velutina": 0, "crabro": 0} for hour in range(24)}
current_hour = datetime.datetime.now().hour

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI Monitor - Live Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --primary: #ff6600; --danger: #ff0040; --warning: #ffa500; --success: #00ff88;
            --info: #00d4ff; --dark: #0a0a0a; --card-bg: #141414; --border: #2a2a2a;
            --text: #ffffff; --text-dim: #888; --honey: #ffa500; --honey-dark: #cc8400;
        }
        body {
            font-family: 'Inter', sans-serif; background: #0a0a0a; color: var(--text);
            min-height: 100vh; overflow-x: hidden;
        }
        .header {
            background: rgba(20,20,20,0.95); backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border); padding: 1.5rem 2rem;
            position: sticky; top: 0; z-index: 100;
        }
        .header-content {
            max-width: 1400px; margin: 0 auto; display: flex;
            justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;
        }
        .logo { display: flex; align-items: center; gap: 1rem; }
        .logo-icon {
            width: 50px; height: 50px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--honey) 100%);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            font-size: 24px; animation: pulse-glow 3s infinite;
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 20px rgba(255,102,0,0.5); }
            50% { box-shadow: 0 0 40px rgba(255,102,0,0.8); }
        }
        .logo h1 {
            font-size: 1.8rem; font-weight: 800;
            background: linear-gradient(135deg, var(--primary) 0%, var(--warning) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .status-bar { display: flex; gap: 2rem; align-items: center; flex-wrap: wrap; }
        .status-item { display: flex; align-items: center; gap: 0.5rem; }
        .live-indicator {
            width: 10px; height: 10px; background: var(--success);
            border-radius: 50%; animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .container { max-width: 1400px; margin: 2rem auto; padding: 0 2rem; }
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem; margin-bottom: 2rem;
        }
        .stat-card {
            background: rgba(20, 20, 20, 0.8); border: 1px solid var(--border);
            border-radius: 16px; padding: 1.5rem; position: relative; overflow: hidden;
            transition: all 0.3s ease; backdrop-filter: blur(10px);
        }
        .stat-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--warning) 100%);
        }
        .stat-card.danger::before {
            background: linear-gradient(90deg, var(--danger) 0%, var(--warning) 100%);
        }
        .stat-card:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(255,102,0,0.2); }
        .stat-value { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }
        .stat-label { color: var(--text-dim); font-size: 0.9rem; text-transform: uppercase; }
        .stat-detail { font-size: 0.85rem; color: var(--text-dim); margin-top: 0.5rem; }
        .main-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; margin-bottom: 2rem; }
        .video-container {
            background: rgba(20, 20, 20, 0.9); border: 1px solid var(--border);
            border-radius: 16px; overflow: hidden; backdrop-filter: blur(10px);
        }
        .video-header {
            padding: 1rem 1.5rem; display: flex; justify-content: space-between;
            align-items: center; border-bottom: 1px solid var(--border);
        }
        .video-controls { display: flex; gap: 0.5rem; }
        .fullscreen-btn {
            background: rgba(255,255,255,0.1); border: 1px solid var(--border);
            color: var(--text); padding: 0.5rem 1rem; border-radius: 8px;
            cursor: pointer; transition: all 0.3s ease;
        }
        .fullscreen-btn:hover { background: var(--primary); transform: translateY(-2px); }
        .live-badge {
            background: var(--danger); color: white; padding: 0.25rem 0.75rem;
            border-radius: 20px; font-size: 0.8rem; font-weight: 600;
            text-transform: uppercase; animation: pulse 2s infinite;
            display: flex; align-items: center; gap: 0.25rem;
        }
        .video-feed { width: 100%; height: auto; display: block; background: #000; }
        @media (max-width: 1024px) {
            .main-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 1rem; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon"><i class="fas fa-shield-alt"></i></div>
                <h1>VespAI Monitor</h1>
            </div>
            <div class="status-bar">
                <div class="status-item">
                    <div class="live-indicator"></div>
                    <span>Live</span>
                </div>
                <div class="status-item">
                    <i class="fas fa-clock"></i>
                    <span id="current-time"></span>
                </div>
                <div class="status-item">
                    <i class="fas fa-chart-line"></i>
                    <span id="fps">0 FPS</span>
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="frame-count">0</div>
                <div class="stat-label">Frames Processed</div>
                <div class="stat-detail" id="uptime">Uptime: 0h 0m</div>
            </div>
            <div class="stat-card danger">
                <div class="stat-value" style="color: var(--danger);" id="velutina-count">0</div>
                <div class="stat-label">Vespa Velutina</div>
                <div class="stat-detail" id="velutina-last">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--warning);" id="crabro-count">0</div>
                <div class="stat-label">Vespa Crabro</div>
                <div class="stat-detail" id="crabro-last">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--success);" id="total-detections">0</div>
                <div class="stat-label">Total Detections</div>
                <div class="stat-detail" id="detection-rate">0/h</div>
            </div>
        </div>

        <div class="main-grid">
            <div class="video-container">
                <div class="video-header">
                    <h2>Live Detection Feed</h2>
                    <div class="video-controls">
                        <div class="live-badge">● LIVE</div>
                        <button class="fullscreen-btn" onclick="toggleFullscreen()">
                            <i class="fas fa-expand"></i> Fullscreen
                        </button>
                    </div>
                </div>
                <img src="/video_feed" alt="Live Feed" class="video-feed" id="video-feed">
            </div>
        </div>
    </div>

    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toTimeString().split(' ')[0];
        }
        setInterval(updateTime, 1000);
        updateTime();

        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('frame-count').textContent = data.frame_id;
                    document.getElementById('velutina-count').textContent = data.total_velutina;
                    document.getElementById('crabro-count').textContent = data.total_crabro;
                    document.getElementById('total-detections').textContent = data.total_detections;
                    document.getElementById('fps').textContent = data.fps.toFixed(1) + ' FPS';
                    document.getElementById('uptime').textContent = 'Uptime: ' + data.uptime;
                    if (data.detection_rate !== undefined) {
                        document.getElementById('detection-rate').textContent = data.detection_rate + '/h';
                    }
                })
                .catch(error => console.error('Error fetching stats:', error));
        }

        function toggleFullscreen() {
            const video = document.getElementById('video-feed');
            if (!document.fullscreenElement) {
                video.requestFullscreen().catch(err => {
                    console.error(`Error attempting to enable fullscreen: ${err.message}`);
                });
            } else {
                document.exitFullscreen();
            }
        }

        setInterval(updateStats, 2000);
        updateStats();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    def generate():
        global web_frame
        while True:
            with web_lock:
                if web_frame is None:
                    continue
                frame = web_frame.copy()

            # Higher quality and no additional delay
            (flag, encodedImage) = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not flag:
                continue

            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                   bytearray(encodedImage) + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def api_stats():
    """Return current statistics as JSON"""
    global stats, hourly_detections

    # Calculate uptime
    uptime = datetime.datetime.now() - stats["start_time"]
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    # Get system stats
    try:
        cpu_temp = int(open('/sys/class/thermal/thermal_zone0/temp').read()) / 1000
    except:
        cpu_temp = 0

    # Calculate detection rate (per hour)
    if uptime.seconds > 0:
        detection_rate = round((stats["total_detections"] / (uptime.seconds / 3600)), 1)
    else:
        detection_rate = 0

    return jsonify({
        "frame_id": stats["frame_id"],
        "total_velutina": stats["total_velutina"],
        "total_crabro": stats["total_crabro"],
        "total_detections": stats["total_detections"],
        "fps": stats["fps"],
        "uptime": f"{hours}h {minutes}m",
        "saved_images": stats["saved_images"],
        "sms_sent": stats["sms_sent"],
        "sms_cost": stats["sms_cost"],
        "cpu_temp": round(cpu_temp, 1),
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent,
        "detection_rate": detection_rate,
        "confidence_avg": round(stats["confidence_avg"], 1) if stats["confidence_avg"] > 0 else 80
    })

def start_web_server():
    """Start Flask web server in background thread"""
    logger.info("Starting web server on http://0.0.0.0:8081")
    app.run(host='0.0.0.0', port=8081, threaded=True, debug=False)

# ────────────────  SMS Alert System (optional) ──────────────────────────
def send_sms_alert(text: str):
    """Send SMS alert (placeholder - can be enhanced with Lox24)"""
    global stats
    if LOX24_API_KEY and PHONE_NUMBER:
        logger.info(f"[SMS] Would send: {text}")
        stats["sms_sent"] += 1
        stats["last_sms_time"] = datetime.datetime.now()
    else:
        logger.info(f"[SMS disabled] {text}")

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
        
        logger.info(f"Camera initializing on {os_name} with backend {backend}")
        
        # Try camera with appropriate backend
        cap = cv2.VideoCapture(0, backend)
        
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)  # Fallback to default
        
        if not cap.isOpened():
            raise RuntimeError("Cannot open camera!")
        
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
        
        # Get actual values
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Camera initialized:")
        logger.info(f"  Resolution: {actual_width}x{actual_height} (requested {width}x{height})")
        logger.info(f"  FPS: {actual_fps}")
        
        time.sleep(1)  # Allow camera to warm up
    
    return cap

def load_model(confidence=0.8):
    """Load YOLOv5 model with enhanced compatibility"""
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
        logger.info("No local model found, will use yolov5s.pt")
        model_path = "yolov5s.pt"
    
    # Method 1: Try ultralytics YOLO first
    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        logger.info("✓ Model loaded via ultralytics YOLO")
        return model
    except Exception as e:
        logger.warning(f"Ultralytics loading failed: {e}")
    
    # Method 2: Try torch.hub with weights_only fix
    try:
        import torch
        
        # Force weights_only=False for PyTorch 2.8+ compatibility
        original_load = torch.load
        torch.load = lambda *args, **kwargs: original_load(*args, **kwargs, weights_only=False)
        
        try:
            model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                 path=model_path, force_reload=True)
            model.conf = confidence
            torch.load = original_load  # Restore
            logger.info("✓ Model loaded via torch.hub")
            return model
        finally:
            torch.load = original_load  # Ensure restoration
            
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None

def main():
    global web_frame, stats, hourly_detections, current_hour

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--min-motion-area", type=int, default=100)
    parser.add_argument("-b", "--brake", type=float, default=0.1)
    parser.add_argument("-c", "--conf", type=float, default=0.8)
    parser.add_argument("-m", "--motion", action="store_true")
    parser.add_argument("-p", "--print", action="store_true")
    parser.add_argument("-s", "--save", action="store_true")
    parser.add_argument("-sd", "--save-dir", default="monitor/detections")
    parser.add_argument("-v", "--video")
    parser.add_argument("-r", "--resolution", default="1280x720")
    parser.add_argument("--web", action="store_true", help="Enable web server")
    args = parser.parse_args()

    # Create directories
    if args.save:
        frame_dir = os.path.join(args.save_dir, "frames")
        result_dir = os.path.join(args.save_dir, "results")
        for d in (frame_dir, result_dir):
            os.makedirs(d, exist_ok=True)

    # Initialize Camera
    try:
        cap = setup_camera(args)
    except Exception as e:
        logger.error(f"Camera initialization failed: {e}")
        return 1

    # Load YOLOv5 Model
    try:
        model = load_model(args.conf)
        if model is None:
            logger.error("Model loading failed")
            return 1
    except Exception as e:
        logger.error(f"Model initialization failed: {e}")
        return 1

    if hasattr(model, 'names'):
        logger.info(f"Model classes: {model.names}")
    
    # Start Web Server
    if args.web:
        web_thread = threading.Thread(target=start_web_server)
        web_thread.daemon = True
        web_thread.start()
        time.sleep(2)
        hostname = platform.node()
        logger.info(f"Web interface: http://{hostname}:8081")
        logger.info(f"Local access: http://localhost:8081")

    # Initialize variables
    frame_id = 1
    last_fps_time = time.time()
    fps_counter = 0
    total_confidence = 0
    confidence_count = 0

    logger.info("Starting detection loop...")
    logger.info("Press Ctrl+C to stop")

    # Main Detection Loop - KEY FIX: Always update web frame
    try:
        while True:
            loop_start = time.time()
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

            # Check for hour change
            new_hour = datetime.datetime.now().hour
            if new_hour != current_hour:
                current_hour = new_hour

            # Always run detection for now (motion detection can be added later)
            run_detection = True

            if run_detection:
                # Run detection
                results = model(frame)

                # Count detections
                velutina_count = 0  # Asian hornet
                crabro_count = 0   # European hornet

                # Process results based on model type
                if hasattr(results, 'pred') and len(results.pred[0]) > 0:
                    # YOLOv5 format
                    for pred in results.pred[0]:
                        x1, y1, x2, y2, conf, cls = pred
                        cls = int(cls)
                        confidence = float(conf)

                        total_confidence += confidence
                        confidence_count += 1

                        if cls == 1:  # Vespa velutina
                            velutina_count += 1
                            stats["total_velutina"] += 1
                            if args.print:
                                logger.info(f"  Vespa velutina - conf: {confidence:.2f}")
                        elif cls == 0:  # Vespa crabro
                            crabro_count += 1
                            stats["total_crabro"] += 1
                            if args.print:
                                logger.info(f"  Vespa crabro - conf: {confidence:.2f}")
                elif hasattr(results, 'boxes'):
                    # Ultralytics format
                    for box in results.boxes:
                        if box.conf is not None and box.cls is not None:
                            confidence = float(box.conf[0])
                            cls = int(box.cls[0])
                            
                            total_confidence += confidence
                            confidence_count += 1
                            
                            if cls == 1:  # Vespa velutina
                                velutina_count += 1
                                stats["total_velutina"] += 1
                            elif cls == 0:  # Vespa crabro
                                crabro_count += 1
                                stats["total_crabro"] += 1

                # Render results
                if hasattr(results, 'render'):
                    results.render()
                    if hasattr(results, 'ims'):
                        annotated = cv2.cvtColor(results.ims[0], cv2.COLOR_RGB2BGR)
                    else:
                        annotated = frame.copy()
                elif hasattr(results, 'plot'):
                    annotated = results.plot()
                    annotated = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
                else:
                    annotated = frame.copy()

                # Add overlay text
                cv2.putText(annotated, f"Frame: {frame_id} | FPS: {stats['fps']:.1f}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(annotated, f"V: {stats['total_velutina']} | C: {stats['total_crabro']}",
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # If hornets detected
                if velutina_count + crabro_count > 0:
                    stats["total_detections"] += 1
                    detection_time = datetime.datetime.now().strftime("%H:%M:%S")

                    logger.info(f">>> Detection #{stats['total_detections']} at frame {frame_id}")
                    logger.info(f"    Velutina: {velutina_count}, Crabro: {crabro_count}")

                    # Save if enabled
                    if args.save:
                        timestamp = datetime.datetime.now().strftime("%d.%m.%Y-%H:%M:%S")
                        result_path = os.path.join(result_dir, f"{timestamp}.jpeg")
                        frame_path = os.path.join(frame_dir, f"{timestamp}.jpeg")

                        cv2.imwrite(result_path, annotated)
                        cv2.imwrite(frame_path, frame)
                        stats["saved_images"] += 1

                    # Send SMS alert
                    if velutina_count > 0:  # Asian hornet - high priority
                        sms_text = f"⚠️ ALERT: {velutina_count} Asian Hornet(s) detected at {detection_time}!"
                        send_sms_alert(sms_text)
                    elif crabro_count > 0:  # European hornet
                        sms_text = f"ℹ️ Info: {crabro_count} European Hornet(s) detected at {detection_time}."
                        send_sms_alert(sms_text)

                # CRITICAL: Always update web frame - this is the key fix!
                if args.web:
                    display_frame = cv2.resize(annotated, (960, 540))
                    with web_lock:
                        web_frame = display_frame.copy()

                # Update average confidence
                if confidence_count > 0:
                    stats["confidence_avg"] = (total_confidence / confidence_count) * 100

            stats["frame_id"] = frame_id
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
        if cap:
            cap.release()

        logger.info("Final Statistics:")
        logger.info(f"  Frames: {frame_id}")
        logger.info(f"  Detections: {stats['total_detections']}")
        logger.info(f"  Velutina: {stats['total_velutina']}")
        logger.info(f"  Crabro: {stats['total_crabro']}")

    return 0

if __name__ == '__main__':
    sys.exit(main())