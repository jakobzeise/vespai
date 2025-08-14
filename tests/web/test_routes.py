#!/usr/bin/env python3
"""
Test suite for VespAI web routes module

This module contains comprehensive tests for the web routes functionality,
ensuring all endpoints work correctly and handle edge cases properly.
"""

import unittest
import sys
import os
import threading
from unittest.mock import Mock, patch
from flask import Flask
import numpy as np
import cv2
from datetime import datetime
from collections import deque

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

from src.vespai.web.routes import register_routes


class TestWebRoutes(unittest.TestCase):
    """Test cases for VespAI web routes"""
    
    def setUp(self):
        """
        Set up test fixtures before each test method.
        
        Creates a Flask test app with mock data and registers routes.
        """
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Mock statistics dictionary
        self.stats = {
            "frame_id": 0,
            "total_velutina": 0,
            "total_crabro": 0,
            "total_detections": 0,
            "fps": 0,
            "last_detection_time": None,
            "start_time": datetime.now(),
            "detection_log": deque(maxlen=20),
            "hourly_stats": deque(maxlen=24),
            "cpu_temp": 0,
            "cpu_usage": 0,
            "ram_usage": 0,
            "disk_usage": 0,
            "uptime": 0,
            "saved_images": 0,
            "sms_sent": 0,
            "sms_cost": 0.0,
            "confidence_avg": 0,
            "detection_history": [],
            "detection_frames": {},
            "last_sms_time": None
        }
        
        # Mock hourly detections tracking
        self.hourly_detections = {hour: {"velutina": 0, "crabro": 0} for hour in range(24)}
        
        # Mock web frame and thread lock
        self.web_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.web_lock = threading.Lock()
        
        # Register routes with the test app
        register_routes(self.app, self.stats, self.hourly_detections, self.web_frame, self.web_lock)
        
        # Create test client
        self.client = self.app.test_client()
    
    def test_index_route(self):
        """Test the main dashboard route returns HTML content."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'VespAI Detection System', response.data)
        self.assertIn(b'Live Camera Feed', response.data)
    
    def test_video_feed_route(self):
        """Test the video feed route returns MJPEG stream."""
        response = self.client.get('/video_feed')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'multipart/x-mixed-replace; boundary=frame')
    
    def test_api_stats_route(self):
        """Test the API stats endpoint returns JSON with system information."""
        with patch('psutil.cpu_percent', return_value=25.5):
            with patch('psutil.virtual_memory') as mock_vm:
                mock_vm.return_value.percent = 45.2
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 60.1
                    
                    response = self.client.get('/api/stats')
                    self.assertEqual(response.status_code, 200)
                    
                    data = response.get_json()
                    self.assertIn('total_velutina', data)
                    self.assertIn('total_crabro', data)
                    self.assertIn('total_detections', data)
                    self.assertIn('fps', data)
                    self.assertIn('cpu_usage', data)
                    self.assertIn('ram_usage', data)
                    self.assertIn('hourly_data', data)
                    self.assertEqual(len(data['hourly_data']), 24)
    
    def test_detection_frame_not_found(self):
        """Test detection frame route with non-existent frame returns 404."""
        response = self.client.get('/api/detection_frame/nonexistent')
        self.assertEqual(response.status_code, 404)
    
    def test_detection_frame_exists(self):
        """Test detection frame route with existing frame returns JPEG image."""
        # Add a test frame to the stats
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.stats["detection_frames"]["test_frame"] = test_frame
        
        response = self.client.get('/api/detection_frame/test_frame')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'image/jpeg')
    
    def test_frame_page_not_found(self):
        """Test frame page route with non-existent frame returns 404."""
        response = self.client.get('/frame/nonexistent')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Frame nonexistent not found', response.data)
    
    def test_frame_page_exists(self):
        """Test frame page route with existing frame returns HTML page."""
        # Add a test frame to the stats
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.stats["detection_frames"]["test_frame"] = test_frame
        
        response = self.client.get('/frame/test_frame')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Detection Frame: test_frame', response.data)
        self.assertIn(b'VespAI Detection', response.data)
    
    def test_list_frames_empty(self):
        """Test frames list API with no frames returns empty list."""
        response = self.client.get('/api/frames')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data['available_frames'], [])
        self.assertEqual(data['total_frames'], 0)
    
    def test_list_frames_with_data(self):
        """Test frames list API with multiple frames returns correct data."""
        # Add test frames to the stats
        self.stats["detection_frames"]["frame1"] = np.zeros((100, 100, 3), dtype=np.uint8)
        self.stats["detection_frames"]["frame2"] = np.zeros((100, 100, 3), dtype=np.uint8)
        
        response = self.client.get('/api/frames')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(len(data['available_frames']), 2)
        self.assertEqual(data['total_frames'], 2)
        self.assertIn('frame1', data['available_frames'])
        self.assertIn('frame2', data['available_frames'])
    
    def test_stats_with_detection_log(self):
        """Test stats API includes detection log data when available."""
        # Add test detection log entry
        self.stats["detection_log"].append({
            "timestamp": "12:34:56",
            "species": "crabro",
            "confidence": "95.2",
            "frame_id": "test_frame"
        })
        
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(len(data['detection_log']), 1)
        self.assertEqual(data['detection_log'][0]['species'], 'crabro')
    
    def test_stats_hourly_data_structure(self):
        """Test stats API hourly data has correct structure."""
        # Add some hourly detection data
        self.hourly_detections[12]["velutina"] = 3
        self.hourly_detections[12]["crabro"] = 5
        
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIn('hourly_data', data)
        self.assertEqual(len(data['hourly_data']), 24)
        
        # Check hour 12 data
        hour_12_data = data['hourly_data'][12]
        self.assertEqual(hour_12_data['velutina'], 3)
        self.assertEqual(hour_12_data['crabro'], 5)
        self.assertEqual(hour_12_data['total'], 8)
        self.assertEqual(hour_12_data['hour'], '12:00')


class TestWebRoutesIntegration(unittest.TestCase):
    """Integration tests for web routes with realistic data"""
    
    def setUp(self):
        """Set up integration test fixtures with realistic test data."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Create realistic test data
        self.stats = {
            "frame_id": 42,
            "total_velutina": 3,
            "total_crabro": 7,
            "total_detections": 10,
            "fps": 15.7,
            "last_detection_time": datetime(2023, 8, 15, 14, 30, 45),
            "start_time": datetime(2023, 8, 15, 12, 0, 0),
            "detection_log": deque([
                {
                    "timestamp": "14:30:45",
                    "species": "velutina",
                    "confidence": "96.8",
                    "frame_id": "42_143045"
                },
                {
                    "timestamp": "14:28:12",
                    "species": "crabro",
                    "confidence": "91.3",
                    "frame_id": "40_142812"
                }
            ], maxlen=20),
            "hourly_stats": deque(maxlen=24),
            "cpu_temp": 45.2,
            "cpu_usage": 23.4,
            "ram_usage": 67.8,
            "disk_usage": 45.1,
            "uptime": 0,
            "saved_images": 5,
            "sms_sent": 2,
            "sms_cost": 0.24,
            "confidence_avg": 94.1,
            "detection_history": [],
            "detection_frames": {},
            "last_sms_time": datetime(2023, 8, 15, 14, 30, 45)
        }
        
        self.hourly_detections = {hour: {"velutina": 0, "crabro": 0} for hour in range(24)}
        self.hourly_detections[14]["velutina"] = 3
        self.hourly_detections[14]["crabro"] = 7
        
        # Create a realistic test frame
        self.web_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        self.web_lock = threading.Lock()
        
        register_routes(self.app, self.stats, self.hourly_detections, self.web_frame, self.web_lock)
        self.client = self.app.test_client()
    
    def test_full_dashboard_workflow(self):
        """Test the complete dashboard workflow with realistic data."""
        # Test main dashboard loads
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Test stats API returns expected data
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Verify detection counts
        self.assertEqual(data['total_velutina'], 3)
        self.assertEqual(data['total_crabro'], 7)
        self.assertEqual(data['total_detections'], 10)
        
        # Verify hourly data
        hour_14 = data['hourly_data'][14]
        self.assertEqual(hour_14['velutina'], 3)
        self.assertEqual(hour_14['crabro'], 7)
        self.assertEqual(hour_14['total'], 10)
    
    def test_detection_workflow(self):
        """Test detection frame viewing workflow."""
        # Add a detection frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        frame_id = "test_detection_123"
        self.stats["detection_frames"][frame_id] = test_frame
        
        # Test frame page renders
        response = self.client.get(f'/frame/{frame_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(frame_id.encode(), response.data)
        
        # Test frame image serves correctly
        response = self.client.get(f'/api/detection_frame/{frame_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'image/jpeg')
        
        # Test frames list includes the frame
        response = self.client.get('/api/frames')
        data = response.get_json()
        self.assertIn(frame_id, data['available_frames'])


if __name__ == '__main__':
    unittest.main(verbosity=2)