"""
YOLOv5 Detection Engine for VespAI
"""
import cv2
import os
import sys
import logging
import torch
import numpy as np
from config.settings import config

logger = logging.getLogger(__name__)

class DetectionEngine:
    """YOLOv5 Hornet Detection Engine"""
    
    def __init__(self, model_path=None, confidence=None):
        self.model_path = model_path or config.MODEL_PATH
        self.confidence = confidence or config.CONFIDENCE_THRESHOLD
        self.model = None
        self.total_confidence = 0
        self.confidence_count = 0
        
        self._load_model()
    
    def _load_model(self):
        """Load YOLOv5 model"""
        logger.info("Loading YOLOv5 model...")
        
        # Check if model exists
        if not os.path.exists(self.model_path):
            logger.warning(f"Model not found at {self.model_path}")
            self._try_alternative_paths()
        
        if not os.path.exists(self.model_path):
            logger.error(f"No valid model found at {self.model_path}")
            raise FileNotFoundError(f"Model weights not found: {self.model_path}")
        
        # Try different loading methods
        self.model = self._try_loading_methods()
        
        if self.model is None:
            raise RuntimeError("Failed to load YOLOv5 model with all methods")
        
        # Set confidence threshold
        if hasattr(self.model, 'conf'):
            self.model.conf = self.confidence
            
        if hasattr(self.model, 'names'):
            logger.info(f"Model classes: {self.model.names}")
            
            # Check if this is a proper hornet detection model
            expected_classes = {'velutina', 'crabro', 'vespa_velutina', 'vespa_crabro'}
            model_classes = set(str(v).lower() for v in self.model.names.values())
            
            if not any(cls in model_classes for cls in expected_classes):
                logger.warning(f"⚠️ Model does not appear to contain hornet classes!")
                logger.warning(f"⚠️ Expected: velutina/crabro, Found: {list(self.model.names.values())[:5]}...")
                logger.warning(f"⚠️ This model will produce false detections - use proper hornet model")
        
        logger.info("✓ YOLOv5 model loaded successfully")
    
    def _try_alternative_paths(self):
        """Try alternative model paths"""
        alternative_paths = [
            "models/yolov5s-all-data.pt",  # VespAI hornet model
            "yolov5s.pt",  # Standard YOLOv5 model
            "models/yolov5s.pt",
            os.path.join(os.getcwd(), "models", "yolov5s.pt"),
            "yolov5s-all-data.pt"
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                self.model_path = alt_path
                logger.info(f"Using alternative model path: {self.model_path}")
                break
    
    def _try_loading_methods(self):
        """Try different YOLOv5 loading methods"""
        model = None
        
        # Method 1: Try ultralytics YOLO (best compatibility)
        try:
            from ultralytics import YOLO
            import torch
            
            # Load model with ultralytics YOLO
            logger.info("Trying ultralytics YOLO model loading...")
            model = YOLO(self.model_path)
            logger.info("Model loaded via ultralytics YOLO")
            return model
            
        except Exception as e:
            logger.warning(f"Ultralytics YOLO loading failed: {e}")
        
        # Method 2: Fallback to standard YOLOv5 if custom model fails
        if "yolov5s-all-data.pt" in self.model_path:
            logger.info("Custom model failed, trying standard YOLOv5...")
            try:
                from ultralytics import YOLO
                # Download and use standard YOLOv5s
                model = YOLO('yolov5s.pt')  # This will auto-download if needed
                logger.warning("⚠️ Using standard YOLOv5 model - not optimized for hornets")
                return model
            except Exception as e:
                logger.debug(f"Standard YOLO fallback failed: {e}")
        
        # Method 3: Try torch.hub with weights_only fix  
        try:
            import torch
            
            # Try torch.hub with weights_only fix
            original_load = torch.load
            torch.load = lambda *args, **kwargs: original_load(*args, **kwargs, weights_only=False)
            
            try:
                model = torch.hub.load(
                    'ultralytics/yolov5', 'custom',
                    path=self.model_path,
                    device='cpu',
                    force_reload=True,  # Force reload to clear cache
                    trust_repo=True,
                    verbose=False
                )
                torch.load = original_load  # Restore original function
                logger.info("Model loaded via torch.hub with weights_only=False")
                return model
            except Exception as e:
                torch.load = original_load  # Restore even on failure
                logger.debug(f"torch.hub with patch failed: {e}")
                
        except Exception as e:
            logger.warning(f"Torch.hub loading failed: {e}")
        
        # Method 2: Try yolov5 package with weights_only fix
        try:
            import yolov5
            import torch
            
            # Monkey patch torch.load globally for yolov5 package
            original_load = torch.load
            torch.load = lambda *args, **kwargs: original_load(*args, **kwargs, weights_only=False)
            
            try:
                model = yolov5.load(self.model_path, device='cpu')
                torch.load = original_load  # Restore original function
                logger.info("Model loaded via yolov5 package with weights_only=False")
                return model
            except Exception as e:
                torch.load = original_load  # Restore even on failure
                logger.warning(f"yolov5 package loading failed: {e}")
                
        except ImportError:
            logger.info("yolov5 package not found, trying alternative methods...")
        except Exception as e:
            logger.warning(f"yolov5 package setup failed: {e}")
        
        # Method 3: Try local YOLOv5 directory
        yolo_dir = os.path.join(os.path.dirname(self.model_path), "yolov5")
        if os.path.exists(yolo_dir):
            sys.path.insert(0, yolo_dir)
            try:
                model = torch.hub.load(
                    yolo_dir, 'custom',
                    path=self.model_path,
                    source='local',
                    force_reload=False,
                    _verbose=False
                )
                logger.info("Model loaded from local YOLOv5 directory")
                return model
            except Exception as e:
                logger.warning(f"Local YOLOv5 loading failed: {e}")
        
        # Method 4: Download from GitHub with weights_only fix (legacy fallback)
        try:
            # Fix for PyTorch 2.6 weights_only issue
            import torch
            torch.serialization.add_safe_globals(['models.yolo.Model'])
            model = torch.hub.load(
                'ultralytics/yolov5', 'custom',
                path=self.model_path,
                force_reload=True,
                trust_repo=True,
                skip_validation=True,
                _verbose=False
            )
            logger.info("Model loaded from GitHub")
            return model
        except Exception as e:
            logger.error(f"GitHub YOLOv5 loading failed: {e}")
            # Try with weights_only=False fallback
            try:
                original_load = torch.load
                torch.load = lambda *args, **kwargs: original_load(*args, **kwargs, weights_only=False)
                model = torch.hub.load(
                    'ultralytics/yolov5', 'custom',
                    path=self.model_path,
                    force_reload=True,
                    trust_repo=True,
                    skip_validation=True,
                    _verbose=False
                )
                torch.load = original_load  # Restore original function
                logger.info("Model loaded from GitHub (fallback method)")
                return model
            except Exception as e2:
                logger.error(f"GitHub YOLOv5 fallback loading also failed: {e2}")
        
        return None
    
    def detect(self, frame):
        """
        Run detection on a frame
        
        Args:
            frame: OpenCV BGR frame
            
        Returns:
            dict: Detection results with counts and annotated frame
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # Convert BGR to RGB for YOLO
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Run inference
            results = self.model(rgb_frame)
            
            # Process results
            detections = self._process_results(results)
            
            # Render results on frame
            results.render()
            annotated_frame = cv2.cvtColor(results.ims[0], cv2.COLOR_RGB2BGR)
            
            # Update confidence tracking
            if detections['total_detections'] > 0:
                avg_conf = sum(detections['confidences']) / len(detections['confidences'])
                self.total_confidence += avg_conf
                self.confidence_count += 1
            
            return {
                'velutina_count': detections['velutina'],
                'crabro_count': detections['crabro'], 
                'total_detections': detections['total_detections'],
                'confidences': detections['confidences'],
                'annotated_frame': annotated_frame,
                'has_detections': detections['total_detections'] > 0
            }
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return {
                'velutina_count': 0,
                'crabro_count': 0,
                'total_detections': 0,
                'confidences': [],
                'annotated_frame': frame.copy(),
                'has_detections': False
            }
    
    def _process_results(self, results):
        """Process YOLO detection results"""
        detections = {
            'velutina': 0,
            'crabro': 0, 
            'total_detections': 0,
            'confidences': []
        }
        
        if len(results.pred[0]) > 0:
            # Check if model has proper hornet classes
            has_hornet_classes = False
            if hasattr(self.model, 'names'):
                model_classes = set(str(v).lower() for v in self.model.names.values())
                expected_classes = {'velutina', 'crabro', 'vespa_velutina', 'vespa_crabro'}
                has_hornet_classes = any(cls in model_classes for cls in expected_classes)
            
            for pred in results.pred[0]:
                x1, y1, x2, y2, conf, cls = pred
                cls = int(cls)
                confidence = float(conf)
                
                if not has_hornet_classes:
                    # Generic model - skip all detections to prevent false alerts
                    logger.debug(f"Skipping detection (generic model): class {cls}, confidence: {confidence:.2f}")
                    continue
                
                detections['confidences'].append(confidence)
                
                if cls == 1:  # Vespa velutina (Asian hornet)
                    detections['velutina'] += 1
                    logger.debug(f"Vespa velutina detected - confidence: {confidence:.2f}")
                elif cls == 0:  # Vespa crabro (European hornet)  
                    detections['crabro'] += 1
                    logger.debug(f"Vespa crabro detected - confidence: {confidence:.2f}")
        
        detections['total_detections'] = detections['velutina'] + detections['crabro']
        return detections
    
    def get_average_confidence(self):
        """Get average confidence of all detections"""
        if self.confidence_count > 0:
            return (self.total_confidence / self.confidence_count) * 100
        return 0
    
    def add_overlay_text(self, frame, frame_id, fps, total_velutina, total_crabro):
        """Add overlay text to detection frame"""
        cv2.putText(frame, 
                   f"Frame: {frame_id} | FPS: {fps:.1f}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                   (0, 255, 0), 2)
        cv2.putText(frame,
                   f"V: {total_velutina} | C: {total_crabro}",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                   (0, 255, 0), 2)
        return frame