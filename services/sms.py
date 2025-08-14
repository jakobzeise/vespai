"""
SMS Alert Service for VespAI using Lox24 API
"""
import datetime
import json
import logging
import requests
from config.settings import config

logger = logging.getLogger(__name__)

class Lox24SMS:
    """SMS service using Lox24 API"""
    
    def __init__(self, api_key: str, sender_name: str = "VespAI"):
        self.api_key = api_key
        self.sender_name = sender_name
        self.sms_available = bool(api_key)
        
        # Parse API key format
        if ":" in api_key:
            self.username, self.password = api_key.split(":", 1)
        else:
            self.username = ""
            self.password = api_key
    
    def send_sms(self, to: str, message: str):
        """Send SMS message"""
        if not self.sms_available:
            logger.info(f"[SMS disabled] Would send: {message}")
            return False, 0.0
        
        url = "https://api.lox24.eu/sms"
        
        try:
            logger.info(f"Sending SMS to {to}: {message[:50]}...")
            
            data = {
                'sender_id': self.sender_name,
                'text': message,
                'service_code': "direct",
                'phone': to,
                'delivery_at': 0,
                'is_unicode': True,
                'callback_data': '123456',
                'voice_lang': 'DE'
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-LOX24-AUTH-TOKEN': self.api_key,
            }
            
            logger.debug(f"SMS API request: {json.dumps(data, indent=2)}")
            
            res = requests.post(url, headers=headers, json=data, timeout=100)
            
            if res.status_code != 201:
                error_msg = self._handle_error_code(res.status_code)
                logger.error(f"SMS API Error: {error_msg}")
                logger.error(f"Response: {res.text}")
                return False, 0.0
            else:
                logger.info(f'✓ SMS sent successfully (status: {res.status_code})')
                response_data = res.json()
                logger.debug(f"SMS API response: {json.dumps(response_data, indent=2)}")
                
                # Extract cost from response
                cost = self._extract_cost(response_data)
                return True, cost
                
        except requests.exceptions.RequestException as e:
            logger.error(f"SMS Request Error: {e}")
            return False, 0.0
        except Exception as e:
            logger.error(f"SMS Unexpected Error: {e}")
            return False, 0.0
    
    def _handle_error_code(self, status_code):
        """Handle API error codes"""
        error_messages = {
            400: "Invalid input",
            401: "Client ID or API key isn't active or invalid",
            402: "Not enough funds on account",
            403: "Account isn't activated",
            404: "Resource not found",
            500: "System error - contact LOX24 support",
            502: "System error - contact LOX24 support",
            503: "System error - contact LOX24 support",
            504: "System error - contact LOX24 support"
        }
        return error_messages.get(status_code, f"Unknown error (code: {status_code})")
    
    def _extract_cost(self, response_data):
        """Extract SMS cost from API response"""
        cost_fields = ['price', 'cost', 'total_price']
        for field in cost_fields:
            if field in response_data:
                try:
                    return float(response_data[field])
                except (ValueError, TypeError):
                    continue
        return 0.0


class SMSAlertService:
    """SMS Alert Service with rate limiting"""
    
    def __init__(self, stats_manager):
        self.stats_manager = stats_manager
        self.sms_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize SMS client"""
        if not config.ENABLE_SMS:
            logger.info("SMS service disabled via configuration")
            return
            
        if not config.LOX24_API_KEY:
            logger.warning("LOX24_API_KEY not configured - SMS disabled")
            return
            
        try:
            self.sms_client = Lox24SMS(
                api_key=config.LOX24_API_KEY,
                sender_name=config.LOX24_SENDER
            )
            logger.info("✓ SMS service initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize SMS service: {e}")
            self.sms_client = None
    
    def send_alert(self, text: str, force: bool = False):
        """Send SMS alert with rate limiting"""
        if not self._can_send_sms():
            logger.info(f"[SMS unavailable] Would send: {text}")
            return False
        
        if not self._check_rate_limit(force):
            return False
        
        # Send the SMS
        success, cost = self.sms_client.send_sms(config.PHONE_NUMBER, text)
        
        if success:
            self._update_stats(text, cost)
            return True
        else:
            logger.error(f"✗ Failed to send SMS: {text}")
            return False
    
    def _can_send_sms(self):
        """Check if SMS can be sent"""
        if not config.ENABLE_SMS:
            return False
        if not self.sms_client:
            return False
        if not config.LOX24_API_KEY or not config.PHONE_NUMBER:
            return False
        return True
    
    def _check_rate_limit(self, force: bool = False):
        """Check SMS rate limiting"""
        if force:
            return True
            
        stats = self.stats_manager.get_stats()
        if stats["last_sms_time"] is None:
            return True
        
        current_time = datetime.datetime.now()
        time_since_last = (current_time - stats["last_sms_time"]).total_seconds() / 60
        
        if time_since_last < config.SMS_DELAY_MINUTES:
            remaining = config.SMS_DELAY_MINUTES - time_since_last
            logger.info(f"[SMS Rate Limited] Next SMS allowed in {remaining:.1f} minutes")
            return False
        
        return True
    
    def _update_stats(self, text: str, cost: float):
        """Update SMS statistics"""
        current_time = datetime.datetime.now()
        
        self.stats_manager.increment_sms_stats(cost, current_time)
        
        # Add to detection log
        log_entry = {
            "time": current_time.strftime("%H:%M:%S"),
            "message": f"📱 SMS Alert sent: {text}",
            "type": "sms"
        }
        self.stats_manager.add_log_entry(log_entry)
        
        logger.info(f"✓ SMS sent: {text}")
        if cost > 0:
            logger.info(f"  Cost: {cost:.3f}€")