# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VespAI is a hornet detection system that uses YOLOv5 computer vision to identify Asian hornets (Vespa velutina) and European hornets (Vespa crabro) in real-time. 

**Important:** This implementation is based on the research paper "VespAI: a deep learning-based system for the detection of invasive hornets" published in Communications Biology (2024), DOI: 10.1038/s42003-024-05979-z.

The system provides:

- Real-time hornet detection using YOLOv5
- Web dashboard with live video feed and statistics
- SMS alerts via Lox24 API for hornet detections
- Motion detection optimization
- Detection logging and visualization

## Architecture

The system is built with a modular architecture in `src/vespai/` that provides:

1. **Computer Vision Pipeline** (`core/detection.py`): OpenCV for camera input and YOLOv5 for object detection
2. **Web Interface** (`web/routes.py`): Flask-based dashboard with real-time statistics and video streaming
3. **Alert System** (`sms/lox24.py`): SMS notifications through Lox24 API with rate limiting
4. **Configuration Management** (`core/config.py`): Centralized configuration and validation
5. **Main Application** (`main.py`): Entry point that orchestrates all components

## Key Components

### Detection Engine
- YOLOv5 model for hornet classification (velutina vs crabro)
- Motion detection using background subtraction (optional)
- Configurable confidence thresholds and detection parameters

### Web Dashboard
- Live video feed at `/video_feed`
- Real-time statistics API at `/api/stats`
- Detection frame viewer at `/frame/<frame_id>`
- Responsive design with mobile optimization

### SMS Alert System
- Lox24 API integration with rate limiting (5-minute delays)
- Different alert levels for Asian vs European hornets
- Cost tracking and delivery confirmation

## Running the Application

### Basic Usage
```bash
python vespai.py --web
```

### Command Line Options
- `--web`: Enable web dashboard (runs on port 5000)
- `-c, --conf <float>`: Detection confidence threshold (default: 0.8)
- `-s, --save`: Save detection images
- `-sd, --save-dir <path>`: Directory for saved images (default: monitor/detections)
- `-v, --video <path>`: Use video file instead of camera
- `-r, --resolution <WxH>`: Camera resolution (default: 1920x1080)
- `-m, --motion`: Enable motion detection
- `-a, --min-motion-area <int>`: Minimum motion area threshold
- `-b, --brake <float>`: Frame processing delay (default: 0.1)
- `-p, --print`: Print detection details to console

### Examples
```bash
# Run with web interface and motion detection
python vespai.py --web --motion --save

# Process video file with high confidence threshold
python vespai.py --video input.mp4 --conf 0.9

# Run with 720p resolution and custom save directory
python vespai.py --web --resolution 720p --save-dir ./detections
```

## Dependencies

The application requires:
- Python 3.7+
- OpenCV (cv2)
- PyTorch
- YOLOv5 (via torch.hub or yolov5 package)
- Flask
- RPi.GPIO (for Raspberry Pi deployment)
- psutil
- requests
- numpy

## Model Requirements

The system expects YOLOv5 model weights at:
- Primary: `/opt/vespai/models/yolov5s-all-data.pt`
- Fallbacks: `models/yolov5s-all-data.pt`, `yolov5s.pt`, `models/yolov5s.pt`

The model should be trained to detect:
- Class 0: Vespa crabro (European hornet)
- Class 1: Vespa velutina (Asian hornet)

## Configuration

Key configuration constants in `src/vespai/core/config.py`:
- `LOX24_API_KEY`: SMS service API credentials
- `PHONE_NUMBER`: Target phone for alerts
- `DOMAIN_NAME`: Public domain for SMS links
- `SMS_DELAY_MINUTES`: Minimum time between SMS alerts

## Web Interface

- Main dashboard: `http://localhost:5000/`
- Video stream: `http://localhost:5000/video_feed`
- Statistics API: `http://localhost:5000/api/stats`
- Detection frames: `http://localhost:5000/frame/<frame_id>`

## Development Notes

- Modular architecture with clear separation of concerns
- Comprehensive test suite (62 tests) ensuring reliability
- In-memory storage (no database required)
- Thread-safe web frame updates using locks
- Detection frames stored temporarily (max 20 frames)
- Hourly statistics tracking with 24-hour rolling window
- Mobile-responsive web interface with honeycomb design theme

## Hardware Requirements

- USB camera (tested with Logitech Brio)
- Raspberry Pi 4+ recommended for deployment
- GPU support optional but recommended for better performance