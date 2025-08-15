#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)
# Diagnostic script for VespAI setup

echo "=== VespAI Setup Diagnostics ==="
echo ""

echo "1. Checking user:"
whoami
id

echo ""
echo "2. Checking home directory:"
ls -la /home/vespai/ | head -10

echo ""
echo "3. Checking for venv:"
if [ -d "/home/vespai/venv" ]; then
    echo "✓ venv exists"
    ls -la /home/vespai/venv/bin/python
else
    echo "✗ venv NOT found at /home/vespai/venv"
fi

echo ""
echo "4. Checking for vespai.py:"
if [ -f "/home/vespai/vespai.py" ]; then
    echo "✓ vespai.py exists"
else
    echo "✗ vespai.py NOT found"
fi

echo ""
echo "5. Checking Python:"
which python
which python3
python3 --version

echo ""
echo "6. Testing venv activation:"
if [ -f "/home/vespai/venv/bin/activate" ]; then
    source /home/vespai/venv/bin/activate
    which python
    python --version
else
    echo "Cannot test - venv not found"
fi

echo ""
echo "7. Current directory structure:"
pwd
ls -la