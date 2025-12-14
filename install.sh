#!/bin/bash

echo "========================================"
echo "Wartooth Scanner Installation"
echo "v2.0 - December 2025"
echo "========================================"

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root: sudo bash install.sh"
    exit 1
fi

if [ -d "/boot/firmware" ]; then
    BOOT_DIR="/boot/firmware"
    echo "Bookworm detected"
else
    BOOT_DIR="/boot"
    echo "Bullseye or older detected"
fi

echo ""
echo "Updating system..."
apt-get update
apt-get upgrade -y

echo ""
echo "Installing packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-pil \
    python3-rpi.gpio \
    bluez \
    bluetooth \
    bluez-tools \
    git

echo ""
echo "Installing Python libraries..."
pip3 install --break-system-packages \
    pillow \
    requests \
    spidev \
    RPi.GPIO

echo ""
echo "Enabling SPI..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null; then
    if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
        echo "dtparam=spi=on" >> ${BOOT_DIR}/config.txt
    fi
fi

echo ""
echo "Configuring Bluetooth..."
systemctl enable bluetooth
systemctl start bluetooth

echo ""
echo "Optimizing Bluetooth..."
cat >> /etc/bluetooth/main.conf << 'EOF'

[General]
DiscoverableTimeout = 0
PairableTimeout = 0
FastConnectable = true

[Policy]
AutoEnable=true
EOF

echo ""
echo "Creating directories..."
mkdir -p /home/pi/wigle_scans
mkdir -p /usr/local/bin/wartooth
chown -R pi:pi /home/pi/wigle_scans

echo ""
if [ -f "$(dirname "$0")/scanner.py" ]; then
    echo "Installing scanner.py..."
    cp "$(dirname "$0")/scanner.py" /usr/local/bin/wartooth/scanner.py
    chmod +x /usr/local/bin/wartooth/scanner.py
elif [ -f "/home/pi/scanner.py" ]; then
    echo "Installing scanner.py from /home/pi..."
    cp /home/pi/scanner.py /usr/local/bin/wartooth/scanner.py
    chmod +x /usr/local/bin/wartooth/scanner.py
else
    echo "ERROR: scanner.py not found!"
    echo "Make sure scanner.py is in the same directory."
    exit 1
fi

echo ""
echo "Creating configuration..."
cat > ${BOOT_DIR}/wigle_config.json << 'EOF'
{
    "api_name": "YOUR_WIGLE_API_NAME",
    "api_token": "YOUR_WIGLE_API_TOKEN",
    "scan_interval": 10,
    "upload_interval": 300
}
EOF

chmod 644 ${BOOT_DIR}/wigle_config.json

echo ""
echo "Creating systemd service..."
cat > /etc/systemd/system/wartooth.service << 'EOF'
[Unit]
Description=Wartooth Bluetooth Scanner
After=network.target bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/bin/wartooth
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/python3 /usr/local/bin/wartooth/scanner.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "Enabling service..."
systemctl daemon-reload
systemctl enable wartooth.service

echo ""
echo "Creating udev rules..."
cat > /etc/udev/rules.d/99-bluetooth.rules << 'EOF'
ACTION=="add", SUBSYSTEM=="usb", ATTRS{bInterfaceClass}=="e0", ATTRS{bInterfaceSubClass}=="01", ATTRS{bInterfaceProtocol}=="01", RUN+="/usr/bin/hciconfig hci0 up"
EOF

udevadm control --reload-rules

echo ""
echo "Creating control script..."
cat > /usr/local/bin/wartooth-control << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "Starting Wartooth..."
        systemctl start wartooth
        ;;
    stop)
        echo "Stopping Wartooth..."
        systemctl stop wartooth
        ;;
    restart)
        echo "Restarting Wartooth..."
        systemctl restart wartooth
        ;;
    status)
        systemctl status wartooth
        ;;
    logs)
        journalctl -u wartooth -f
        ;;
    config)
        BOOT_DIR="/boot/firmware"
        [ ! -d "$BOOT_DIR" ] && BOOT_DIR="/boot"
        nano ${BOOT_DIR}/wigle_config.json
        echo ""
        echo "Restart scanner after changes:"
        echo "  wartooth-control restart"
        ;;
    files)
        echo "Saved scans:"
        ls -lh /home/pi/wigle_scans/ | tail -20
        echo ""
        echo "Total size:"
        du -sh /home/pi/wigle_scans/
        ;;
    test)
        echo "Testing Bluetooth..."
        sudo hciconfig hci0 up
        sudo hcitool dev
        echo ""
        echo "Testing display..."
        python3 -c "import RPi.GPIO; import spidev; print('GPIO & SPI OK')" 2>/dev/null && echo "Display libs OK" || echo "Display libs missing"
        ;;
    *)
        echo "Wartooth Control v2.0"
        echo ""
        echo "Usage: wartooth-control [command]"
        echo ""
        echo "Commands:"
        echo "  start    - Start scanner"
        echo "  stop     - Stop scanner"
        echo "  restart  - Restart scanner"
        echo "  status   - Show status"
        echo "  logs     - View live logs"
        echo "  config   - Edit configuration"
        echo "  files    - Show saved scans"
        echo "  test     - Test Bluetooth & hardware"
        echo ""
        ;;
esac
EOF

chmod +x /usr/local/bin/wartooth-control

echo ""
echo "========================================"
echo "Installation complete!"
echo "========================================"
echo ""
echo "✓ System updated"
echo "✓ Bluetooth configured"
echo "✓ Display drivers installed"
echo "✓ Scanner installed"
echo "✓ Autostart enabled"
echo ""
echo "NEXT STEPS:"
echo "========================================"
echo ""
echo "1. Configure API credentials:"
echo "   sudo wartooth-control config"
echo ""
echo "   Enter:"
echo "   - api_name: Your Wigle.net API Name"
echo "   - api_token: Your Wigle.net API Token"
echo ""
echo "2. Test hardware:"
echo "   sudo wartooth-control test"
echo ""
echo "3. Start scanner:"
echo "   sudo wartooth-control start"
echo ""
echo "USEFUL COMMANDS:"
echo "========================================"
echo "  wartooth-control status   - Check status"
echo "  wartooth-control logs     - View live logs"
echo "  wartooth-control files    - Show scans"
echo "  wartooth-control restart  - After config changes"
echo ""
echo "NOTES:"
echo "========================================"
echo "- Plug in USB Bluetooth dongle BEFORE starting"
echo "- Scanner starts automatically on boot"
echo "- CSV files: /home/pi/wigle_scans/"
echo "- Config: ${BOOT_DIR}/wigle_config.json"
echo ""

read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting in 3 seconds..."
    sleep 3
    reboot
fi
