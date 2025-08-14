"""
Statistics management for VespAI
"""
import datetime
import threading
from collections import deque
import psutil
import logging

logger = logging.getLogger(__name__)

class StatsManager:
    """Manages real-time statistics for VespAI"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.start_time = datetime.datetime.now()
        
        # Initialize statistics
        self.stats = {
            "frame_id": 0,
            "total_velutina": 0,
            "total_crabro": 0,
            "total_detections": 0,
            "fps": 0,
            "last_detection_time": None,
            "start_time": self.start_time,
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
        
        # Hourly detection tracking
        self.hourly_detections = {hour: {"velutina": 0, "crabro": 0} for hour in range(24)}
        self.current_hour = datetime.datetime.now().hour
    
    def get_stats(self):
        """Get current statistics (thread-safe)"""
        with self.lock:
            return self.stats.copy()
    
    def update_frame_stats(self, frame_id, fps):
        """Update frame processing statistics"""
        with self.lock:
            self.stats["frame_id"] = frame_id
            self.stats["fps"] = fps
    
    def add_detection(self, detection_type, confidence, frame_id, annotated_frame):
        """Add a new detection"""
        with self.lock:
            current_time = datetime.datetime.now()
            
            # Update counters
            if detection_type == "velutina":
                self.stats["total_velutina"] += 1
                self.hourly_detections[self.current_hour]["velutina"] += 1
            elif detection_type == "crabro":
                self.stats["total_crabro"] += 1
                self.hourly_detections[self.current_hour]["crabro"] += 1
            
            self.stats["total_detections"] += 1
            self.stats["last_detection_time"] = current_time
            
            # Store detection frame
            detection_key = f"{frame_id}_{current_time.strftime('%H%M%S')}"
            self.stats["detection_frames"][detection_key] = annotated_frame.copy()
            
            # Limit stored frames
            if len(self.stats["detection_frames"]) > 20:
                oldest_key = list(self.stats["detection_frames"].keys())[0]
                del self.stats["detection_frames"][oldest_key]
            
            return detection_key
    
    def add_log_entry(self, log_entry):
        """Add entry to detection log"""
        with self.lock:
            self.stats["detection_log"].append(log_entry)
    
    def update_confidence(self, confidence):
        """Update average confidence"""
        # This would need a running average implementation
        # For now, just store the latest
        with self.lock:
            self.stats["confidence_avg"] = confidence
    
    def increment_sms_stats(self, cost, timestamp):
        """Update SMS statistics"""
        with self.lock:
            self.stats["sms_sent"] += 1
            self.stats["sms_cost"] += cost
            self.stats["last_sms_time"] = timestamp
    
    def increment_saved_images(self):
        """Increment saved images counter"""
        with self.lock:
            self.stats["saved_images"] += 1
    
    def update_system_stats(self):
        """Update system performance statistics"""
        try:
            cpu_temp = self._get_cpu_temperature()
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent
            
            with self.lock:
                self.stats["cpu_temp"] = cpu_temp
                self.stats["cpu_usage"] = cpu_usage
                self.stats["ram_usage"] = ram_usage
                
        except Exception as e:
            logger.warning(f"Failed to update system stats: {e}")
    
    def check_hour_change(self):
        """Check if hour has changed and update hourly tracking"""
        new_hour = datetime.datetime.now().hour
        if new_hour != self.current_hour:
            with self.lock:
                # Reset current hour counters
                self.hourly_detections[self.current_hour] = {"velutina": 0, "crabro": 0}
                self.current_hour = new_hour
                return True
        return False
    
    def get_hourly_stats(self):
        """Get hourly statistics for chart"""
        with self.lock:
            hourly_stats = []
            current_hour = datetime.datetime.now().hour
            
            for i in range(24):
                hour = (current_hour - 23 + i) % 24
                hourly_stats.append({
                    "hour": hour,
                    "velutina": self.hourly_detections[hour]["velutina"],
                    "crabro": self.hourly_detections[hour]["crabro"],
                    "total": (self.hourly_detections[hour]["velutina"] + 
                             self.hourly_detections[hour]["crabro"])
                })
            
            return hourly_stats
    
    def get_detection_frame(self, frame_id):
        """Get a specific detection frame"""
        with self.lock:
            return self.stats["detection_frames"].get(frame_id)
    
    def get_api_stats(self):
        """Get formatted statistics for API response"""
        with self.lock:
            # Calculate uptime
            uptime = datetime.datetime.now() - self.start_time
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            # Calculate detection rate
            detection_rate = 0
            if uptime.seconds > 0:
                detection_rate = round(
                    (self.stats["total_detections"] / (uptime.seconds / 3600)), 1
                )
            
            # Get last detection times
            last_velutina = self._get_last_detection_time("velutina")
            last_crabro = self._get_last_detection_time("crabro")
            last_sms = self._format_sms_time()
            
            return {
                "frame_id": self.stats["frame_id"],
                "total_velutina": self.stats["total_velutina"],
                "total_crabro": self.stats["total_crabro"],
                "total_detections": self.stats["total_detections"],
                "fps": self.stats["fps"],
                "uptime": f"{hours}h {minutes}m",
                "saved_images": self.stats["saved_images"],
                "sms_sent": self.stats["sms_sent"],
                "sms_cost": self.stats["sms_cost"],
                "cpu_temp": round(self.stats["cpu_temp"], 1),
                "cpu_usage": self.stats["cpu_usage"],
                "ram_usage": self.stats["ram_usage"],
                "disk_usage": self.stats["disk_usage"],
                "detection_rate": detection_rate,
                "detection_log": list(self.stats["detection_log"]),
                "hourly_stats": self.get_hourly_stats(),
                "last_velutina": last_velutina,
                "last_crabro": last_crabro,
                "last_sms": last_sms,
                "confidence_avg": round(self.stats["confidence_avg"], 1) if self.stats["confidence_avg"] > 0 else 80
            }
    
    def _get_cpu_temperature(self):
        """Get CPU temperature (Raspberry Pi)"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read()) / 1000
                return round(temp, 1)
        except:
            return 0
    
    def _get_last_detection_time(self, detection_type):
        """Get last detection time for specific type"""
        for entry in reversed(list(self.stats["detection_log"])):
            if detection_type in entry.get("type", ""):
                time_str = entry["time"]
                return time_str.split(" ")[1] if " " in time_str else time_str
        return None
    
    def _format_sms_time(self):
        """Format last SMS time"""
        if self.stats["last_sms_time"]:
            return self.stats["last_sms_time"].strftime("%H:%M:%S")
        return None