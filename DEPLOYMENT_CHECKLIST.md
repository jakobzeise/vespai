# Deployment Checklist for Beekeeper
# Author: Jakob Zeise (Zeise Digital)

## ✅ Pre-Deployment (Before giving to beekeeper)

### 1. Hardware Setup
- [ ] Raspberry Pi 4+ with sufficient power supply
- [ ] MicroSD card (32GB+) with Raspberry Pi OS installed
- [ ] USB camera (preferably Logitech Brio) connected
- [ ] Ethernet cable OR WiFi configured
- [ ] Internet connection verified

### 2. Software Setup on Pi
- [ ] User 'vespai' created with sudo privileges
- [ ] VespAI code cloned to `/home/vespai`
- [ ] Python virtual environment created: `python3 -m venv venv`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Camera permissions configured
- [ ] Git configured with credentials (for auto-pulls)

### 3. Run These Commands on Pi:
```bash
cd ~/vespai
chmod +x one_time_install.sh smart_start.sh test_remote_control.sh
bash one_time_install.sh
```

### 4. Test System
- [ ] Run: `bash test_remote_control.sh` (all tests should pass)
- [ ] Service status: `sudo systemctl status vespai.service` (should be active)
- [ ] Web interface: Open `http://[pi-ip]:5000` (should show dashboard)
- [ ] Camera feed: Verify video stream is working

### 5. Test Remote Control
- [ ] Edit `remote_config.json` locally (change confidence to 0.9)
- [ ] Push to GitHub: `git push`
- [ ] Reboot Pi: `sudo reboot`
- [ ] Verify new config applied: `tail ~/vespai/startup.log`
- [ ] Reset config back to original values

## ✅ At Beekeeper Location

### 1. Physical Installation
- [ ] Mount Raspberry Pi in weatherproof case
- [ ] Position camera with clear view of hive entrance
- [ ] Connect power (ensure stable power supply)
- [ ] Connect to internet (WiFi or ethernet)
- [ ] Test camera angle and lighting

### 2. Network Setup
- [ ] Find Pi's IP address: `hostname -I`
- [ ] Test web access from phone/laptop on same network
- [ ] Document IP address for beekeeper
- [ ] Configure router port forwarding if needed (optional)

### 3. Final Testing
- [ ] Let system run for 1 hour
- [ ] Check detection functionality with test objects
- [ ] Verify logs are being written
- [ ] Test reboot cycle: `sudo reboot`
- [ ] Confirm auto-startup after reboot

### 4. Beekeeper Training
- [ ] Show web interface on their device
- [ ] Explain how to reboot (power cycle)
- [ ] Give them the IP address
- [ ] Leave printed copy of `BEEKEEPER_SETUP.md`

## ✅ Ongoing Remote Management

### Your Development Workflow:
1. [ ] Make changes locally
2. [ ] Test thoroughly
3. [ ] Update `remote_config.json` if needed
4. [ ] Commit and push: `git push origin main`
5. [ ] Contact beekeeper: "Please reboot the device"
6. [ ] Verify deployment via logs (if accessible)

### Emergency Procedures:
- [ ] **Stop system**: Set `"enabled": false` in config, push, have them reboot
- [ ] **Rollback**: `git revert HEAD`, push, have them reboot
- [ ] **Debug**: Ask for log files: `~/vespai.log`, `~/startup.log`

## ✅ Files to Give Beekeeper
- [ ] Printed copy of `BEEKEEPER_SETUP.md`
- [ ] IP address written down
- [ ] Your contact information
- [ ] Simple troubleshooting guide

## 🚀 System is Ready!
Once all items are checked, the beekeeper can operate independently with you controlling everything via GitHub!