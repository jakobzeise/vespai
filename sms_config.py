#!/usr/bin/env python3
"""
SMS Configuration for VespAI
Author: Jakob Zeise (Zeise Digital)

This file contains SMS settings that can be tracked in the repository.
"""

# SMS Configuration
SMS_CONFIG = {
    # Target phone number for SMS alerts
    "phone_number": "",  # Set your phone number here, e.g., "+491234567890"
    
    # SMS sender name (appears on SMS)
    "sender_name": "VespAI",
    
    # Minimum delay between SMS messages in minutes
    "delay_minutes": 5,
    
    # Enable/disable SMS alerts
    "enabled": True,
    
    # Domain name for SMS links (for viewing detection images)
    "domain_name": "vespai.eu",
    
    # Override SMS cost (in EUR) - if None, use cost from API response
    # Set to 0.08 to force 8 cent cost instead of API response
    "cost_override": None  # or 0.08 to force 8 cents
}

def get_phone_number():
    """Get the configured phone number"""
    return SMS_CONFIG.get("phone_number", "")

def get_sender_name():
    """Get the configured sender name"""
    return SMS_CONFIG.get("sender_name", "VespAI")

def get_delay_minutes():
    """Get the configured delay in minutes"""
    return SMS_CONFIG.get("delay_minutes", 5)

def is_sms_enabled():
    """Check if SMS is enabled in config"""
    return SMS_CONFIG.get("enabled", True)

def get_domain_name():
    """Get the configured domain name"""
    return SMS_CONFIG.get("domain_name", "localhost")

def get_cost_override():
    """Get the cost override value (None to use API response)"""
    return SMS_CONFIG.get("cost_override", None)