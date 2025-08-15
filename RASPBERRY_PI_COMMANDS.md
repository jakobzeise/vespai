# Raspberry Pi Setup Commands
# Author: Jakob Zeise (Zeise Digital)

Copy and paste these commands one by one on your Raspberry Pi:

## 1. Navigate to the vespai directory
```bash
cd ~/vespai
```

## 2. Make scripts executable
```bash
chmod +x one_time_install.sh smart_start.sh
```

## 3. Run the one-time installation
```bash
bash one_time_install.sh
```

## 4. Check if service is running
```bash
sudo systemctl status vespai.service
```

## 5. Check logs to see if it's working
```bash
tail -f ~/vespai.log
```

## 6. Test web interface
Open browser and go to: http://[raspberry-pi-ip]:5000

---

## If something goes wrong:

### View detailed logs:
```bash
sudo journalctl -u vespai.service -f
```

### Restart the service:
```bash
sudo systemctl restart vespai.service
```

### Check if git pull worked:
```bash
cd ~/vespai && git log --oneline -5
```

### Test reboot cycle:
```bash
sudo reboot
```
Wait 2 minutes, then check service status again.

---

## For testing remote control:

1. Change remote_config.json on your computer
2. Push to GitHub
3. Run on Pi: `sudo reboot`
4. Check if changes took effect: `tail ~/startup.log`