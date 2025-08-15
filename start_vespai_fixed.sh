#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)

# Ensure we're in the right directory
cd /home/vespai

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found at /home/vespai/venv"
    exit 1
fi

# Activate virtual environment
source /home/vespai/venv/bin/activate

# Check if vespai.py exists
if [ ! -f "vespai.py" ]; then
    echo "vespai.py not found in /home/vespai"
    exit 1
fi

# Run the VespAI detection system
exec python vespai.py --web --motion --save --resolution 1920x1080 --conf 0.8