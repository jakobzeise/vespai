# Remote Control Guide for Developers
# Author: Jakob Zeise (Zeise Digital)

## How It Works

The system automatically pulls from GitHub and reads `remote_config.json` on every reboot.
You can control everything by editing this file and pushing to GitHub.

## Quick Examples

### Switch to Monolithic Version
Edit `remote_config.json`:
```json
{
  "mode": "monolithic",
  "executable": "web_preview.py",
  ...
}
```
Push to GitHub. Tell beekeeper to reboot.

### Switch to Modular Version
```json
{
  "mode": "modular",
  "executable": "vespai.py",
  ...
}
```

### Disable System Temporarily
```json
{
  "enabled": false,
  ...
}
```

### Enable SMS Alerts
```json
{
  "sms_alerts": true,
  ...
}
```

### Change Detection Sensitivity
```json
{
  "confidence": 0.95,  // Higher = fewer false positives
  ...
}
```

### Run Custom Script for Testing
```json
{
  "mode": "custom",
  "executable": "test_scripts/camera_test.py",
  "custom_args": "--debug",
  ...
}
```

## Configuration Options

| Field | Options | Description |
|-------|---------|-------------|
| mode | "modular", "monolithic", "legacy", "custom" | Which version to run |
| executable | any .py file | Script to execute |
| enabled | true/false | Enable/disable system |
| web_interface | true/false | Enable web dashboard |
| motion_detection | true/false | Use motion detection |
| save_detections | true/false | Save detection images |
| confidence | 0.0-1.0 | Detection threshold |
| resolution | "1920x1080", "1280x720", etc | Camera resolution |
| sms_alerts | true/false | Send SMS on detection |
| custom_args | string | Additional arguments |

## Deployment Workflow

1. **Development**:
   - Make changes locally
   - Test thoroughly
   - Update `remote_config.json` if needed

2. **Deployment**:
   ```bash
   git add .
   git commit -m "Update for beekeeper deployment"
   git push origin main
   ```

3. **Activation**:
   - Tell beekeeper: "Please reboot the Raspberry Pi"
   - System automatically updates and runs new version

## Monitoring

Check logs remotely by having beekeeper send you:
- `/home/vespai/vespai/vespai.log`
- `/home/vespai/vespai/startup.log`

## Emergency Stop

To stop system without SSH:
1. Set `"enabled": false` in remote_config.json
2. Push to GitHub
3. Have beekeeper reboot

## Testing New Features

1. Create feature in separate file
2. Set mode to "custom"
3. Point executable to your test file
4. Push and have them reboot
5. If it works, integrate into main code

## No SSH Needed!

Everything can be controlled through GitHub:
- Version switching
- Parameter tuning  
- Enabling/disabling features
- Running diagnostics
- Emergency stops

The beekeeper only needs to reboot when you tell them to!