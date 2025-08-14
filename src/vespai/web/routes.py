#!/usr/bin/env python3
"""
VespAI Web Routes Module

This module contains all essential Flask web routes for the VespAI hornet detection system.
Routes extracted from the working web_preview.py implementation to provide a clean,
modular web interface.

Key Features:
- Live MJPEG video streaming from camera
- Real-time detection statistics API
- Detection frame viewing with SMS-friendly links
- System monitoring (CPU, RAM, temperature)
- Interactive dashboard with live updates

Routes:
- GET /: Main dashboard page
- GET /video_feed: Live MJPEG video stream
- GET /api/stats: Real-time system statistics JSON
- GET /api/detection_frame/<id>: Individual detection frame images
- GET /frame/<id>: HTML page for viewing detection frames
- GET /api/frames: List all available detection frames

Author: VespAI Team
Version: 1.0
"""

import cv2
import psutil
import datetime
from flask import Response, render_template, jsonify
import os


def register_routes(app, stats, hourly_detections, web_frame, web_lock):
    """
    Register all essential web routes with the Flask app.
    
    Args:
        app (Flask): The Flask application instance
        stats (dict): Global statistics dictionary containing detection counts, system stats, etc.
        hourly_detections (dict): Dictionary tracking detections per hour (24-hour format)
        web_frame (numpy.ndarray): Current video frame for streaming
        web_lock (threading.Lock): Thread lock for safe web frame access
    """
    
    @app.route('/')
    def index():
        """
        Serve the main dashboard page with live video feed and statistics.
        
        Returns:
            str: HTML content for the main VespAI dashboard
        """
        return render_template('dashboard.html')

    @app.route('/video_feed')
    def video_feed():
        """
        Provide live MJPEG video stream from the camera.
        
        This endpoint streams live video frames in Motion JPEG format using 
        multipart HTTP response. Frames are continuously encoded and sent
        to connected clients.
        
        Returns:
            Response: Flask Response object with MJPEG stream mimetype
        """
        def generate():
            """
            Generator function that yields MJPEG frames for streaming.
            
            Yields:
                bytes: MJPEG frame data with HTTP multipart boundaries
            """
            while True:
                with web_lock:
                    if web_frame is not None:
                        # Encode frame to JPEG
                        ret, buffer = cv2.imencode('.jpg', web_frame)
                        if ret:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/api/detection_frame/<frame_id>')
    def get_detection_frame(frame_id):
        """
        Return a specific detection frame as JPEG image.
        
        Args:
            frame_id (str): Unique identifier for the detection frame
            
        Returns:
            Response: JPEG image data or 404 error if frame not found
        """
        if frame_id in stats["detection_frames"]:
            frame = stats["detection_frames"][frame_id]
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                return Response(buffer.tobytes(), mimetype='image/jpeg')
        return "Frame not found", 404

    @app.route('/frame/<frame_id>')
    def serve_detection_frame(frame_id):
        """
        Serve detection frame with HTML page for SMS links and viewing.
        
        This creates a user-friendly HTML page that displays the detection frame
        with navigation options. Primarily used for SMS alert links.
        
        Args:
            frame_id (str): Unique identifier for the detection frame
            
        Returns:
            str: HTML page with detection frame or 404 error message
        """
        print(f"[DEBUG] Requested frame_id: {frame_id}")
        print(f"[DEBUG] Available frames: {list(stats['detection_frames'].keys())}")
        
        if frame_id not in stats["detection_frames"]:
            return f"Frame {frame_id} not found", 404
            
        return render_template_string(FRAME_TEMPLATE, frame_id=frame_id)

    @app.route('/api/frames')
    def list_frames():
        """
        List all available detection frames for debugging purposes.
        
        Returns:
            dict: JSON response containing list of available frame IDs and count
        """
        return jsonify({
            "available_frames": list(stats["detection_frames"].keys()),
            "total_frames": len(stats["detection_frames"])
        })

    @app.route('/api/stats')
    def api_stats():
        """
        Return current system and detection statistics as JSON.
        
        This endpoint provides real-time statistics including:
        - Detection counts (Asian/European hornets, total)
        - System performance (CPU, RAM, temperature, uptime)
        - SMS alert statistics
        - Hourly detection data for charts
        - Recent detection log entries
        
        Returns:
            dict: JSON response with complete system statistics
        """
        # Calculate uptime
        uptime_seconds = (datetime.datetime.now() - stats["start_time"]).total_seconds()
        stats["uptime"] = uptime_seconds

        # Get system stats
        try:
            stats["cpu_usage"] = psutil.cpu_percent(interval=0.1)
            stats["ram_usage"] = psutil.virtual_memory().percent
            stats["disk_usage"] = psutil.disk_usage('/').percent
        except:
            pass

        # CPU temperature (Raspberry Pi)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read()) / 1000
                stats["cpu_temp"] = temp
        except:
            stats["cpu_temp"] = 0

        # Prepare hourly data for chart
        hourly_data = []
        for hour in range(24):
            hourly_data.append({
                "hour": f"{hour:02d}:00",
                "velutina": hourly_detections[hour]["velutina"],
                "crabro": hourly_detections[hour]["crabro"],
                "total": hourly_detections[hour]["velutina"] + hourly_detections[hour]["crabro"]
            })

        response_data = dict(stats)
        response_data["hourly_data"] = hourly_data
        
        # Add missing fields with defaults if not present
        response_data.setdefault("sms_sent", 0)
        response_data.setdefault("sms_cost", 0.0)
        response_data.setdefault("saved_images", 0)
        response_data.setdefault("last_sms_time", None)
        
        # Convert deque to list for JSON serialization
        if "detection_log" in response_data:
            response_data["detection_log"] = list(response_data["detection_log"])
        if "hourly_stats" in response_data:
            response_data["hourly_stats"] = list(response_data["hourly_stats"])
        
        # Format timestamps
        if response_data.get("last_detection_time"):
            response_data["last_detection_time"] = response_data["last_detection_time"].strftime("%H:%M:%S")
        if response_data.get("last_sms_time"):
            response_data["last_sms_time"] = response_data["last_sms_time"].strftime("%H:%M:%S")
            
        if response_data.get("start_time"):
            response_data["start_time"] = response_data["start_time"].strftime("%H:%M:%S")

        return jsonify(response_data)


# HTML Templates extracted from working web_preview.py
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI - Hornet Detection System</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .video-section {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .video-container {
            position: relative;
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .video-stream {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .stats-section {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .velutina { color: #ff4444; }
        .crabro { color: #44ff44; }
        .total { color: #ffaa44; }
        
        .system-stats {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .system-stats h3 {
            margin-bottom: 15px;
            text-align: center;
        }
        
        .system-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .detections-section {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .detection-log {
            max-height: 300px;
            overflow-y: auto;
            margin-top: 15px;
        }
        
        .detection-item {
            background: rgba(255,255,255,0.1);
            margin: 5px 0;
            padding: 10px;
            border-radius: 8px;
            border-left: 4px solid #44ff44;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .detection-item:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .detection-item.velutina {
            border-left-color: #ff4444;
        }
        
        .detection-time {
            font-size: 0.8rem;
            opacity: 0.7;
        }
        
        .status-bar {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 15px;
            margin-top: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            text-align: center;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #44ff44;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐝 VespAI Detection System</h1>
            <p>Real-time Asian & European Hornet Detection</p>
        </div>
        
        <div class="main-grid">
            <div class="video-section">
                <h2 style="margin-bottom: 15px;">📹 Live Camera Feed</h2>
                <div class="video-container">
                    <img src="/video_feed" alt="Live Video Feed" class="video-stream">
                </div>
            </div>
            
            <div class="stats-section">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value velutina" id="velutina-count">0</div>
                        <div class="stat-label">Asian Hornets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value crabro" id="crabro-count">0</div>
                        <div class="stat-label">European Hornets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value total" id="total-count">0</div>
                        <div class="stat-label">Total Detections</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="fps">0</div>
                        <div class="stat-label">FPS</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="sms-count">0</div>
                        <div class="stat-label">SMS Alerts</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="sms-cost">0.00€</div>
                        <div class="stat-label">SMS Costs</div>
                    </div>
                </div>
                
                <div class="system-stats">
                    <h3>📊 System Status</h3>
                    <div class="system-grid">
                        <div>CPU: <span id="cpu-usage">0%</span></div>
                        <div>RAM: <span id="ram-usage">0%</span></div>
                        <div>Temp: <span id="cpu-temp">0°C</span></div>
                        <div>Uptime: <span id="uptime">0s</span></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="detections-section">
            <h2>📋 Recent Detections</h2>
            <div class="detection-log" id="detection-log">
                <p style="opacity: 0.7; text-align: center;">No detections yet...</p>
            </div>
        </div>
        
        <div class="status-bar">
            <span class="status-indicator"></span>
            System Active - Monitoring for hornets...
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('velutina-count').textContent = data.total_velutina;
                    document.getElementById('crabro-count').textContent = data.total_crabro;
                    document.getElementById('total-count').textContent = data.total_detections;
                    document.getElementById('fps').textContent = data.fps.toFixed(1);
                    document.getElementById('sms-count').textContent = data.sms_sent;
                    document.getElementById('sms-cost').textContent = data.sms_cost.toFixed(2) + '€';
                    
                    // Update system stats
                    document.getElementById('cpu-usage').textContent = data.cpu_usage.toFixed(1) + '%';
                    document.getElementById('ram-usage').textContent = data.ram_usage.toFixed(1) + '%';
                    document.getElementById('cpu-temp').textContent = data.cpu_temp.toFixed(1) + '°C';
                    
                    // Format uptime
                    const uptime = data.uptime;
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    document.getElementById('uptime').textContent = `${hours}h ${minutes}m`;
                    
                    // Update detection log
                    const logDiv = document.getElementById('detection-log');
                    if (data.detection_log && data.detection_log.length > 0) {
                        logDiv.innerHTML = '';
                        data.detection_log.slice(-10).reverse().forEach(detection => {
                            const item = document.createElement('div');
                            item.className = `detection-item ${detection.species === 'velutina' ? 'velutina' : 'crabro'}`;
                            item.onclick = () => window.open(`/frame/${detection.frame_id}`, '_blank');
                            item.innerHTML = `
                                <strong>${detection.species === 'velutina' ? '🐝 Asian Hornet' : '🐛 European Hornet'}</strong>
                                <div class="detection-time">${detection.timestamp} - Confidence: ${detection.confidence}%</div>
                            `;
                            logDiv.appendChild(item);
                        });
                    }
                })
                .catch(error => console.error('Error fetching stats:', error));
        }
        
        // Update every 2 seconds
        setInterval(updateStats, 2000);
        updateStats(); // Initial load
    </script>
</body>
</html>'''

FRAME_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI - Detection Frame</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .frame-container {
            max-width: 90vw;
            max-height: 70vh;
            border: 2px solid #444;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        
        .frame-image {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .actions {
            margin-top: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .btn {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background 0.3s;
        }
        
        .btn:hover {
            background: #0056b3;
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-secondary:hover {
            background: #545b62;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐝 VespAI Detection</h1>
        <p>Detection Frame: {{ frame_id }}</p>
    </div>
    
    <div class="frame-container">
        <img src="/api/detection_frame/{{ frame_id }}" alt="Detection Frame" class="frame-image">
    </div>
    
    <div class="actions">
        <a href="/" class="btn">📊 Back to Dashboard</a>
        <a href="/api/detection_frame/{{ frame_id }}" class="btn btn-secondary" download="detection_{{ frame_id }}.jpg">💾 Download Image</a>
    </div>
</body>
</html>'''