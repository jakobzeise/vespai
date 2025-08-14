#!/bin/bash
# VespAI Raspberry Pi Setup Script
# Handles PEP 668 virtual environment requirements

set -e

echo "🍓 VespAI Raspberry Pi Setup"
echo "=============================="

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "   Use scripts/setup.py for other systems"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
echo "📋 Python version: $python_version"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
    echo "❌ Python 3.7+ required. Please upgrade Python."
    exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt update

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y python3-full python3-pip python3-opencv git curl

# Check if virtual environment exists
if [ ! -d "vespai-env" ]; then
    echo "🔨 Creating virtual environment..."
    python3 -m venv vespai-env
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source vespai-env/bin/activate

# Verify we're in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"

# Run main setup script
echo "🚀 Running VespAI setup..."
python scripts/setup.py

echo ""
echo "🎉 Raspberry Pi setup complete!"
echo ""
echo "🔧 To use VespAI:"
echo "   1. Activate virtual environment: source vespai-env/bin/activate"
echo "   2. Run VespAI: python main.py --web --resolution 720p --motion"
echo "   3. Open http://$(hostname -I | awk '{print $1}'):8081 in browser"
echo ""
echo "💡 For best performance on Raspberry Pi:"
echo "   - Use --resolution 720p or 640x480"
echo "   - Enable --motion detection"
echo "   - Set GPU memory to 128MB+ with sudo raspi-config"
echo ""