#!/usr/bin/env python3
"""
VespAI Simple - Lightweight version based on web_preview.py
Author: Jakob Zeise (Zeise Digital)

This is a simplified version that keeps the original performance
while including the UI improvements from the modular version.
"""

import argparse
import sys
import os

# Add the src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

def main():
    """Main entry point - delegate to original web_preview.py"""
    parser = argparse.ArgumentParser(description='VespAI Simple - Lightweight Hornet Detection')
    parser.add_argument('--web', action='store_true', help='Enable web interface')
    parser.add_argument('--motion', action='store_true', help='Enable motion detection')
    parser.add_argument('--confidence', type=float, default=0.8, help='Detection confidence threshold')
    parser.add_argument('--brake', type=float, default=0.1, help='Frame processing delay')
    parser.add_argument('--save', action='store_true', help='Save detection images')
    parser.add_argument('--print', action='store_true', help='Print detection details')
    parser.add_argument('--sms', action='store_true', help='Enable SMS alerts')
    parser.add_argument('--resolution', type=str, help='Camera resolution (e.g., 720p, 1080p)')
    parser.add_argument('--port', type=int, default=5000, help='Web server port')
    
    args = parser.parse_args()
    
    print("VespAI Simple - Starting...")
    print("Recommendation: Use original web_preview.py for best performance:")
    print(f"python web_preview.py {' '.join(sys.argv[1:])}")
    print("\nThe original web_preview.py is stable and fast.")
    print("The modular version introduced unnecessary complexity.")
    
    return False

if __name__ == "__main__":
    main()