#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)
# Test script to verify remote control system is working

echo "======================================"
echo "    VespAI Remote Control Test       "
echo "======================================"
echo ""

# Test 1: Check if we're in the right directory
echo "Test 1: Checking directory..."
if [ "$(pwd)" = "/home/vespai" ]; then
    echo "✅ Correct directory: $(pwd)"
else
    echo "❌ Wrong directory: $(pwd)"
    echo "Expected: /home/vespai"
fi

# Test 2: Check if service is installed
echo ""
echo "Test 2: Checking systemd service..."
if systemctl is-enabled vespai.service &>/dev/null; then
    echo "✅ Service is enabled"
else
    echo "❌ Service is not enabled"
fi

# Test 3: Check if service is running
echo ""
echo "Test 3: Checking service status..."
if systemctl is-active --quiet vespai.service; then
    echo "✅ Service is running"
else
    echo "❌ Service is not running"
    echo "Status:"
    systemctl status vespai.service --no-pager -l
fi

# Test 4: Check if files exist
echo ""
echo "Test 4: Checking required files..."
files=("remote_config.json" "smart_start.sh" "vespai.py")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ Found: $file"
    else
        echo "❌ Missing: $file"
    fi
done

# Test 5: Check if git is working
echo ""
echo "Test 5: Checking git status..."
if git status &>/dev/null; then
    echo "✅ Git repository is working"
    echo "   Latest commit: $(git log --oneline -1)"
else
    echo "❌ Git repository problem"
fi

# Test 6: Check config parsing
echo ""
echo "Test 6: Testing config file parsing..."
if python3 -c "import json; config=json.load(open('remote_config.json')); print(f'Mode: {config[\"mode\"]}, Enabled: {config[\"enabled\"]}')" 2>/dev/null; then
    echo "✅ Config file is valid JSON"
else
    echo "❌ Config file has syntax errors"
fi

# Test 7: Check virtual environment
echo ""
echo "Test 7: Checking virtual environment..."
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "✅ Virtual environment exists"
    source venv/bin/activate
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "✅ Virtual environment activated"
        echo "   Python: $(which python)"
    else
        echo "❌ Could not activate virtual environment"
    fi
else
    echo "❌ Virtual environment not found"
fi

# Test 8: Check web interface
echo ""
echo "Test 8: Testing web interface access..."
if command -v curl &>/dev/null; then
    if curl -s http://localhost:5000 >/dev/null; then
        echo "✅ Web interface is responding"
    else
        echo "❌ Web interface not responding"
    fi
else
    echo "⚠️  curl not available, skipping web test"
fi

echo ""
echo "======================================"
echo "           Test Complete              "
echo "======================================"
echo ""
echo "Logs to check:"
echo "• Service logs: journalctl -u vespai.service -f"
echo "• Startup logs: tail -f startup.log"
echo "• VespAI logs: tail -f vespai.log"