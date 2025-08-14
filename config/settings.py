"""
Configuration management for VespAI
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # SMS Configuration (Lox24 API)
    LOX24_API_KEY = os.getenv("LOX24_API_KEY", "")
    LOX24_SENDER = os.getenv("LOX24_SENDER", "VespAI")
    PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
    SMS_DELAY_MINUTES = int(os.getenv("SMS_DELAY_MINUTES", "5"))
    ENABLE_SMS = os.getenv("ENABLE_SMS", "true").lower() == "true"
    
    # Web Server Configuration
    DOMAIN_NAME = os.getenv("DOMAIN_NAME", "localhost")
    USE_HTTPS = os.getenv("USE_HTTPS", "false").lower() == "true"
    WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
    
    # Detection Configuration
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.8"))
    SAVE_DETECTIONS = os.getenv("SAVE_DETECTIONS", "false").lower() == "true"
    SAVE_DIRECTORY = os.getenv("SAVE_DIRECTORY", "monitor/detections")
    
    # Camera Configuration
    CAMERA_RESOLUTION = os.getenv("CAMERA_RESOLUTION", "1920x1080")
    CAMERA_FPS = int(os.getenv("CAMERA_FPS", "30"))
    
    # Model Configuration
    MODEL_PATH = os.getenv("MODEL_PATH", "/opt/vespai/models/yolov5-params/yolov5s-all-data.pt")
    
    # Motion Detection
    ENABLE_MOTION_DETECTION = os.getenv("ENABLE_MOTION_DETECTION", "false").lower() == "true"
    MIN_MOTION_AREA = int(os.getenv("MIN_MOTION_AREA", "100"))
    MOTION_DILATION = int(os.getenv("MOTION_DILATION", "1"))
    
    @property
    def public_url(self):
        """Get the public URL for SMS links"""
        protocol = "https" if self.USE_HTTPS else "http"
        return f"{protocol}://{self.DOMAIN_NAME}"
    
    @classmethod
    def validate_config(cls):
        """Validate critical configuration and show warnings"""
        warnings = []
        
        if cls.ENABLE_SMS:
            if not cls.LOX24_API_KEY:
                warnings.append("⚠️  Warning: LOX24_API_KEY not set - SMS alerts disabled")
            if not cls.PHONE_NUMBER:
                warnings.append("⚠️  Warning: PHONE_NUMBER not set - SMS alerts disabled")
        
        if not os.path.exists(cls.MODEL_PATH):
            warnings.append(f"⚠️  Warning: Model not found at {cls.MODEL_PATH}")
            
        return warnings

# Global config instance
config = Config()