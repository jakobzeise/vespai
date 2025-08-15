# VespAI Autostart Setup Instructions
# Author: Jakob Zeise (Zeise Digital)

## Setup Steps on Raspberry Pi

1. **Copy files to Raspberry Pi:**
```bash
# Copy the scripts to /home/vespai/
scp start_vespai.sh update_vespai.sh pi@raspberrypi:/home/vespai/
scp vespai.service pi@raspberrypi:/tmp/
```

2. **SSH into Raspberry Pi and run:**
```bash
# Make scripts executable
chmod +x /home/vespai/start_vespai.sh
chmod +x /home/vespai/update_vespai.sh

# Copy service file to systemd
sudo cp /tmp/vespai.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable vespai.service
sudo systemctl start vespai.service
```

3. **Check status:**
```bash
sudo systemctl status vespai.service
sudo journalctl -u vespai.service -f  # View logs
```

## Remote Management

### To update the code remotely:
1. Push changes to git repository
2. SSH into Pi and restart service:
   ```bash
   sudo systemctl restart vespai.service
   ```
   The service will automatically pull latest changes before starting.

### To stop/start manually:
```bash
sudo systemctl stop vespai.service
sudo systemctl start vespai.service
```

### To disable autostart:
```bash
sudo systemctl disable vespai.service
```

## Troubleshooting

- Check logs: `tail -f /var/log/vespai.log`
- Check update logs: `tail -f /var/log/vespai_updates.log`
- Service status: `sudo systemctl status vespai.service`

## Notes
- The service runs as user 'pi' for security
- Automatically restarts if crashes
- Pulls latest git changes on every restart
- Logs are stored in /var/log/vespai.log