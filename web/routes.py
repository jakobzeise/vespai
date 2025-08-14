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
        """Main dashboard page - reliable JavaScript feed without page reload"""
        import time
        stats_manager = current_app.config['STATS_MANAGER']
        stats = stats_manager.get_stats()
        
        return render_template('reliable_feed.html',
                             timestamp=time.strftime("%H:%M:%S"),
                             timestamp_ms=int(time.time() * 1000),
                             frame_id=stats.get('frame_id', 0),
                             fps=stats.get('fps', 0.0))
    
    @app.route('/dashboard')
    def dashboard():
        """Full dashboard page"""
        return render_template('dashboard.html')
        
    @app.route('/test')
    def test_video():
        """Simple test page for video debugging"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>VespAI Video Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #000; color: #fff; }
        .test-container { max-width: 800px; margin: 0 auto; }
        img, video { border: 2px solid #ff6600; margin: 10px 0; }
        .info { background: #333; padding: 20px; margin: 10px 0; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="test-container">
        <h1>🐝 VespAI Video Stream Test</h1>
        
        <div class="info">
            <h3>Test 1: Static Image</h3>
            <p>This should show a static test image:</p>
            <img src="/debug_frame.jpg" alt="Debug Frame" style="width: 480px;">
        </div>
        
        <div class="info">
            <h3>Test 2: MJPEG Stream (as IMG)</h3>
            <p>This should show the live video stream:</p>
            <img src="/video_feed" alt="Live Feed" style="width: 480px;">
        </div>
        
        <div class="info">
            <h3>Test 3: MJPEG Stream (as VIDEO)</h3>
            <p>Alternative video element:</p>
            <video width="480" autoplay muted>
                <source src="/video_feed" type="video/mp4">
                Your browser does not support video.
            </video>
        </div>
        
        <div class="info">
            <p><a href="/" style="color: #ff6600;">← Back to main dashboard</a></p>
        </div>
    </div>
</body>
</html>'''
    
    @app.route('/video_feed')
    def video_feed():
        """Live video stream endpoint with enhanced cache-busting"""
        def generate():
            import time
            import uuid
            import numpy as np
            import random
            
            # Generate unique session ID for this stream
            session_id = str(uuid.uuid4())[:8]
            frame_counter = 0
            
            while True:
                frame = get_web_frame()
                frame_counter += 1
                
                if frame is None:
                    # Create a fallback "waiting" frame
                    fallback_frame = np.zeros((540, 960, 3), dtype=np.uint8)
                    cv2.putText(fallback_frame, "VespAI - Initializing Camera...", (200, 270), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 102, 0), 2)
                    frame = fallback_frame
                else:
                    # Add live timestamp overlay with microseconds
                    current_time = time.time()
                    timestamp = time.strftime("%H:%M:%S", time.localtime(current_time))
                    microsec = int((current_time % 1) * 1000000)
                    cv2.putText(frame, f"LIVE {timestamp}.{microsec:06d}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Add moving visual indicator to force frame differences
                    dot_x = 50 + int(30 * np.sin(current_time * 2))  # Moving dot
                    color = (
                        int(127 + 127 * np.sin(current_time * 3)),
                        int(127 + 127 * np.cos(current_time * 2.5)),
                        int(127 + 127 * np.sin(current_time * 1.8))
                    )
                    cv2.circle(frame, (dot_x, 70), 8, color, -1)
                    
                    # Frame session info
                    cv2.putText(frame, f"#{frame_counter} [{session_id}]", (10, frame.shape[0] - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                
                # Add noise to ensure each frame is unique
                noise = np.random.randint(0, 2, (2, 2, 3), dtype=np.uint8)
                frame[:2, :2] = noise
                
                # Encode frame as JPEG
                success, encoded_image = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80]
                )
                if not success:
                    time.sleep(0.1)
                    continue
                
                # Generate unique boundary per frame
                boundary_id = f"frame_{frame_counter}_{int(current_time * 1000000)}"
                
                # MJPEG multipart boundary with content length
                content_length = len(encoded_image.tobytes())
                yield (f'--{boundary_id}\r\n'
                       f'Content-Type: image/jpeg\r\n'
                       f'Content-Length: {content_length}\r\n'
                       f'X-Frame-ID: {frame_counter}\r\n'
                       f'X-Timestamp: {int(current_time * 1000)}\r\n'
                       '\r\n').encode() + encoded_image.tobytes() + b'\r\n'
                
                time.sleep(0.05)  # 20 FPS for better stability
        
        response = Response(generate(),
                           mimetype='multipart/x-mixed-replace; boundary=frame')
        
        # Ultra-aggressive cache prevention headers
        response.headers.update({
            'Cache-Control': 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0',
            'Pragma': 'no-cache',
            'Expires': 'Thu, 01 Jan 1970 00:00:00 GMT',
            'Last-Modified': 'Thu, 01 Jan 1970 00:00:00 GMT',
            'ETag': None,
            'Connection': 'close',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Access-Control-Allow-Origin': '*',
            'Vary': '*'
        })
        return response
    
    @app.route('/video_sse')
    def video_sse():
        """Server-Sent Events video stream (alternative to MJPEG)"""
        def generate():
            import time
            import base64
            import json
            
            while True:
                frame = get_web_frame()
                
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Encode frame to base64 for SSE transmission
                success, encoded_image = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if not success:
                    time.sleep(0.1)
                    continue
                
                # Convert to base64
                frame_b64 = base64.b64encode(encoded_image.tobytes()).decode('utf-8')
                
                # Create SSE data payload
                sse_data = json.dumps({
                    'type': 'frame',
                    'data': frame_b64,
                    'timestamp': int(time.time() * 1000)
                })
                
                yield f"data: {sse_data}\n\n"
                time.sleep(0.1)  # 10 FPS for SSE
        
        response = Response(generate(), mimetype='text/event-stream')
        response.headers.update({
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        })
        return response
    
    @app.route('/video_live')
    def video_live():
        """Alternative live video stream with different headers"""
        def generate():
            import time
            import numpy as np
            import random
            
            while True:
                frame = get_web_frame()
                
                if frame is None:
                    # Create colorful fallback frame
                    fallback_frame = np.zeros((540, 960, 3), dtype=np.uint8)
                    # Add some color to make it obvious
                    fallback_frame[:, :, 1] = 50  # Green channel
                    cv2.putText(fallback_frame, "VespAI - Connecting to Camera...", (180, 270), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    frame = fallback_frame
                else:
                    # Make timestamp very obvious
                    current_time = time.time()
                    timestamp = time.strftime("%H:%M:%S", time.localtime(current_time))
                    millisec = int((current_time % 1) * 1000)
                    
                    # Add dynamic elements to prove it's updating
                    cv2.putText(frame, f"LIVE {timestamp}.{millisec:03d}", (10, 40), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                    
                    # Add random color dot that changes every frame
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                    cv2.circle(frame, (50, 80), 10, color, -1)
                    
                    # Frame counter
                    frame_counter = int(current_time * 2) % 9999
                    cv2.putText(frame, f"Frame #{frame_counter}", (10, 480), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # Encode frame
                success, encoded_image = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80]
                )
                if not success:
                    time.sleep(0.1)
                    continue
                
                # Simple boundary
                boundary = f"--boundary{int(time.time() * 1000)}\r\n"
                yield (boundary.encode() +
                       b'Content-Type: image/jpeg\r\n\r\n' + 
                       encoded_image.tobytes() + b'\r\n')
                
                time.sleep(0.1)  # 10 FPS for testing
        
        response = Response(generate(),
                           mimetype='multipart/x-mixed-replace; boundary=boundary')
        response.headers.update({
            'Cache-Control': 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1',
            'Connection': 'close',
            'Access-Control-Allow-Origin': '*'
        })
        return response
    
    @app.route('/chrome_test')
    def chrome_test():
        """Chrome-optimized video test"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>VespAI Chrome Test</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #1a1a1a; 
            color: #fff; 
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .test-section { 
            margin: 20px 0; 
            padding: 20px; 
            border: 1px solid #4CAF50; 
            border-radius: 8px; 
            background: #2a2a2a;
        }
        img { 
            border: 2px solid #4CAF50; 
            margin: 10px; 
            max-width: 640px;
            height: auto;
        }
        .status { 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 6px; 
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        .good { background: #1b4332; color: #40ff40; border: 1px solid #40ff40; }
        .error { background: #4a0e0e; color: #ff4040; border: 1px solid #ff4040; }
        .info { background: #1e3a5f; color: #40a0ff; border: 1px solid #40a0ff; }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 12px 24px;
            margin: 8px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s;
        }
        button:hover { background: #45a049; }
        button:disabled { background: #666; cursor: not-allowed; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-box {
            background: #333;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            font-size: 12px;
            color: #aaa;
            margin-top: 5px;
        }
    </style>
    <script>
        let pollingInterval = null;
        let requestCount = 0;
        let successCount = 0;
        let errorCount = 0;
        let startTime = Date.now();
        
        function updateStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
        }
        
        function updateStats() {
            document.getElementById('requests').textContent = requestCount;
            document.getElementById('successes').textContent = successCount;
            document.getElementById('errors').textContent = errorCount;
            document.getElementById('uptime').textContent = Math.floor((Date.now() - startTime) / 1000) + 's';
            
            const successRate = requestCount > 0 ? Math.floor((successCount / requestCount) * 100) : 0;
            document.getElementById('success-rate').textContent = successRate + '%';
        }
        
        function startTesting() {
            const img = document.getElementById('test-img');
            updateStatus('Starting Chrome-optimized video polling...', 'info');
            
            function updateFrame() {
                requestCount++;
                const timestamp = Date.now();
                const newSrc = `/current_frame.jpg?chrome=true&t=${timestamp}&frame=${requestCount}`;
                
                // Chrome-optimized approach: simple and direct
                const testImg = new Image();
                
                testImg.onload = function() {
                    img.src = newSrc;
                    successCount++;
                    updateStatus(`✓ Frame ${requestCount} loaded successfully at ${new Date().toLocaleTimeString()}`, 'good');
                    updateStats();
                };
                
                testImg.onerror = function() {
                    errorCount++;
                    updateStatus(`✗ Frame ${requestCount} failed to load at ${new Date().toLocaleTimeString()}`, 'error');
                    updateStats();
                };
                
                testImg.src = newSrc;
                updateStats();
            }
            
            updateFrame(); // Immediate update
            pollingInterval = setInterval(updateFrame, 500); // 2 FPS
            
            document.getElementById('start-btn').disabled = true;
            document.getElementById('stop-btn').disabled = false;
        }
        
        function stopTesting() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
            updateStatus('Testing stopped', 'info');
            document.getElementById('start-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
        }
        
        // Initialize on load
        window.onload = function() {
            updateStats();
            document.getElementById('browser-info').textContent = navigator.userAgent;
        };
    </script>
</head>
<body>
    <div class="container">
        <h1>🐝 VespAI Chrome Test</h1>
        
        <div class="test-section">
            <h2>Browser Information</h2>
            <div style="font-family: monospace; font-size: 12px; color: #aaa; word-break: break-all;" id="browser-info"></div>
        </div>
        
        <div class="test-section">
            <h2>Live Video Test</h2>
            <div class="status info" id="status">Click 'Start Test' to begin Chrome-optimized video polling</div>
            
            <div>
                <button id="start-btn" onclick="startTesting()">▶️ Start Test</button>
                <button id="stop-btn" onclick="stopTesting()" disabled>⏹️ Stop Test</button>
                <button onclick="location.reload()">🔄 Reload Page</button>
            </div>
            
            <div style="margin-top: 20px;">
                <img id="test-img" src="/current_frame.jpg" alt="Live Feed" style="width: 640px;">
            </div>
        </div>
        
        <div class="test-section">
            <h2>Statistics</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value" id="requests">0</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="successes">0</div>
                    <div class="stat-label">Successful Loads</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="errors">0</div>
                    <div class="stat-label">Failed Loads</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="success-rate">0%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="uptime">0s</div>
                    <div class="stat-label">Test Duration</div>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 30px; text-align: center;">
            <p><a href="/" style="color: #4CAF50; text-decoration: none;">← Back to main dashboard</a></p>
        </div>
    </div>
</body>
</html>'''
    
    @app.route('/canvas_test')
    def canvas_test():
        """Canvas-based video (Safari-proof)"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>VespAI Canvas Test (Safari-Proof)</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #000; 
            color: #fff; 
        }
        .test-section { 
            margin: 20px 0; 
            padding: 20px; 
            border: 1px solid #ff6600; 
            border-radius: 8px; 
        }
        canvas { 
            border: 2px solid #ff6600; 
            margin: 10px; 
        }
        .status { 
            padding: 10px; 
            margin: 10px 0; 
            border-radius: 4px; 
            font-family: monospace;
        }
        .good { background: #003300; color: #00ff00; }
        .error { background: #330000; color: #ff0000; }
        .info { background: #003366; color: #00ffff; }
        button {
            background: #ff6600;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
        }
    </style>
    <script>
        let canvasInterval = null;
        let canvas = null;
        let ctx = null;
        let requestCount = 0;
        
        function isSafari() {
            return navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome');
        }
        
        function updateStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
        }
        
        function startCanvas() {
            canvas = document.getElementById('video-canvas');
            ctx = canvas.getContext('2d');
            updateStatus('Starting Canvas mode (Safari-proof)...', 'info');
            
            function updateCanvasFrame() {
                requestCount++;
                const timestamp = Date.now();
                const newSrc = `/current_frame.jpg?canvas=true&t=${timestamp}&r=${Math.random()}`;
                
                const img = new Image();
                img.crossOrigin = 'anonymous';
                
                img.onload = function() {
                    // Clear canvas and draw new image
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    
                    // Add canvas-specific overlay
                    ctx.fillStyle = '#00ff00';
                    ctx.font = '16px Arial';
                    ctx.fillText(`CANVAS UPDATE #${requestCount}`, 10, 30);
                    ctx.fillText(`${new Date().toLocaleTimeString()}`, 10, 50);
                    
                    updateStatus(`✓ Canvas update ${requestCount} SUCCESS (${isSafari() ? 'Safari' : 'Other'})`, 'good');
                };
                
                img.onerror = function() {
                    updateStatus(`✗ Canvas update ${requestCount} FAILED`, 'error');
                };
                
                img.src = newSrc;
            }
            
            updateCanvasFrame(); // Immediate update
            canvasInterval = setInterval(updateCanvasFrame, 1000); // 1 FPS for testing
            
            document.getElementById('start-btn').disabled = true;
            document.getElementById('stop-btn').disabled = false;
        }
        
        function stopCanvas() {
            if (canvasInterval) {
                clearInterval(canvasInterval);
                canvasInterval = null;
            }
            updateStatus('Canvas stopped', 'info');
            document.getElementById('start-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
        }
    </script>
</head>
<body>
    <h1>🐝 VespAI Canvas Test (Safari-Proof)</h1>
    
    <div class="test-section">
        <h2>Canvas-Based Video (Cannot Be Cached)</h2>
        <p>This uses HTML5 Canvas instead of IMG elements - Safari CANNOT cache this!</p>
        
        <div class="status info" id="status">Click 'Start Canvas' to begin</div>
        
        <div>
            <button id="start-btn" onclick="startCanvas()">🎨 Start Canvas Mode</button>
            <button id="stop-btn" onclick="stopCanvas()" disabled>⏹️ Stop Canvas</button>
        </div>
        
        <div style="margin-top: 20px;">
            <canvas id="video-canvas" width="640" height="360" style="background: #222;"></canvas>
        </div>
        
        <div style="margin-top: 20px; font-size: 0.9em; color: #aaa;">
            <p><strong>Canvas Benefits:</strong></p>
            <ul>
                <li>✅ Safari cannot cache canvas drawings</li>
                <li>✅ Direct pixel manipulation</li>
                <li>✅ Guaranteed to update every time</li>
                <li>✅ Works identically on all browsers</li>
            </ul>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <p><a href="/" style="color: #ff6600;">← Back to main dashboard</a></p>
    </div>
</body>
</html>'''
    
    @app.route('/safari_debug')
    def safari_debug():
        """Safari-specific debugging page"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>VespAI Safari Debug</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #000; 
            color: #fff; 
        }
        .debug-section { 
            margin: 20px 0; 
            padding: 20px; 
            border: 1px solid #ff6600; 
            border-radius: 8px; 
        }
        img { 
            border: 2px solid #ff6600; 
            margin: 10px; 
            width: 480px;
        }
        .status { 
            padding: 10px; 
            margin: 10px 0; 
            border-radius: 4px; 
            font-family: monospace;
        }
        .good { background: #003300; color: #00ff00; }
        .error { background: #330000; color: #ff0000; }
        .info { background: #003366; color: #00ffff; }
        button {
            background: #ff6600;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
        }
    </style>
    <script>
        let debugInterval = null;
        let requestCount = 0;
        
        function isSafari() {
            return navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome');
        }
        
        function updateStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
        }
        
        function startDebug() {
            const img = document.getElementById('debug-img');
            updateStatus('Starting Safari debug mode...', 'info');
            
            function updateFrame() {
                requestCount++;
                const timestamp = Date.now();
                const microseconds = performance.now() * 1000;
                const newSrc = `/current_frame.jpg?debug=safari&t=${timestamp}&micro=${microseconds}&req=${requestCount}&r=${Math.random()}`;
                
                const testImg = new Image();
                testImg.crossOrigin = 'anonymous';
                
                testImg.onload = function() {
                    // NUCLEAR SAFARI CACHE BYPASS: Replace entire element
                    if (isSafari()) {
                        const parent = img.parentNode;
                        const newImg = document.createElement('img');
                        newImg.id = 'debug-img';
                        newImg.src = newSrc;
                        newImg.alt = 'Debug Frame';
                        newImg.style.cssText = img.style.cssText;
                        
                        parent.replaceChild(newImg, img);
                        img = newImg; // Update reference
                        
                        updateStatus(`✓ Request ${requestCount} SUCCESS at ${new Date().toLocaleTimeString()} (Safari-NUCLEAR)`, 'good');
                    } else {
                        img.src = newSrc;
                        updateStatus(`✓ Request ${requestCount} SUCCESS at ${new Date().toLocaleTimeString()} (Standard Mode)`, 'good');
                    }
                };
                
                testImg.onerror = function() {
                    updateStatus(`✗ Request ${requestCount} FAILED at ${new Date().toLocaleTimeString()}`, 'error');
                };
                
                testImg.src = newSrc;
            }
            
            updateFrame(); // Immediate update
            debugInterval = setInterval(updateFrame, 1000); // 1 FPS for clear debugging
            
            document.getElementById('start-btn').disabled = true;
            document.getElementById('stop-btn').disabled = false;
        }
        
        function stopDebug() {
            if (debugInterval) {
                clearInterval(debugInterval);
                debugInterval = null;
            }
            updateStatus('Debug stopped', 'info');
            document.getElementById('start-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
        }
        
        // Show browser info on load
        window.onload = function() {
            document.getElementById('browser-info').innerHTML = 
                `Browser: ${navigator.userAgent}<br>` +
                `Safari Detected: ${isSafari()}<br>` +
                `Timestamp: ${Date.now()}`;
        };
    </script>
</head>
<body>
    <h1>🐝 VespAI Safari Debug Mode</h1>
    
    <div class="debug-section">
        <h2>Browser Detection</h2>
        <div id="browser-info" style="font-family: monospace; font-size: 12px; color: #aaa;"></div>
    </div>
    
    <div class="debug-section">
        <h2>Safari Cache Debug Test</h2>
        <div class="status info" id="status">Click 'Start Debug' to begin testing</div>
        
        <div>
            <button id="start-btn" onclick="startDebug()">🔍 Start Debug (1 FPS)</button>
            <button id="stop-btn" onclick="stopDebug()" disabled>⏹️ Stop Debug</button>
            <button onclick="location.reload()">🔄 Reload Page</button>
        </div>
        
        <div style="margin-top: 20px;">
            <img id="debug-img" src="/current_frame.jpg" alt="Debug Frame">
        </div>
        
        <div style="margin-top: 20px; font-size: 0.9em; color: #aaa;">
            <p><strong>What to look for:</strong></p>
            <ul>
                <li>SUCCESS messages should appear every second</li>
                <li>Image should show live timestamp updating</li>
                <li>Moving colored dot should change position</li>
                <li>If image stays static = Safari caching issue confirmed</li>
            </ul>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <p><a href="/" style="color: #ff6600;">← Back to main dashboard</a></p>
    </div>
</body>
</html>'''
    
    @app.route('/universal_test') 
    def universal_test():
        """Universal compatibility test page"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>VespAI Universal Compatibility Test</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #000; 
            color: #fff; 
        }
        .test-section { 
            margin: 20px 0; 
            padding: 20px; 
            border: 1px solid #ff6600; 
            border-radius: 8px; 
        }
        img { 
            border: 2px solid #ff6600; 
            margin: 10px; 
            max-width: 640px;
        }
        button {
            background: #ff6600;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover { background: #e55a00; }
        .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .status.good { background: #003300; color: #00ff00; }
        .status.error { background: #330000; color: #ff0000; }
        .status.info { background: #003366; color: #00ffff; }
    </style>
    <script>
        let pollingInterval = null;
        
        function startPolling() {
            const img = document.getElementById('live-frame');
            const status = document.getElementById('status');
            
            function updateFrame() {
                const timestamp = Date.now();
                const newSrc = `/current_frame.jpg?t=${timestamp}&r=${Math.random()}`;
                
                const testImg = new Image();
                testImg.onload = function() {
                    img.src = newSrc;
                    status.className = 'status good';
                    status.textContent = `✓ Live update: ${new Date().toLocaleTimeString()}`;
                };
                testImg.onerror = function() {
                    status.className = 'status error';
                    status.textContent = `✗ Failed to load frame at ${new Date().toLocaleTimeString()}`;
                };
                testImg.src = newSrc;
            }
            
            updateFrame(); // Immediate update
            pollingInterval = setInterval(updateFrame, 500); // 2 FPS for testing
            
            document.getElementById('start-btn').disabled = true;
            document.getElementById('stop-btn').disabled = false;
        }
        
        function stopPolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
            
            const status = document.getElementById('status');
            status.className = 'status info';
            status.textContent = 'Polling stopped';
            
            document.getElementById('start-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
        }
    </script>
</head>
<body>
    <h1>🐝 VespAI Universal Compatibility Test</h1>
    
    <div class="test-section">
        <h2>Universal Image Polling (Works on All Browsers/Platforms)</h2>
        <p>This method uses simple JavaScript image polling - compatible with:</p>
        <ul>
            <li>Safari (macOS) - Aggressive caching handled</li>
            <li>Chrome (Windows/Mac/Linux) - Full compatibility</li> 
            <li>Firefox (All platforms) - Full compatibility</li>
            <li>Edge (Windows) - Full compatibility</li>
            <li>Mobile browsers - Full compatibility</li>
        </ul>
        
        <div class="status info" id="status">Click 'Start' to begin polling</div>
        
        <div>
            <button id="start-btn" onclick="startPolling()">▶️ Start Live Feed</button>
            <button id="stop-btn" onclick="stopPolling()" disabled>⏹️ Stop Feed</button>
        </div>
        
        <div style="margin-top: 20px;">
            <img id="live-frame" src="/current_frame.jpg" alt="Live Feed" style="width: 640px; height: auto;">
        </div>
        
        <div style="margin-top: 20px; font-size: 0.9em; color: #aaa;">
            <p><strong>How it works:</strong></p>
            <ul>
                <li>JavaScript polls /current_frame.jpg every 500ms</li>
                <li>Each request has unique timestamp parameters</li>
                <li>Ultra-aggressive cache-busting headers</li>
                <li>Fallback error handling with status display</li>
            </ul>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <p><a href="/" style="color: #ff6600;">← Back to main dashboard</a></p>
        <p><a href="/live_test" style="color: #ff6600;">→ Legacy MJPEG test</a></p>
    </div>
</body>
</html>'''
    
    @app.route('/live_test')
    def live_test():
        """Test page to diagnose video feed issues"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>VespAI Live Test</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #000; 
            color: #fff; 
        }
        .test-section { 
            margin: 20px 0; 
            padding: 20px; 
            border: 1px solid #ff6600; 
            border-radius: 8px; 
        }
        img, video { 
            border: 2px solid #ff6600; 
            margin: 10px; 
            max-width: 640px; 
        }
        .info {
            background: #333;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        button {
            background: #ff6600;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover { background: #e55a00; }
    </style>
    <script>
        function refreshFeeds() {
            // Force refresh all video feeds
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                const src = img.src;
                img.src = '';
                setTimeout(() => { img.src = src + '?t=' + Date.now(); }, 100);
            });
        }
        
        function checkStatus() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        'Frames: ' + data.frame_id + ', FPS: ' + data.fps.toFixed(1);
                })
                .catch(err => {
                    document.getElementById('status').innerHTML = 'Error: ' + err.message;
                });
        }
        
        setInterval(checkStatus, 1000);
        
        // SSE video stream functions
        let sseEventSource = null;
        let sseCanvas = null;
        let sseCtx = null;
        
        function startSSE() {
            if (sseEventSource) {
                stopSSE();
            }
            
            sseCanvas = document.getElementById('sse-canvas');
            sseCtx = sseCanvas.getContext('2d');
            
            sseEventSource = new EventSource('/video_sse');
            document.getElementById('sse-status').textContent = 'Connecting...';
            
            sseEventSource.onopen = function() {
                document.getElementById('sse-status').textContent = 'Connected ✓';
                document.getElementById('sse-status').style.color = '#00aa00';
            };
            
            sseEventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'frame') {
                        const img = new Image();
                        img.onload = function() {
                            sseCtx.clearRect(0, 0, sseCanvas.width, sseCanvas.height);
                            sseCtx.drawImage(img, 0, 0, sseCanvas.width, sseCanvas.height);
                        };
                        img.src = 'data:image/jpeg;base64,' + data.data;
                    }
                } catch (e) {
                    console.error('SSE parsing error:', e);
                }
            };
            
            sseEventSource.onerror = function() {
                document.getElementById('sse-status').textContent = 'Connection error ✗';
                document.getElementById('sse-status').style.color = '#aa0000';
            };
        }
        
        function stopSSE() {
            if (sseEventSource) {
                sseEventSource.close();
                sseEventSource = null;
            }
            document.getElementById('sse-status').textContent = 'Disconnected';
            document.getElementById('sse-status').style.color = '#ffffff';
        }
    </script>
</head>
<body>
    <h1>🐝 VespAI Live Video Test</h1>
    
    <div class="info">
        <strong>Status:</strong> <span id="status">Loading...</span>
        <button onclick="refreshFeeds()">🔄 Refresh All Feeds</button>
        <button onclick="location.reload()">🔄 Reload Page</button>
    </div>
    
    <div class="test-section">
        <h2>Test 1: Static Debug Frame</h2>
        <p>This should show current camera frame (static):</p>
        <img src="/debug_frame.jpg" alt="Debug Frame" onclick="this.src='/debug_frame.jpg?t='+Date.now()">
    </div>
    
    <div class="test-section">
        <h2>Test 2: Original MJPEG Stream</h2>
        <p>This should show live updating video:</p>
        <img src="/video_feed" alt="Original Live Feed">
    </div>
    
    <div class="test-section">
        <h2>Test 3: Alternative MJPEG Stream</h2>
        <p>This should show live updating video with visible timestamp:</p>
        <img src="/video_live" alt="Alternative Live Feed">
    </div>
    
    <div class="test-section">
        <h2>Test 4: Server-Sent Events Stream</h2>
        <p>JavaScript-based video stream (fallback for MJPEG issues):</p>
        <canvas id="sse-canvas" width="640" height="360" style="border: 2px solid #ff6600; background: #222;"></canvas>
        <div style="margin-top: 10px;">
            <button onclick="startSSE()" style="background: #00aa00;">Start SSE Stream</button>
            <button onclick="stopSSE()" style="background: #aa0000;">Stop SSE Stream</button>
            <span id="sse-status" style="margin-left: 10px;">Not connected</span>
        </div>
    </div>
    
    <div class="info">
        <p>🔍 <strong>What to look for:</strong></p>
        <ul>
            <li>Test 1 should show a static camera image</li>
            <li>Test 2 & 3 should show LIVE timestamp updating every second</li>
            <li>Test 3 should have a colorful dot changing color</li>
            <li>If you see "Initializing..." that means frames aren't reaching the browser</li>
        </ul>
        <p><a href="/" style="color: #ff6600;">← Back to main dashboard</a></p>
    </div>
</body>
</html>'''
    
    @app.route('/debug_frame.jpg')
    def debug_frame():
        """Debug endpoint - returns current frame as static JPEG"""
        import numpy as np
        frame = get_web_frame()
        if frame is None:
            # Create a debug frame
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            cv2.putText(frame, "VespAI Debug Frame", (300, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 102, 0), 2)
            cv2.putText(frame, "Static image test", (320, 300), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if success:
            from flask import Response
            response = Response(buffer.tobytes(), mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return "Failed to encode frame", 500
    
    @app.route('/current_frame.jpg')
    def current_frame():
        """Universal current frame endpoint - works on all browsers/platforms"""
        import time
        import uuid
        import numpy as np
        
        current_time = time.time()
        frame = get_web_frame()
        if frame is None:
            # Create fallback frame
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            cv2.putText(frame, "VespAI - Camera Initializing", (250, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 102, 0), 2)
            cv2.putText(frame, f"Waiting... {int(time.time()) % 10}", (300, 300), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        else:
            # Add live indicators to ensure frame uniqueness
            timestamp = time.strftime("%H:%M:%S", time.localtime(current_time))
            millisec = int((current_time % 1) * 1000)
            
            # Live timestamp  
            cv2.putText(frame, f"LIVE {timestamp}.{millisec:03d}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Unique session marker
            session_marker = str(uuid.uuid4())[:8]
            cv2.putText(frame, f"#{session_marker}", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Moving dot for visual confirmation
            dot_x = 50 + int(20 * np.sin(current_time * 2))
            cv2.circle(frame, (dot_x, 60), 6, (0, 255, 255), -1)
        
        # Encode with unique quality to prevent caching
        quality = 75 + (int(time.time()) % 20)  # Quality 75-94, changes every second
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        if success:
            from flask import Response
            
            # Ultra-aggressive anti-cache headers with Safari-specific fixes
            response = Response(buffer.tobytes(), mimetype='image/jpeg')
            response.headers.update({
                'Cache-Control': 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0',
                'Pragma': 'no-cache', 
                'Expires': 'Thu, 01 Jan 1970 00:00:00 GMT',
                'Last-Modified': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
                'ETag': f'"{uuid.uuid4()}"',
                'X-Timestamp': str(int(time.time() * 1000)),
                'Vary': 'Accept-Encoding, User-Agent, *',
                'Access-Control-Allow-Origin': '*',
                # Safari-specific cache bypass headers
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'SAMEORIGIN', 
                'Content-Disposition': 'inline',
                'X-Safari-No-Cache': 'true',  # Custom Safari header
                'X-Webkit-No-Cache': 'true',  # Webkit engine header
                'X-Frame-Counter': str(int(current_time * 1000000))  # Microsecond precision
            })
            return response
        else:
            return "Failed to encode frame", 500

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