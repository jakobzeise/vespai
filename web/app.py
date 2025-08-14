"""
Flask Web Application for VespAI
"""
import threading
from flask import Flask
from config.settings import config
from vespai_utils.stats import StatsManager

# Global variables for web interface
web_frame = None
web_lock = threading.Lock()

def create_app(stats_manager: StatsManager):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Store stats manager in app config
    app.config['STATS_MANAGER'] = stats_manager
    
    # Register routes
    from web.routes import register_routes
    register_routes(app)
    
    return app

def update_web_frame(frame):
    """Update the web frame (thread-safe)"""
    global web_frame
    with web_lock:
        web_frame = frame.copy()

def get_web_frame():
    """Get current web frame (thread-safe)"""
    global web_frame
    with web_lock:
        if web_frame is None:
            return None
        return web_frame.copy()

def start_web_server(app):
    """Start Flask web server in background thread"""
    print(f"Starting web server on http://0.0.0.0:{config.WEB_PORT}")
    app.run(
        host='0.0.0.0', 
        port=config.WEB_PORT, 
        threaded=True, 
        debug=False
    )