#!/usr/bin/env python3
"""
Test suite for VespAI core detection module

Comprehensive tests for camera management, model loading, and detection processing.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import cv2
from datetime import datetime
from collections import deque

# Add src to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

from src.vespai.core.detection import CameraManager, ModelManager, DetectionProcessor, parse_resolution


class TestCameraManager(unittest.TestCase):
    """Test cases for CameraManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.camera_manager = CameraManager((1920, 1080))
    
    def test_init(self):
        """Test camera manager initialization"""
        self.assertEqual(self.camera_manager.width, 1920)
        self.assertEqual(self.camera_manager.height, 1080)
        self.assertIsNone(self.camera_manager.cap)
    
    @patch('src.vespai.core.detection.cv2.VideoCapture')
    def test_initialize_camera_with_video_file(self, mock_video_capture):
        """Test camera initialization with video file"""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_video_capture.return_value = mock_cap
        
        result = self.camera_manager.initialize_camera("test_video.mp4")
        
        self.assertEqual(result, mock_cap)
        mock_video_capture.assert_called_once_with("test_video.mp4")
    
    @patch('src.vespai.core.detection.cv2.VideoCapture')
    @patch('src.vespai.core.detection.time.sleep')
    def test_initialize_camera_success(self, mock_sleep, mock_video_capture):
        """Test successful camera initialization"""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = [1920, 1080, 30]  # width, height, fps
        mock_video_capture.return_value = mock_cap
        
        result = self.camera_manager.initialize_camera()
        
        self.assertEqual(result, mock_cap)
        self.assertTrue(mock_video_capture.called)
        mock_sleep.assert_called_once_with(2)
    
    @patch('src.vespai.core.detection.cv2.VideoCapture')
    def test_initialize_camera_failure(self, mock_video_capture):
        """Test camera initialization failure"""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        with self.assertRaises(RuntimeError):
            self.camera_manager.initialize_camera()
    
    def test_read_frame_no_camera(self):
        """Test reading frame without initialized camera"""
        success, frame = self.camera_manager.read_frame()
        
        self.assertFalse(success)
        self.assertIsNone(frame)
    
    def test_read_frame_with_camera(self):
        """Test reading frame with initialized camera"""
        mock_cap = Mock()
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3)))
        self.camera_manager.cap = mock_cap
        
        success, frame = self.camera_manager.read_frame()
        
        self.assertTrue(success)
        self.assertIsNotNone(frame)
    
    def test_release_camera(self):
        """Test camera release"""
        mock_cap = Mock()
        self.camera_manager.cap = mock_cap
        
        self.camera_manager.release()
        
        mock_cap.release.assert_called_once()


class TestModelManager(unittest.TestCase):
    """Test cases for ModelManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model_path = "test_model.pt"
        self.model_manager = ModelManager(self.model_path, confidence=0.8)
    
    def test_init(self):
        """Test model manager initialization"""
        self.assertEqual(self.model_manager.model_path, "test_model.pt")
        self.assertEqual(self.model_manager.confidence, 0.8)
        self.assertIsNone(self.model_manager.model)
        self.assertEqual(self.model_manager.class_names, {})
    
    @patch('os.path.exists')
    def test_find_model_file_exists(self, mock_exists):
        """Test finding existing model file"""
        mock_exists.return_value = True
        
        result = self.model_manager._find_model_file()
        
        self.assertTrue(result)
        self.assertEqual(self.model_manager.model_path, "test_model.pt")
    
    @patch('os.path.exists')
    def test_find_model_file_fallback(self, mock_exists):
        """Test finding model file with fallback paths"""
        # First call (original path) returns False, second call (fallback) returns True
        mock_exists.side_effect = [False, True]
        
        result = self.model_manager._find_model_file()
        
        self.assertTrue(result)
        # Should update to first fallback path
        self.assertEqual(self.model_manager.model_path, "/opt/vespai/models/yolov5s-all-data.pt")
    
    @patch('os.path.exists')
    def test_find_model_file_not_found(self, mock_exists):
        """Test model file not found anywhere"""
        mock_exists.return_value = False
        
        result = self.model_manager._find_model_file()
        
        self.assertFalse(result)
    
    @patch.object(ModelManager, '_find_model_file')
    @patch.object(ModelManager, '_load_via_yolov5_package')
    def test_load_model_success(self, mock_load, mock_find):
        """Test successful model loading"""
        mock_find.return_value = True
        mock_model = Mock()
        mock_model.names = {0: 'crabro', 1: 'velutina'}
        mock_load.return_value = mock_model
        mock_load.__name__ = '_load_via_yolov5_package'  # Fix __name__ issue
        
        result = self.model_manager.load_model()
        
        self.assertEqual(result, mock_model)
        self.assertEqual(self.model_manager.model, mock_model)
        self.assertEqual(mock_model.conf, 0.8)
    
    @patch.object(ModelManager, '_find_model_file')
    def test_load_model_file_not_found(self, mock_find):
        """Test model loading when file not found"""
        mock_find.return_value = False
        
        with self.assertRaises(RuntimeError) as context:
            self.model_manager.load_model()
        
        self.assertIn("Model file not found", str(context.exception))
    
    def test_predict_no_model(self):
        """Test prediction without loaded model"""
        frame = np.zeros((480, 640, 3))
        
        with self.assertRaises(RuntimeError):
            self.model_manager.predict(frame)
    
    def test_predict_with_model(self):
        """Test prediction with loaded model"""
        mock_model = Mock()
        mock_predictions = Mock()
        mock_model.return_value = mock_predictions
        self.model_manager.model = mock_model
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)  # Fix dtype
        result = self.model_manager.predict(frame)
        
        self.assertEqual(result, mock_predictions)
        mock_model.assert_called_once()


class TestDetectionProcessor(unittest.TestCase):
    """Test cases for DetectionProcessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = DetectionProcessor()
    
    def test_init(self):
        """Test detection processor initialization"""
        self.assertEqual(self.processor.stats["total_velutina"], 0)
        self.assertEqual(self.processor.stats["total_crabro"], 0)
        self.assertEqual(self.processor.stats["total_detections"], 0)
        self.assertIsInstance(self.processor.stats["detection_log"], deque)
        self.assertEqual(len(self.processor.hourly_detections), 24)
    
    def test_process_detections_no_detections(self):
        """Test processing frame with no detections"""
        # Mock empty results
        mock_results = Mock()
        mock_results.pred = [torch.tensor([])]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        velutina, crabro, annotated = self.processor.process_detections(
            mock_results, frame, 1
        )
        
        self.assertEqual(velutina, 0)
        self.assertEqual(crabro, 0)
        np.testing.assert_array_equal(annotated, frame)
    
    def test_process_detections_with_velutina(self):
        """Test processing frame with Asian hornet detection"""
        import torch
        
        # Mock results with one velutina detection
        mock_results = Mock()
        mock_results.pred = [torch.tensor([[100, 100, 200, 200, 0.95, 1]])]  # cls=1 is velutina
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        velutina, crabro, annotated = self.processor.process_detections(
            mock_results, frame, 1
        )
        
        self.assertEqual(velutina, 1)
        self.assertEqual(crabro, 0)
        self.assertEqual(self.processor.stats["total_velutina"], 1)
        self.assertEqual(self.processor.stats["total_detections"], 1)
        
        # Check that detection was logged
        self.assertEqual(len(self.processor.stats["detection_log"]), 1)
        log_entry = self.processor.stats["detection_log"][0]
        self.assertEqual(log_entry["species"], "velutina")
    
    def test_process_detections_with_crabro(self):
        """Test processing frame with European hornet detection"""
        import torch
        
        # Mock results with one crabro detection
        mock_results = Mock()
        mock_results.pred = [torch.tensor([[150, 150, 250, 250, 0.87, 0]])]  # cls=0 is crabro
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        velutina, crabro, annotated = self.processor.process_detections(
            mock_results, frame, 2
        )
        
        self.assertEqual(velutina, 0)
        self.assertEqual(crabro, 1)
        self.assertEqual(self.processor.stats["total_crabro"], 1)
        self.assertEqual(self.processor.stats["total_detections"], 1)
        
        # Check that detection was logged
        self.assertEqual(len(self.processor.stats["detection_log"]), 1)
        log_entry = self.processor.stats["detection_log"][0]
        self.assertEqual(log_entry["species"], "crabro")
    
    def test_process_detections_low_confidence(self):
        """Test processing detections below confidence threshold"""
        import torch
        
        # Mock results with low confidence detection
        mock_results = Mock()
        mock_results.pred = [torch.tensor([[100, 100, 200, 200, 0.3, 1]])]  # Low confidence
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        velutina, crabro, annotated = self.processor.process_detections(
            mock_results, frame, 1, confidence_threshold=0.8
        )
        
        # Should be filtered out due to low confidence
        self.assertEqual(velutina, 0)
        self.assertEqual(crabro, 0)
        self.assertEqual(self.processor.stats["total_detections"], 0)
    
    def test_process_detections_multiple_hornets(self):
        """Test processing multiple hornet detections"""
        import torch
        
        # Mock results with multiple detections
        detections = torch.tensor([
            [100, 100, 200, 200, 0.95, 1],  # Velutina
            [300, 300, 400, 400, 0.89, 0],  # Crabro
            [500, 500, 600, 600, 0.92, 1],  # Another Velutina
        ])
        mock_results = Mock()
        mock_results.pred = [detections]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        velutina, crabro, annotated = self.processor.process_detections(
            mock_results, frame, 3
        )
        
        self.assertEqual(velutina, 2)
        self.assertEqual(crabro, 1)
        self.assertEqual(self.processor.stats["total_detections"], 3)
    
    def test_detection_frame_storage_limit(self):
        """Test that detection frame storage is limited"""
        import torch
        
        # Create many detections to test frame limit
        mock_results = Mock()
        mock_results.pred = [torch.tensor([[100, 100, 200, 200, 0.95, 1]])]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Process many frames to exceed storage limit
        for i in range(25):  # More than the 20 frame limit
            self.processor.process_detections(mock_results, frame, i + 1)
        
        # Should not exceed 20 stored frames
        self.assertLessEqual(len(self.processor.stats["detection_frames"]), 20)


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions"""
    
    def test_parse_resolution_standard_formats(self):
        """Test parsing standard resolution formats"""
        self.assertEqual(parse_resolution("4k"), (3840, 2160))
        self.assertEqual(parse_resolution("1080p"), (1920, 1080))
        self.assertEqual(parse_resolution("720p"), (1280, 720))
    
    def test_parse_resolution_custom_format(self):
        """Test parsing custom resolution format"""
        self.assertEqual(parse_resolution("1600x900"), (1600, 900))
        self.assertEqual(parse_resolution("800x600"), (800, 600))
    
    def test_parse_resolution_invalid_format(self):
        """Test parsing invalid resolution format"""
        # Should return default resolution
        self.assertEqual(parse_resolution("invalid"), (1920, 1080))
        self.assertEqual(parse_resolution("800"), (1920, 1080))
        self.assertEqual(parse_resolution(""), (1920, 1080))


class TestDetectionIntegration(unittest.TestCase):
    """Integration tests for detection components"""
    
    @patch('src.vespai.core.detection.cv2.VideoCapture')
    @patch('src.vespai.core.detection.time.sleep')
    def test_camera_and_processor_integration(self, mock_sleep, mock_video_capture):
        """Test integration between camera manager and detection processor"""
        # Setup camera mock
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = [640, 480, 30]
        mock_cap.read.return_value = (True, np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        # Initialize components
        camera = CameraManager((640, 480))
        processor = DetectionProcessor()
        
        # Initialize camera
        cap = camera.initialize_camera()
        self.assertIsNotNone(cap)
        
        # Read frame and verify
        success, frame = camera.read_frame()
        self.assertTrue(success)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (480, 640, 3))
        
        # Mock detection results
        import torch
        mock_results = Mock()
        mock_results.pred = [torch.tensor([[100, 100, 200, 200, 0.95, 1]])]
        
        # Process detections
        velutina, crabro, annotated = processor.process_detections(mock_results, frame, 1)
        
        self.assertEqual(velutina, 1)
        self.assertEqual(crabro, 0)
        self.assertEqual(processor.stats["total_detections"], 1)


if __name__ == '__main__':
    # Import torch for tensor operations in tests
    try:
        import torch
    except ImportError:
        print("Warning: PyTorch not available, some tests may fail")
    
    unittest.main(verbosity=2)