#!/bin/bash
# Author: Jakob Zeise (Zeise Digital)
# Smart startup script that reads config from git and adapts

LOG_FILE="/home/vespai/startup.log"
CONFIG_FILE="/home/vespai/remote_config.json"

echo "$(date): Starting VespAI Smart Launcher" >> $LOG_FILE

# Navigate to VespAI directory
cd /home/vespai

# Always pull latest changes from git on reboot
echo "$(date): Pulling latest changes from git..." >> $LOG_FILE
git pull origin main >> $LOG_FILE 2>&1

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "$(date): No remote_config.json found, using defaults" >> $LOG_FILE
    CONFIG_FILE="remote_config_default.json"
fi

# Read configuration
MODE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['mode'])" 2>/dev/null || echo "modular")
EXECUTABLE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['executable'])" 2>/dev/null || echo "vespai.py")
ENABLED=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['enabled'])" 2>/dev/null || echo "true")
WEB=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['web_interface'])" 2>/dev/null || echo "true")
MOTION=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['motion_detection'])" 2>/dev/null || echo "true")
SAVE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['save_detections'])" 2>/dev/null || echo "true")
CONFIDENCE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['confidence'])" 2>/dev/null || echo "0.8")
RESOLUTION=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['resolution'])" 2>/dev/null || echo "1920x1080")
SMS=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['sms_alerts'])" 2>/dev/null || echo "false")
CUSTOM_ARGS=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['custom_args'])" 2>/dev/null || echo "")

echo "$(date): Configuration loaded - Mode: $MODE, Executable: $EXECUTABLE" >> $LOG_FILE

# Check if enabled
if [ "$ENABLED" != "true" ]; then
    echo "$(date): VespAI is disabled via remote_config.json" >> $LOG_FILE
    exit 0
fi

# Activate virtual environment
source /home/vespai/venv/bin/activate

# Update dependencies if requirements changed
pip install -r requirements.txt --quiet >> $LOG_FILE 2>&1

# Build command based on configuration
CMD="python"

# Choose executable based on mode
case "$MODE" in
    "modular")
        CMD="$CMD vespai.py"
        ;;
    "monolithic")
        CMD="$CMD web_preview.py"
        ;;
    "legacy")
        CMD="$CMD legacy/web_preview.py"
        ;;
    "custom")
        CMD="$CMD $EXECUTABLE"
        ;;
    *)
        echo "$(date): Unknown mode: $MODE, using default" >> $LOG_FILE
        CMD="$CMD vespai.py"
        ;;
esac

# Add flags based on config
[ "$WEB" == "true" ] && CMD="$CMD --web"
[ "$MOTION" == "true" ] && CMD="$CMD --motion"
[ "$SAVE" == "true" ] && CMD="$CMD --save"
[ "$SMS" == "true" ] && CMD="$CMD --sms"
CMD="$CMD --conf $CONFIDENCE"
CMD="$CMD --resolution $RESOLUTION"

# Add custom arguments if any
[ ! -z "$CUSTOM_ARGS" ] && CMD="$CMD $CUSTOM_ARGS"

echo "$(date): Executing: $CMD" >> $LOG_FILE

# Execute the command
exec $CMD