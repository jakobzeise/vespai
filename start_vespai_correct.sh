#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)

# Navigate to VespAI directory
cd /home/vespai/vespai

# Pull latest changes from git (optional - comment out if you don't want auto-update)
git pull origin main 2>&1 | tee -a vespai.log

# Activate virtual environment
source /home/vespai/vespai/venv/bin/activate

# Install/update dependencies if requirements.txt changed
pip install -r requirements.txt --quiet 2>&1 | tee -a vespai.log

# Run the VespAI detection system
exec python vespai.py --web --motion --save --resolution 1920x1080 --conf 0.8