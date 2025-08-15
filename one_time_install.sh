#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)
# One-time installation script for beekeepers

echo "======================================"
echo "   VespAI Automatic Setup Starting   "
echo "======================================"
echo ""

# Make sure we're in the right directory
cd /home/vespai

# Make scripts executable
chmod +x smart_start.sh

# Install the systemd service
sudo cp vespai_auto.service /etc/systemd/system/vespai.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable vespai.service

# Start the service now
sudo systemctl start vespai.service

# Wait a moment
sleep 5

# Check if it's running
if sudo systemctl is-active --quiet vespai.service; then
    echo ""
    echo "✅ SUCCESS! VespAI is now running!"
    echo ""
    echo "======================================"
    echo "        SETUP COMPLETE!               "
    echo "======================================"
    echo ""
    echo "The system will now:"
    echo "• Start automatically on every boot"
    echo "• Update from GitHub on every reboot"
    echo "• Run with remote configuration"
    echo ""
    echo "To update: Simply reboot the Raspberry Pi"
    echo ""
else
    echo ""
    echo "⚠️  Service may not have started correctly."
    echo "Try rebooting the Raspberry Pi."
    echo ""
fi

echo "Installation log saved to: /home/vespai/install.log"
date >> /home/vespai/install.log
echo "Installation completed" >> /home/vespai/install.log