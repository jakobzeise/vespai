#!/usr/bin/env python3
"""
Test script to compare model loading performance between legacy and modular approaches.
Author: Jakob Zeise (Zeise Digital)
"""

import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_legacy_loading():
    """Test the legacy model loading approach from web_preview.py"""
    print("=== Testing Legacy Model Loading ===")
    
    weights_pt = "models/yolov5s-all-data.pt"
    confidence = 0.8
    model = None
    
    # Check for alternative paths like legacy does
    if not os.path.exists(weights_pt):
        alternative_paths = [
            "/opt/vespai/models/yolov5s-all-data.pt",
            "models/yolov5s-all-data.pt", 
            "yolov5s-all-data.pt",
            "yolov5s.pt",
            "models/yolov5s.pt",
            os.path.join(os.getcwd(), "yolov5s.pt")
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                print(f"Using alternative model path: {alt_path}")
                weights_pt = alt_path
                break
                
    if not os.path.exists(weights_pt):
        print(f"Model not found at {weights_pt}")
        return None
    
    print(f"Legacy model path: {os.path.abspath(weights_pt)}")
    
    start_time = time.time()
    
    # Method 1: Try yolov5 package (like legacy)
    try:
        import yolov5
        model = yolov5.load(weights_pt, device='cpu')
        model.conf = confidence
        print("✓ Legacy: Model loaded via yolov5 package")
    except ImportError as e:
        print(f"✗ Legacy: yolov5 package not found: {e}")
        return None
    except Exception as e:
        print(f"✗ Legacy: Failed to load model: {e}")
        return None
    
    end_time = time.time()
    print(f"Legacy loading time: {end_time - start_time:.2f} seconds")
    
    # Test a quick inference
    import numpy as np
    test_frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    inference_start = time.time()
    try:
        results = model(test_frame)
        inference_end = time.time()
        print(f"Legacy inference time: {inference_end - inference_start:.3f} seconds")
    except Exception as e:
        print(f"✗ Legacy inference failed: {e}")
    
    return model

def test_modular_loading():
    """Test the modular model loading approach"""
    print("\n=== Testing Modular Model Loading ===")
    
    from vespai.core.detection import ModelManager
    
    try:
        model_manager = ModelManager("models/yolov5s-all-data.pt", confidence=0.8)
        print(f"Modular model path: {os.path.abspath(model_manager.model_path)}")
        
        start_time = time.time()
        model = model_manager.load_model()
        print("✓ Modular: Model loaded successfully")
        print(f"Final modular model path used: {os.path.abspath(model_manager.model_path)}")
    except Exception as e:
        print(f"✗ Modular: Failed to load model: {e}")
        return None
    
    end_time = time.time()
    print(f"Modular loading time: {end_time - start_time:.2f} seconds")
    
    # Test a quick inference
    import numpy as np
    test_frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    inference_start = time.time()
    try:
        results = model_manager.predict(test_frame)
        inference_end = time.time()
        print(f"Modular inference time: {inference_end - inference_start:.3f} seconds")
    except Exception as e:
        print(f"✗ Modular inference failed: {e}")
    
    return model_manager

def main():
    """Run both tests and compare performance"""
    print("Model Loading Performance Comparison")
    print("=" * 50)
    
    legacy_model = test_legacy_loading()
    modular_model = test_modular_loading()
    
    print("\n=== Comparison Results ===")
    if legacy_model and modular_model:
        print("Both loading methods successful")
        print("Check the timing results above to see performance differences")
    elif legacy_model:
        print("Only legacy loading successful")
    elif modular_model:
        print("Only modular loading successful")
    else:
        print("Both loading methods failed")

if __name__ == "__main__":
    main()