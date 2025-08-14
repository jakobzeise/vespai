#!/usr/bin/env python3
"""
VespAI Setup Script
Automated installation and configuration for the VespAI hornet detection system
"""

import os
import sys
import subprocess
import urllib.request
import logging
from pathlib import Path

# Configure logging with proper Unicode support for Windows
import platform
if platform.system() == 'Windows':
    # For Windows, use UTF-8 encoding to handle Unicode characters
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
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[UnicodeFilterHandler(sys.stdout)]
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
else:
    # For non-Windows systems, use standard configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
logger = logging.getLogger(__name__)

class VespAISetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent  # Go up one level since we're in scripts/
        self.models_dir = self.project_root / "models"
        self.requirements_file = self.project_root / "requirements.txt"
        
        # Model URLs and paths
        self.models = {
            # Standard YOLOv5 models (general object detection)
            'yolov5s.pt': 'https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt',
            'yolov5m.pt': 'https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5m.pt',
            'yolov5l.pt': 'https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5l.pt',
            # VespAI hornet-specific model (not publicly available yet)
            # 'yolov5s-all-data.pt': 'https://github.com/andrw3000/vespai/releases/...'  # To be added when available
        }
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        logger.info("Checking Python version...")
        if sys.version_info < (3, 7):
            logger.error("Python 3.7+ is required. Current version: %s", sys.version)
            return False
        logger.info("Python version: %s ✓", sys.version.split()[0])
        return True
    
    def install_requirements(self):
        """Install Python dependencies with virtual environment support"""
        logger.info("Installing Python dependencies...")
        if not self.requirements_file.exists():
            logger.error("requirements.txt not found!")
            return False
        
        # Check if we're in a virtual environment or need to create one
        venv_path = self.project_root / "venv"
        python_cmd = sys.executable
        pip_cmd = [sys.executable, "-m", "pip"]
        
        # Check if system requires virtual environment (PEP 668)
        test_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--dry-run", "setuptools"],
            capture_output=True, text=True
        )
        
        needs_venv = "externally-managed-environment" in test_result.stderr.lower()
        
        if needs_venv and not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            logger.info("System requires virtual environment (PEP 668)")
            logger.info("Creating virtual environment...")
            
            # Create virtual environment
            try:
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
                logger.info("Virtual environment created at: %s", venv_path)
                
                # Update python and pip commands for venv
                if platform.system() == 'Windows':
                    python_cmd = str(venv_path / "Scripts" / "python.exe")
                    pip_cmd = [python_cmd, "-m", "pip"]
                else:
                    python_cmd = str(venv_path / "bin" / "python")
                    pip_cmd = [python_cmd, "-m", "pip"]
                    
            except subprocess.CalledProcessError as e:
                logger.error("Failed to create virtual environment: %s", e)
                logger.info("Trying with --break-system-packages as fallback...")
                pip_cmd = [sys.executable, "-m", "pip", "--break-system-packages"]
        
        try:
            cmd = pip_cmd + ["install", "-r", str(self.requirements_file)]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Dependencies installed successfully ✓")
            
            # If we created a venv, provide activation instructions
            if venv_path.exists():
                logger.info("")
                logger.info("🔧 Virtual environment created!")
                if platform.system() == 'Windows':
                    logger.info("To activate: %s\\Scripts\\activate", venv_path)
                    logger.info("To run VespAI: %s\\Scripts\\python main.py --web", venv_path)
                else:
                    logger.info("To activate: source %s/bin/activate", venv_path)
                    logger.info("To run VespAI: %s/bin/python main.py --web", venv_path)
                logger.info("")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Failed to install dependencies: %s", e.stderr)
            if "externally-managed-environment" in e.stderr:
                logger.info("")
                logger.info("💡 Raspberry Pi users: Run this setup from within a virtual environment:")
                logger.info("   python3 -m venv vespai-env")
                logger.info("   source vespai-env/bin/activate")
                logger.info("   python scripts/setup.py")
                logger.info("")
            return False
    
    def create_directories(self):
        """Create necessary directories"""
        logger.info("Creating project directories...")
        directories = [
            self.models_dir,
            self.project_root / "monitor" / "detections",
            self.project_root / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory: %s", directory)
        
        return True
    
    def download_models(self, models_to_download=None):
        """Download YOLOv5 model weights"""
        if models_to_download is None:
            models_to_download = ['yolov5s.pt']  # Default to lightweight model
        
        logger.info("Downloading YOLOv5 models...")
        
        for model_name in models_to_download:
            if model_name not in self.models:
                logger.warning("Unknown model: %s", model_name)
                continue
                
            model_path = self.project_root / model_name
            if model_path.exists():
                logger.info("Model already exists: %s ✓", model_name)
                continue
            
            url = self.models[model_name]
            logger.info("Downloading %s...", model_name)
            
            try:
                urllib.request.urlretrieve(url, model_path)
                file_size = model_path.stat().st_size / (1024 * 1024)  # MB
                logger.info("Downloaded %s (%.1f MB) ✓", model_name, file_size)
            except Exception as e:
                logger.error("Failed to download %s: %s", model_name, e)
                return False
        
        return True
    
    def check_camera(self):
        """Check for available cameras"""
        logger.info("Checking camera availability...")
        try:
            import cv2
            
            # Test cameras 0-4
            for i in range(5):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        logger.info("Camera %d available ✓", i)
                        return True
            
            logger.warning("No cameras detected - VespAI will work with video files")
            return True  # Not fatal, can use video files
            
        except ImportError:
            logger.warning("OpenCV not available for camera test")
            return True
        except Exception as e:
            logger.warning("Camera test failed: %s", e)
            return True  # Not fatal
    
    def create_config_template(self):
        """Create configuration template"""
        logger.info("Creating configuration template...")
        
        env_template = """# VespAI Configuration
# Copy to .env and customize for your setup

# SMS Alert Configuration (Optional)
# LOX24_API_KEY=your_api_key_here
# PHONE_NUMBER=+1234567890
# DOMAIN_NAME=your-domain.com

# Model Configuration
MODEL_PATH=/opt/vespai/models/yolov5-params/yolov5s-all-data.pt
CONFIDENCE_THRESHOLD=0.8

# Camera Configuration
CAMERA_INDEX=0
CAMERA_RESOLUTION=1920x1080
CAMERA_FPS=30

# Detection Configuration
SAVE_DETECTIONS=true
SAVE_DIRECTORY=monitor/detections

# Motion Detection (Optional)
ENABLE_MOTION_DETECTION=false
MIN_MOTION_AREA=5000

# Web Interface
WEB_HOST=0.0.0.0
WEB_PORT=8081
"""
        
        config_path = self.project_root / ".env.template"
        with open(config_path, 'w') as f:
            f.write(env_template)
        
        logger.info("Configuration template created: .env.template")
        return True
    
    def run_setup(self):
        """Run complete setup process"""
        logger.info("Starting VespAI setup...")
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Creating directories", self.create_directories),
            ("Installing dependencies", self.install_requirements),
            ("Downloading models", self.download_models),
            ("Checking camera", self.check_camera),
            ("Creating config template", self.create_config_template),
        ]
        
        for step_name, step_func in steps:
            logger.info("=== %s ===", step_name)
            if not step_func():
                logger.error("Setup failed at: %s", step_name)
                return False
            logger.info("")
        
        logger.info("🎉 VespAI setup completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Customize .env.template and save as .env (optional)")
        logger.info("2. Run: python main.py --web")
        logger.info("3. Open http://localhost:8081 in your browser")
        logger.info("")
        
        return True

def main():
    """Main setup function"""
    setup = VespAISetup()
    
    # Parse command line arguments for custom models
    models = ['yolov5s.pt']  # Default
    if len(sys.argv) > 1:
        if '--all-models' in sys.argv:
            models = ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt']
        elif '--model' in sys.argv:
            model_idx = sys.argv.index('--model') + 1
            if model_idx < len(sys.argv):
                models = [sys.argv[model_idx]]
    
    # Override download method to use custom models
    original_download = setup.download_models
    setup.download_models = lambda: original_download(models)
    
    success = setup.run_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()