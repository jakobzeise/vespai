#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)

# Navigate to VespAI directory
cd /home/vespai

# Pull latest changes from git
git pull origin main

# Activate virtual environment and update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt --quiet

# Log the update
echo "$(date): VespAI updated from git" >> /var/log/vespai_updates.log