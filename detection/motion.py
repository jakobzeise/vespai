"""
Motion Detection Module for VespAI
"""
import cv2
import logging

logger = logging.getLogger(__name__)

class MotionDetector:
    """Motion detection using background subtraction"""
    
    def __init__(self, min_area=100, dilation_iterations=1):
        self.min_area = min_area
        self.dilation_iterations = dilation_iterations
        self.background_subtractor = None
        self.initialized = False
        
    def initialize(self, frame):
        """Initialize background subtractor with first frame"""
        try:
            # Try to use VIBE background subtractor if available
            try:
                from vibe import BackgroundSubtractor
                self.background_subtractor = BackgroundSubtractor()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                self.background_subtractor.init_history(gray)
                self.initialized = True
                logger.info("Motion detection initialized with VIBE")
                return True
            except ImportError:
                logger.warning("VIBE not available, using OpenCV background subtractor")
                
            # Fallback to OpenCV background subtractor
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                detectShadows=True
            )
            self.initialized = True
            logger.info("Motion detection initialized with MOG2")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize motion detection: {e}")
            return False
    
    def detect_motion(self, frame):
        """
        Detect motion in frame
        
        Args:
            frame: OpenCV BGR frame
            
        Returns:
            bool: True if significant motion detected
        """
        if not self.initialized:
            return self.initialize(frame)
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Use VIBE if available
            if hasattr(self.background_subtractor, 'segmentation'):
                # VIBE background subtractor
                seg = self.background_subtractor.segmentation(gray)
                self.background_subtractor.update(gray, seg)
                motion_mask = seg
            else:
                # OpenCV background subtractor
                motion_mask = self.background_subtractor.apply(gray)
            
            # Post-process motion mask
            motion_mask = cv2.medianBlur(motion_mask, 3)
            motion_mask = cv2.dilate(motion_mask, None, iterations=self.dilation_iterations)
            
            # Find contours
            contours, _ = cv2.findContours(
                motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Check if any contour is large enough
            for contour in contours:
                if cv2.contourArea(contour) > self.min_area:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Motion detection error: {e}")
            # If motion detection fails, assume motion is present
            return True