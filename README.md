# VespAI - Hornet Detection System

VespAI is a real-time hornet detection system that uses YOLOv5 computer vision to identify and alert on Asian hornets (Vespa velutina) and European hornets (Vespa crabro). The system provides a web dashboard, SMS alerts, and comprehensive logging for monitoring hornet activity.

## Features

- **Real-time Detection**: YOLOv5-based computer vision for accurate hornet identification
- **Web Dashboard**: Live video feed with statistics and detection history
- **SMS Alerts**: Automated notifications via Lox24 API with rate limiting
- **Motion Detection**: Optional motion-based optimization to reduce false positives
- **Data Logging**: Comprehensive detection logs and hourly statistics
- **Mobile Responsive**: Web interface optimized for mobile devices

## Quick Start

### 1. Clone and Setup
```bash

# Clone repository and install dependencies
git clone https://github.com/jakobzeise/vespai.git
cd vespai
pip install -r requirements.txt
```

### 2. Configure Environment
```bash

# Edit .env with your configuration (see Configuration section)
cp .env.example .env
```

### 3. Download YOLOv5 Model
Place your trained hornet detection model at:
- `/opt/vespai/models/yolov5-params/yolov5s-all-data.pt` (recommended)
- Or use default YOLOv5 model: `yolov5s.pt`

### 4. Run the System
```bash

# Basic usage with web interface
python main.py --web

# With motion detection and image saving
python main.py --web --motion --save
```

### 5. Access Dashboard
Open your browser to: `http://localhost:5000`

## Configuration

### Environment Variables (.env file)

```bash

# SMS Configuration (Lox24 API)
LOX24_API_KEY=your_customer_number:your_api_key
LOX24_SENDER=VespAI
PHONE_NUMBER=+1234567890
SMS_DELAY_MINUTES=5
ENABLE_SMS=true

# Web Server
DOMAIN_NAME=localhost
USE_HTTPS=false

# Detection
CONFIDENCE_THRESHOLD=0.8
SAVE_DETECTIONS=false
SAVE_DIRECTORY=monitor/detections
```

### Command Line Options

```bash

# Usage:
python main.py [OPTIONS]

Options:
  --web                    Enable web dashboard (port 5000)
  -c, --conf FLOAT        Detection confidence threshold (default: 0.8)
  -s, --save              Save detection images
  -sd, --save-dir PATH    Directory for saved images
  -v, --video PATH        Use video file instead of camera
  -r, --resolution WxH    Camera resolution (default: 1920x1080)
  -m, --motion            Enable motion detection
  -a, --min-motion-area INT  Minimum motion area threshold
  -b, --brake FLOAT       Frame processing delay (default: 0.1)
  -p, --print             Print detection details to console
```

## Installation

### System Requirements

- Python 3.7+
- USB Camera (tested with Logitech Brio)
- Raspberry Pi 4+ (recommended for deployment)

### Dependencies Installation

#### Standard Installation
```bash

# Install Python packages
pip install -r requirements.txt
```

#### Raspberry Pi Specific
```bash

# Install system dependencies
sudo apt update
sudo apt install python3-opencv python3-pip

# Install Python packages
pip install -r requirements.txt
```

### YOLOv5 Model Setup

1. **Custom Model** (Recommended):
   - Train a YOLOv5 model with hornet classes:
     - Class 0: Vespa crabro (European hornet)
     - Class 1: Vespa velutina (Asian hornet)
   - Place model at: `/opt/vespai/models/yolov5-params/yolov5s-all-data.pt`

2. **Default Model**:
   - System will download `yolov5s.pt` automatically
   - May not be optimized for hornet detection

## Usage Examples

### Basic Monitoring
```bash

# Start with web interface
python main.py --web

# Add motion detection for better performance
python main.py --web --motion
```

### Production Deployment
```bash

# Full featured production setup
python main.py --web --motion --save --conf 0.85

# Process recorded video
python main.py --video input.mp4 --save --conf 0.9
```

### Development/Testing
```bash

# High verbosity for debugging
python main.py --web --print --conf 0.7

# Test with 720p resolution
python main.py --web --resolution 720p
```

## Web Interface

### Dashboard Features
- **Live Video Feed**: Real-time camera stream with detection overlays
- **Statistics Cards**: Frame count, detection counts, system stats
- **Detection Log**: Chronological list of all detections with timestamps
- **Hourly Chart**: 24-hour detection history visualization
- **System Monitor**: CPU, RAM, temperature monitoring

### API Endpoints
- `GET /` - Main dashboard
- `GET /video_feed` - Live video stream
- `GET /api/stats` - Real-time statistics JSON
- `GET /frame/<frame_id>` - Specific detection frame

## SMS Alerts

### Lox24 Configuration
1. Register at [Lox24](https://www.lox24.eu/)
2. Get your API credentials
3. Set in `.env`:
   ```bash
   LOX24_API_KEY=customer_number:api_key
   PHONE_NUMBER=+1234567890
   ```

### Alert Behavior
- **Asian Hornet**: High priority alert sent immediately
- **European Hornet**: Lower priority info message
- **Rate Limiting**: Minimum 5-minute delay between SMS
- **Cost Tracking**: Monitors SMS costs and delivery status

## Production Deployment

### Raspberry Pi Setup
```bash

# System setup
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-opencv git

# Clone and setup
git clone https://github.com/your-username/vespai.git
cd vespai
pip install -r requirements.txt

# Configure autostart (systemd service recommended)
```

### Security Considerations
- Never commit `.env` files to git
- Use strong SMS API credentials
- Consider VPN access for remote monitoring
- Regular security updates

### Performance Optimization
- Use motion detection (`--motion`) to reduce CPU usage
- Adjust confidence threshold based on your environment
- Consider GPU acceleration for better performance
- Monitor system resources via dashboard

## Development

### Project Structure
```
vespai/
├── main.py                     # Main entry point
├── config/
│   ├── __init__.py
│   └── settings.py            # Configuration management
├── detection/
│   ├── __init__.py
│   ├── engine.py              # YOLOv5 detection logic
│   └── motion.py              # Motion detection
├── services/
│   ├── __init__.py
│   └── sms.py                 # SMS alert service
├── utils/
│   ├── __init__.py
│   └── stats.py               # Statistics management
├── web/
│   ├── __init__.py
│   ├── app.py                 # Flask application
│   ├── routes.py              # Web routes
│   ├── templates/
│   │   └── dashboard.html     # Dashboard template
│   └── static/
│       ├── css/               # Stylesheets (to be added)
│       └── js/
│           └── dashboard.js   # Dashboard JavaScript
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── CLAUDE.md                 # Claude Code assistant guide
├── LICENSE                   # MIT License
├── Dockerfile                # Docker container config
└── docker-compose.yml        # Docker Compose config
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Testing
- Test with various lighting conditions
- Verify SMS delivery and costs
- Check web interface on mobile devices
- Validate motion detection accuracy

## Troubleshooting

### Common Issues

**Camera not detected:**
```bash

# Check camera devices
ls /dev/video*
# Try different camera indices
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

**YOLOv5 model loading errors:**
- Ensure model path is correct
- Check PyTorch installation
- Verify model compatibility

**SMS not working:**
- Check API credentials in `.env`
- Verify phone number format (+country_code)
- Check Lox24 account balance

**Web interface not accessible:**
- Confirm port 5000 is not blocked
- Check firewall settings
- Verify Flask is running

### Logs
Check `vespai.log` for detailed error information and system status.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- YOLOv5 by Ultralytics
- Lox24 SMS API
- Flask web framework
- OpenCV computer vision library