"""
Flask routes for VespAI web interface
"""
import cv2
import datetime
from flask import Response, render_template, jsonify, current_app
from web.app import get_web_frame

def register_routes(app):
    """Register all Flask routes"""
    
    @app.route('/')
    def index():
        """Main dashboard page"""
        return render_template('dashboard.html')
    
    @app.route('/video_feed')
    def video_feed():
        """Live video stream endpoint"""
        def generate():
            while True:
                frame = get_web_frame()
                if frame is None:
                    continue
                
                # Encode frame as JPEG
                success, encoded_image = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
                )
                if not success:
                    continue
                
                yield (b'--frame\r\n' 
                       b'Content-Type: image/jpeg\r\n\r\n' + 
                       bytearray(encoded_image) + b'\r\n')
        
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/api/stats')
    def api_stats():
        """API endpoint for real-time statistics"""
        stats_manager = current_app.config['STATS_MANAGER']
        return jsonify(stats_manager.get_api_stats())
    
    @app.route('/api/detection_frame/<frame_id>')
    def get_detection_frame(frame_id):
        """Return a specific detection frame as image"""
        stats_manager = current_app.config['STATS_MANAGER']
        frame = stats_manager.get_detection_frame(frame_id)
        
        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            response = Response(buffer.tobytes(), mimetype='image/jpeg')
            return response
        else:
            return "Frame not found", 404
    
    @app.route('/frame/<frame_id>')
    def serve_detection_frame(frame_id):
        """Serve detection frame with HTML page for SMS links"""
        stats_manager = current_app.config['STATS_MANAGER']
        frame = stats_manager.get_detection_frame(frame_id)
        
        if frame is not None:
            html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI Detection - Frame {frame_id}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: #0a0a0a;
            color: white;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            text-align: center;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            margin-bottom: 20px;
        }}
        .logo {{
            color: #ff6600;
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .frame-info {{
            background: rgba(255, 102, 0, 0.1);
            border: 1px solid #ff6600;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .detection-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(255, 102, 0, 0.3);
        }}
        .footer {{
            margin-top: 20px;
            font-size: 0.9rem;
            opacity: 0.7;
        }}
        .live-link {{
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: #ff6600;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }}
        .live-link:hover {{
            background: #ff4400;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🛡️ VespAI Monitor</div>
            <h1>Hornet Detection</h1>
        </div>
        
        <div class="frame-info">
            <h2>Detection Frame: {frame_id}</h2>
            <p>Captured: {datetime.datetime.now().strftime("%d.%m.%Y at %H:%M:%S")}</p>
        </div>
        
        <img src="/api/detection_frame/{frame_id}" alt="Detection Frame" class="detection-image">
        
        <div class="footer">
            <p>VespAI Hornet Detection System</p>
            <a href="/" class="live-link">📱 View Live Dashboard</a>
        </div>
    </div>
</body>
</html>
            '''
            return html_content
        else:
            available_frames = list(stats_manager.get_stats()["detection_frames"].keys())
            return f"Frame not found. Available frames: {available_frames}", 404
    
    @app.route('/api/frames')
    def list_frames():
        """List all available detection frames for debugging"""
        stats_manager = current_app.config['STATS_MANAGER']
        stats = stats_manager.get_stats()
        return jsonify({
            "available_frames": list(stats["detection_frames"].keys()),
            "frame_count": len(stats["detection_frames"])
        })