#!/usr/bin/env python3
"""
VespAI Core Detection Module

This module contains the main detection logic for hornet identification
using YOLOv5 computer vision models.

Author: VespAI Team
Version: 1.0
"""

import cv2
import time
import datetime
import numpy as np
import logging
from typing import Tuple, Optional, Dict, Any, List
from collections import deque

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Manages camera initialization and configuration for video capture.
    
    Handles different camera backends and resolution settings with fallbacks
    for cross-platform compatibility.
    """
    
    def __init__(self, resolution: Tuple[int, int] = (1920, 1080)):
        """
        Initialize camera manager.
        
        Args:
            resolution: Tuple of (width, height) for camera resolution
        """
        self.width, self.height = resolution
        self.cap: Optional[cv2.VideoCapture] = None
    
    def initialize_camera(self, video_file: Optional[str] = None) -> cv2.VideoCapture:
        """
        Initialize camera capture with multiple backend fallbacks.
        
        Args:
            video_file: Path to video file, or None for live camera
            
        Returns:
            cv2.VideoCapture: Initialized video capture object
            
        Raises:
            RuntimeError: If no camera can be opened
        """
        if video_file:
            logger.info("Opening video file: %s", video_file)
            self.cap = cv2.VideoCapture(video_file)
        else:
            logger.info("Initializing camera with resolution %dx%d", self.width, self.height)
            
            # Try different backends for cross-platform compatibility
            backends = [
                (0, cv2.CAP_V4L2),      # Linux
                ("/dev/video0", cv2.CAP_V4L2),  # Linux backup
                (0, cv2.CAP_DSHOW),     # Windows DirectShow
                (0, cv2.CAP_AVFOUNDATION),  # macOS
                (0, None),              # Default backend
            ]
            
            for device, backend in backends:
                try:
                    if backend is not None:
                        self.cap = cv2.VideoCapture(device, backend)
                    else:
                        self.cap = cv2.VideoCapture(device)
                        
                    if self.cap.isOpened():
                        logger.info("Camera opened with device %s, backend %s", device, backend)
                        break
                except Exception as e:
                    logger.debug("Failed to open camera with device %s, backend %s: %s", device, backend, e)
                    continue
            
            if not self.cap or not self.cap.isOpened():
                raise RuntimeError("Cannot open camera with any backend")
            
            # Configure camera properties
            self._configure_camera()
        
        if not self.cap.isOpened():
            raise RuntimeError("Failed to initialize video capture")
            
        logger.info("Camera initialized successfully")
        time.sleep(2)  # Allow camera to stabilize
        return self.cap
    
    def _configure_camera(self):
        """Configure camera properties for optimal capture."""
        if not self.cap:
            return
            
        # Set MJPEG codec for better performance
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # Set frame rate
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Log actual settings
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        logger.info("Camera configured - Resolution: %dx%d, FPS: %.1f", 
                   actual_width, actual_height, actual_fps)
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a frame from the camera.
        
        Returns:
            Tuple of (success, frame) where success is bool and frame is numpy array
        """
        if not self.cap:
            return False, None
            
        return self.cap.read()
    
    def release(self):
        """Release camera resources."""
        if self.cap:
            self.cap.release()
            logger.info("Camera released")


class ModelManager:
    """
    Manages YOLOv5 model loading with multiple fallback methods.
    
    Handles different loading approaches for better compatibility across
    different environments and installations.
    """
    
    def __init__(self, model_path: str, confidence: float = 0.8):
        """
        Initialize model manager.
        
        Args:
            model_path: Path to YOLOv5 model weights
            confidence: Detection confidence threshold
        """
        self.model_path = model_path
        self.confidence = confidence
        self.model = None
        self.class_names = {}
    
    def load_model(self) -> Any:
        """
        Load YOLOv5 model with multiple fallback methods.
        
        Returns:
            Loaded YOLOv5 model object
            
        Raises:
            RuntimeError: If model cannot be loaded
        """
        logger.info("Loading YOLOv5 model from: %s", self.model_path)
        
        if not self._find_model_file():
            raise RuntimeError(f"Model file not found: {self.model_path}")
        
        # Try different loading methods
        loading_methods = [
            self._load_via_yolov5_package,
            self._load_via_local_directory,
            self._load_via_github
        ]
        
        for method in loading_methods:
            try:
                self.model = method()
                if self.model is not None:
                    self._configure_model()
                    logger.info("Model loaded successfully via %s", method.__name__)
                    return self.model
            except Exception as e:
                logger.debug("Loading method %s failed: %s", method.__name__, e)
                continue
        
        raise RuntimeError("Failed to load model with any method")
    
    def _find_model_file(self) -> bool:
        """
        Find the model file using fallback paths.
        
        Returns:
            bool: True if model file found and updated self.model_path
        """
        import os
        
        if os.path.exists(self.model_path):
            return True
        
        # Try alternative paths
        alternative_paths = [
            "/opt/vespai/models/yolov5s-all-data.pt",
            "models/yolov5s-all-data.pt", 
            "yolov5s-all-data.pt",
            "yolov5s.pt",
            "models/yolov5s.pt",
            os.path.join(os.getcwd(), "yolov5s.pt")
        ]
        
        for path in alternative_paths:
            if os.path.exists(path):
                logger.info("Using alternative model path: %s", path)
                self.model_path = path
                return True
        
        return False
    
    def _load_via_yolov5_package(self):
        """Load model using the yolov5 package."""
        import yolov5
        return yolov5.load(self.model_path, device='cpu')
    
    def _load_via_local_directory(self):
        """Load model from local YOLOv5 directory."""
        import os
        import sys
        import torch
        
        yolo_dir = os.path.join(os.getcwd(), "models/yolov5")
        if not os.path.exists(yolo_dir):
            raise RuntimeError("Local YOLOv5 directory not found")
        
        sys.path.insert(0, yolo_dir)
        return torch.hub.load(yolo_dir, 'custom',
                             path=self.model_path,
                             source='local',
                             force_reload=False,
                             _verbose=False)
    
    def _load_via_github(self):
        """Load model from GitHub repository."""
        import torch
        
        return torch.hub.load('ultralytics/yolov5', 'custom',
                             path=self.model_path,
                             force_reload=True,
                             trust_repo=True,
                             skip_validation=True,
                             _verbose=False)
    
    def _configure_model(self):
        """Configure model after loading."""
        if not self.model:
            return
        
        self.model.conf = self.confidence
        
        # Extract class names
        if hasattr(self.model, 'names'):
            self.class_names = self.model.names
            logger.info("Model classes: %s", self.class_names)
        
        # Log model info
        if hasattr(self.model, 'yaml'):
            logger.debug("Model config: %s", self.model.yaml)
    
    def predict(self, frame: np.ndarray):
        """
        Run inference on a frame.
        
        Args:
            frame: Input image frame
            
        Returns:
            Model predictions
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        # Convert BGR to RGB for YOLOv5
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return self.model(rgb_frame)


class DetectionProcessor:
    """
    Processes detection results and manages statistics.
    
    Handles detection counting, confidence tracking, and frame annotation.
    """
    
    def __init__(self):
        """Initialize detection processor."""
        self.stats = {
            "frame_id": 0,
            "total_velutina": 0,
            "total_crabro": 0,
            "total_detections": 0,
            "fps": 0,
            "last_detection_time": None,
            "start_time": datetime.datetime.now(),
            "detection_log": deque(maxlen=20),
            "detection_frames": {},
            "confidence_avg": 0,
        }
        
        self.hourly_detections = {hour: {"velutina": 0, "crabro": 0} for hour in range(24)}
        self.current_hour = datetime.datetime.now().hour
        
    def process_detections(self, 
                          results, 
                          frame: np.ndarray,
                          frame_id: int,
                          confidence_threshold: float = 0.8) -> Tuple[int, int, np.ndarray]:
        """
        Process detection results and update statistics.
        
        Args:
            results: YOLOv5 prediction results
            frame: Original image frame
            frame_id: Current frame ID
            confidence_threshold: Minimum confidence for valid detections
            
        Returns:
            Tuple of (asian_hornets, european_hornets, annotated_frame)
        """
        velutina_count = 0  # Asian hornets
        crabro_count = 0    # European hornets
        annotated_frame = frame.copy()
        
        # Parse predictions
        if len(results.pred[0]) > 0:
            predictions = results.pred[0]
            
            total_confidence = 0
            confidence_count = 0
            
            for pred in predictions:
                x1, y1, x2, y2, conf, cls = pred
                cls = int(cls)
                confidence = float(conf)
                
                if confidence < confidence_threshold:
                    continue
                
                total_confidence += confidence
                confidence_count += 1
                
                # Count detections by class
                if cls == 1:  # Velutina (Asian hornet)
                    velutina_count += 1
                    color = (0, 0, 255)  # Red for Asian hornets
                    label = f"Velutina {confidence:.2f}"
                elif cls == 0:  # Crabro (European hornet)
                    crabro_count += 1
                    color = (0, 255, 0)  # Green for European hornets  
                    label = f"Crabro {confidence:.2f}"
                else:
                    continue  # Unknown class
                
                # Draw bounding box
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated_frame, label, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Update statistics if detections found
            if velutina_count > 0 or crabro_count > 0:
                self._update_detection_stats(velutina_count, crabro_count, 
                                           frame_id, total_confidence, confidence_count,
                                           annotated_frame)
        
        return velutina_count, crabro_count, annotated_frame
    
    def _update_detection_stats(self, 
                               velutina: int, 
                               crabro: int, 
                               frame_id: int,
                               total_confidence: float,
                               confidence_count: int,
                               frame: np.ndarray):
        """Update detection statistics and logs."""
        current_time = datetime.datetime.now()
        
        # Update global stats
        self.stats["total_velutina"] += velutina
        self.stats["total_crabro"] += crabro
        self.stats["total_detections"] += (velutina + crabro)
        self.stats["last_detection_time"] = current_time
        self.stats["frame_id"] = frame_id
        
        # Update hourly stats
        current_hour = current_time.hour
        if current_hour != self.current_hour:
            self.current_hour = current_hour
            
        self.hourly_detections[current_hour]["velutina"] += velutina
        self.hourly_detections[current_hour]["crabro"] += crabro
        
        # Update average confidence
        if confidence_count > 0:
            avg_confidence = (total_confidence / confidence_count) * 100
            self.stats["confidence_avg"] = avg_confidence
        
        # Create detection log entry
        species = "velutina" if velutina > 0 else "crabro"
        confidence_str = f"{self.stats['confidence_avg']:.1f}"
        detection_key = f"{frame_id}_{current_time.strftime('%H%M%S')}"
        
        log_entry = {
            "timestamp": current_time.strftime("%H:%M:%S"),
            "species": species,
            "confidence": confidence_str,
            "frame_id": detection_key,
            "velutina_count": velutina,
            "crabro_count": crabro
        }
        
        self.stats["detection_log"].append(log_entry)
        
        # Store detection frame
        self.stats["detection_frames"][detection_key] = frame.copy()
        
        # Limit stored frames to prevent memory issues
        if len(self.stats["detection_frames"]) > 20:
            oldest_key = min(self.stats["detection_frames"].keys())
            del self.stats["detection_frames"][oldest_key]
        
        logger.info("Detection #%d: %d Velutina, %d Crabro (confidence: %.1f%%)",
                   self.stats["total_detections"], velutina, crabro, 
                   self.stats["confidence_avg"])


def parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """
    Parse resolution string into width and height.
    
    Args:
        resolution_str: Resolution string (e.g., "1920x1080", "1080p", "4k")
        
    Returns:
        Tuple of (width, height)
    """
    resolution_map = {
        "4k": (3840, 2160),
        "1080p": (1920, 1080), 
        "720p": (1280, 720)
    }
    
    if resolution_str in resolution_map:
        return resolution_map[resolution_str]
    
    try:
        width, height = map(int, resolution_str.split('x'))
        return width, height
    except:
        logger.warning("Invalid resolution format '%s', using default 1920x1080", resolution_str)
        return 1920, 1080