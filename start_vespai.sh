#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)

# Wait for network to be fully ready
sleep 10

# Navigate to VespAI directory
cd /home/vespai

# Activate virtual environment
source venv/bin/activate

# Run the VespAI detection system with web interface
python vespai.py --web --motion --save --resolution 1920x1080 --conf 0.8