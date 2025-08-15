# VespAI Installation Guide for Beekeepers
# Author: Jakob Zeise (Zeise Digital)

## One-Time Setup (Only do this once!)

1. **Connect your Raspberry Pi to the internet**
   - Make sure it has WiFi or Ethernet connection

2. **Run this single command:**
```bash
cd ~/vespai && bash one_time_install.sh
```

3. **That's it!** The system will:
   - Start automatically on every boot
   - Update itself from GitHub on every reboot
   - Run with the settings I configure remotely

## Daily Use

- **To update the software**: Simply reboot your Raspberry Pi
  - Unplug power, wait 5 seconds, plug back in
  - OR press the reset button if you have one

- **To check if it's working**: 
  - Open web browser on any device on same network
  - Go to: http://[raspberry-pi-ip]:5000
  - You should see the VespAI dashboard

## If Something Goes Wrong

- **Reboot the Raspberry Pi** - this fixes 90% of issues
- **Check the green LED** - should be on when running
- **Contact me** with the time of the issue so I can check logs

## What Happens on Each Reboot

1. Raspberry Pi starts
2. Waits 30 seconds for network
3. Downloads latest version from GitHub
4. Reads my configuration settings
5. Starts VespAI with those settings
6. Runs until next reboot

## NO MAINTENANCE NEEDED!

You don't need to:
- Update software (happens automatically)
- Change settings (I do this remotely)
- Access terminal/SSH (everything is automatic)
- Install updates (happens on reboot)

Just keep it powered and connected to internet!