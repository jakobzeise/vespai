#!/bin/bash
# VespAI Quick Start Script for Linux/macOS
echo "========================================"
echo "VespAI Hornet Detection System"  
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "ERROR: Python not found! Please install Python 3.7+ first."
    echo "Linux: sudo apt install python3 python3-pip"
    echo "macOS: brew install python3"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "[1/3] Running automated setup..."
$PYTHON_CMD scripts/setup.py
if [ $? -ne 0 ]; then
    echo "ERROR: Setup failed! Check error messages above."
    exit 1
fi

echo ""
echo "[2/3] Setup completed successfully!"
echo "[3/3] Starting VespAI web interface..."
echo ""
echo "Open your browser to: http://localhost:8081"
echo "Press Ctrl+C to stop the server"
echo ""

$PYTHON_CMD main.py --web