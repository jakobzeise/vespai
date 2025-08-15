#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)
# Quick setup script for VespAI autostart

echo "=== Setting up VespAI Autostart ==="

# Check if running as vespai user
if [ "$USER" != "vespai" ]; then
    echo "Warning: Not running as vespai user (current: $USER)"
fi

# Navigate to vespai directory
cd /home/vespai/vespai

# Make start script executable
chmod +x start_vespai.sh

# Copy service file to systemd
sudo cp vespai_correct.service /etc/systemd/system/vespai.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable vespai.service
sudo systemctl start vespai.service

# Check status
echo ""
echo "=== Service Status ==="
sudo systemctl status vespai.service

echo ""
echo "=== Setup Complete ==="
echo "Commands:"
echo "  View logs:    tail -f /home/vespai/vespai/vespai.log"
echo "  Stop:         sudo systemctl stop vespai.service"
echo "  Start:        sudo systemctl start vespai.service"
echo "  Restart:      sudo systemctl restart vespai.service"
echo "  Disable:      sudo systemctl disable vespai.service"