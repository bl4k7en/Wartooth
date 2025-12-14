# 🦷 Wartooth

**Bluetooth Wardriving Scanner for Raspberry Pi Zero 2W**

A dedicated Bluetooth scanning device that automatically discovers, logs, and uploads Bluetooth devices to [Wigle.net](https://wigle.net) for wardriving and wireless network mapping.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20Zero%202W-red.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)

## 📸 Features

- 🔍 **Automatic Bluetooth Scanning** - Continuous device discovery
- 📊 **Real-time LCD Display** - 128x128 pixel status screen (Waveshare 1.44")
- 📤 **Auto-Upload to Wigle.net** - Automatic CSV uploads via API
- 💾 **Local CSV Storage** - Backup of all scans in Wigle.net format
- 🔌 **USB Bluetooth Dongle Support** - External adapter compatibility
- 🚀 **Auto-start on Boot** - Systemd service integration
- 📡 **Headless Operation** - No keyboard/monitor needed

## 🛠️ Hardware Requirements

| Component | Specification |
|-----------|--------------|
| **Board** | Raspberry Pi Zero 2W |
| **Display** | Waveshare 1.44" LCD HAT (128x128, ST7735S) |
| **USB Hub** | Waveshare ETH/USB HAT |
| **Bluetooth** | USB Bluetooth Dongle (CSR/Broadcom recommended) |
| **Storage** | MicroSD Card (8GB+ Class 10) |
| **Power** | 5V 2A USB power supply |

### Recommended USB Bluetooth Adapters

- **CSR8510** - Excellent compatibility (~$5)
- **Broadcom BCM20702** - High reliability (~$8)
- **ASUS USB-BT400** - Premium option (~$15)

## 🚀 Quick Start

### 1. Prepare Raspberry Pi OS

**RECOMMENDED OS**: Raspberry Pi OS Lite (32-bit) Bookworm

Why 32-bit? The Pi Zero 2W only has 512MB RAM. 32-bit OS uses ~50MB less memory than 64-bit, which is crucial for stability during long scanning sessions.

```bash
# Download Raspberry Pi Imager
# https://www.raspberrypi.com/software/

# Flash: Raspberry Pi OS Lite (32-bit) - Bookworm
# Configure:
# - Enable SSH
# - Set WiFi credentials
# - Set hostname: wartooth (optional)
```

### 2. Install Wartooth

```bash
# SSH into your Pi
ssh pi@wartooth.local

# Download installation files
git clone https://github.com/yourusername/wartooth.git
cd wartooth

# Run installer
sudo bash install.sh
```

Installation takes approximately 10-15 minutes.

### 3. Configure Wigle.net API

Get your API credentials from [Wigle.net](https://wigle.net):
1. Register an account
2. Navigate to: **Account → API Token**
3. Copy your API Name and API Token

```bash
# Edit configuration
sudo wartooth-control config

# Insert your credentials:
{
    "api_name": "AIDxxxxxxxxxxxxxx",
    "api_token": "xxxxxxxxxxxxxxxx",
    "scan_interval": 10,
    "upload_interval": 300
}
```

### 4. Start Scanning

```bash
# Test hardware
sudo wartooth-control test

# Start scanner
sudo wartooth-control start

# View live logs
sudo wartooth-control logs
```

## 📱 LCD Display

The 128x128 display shows real-time status:

```
┌──────────────────────┐
│  Wartooth Scanner    │
├──────────────────────┤
│  Found: 42           │
│  Scans: 156          │
│  Upload: 14:30       │
├──────────────────────┤
│  OK: 3 new           │
└──────────────────────┘
```

## 🎮 Control Commands

```bash
wartooth-control start     # Start scanner
wartooth-control stop      # Stop scanner
wartooth-control restart   # Restart scanner
wartooth-control status    # View service status
wartooth-control logs      # View live logs (Ctrl+C to exit)
wartooth-control config    # Edit API credentials
wartooth-control files     # List saved CSV files
wartooth-control test      # Test Bluetooth & hardware
```

## 📁 File Structure

```
wartooth/
├── scanner.py              # Main scanner application
├── install.sh              # Installation script
├── README.md               # This file
└── LICENSE                 # MIT License

/home/pi/wigle_scans/       # CSV scan files
/usr/local/bin/wartooth/    # Installed application
/boot/firmware/wigle_config.json # Configuration
/etc/systemd/system/wartooth.service # Auto-start service
```

## ⚙️ Configuration

Edit `/boot/firmware/wigle_config.json` (or `/boot/wigle_config.json` on older systems):

```json
{
    "api_name": "YOUR_WIGLE_API_NAME",
    "api_token": "YOUR_WIGLE_API_TOKEN",
    "scan_interval": 10,        // Seconds between scans
    "upload_interval": 300      // Seconds between uploads
}
```

### Recommended Settings by Use Case

| Use Case | scan_interval | upload_interval |
|----------|---------------|-----------------|
| **Wardriving** (mobile) | 5 | 180 |
| **Fixed Location** | 30 | 600 |
| **Power Saving** | 60 | 1800 |

## 🔧 Troubleshooting

### Bluetooth Not Working

```bash
# Check Bluetooth status
sudo hciconfig -a

# Should show: UP RUNNING
# If DOWN:
sudo hciconfig hci0 up

# Check USB Bluetooth device
lsusb | grep -i bluetooth
```

### Display Black Screen

```bash
# Verify SPI enabled
ls -l /dev/spidev*

# Should show: /dev/spidev0.0 and /dev/spidev0.1

# Enable SPI if missing:
sudo raspi-config
# → Interface Options → SPI → Yes
sudo reboot
```

### Scanner Not Starting

```bash
# Check logs
sudo journalctl -u wartooth -n 50

# Common fixes:
sudo pip3 install --break-system-packages pillow requests
sudo chmod +x /usr/local/bin/wartooth/scanner.py
sudo systemctl restart wartooth
```

### Upload Failing

```bash
# Test API credentials manually
curl -u "YOUR_API_NAME:YOUR_TOKEN" \
  -F "file=@/home/pi/wigle_scans/wartooth_XXXXXX.csv" \
  https://api.wigle.net/api/v2/file/upload

# Expected response:
# {"success":true,...}
```

## 📊 Wigle.net CSV Format

Wartooth generates CSV files compatible with Wigle.net v1.4 format:

```csv
WigleWifi-1.4,appRelease=2.0,model=Wartooth,...
MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,CurrentLatitude,...
AA:BB:CC:DD:EE:FF,Device Name,[BT],2024-12-14 12:00:00,0,0,0.0,0.0,0.0,0.0,BT
```

## 🔋 Power Optimization

For mobile/battery-powered operation:

```bash
# Disable WiFi (if not needed for uploads)
sudo rfkill block wifi

# Disable HDMI
sudo /usr/bin/tvservice -o

# Increase scan intervals
sudo wartooth-control config
# Set: scan_interval=30, upload_interval=600
```

Expected battery life with 10,000mAh power bank: **~8-12 hours**

## 🌍 GPS Integration (Optional)

For wardriving with real GPS coordinates:

1. Connect USB GPS module (BU-353S4 recommended)
2. Install GPS daemon:
```bash
sudo apt-get install gpsd gpsd-clients python3-gps
```
3. GPS coordinates will be automatically included in CSV if available

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Notice

**Important**: This tool is intended for educational and research purposes only.

- Always comply with local laws regarding wireless scanning
- Respect privacy and data protection regulations
- Only scan in areas where you have permission
- Do not use this tool for malicious purposes

The authors are not responsible for misuse of this software.

## 🙏 Acknowledgments

- [Wigle.net](https://wigle.net) - Wireless network mapping community
- [Waveshare](https://www.waveshare.com) - Display and USB HAT hardware
- Raspberry Pi Foundation - Excellent single-board computers
- Wardriving community - Inspiration and support


**Made with ❤️ for the Wardriving Community**

*Happy Scanning!* 🦷📡
