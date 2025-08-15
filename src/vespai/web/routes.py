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
import numpy as np
import time


def convert_numpy_to_serializable(data):
    """
    Recursively convert numpy arrays and other non-serializable types to JSON-serializable types.
    
    Args:
        data: Any data structure that might contain numpy arrays
        
    Returns:
        JSON-serializable version of the data
    """
    if isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    elif isinstance(data, dict):
        return {key: convert_numpy_to_serializable(value) for key, value in data.items()}
    elif isinstance(data, (list, tuple)):
        return [convert_numpy_to_serializable(item) for item in data]
    else:
        return data


def register_routes(app, stats, hourly_detections, app_instance):
    """
    Register all essential web routes with the Flask app.
    
    Args:
        app (Flask): The Flask application instance
        stats (dict): Global statistics dictionary containing detection counts, system stats, etc.
        hourly_detections (dict): Dictionary tracking detections per hour (24-hour format)
        app_instance (VespAIApplication): The main application instance with web_frame and web_lock
    """
    
    # Cache for hourly data to avoid recalculating on every request
    hourly_data_cache = {
        'last_update': 0,
        'data_24h': [],
        'data_4h': []
    }
    
    @app.route('/')
    def index():
        """
        Serve the main dashboard page with live video feed and statistics.
        
        Returns:
            str: HTML content for the main VespAI dashboard
        """
        response = app.make_response(render_template('dashboard.html', timestamp=int(time.time())))
        # Prevent caching of the main dashboard page
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

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
                with app_instance.web_lock:
                    if app_instance.web_frame is None:
                        continue
                    frame = app_instance.web_frame.copy()

                # Higher quality and no additional delay (matching original)
                (flag, encodedImage) = cv2.imencode(".jpg", frame,
                                                    [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not flag:
                    continue

                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                       bytearray(encodedImage) + b'\r\n')

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
            # Optimized JPEG encoding with lower quality for faster loading
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                response = Response(buffer.tobytes(), mimetype='image/jpeg')
                # Add caching headers for better performance
                response.headers['Cache-Control'] = 'public, max-age=3600'
                response.headers['ETag'] = f'"{frame_id}"'
                return response
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
        if frame_id not in stats["detection_frames"]:
            return f"Frame {frame_id} not found", 404
            
        # Add caching headers for the HTML page as well
        response = app.make_response(render_template('frame.html', frame_id=frame_id))
        response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
        return response

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
        # Calculate uptime (matching original format)
        uptime = datetime.datetime.now() - stats["start_time"]
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        stats["uptime"] = f"{hours}h {minutes}m"

        # Get system stats (non-blocking)
        try:
            stats["cpu_usage"] = psutil.cpu_percent(interval=None)  # Non-blocking
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

        # Prepare hourly data with caching (only recalculate if detections changed)
        current_total_detections = stats.get("total_detections", 0)
        if hourly_data_cache['last_update'] != current_total_detections:
            # Recalculate hourly data
            hourly_data_cache['last_update'] = current_total_detections
            
            # 24-hour detailed data (matching original)
            hourly_data_cache['data_24h'] = []
            for hour in range(24):
                hourly_data_cache['data_24h'].append({
                    "hour": f"{hour:02d}:00",
                    "velutina": hourly_detections[hour]["velutina"],
                    "crabro": hourly_detections[hour]["crabro"],
                    "total": hourly_detections[hour]["velutina"] + hourly_detections[hour]["crabro"]
                })
            
            # 4-hour grouped data (for mobile)
            hourly_data_cache['data_4h'] = []
            for block in range(6):  # 6 blocks of 4 hours each
                start_hour = block * 4
                end_hour = start_hour + 3
                
                # Sum up detections for this 4-hour block
                block_velutina = 0
                block_crabro = 0
                for hour in range(start_hour, start_hour + 4):
                    block_velutina += hourly_detections[hour]["velutina"]
                    block_crabro += hourly_detections[hour]["crabro"]
                
                hourly_data_cache['data_4h'].append({
                    "hour": f"{start_hour:02d}-{end_hour:02d}h",
                    "velutina": block_velutina,
                    "crabro": block_crabro,
                    "total": block_velutina + block_crabro
                })
        
        # Use cached data
        hourly_data_24h = hourly_data_cache['data_24h']
        hourly_data_4h = hourly_data_cache['data_4h']

        response_data = dict(stats)
        response_data["hourly_data"] = hourly_data_24h  # Default to 24h for backward compatibility
        response_data["hourly_data_24h"] = hourly_data_24h  # Detailed 24-hour data
        response_data["hourly_data_4h"] = hourly_data_4h   # Grouped 4-hour data
        
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

        # Convert any numpy arrays to JSON-serializable types
        response_data = convert_numpy_to_serializable(response_data)
        
        return jsonify(response_data)


# Template files have been extracted to separate files:
# - dashboard.html: Main modern dashboard with custom styling and orange neon cursor
# - frame.html: Detection frame viewer page
# - legacy_dashboard.html: Legacy backup template for fallback compatibility