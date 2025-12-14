#!/usr/bin/env python3

import subprocess
import json
import csv
import requests
import time
import os
import re
from datetime import datetime
from pathlib import Path
import threading

try:
    from PIL import Image, ImageDraw, ImageFont
    import spidev
    import RPi.GPIO as GPIO
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    print("Display modules not available")

CONFIG_FILE = "/boot/firmware/wigle_config.json"
if not os.path.exists(CONFIG_FILE):
    CONFIG_FILE = "/boot/wigle_config.json"

CSV_DIR = "/home/pi/wigle_scans"
SCAN_INTERVAL = 10
UPLOAD_INTERVAL = 300

class ST7735S:
    
    def __init__(self):
        self.DC_PIN = 25
        self.RST_PIN = 27
        self.BL_PIN = 24
        
        self.width = 128
        self.height = 128
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.DC_PIN, GPIO.OUT)
        GPIO.setup(self.RST_PIN, GPIO.OUT)
        GPIO.setup(self.BL_PIN, GPIO.OUT)
        
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 4000000
        self.spi.mode = 0
        
        self.reset()
        self.init_display()
        
        GPIO.output(self.BL_PIN, GPIO.HIGH)
    
    def reset(self):
        GPIO.output(self.RST_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.RST_PIN, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(self.RST_PIN, GPIO.HIGH)
        time.sleep(0.1)
    
    def write_cmd(self, cmd):
        GPIO.output(self.DC_PIN, GPIO.LOW)
        self.spi.writebytes([cmd])
    
    def write_data(self, data):
        GPIO.output(self.DC_PIN, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            self.spi.writebytes(data)
    
    def init_display(self):
        self.write_cmd(0x11)
        time.sleep(0.12)
        
        self.write_cmd(0xB1)
        self.write_data([0x01, 0x2C, 0x2D])
        
        self.write_cmd(0xB2)
        self.write_data([0x01, 0x2C, 0x2D])
        
        self.write_cmd(0xB3)
        self.write_data([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])
        
        self.write_cmd(0xB4)
        self.write_data(0x07)
        
        self.write_cmd(0xC0)
        self.write_data([0xA2, 0x02, 0x84])
        
        self.write_cmd(0xC1)
        self.write_data(0xC5)
        
        self.write_cmd(0xC2)
        self.write_data([0x0A, 0x00])
        
        self.write_cmd(0xC3)
        self.write_data([0x8A, 0x2A])
        
        self.write_cmd(0xC4)
        self.write_data([0x8A, 0xEE])
        
        self.write_cmd(0xC5)
        self.write_data(0x0E)
        
        self.write_cmd(0x36)
        self.write_data(0xC8)
        
        self.write_cmd(0x3A)
        self.write_data(0x05)
        
        self.write_cmd(0x2A)
        self.write_data([0x00, 0x02, 0x00, 0x81])
        
        self.write_cmd(0x2B)
        self.write_data([0x00, 0x01, 0x00, 0x80])
        
        self.write_cmd(0xE0)
        self.write_data([0x02, 0x1c, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2d,
                        0x29, 0x25, 0x2B, 0x39, 0x00, 0x01, 0x03, 0x10])
        
        self.write_cmd(0xE1)
        self.write_data([0x03, 0x1d, 0x07, 0x06, 0x2E, 0x2C, 0x29, 0x2D,
                        0x2E, 0x2E, 0x37, 0x3F, 0x00, 0x00, 0x02, 0x10])
        
        self.write_cmd(0x13)
        time.sleep(0.01)
        
        self.write_cmd(0x29)
        time.sleep(0.12)
    
    def display_image(self, image):
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        
        rgb_image = image.convert('RGB')
        pixels = []
        
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = rgb_image.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixels.append(rgb565 >> 8)
                pixels.append(rgb565 & 0xFF)
        
        self.write_cmd(0x2C)
        self.write_data(pixels)

class Display:
    def __init__(self):
        self.available = DISPLAY_AVAILABLE
        if self.available:
            try:
                self.disp = ST7735S()
                self.width = 128
                self.height = 128
                self.image = Image.new('RGB', (self.width, self.height), color=(0, 0, 0))
                self.draw = ImageDraw.Draw(self.image)
                try:
                    self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                    self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                except:
                    self.font = ImageFont.load_default()
                    self.font_large = ImageFont.load_default()
            except Exception as e:
                print(f"Display error: {e}")
                self.available = False
    
    def clear(self):
        if self.available:
            self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=(0, 0, 0))
    
    def show_status(self, devices_found, total_scans, last_upload, status_msg):
        if not self.available:
            return
        
        try:
            self.clear()
            y = 5
            
            self.draw.text((5, y), "Wartooth Scanner", font=self.font_large, fill=(0, 255, 0))
            y += 20
            
            self.draw.line((5, y, self.width - 5, y), fill=(0, 150, 0))
            y += 8
            
            self.draw.text((5, y), f"Found: {devices_found}", font=self.font, fill=(255, 255, 255))
            y += 15
            
            self.draw.text((5, y), f"Scans: {total_scans}", font=self.font, fill=(255, 255, 255))
            y += 15
            
            if last_upload:
                upload_time = last_upload.strftime("%H:%M")
                self.draw.text((5, y), f"Upload: {upload_time}", font=self.font, fill=(255, 255, 0))
            else:
                self.draw.text((5, y), "Upload: pending", font=self.font, fill=(255, 255, 0))
            y += 20
            
            self.draw.line((5, y, self.width - 5, y), fill=(0, 150, 0))
            y += 8
            
            words = status_msg.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                if len(test_line) * 6 < self.width - 10:
                    line = test_line
                else:
                    self.draw.text((5, y), line, font=self.font, fill=(0, 200, 255))
                    y += 12
                    line = word + " "
            if line:
                self.draw.text((5, y), line, font=self.font, fill=(0, 200, 255))
            
            self.disp.display_image(self.image)
        except Exception as e:
            print(f"Display update error: {e}")

class WigleConfig:
    def __init__(self):
        self.api_name = ""
        self.api_token = ""
        self.load_config()
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.api_name = config.get('api_name', '')
                self.api_token = config.get('api_token', '')
        else:
            self.create_default_config()
    
    def create_default_config(self):
        config = {
            'api_name': 'YOUR_WIGLE_API_NAME',
            'api_token': 'YOUR_WIGLE_API_TOKEN',
            'scan_interval': SCAN_INTERVAL,
            'upload_interval': UPLOAD_INTERVAL
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Config created: {CONFIG_FILE}")

class BluetoothScanner:
    def __init__(self, config, display):
        self.config = config
        self.display = display
        self.csv_file = None
        self.csv_writer = None
        self.devices_found = 0
        self.total_scans = 0
        self.last_upload = None
        self.status_msg = "Initializing..."
        self.setup_csv()
    
    def setup_csv(self):
        Path(CSV_DIR).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{CSV_DIR}/wartooth_{timestamp}.csv"
        
        self.csv_file = open(filename, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        
        self.csv_writer.writerow([
            'WigleWifi-1.4',
            'appRelease=2.0',
            'model=Wartooth',
            'release=RaspberryPiZero2W',
            'device=btscanner',
            'display=waveshare144',
            'board=bcm2710',
            'brand=wartooth'
        ])
        
        self.csv_writer.writerow([
            'MAC', 'SSID', 'AuthMode', 'FirstSeen', 'Channel', 
            'RSSI', 'CurrentLatitude', 'CurrentLongitude', 
            'AltitudeMeters', 'AccuracyMeters', 'Type'
        ])
        self.csv_file.flush()
        
        print(f"CSV created: {filename}")
        self.current_csv = filename
    
    def scan_bluetooth(self):
        try:
            self.status_msg = "Scanning..."
            self.update_display()
            
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], 
                         capture_output=True, timeout=5)
            
            result = subprocess.run(
                ['sudo', 'hcitool', 'scan', '--flush'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_devices = 0
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('Scanning'):
                    parts = line.split(maxsplit=1)
                    if len(parts) >= 1:
                        mac = parts[0]
                        name = parts[1] if len(parts) > 1 else 'Unknown'
                        
                        self.csv_writer.writerow([
                            mac,
                            name,
                            '[BT]',
                            timestamp,
                            '0',
                            '0',
                            '0.0',
                            '0.0',
                            '0.0',
                            '0.0',
                            'BT'
                        ])
                        new_devices += 1
            
            self.csv_file.flush()
            self.devices_found += new_devices
            self.total_scans += 1
            
            self.status_msg = f"OK: {new_devices} new"
            print(f"Scan #{self.total_scans}: {new_devices} devices")
            
        except subprocess.TimeoutExpired:
            self.status_msg = "Scan timeout"
            print("Scan timeout")
        except Exception as e:
            self.status_msg = f"Error: {str(e)[:20]}"
            print(f"Scan error: {e}")
        
        self.update_display()
    
    def upload_to_wigle(self):
        if not self.config.api_name or self.config.api_name == 'YOUR_WIGLE_API_NAME':
            self.status_msg = "No API keys"
            self.update_display()
            return
        
        if not os.path.exists(self.current_csv):
            self.status_msg = "No data"
            self.update_display()
            return
        
        try:
            self.status_msg = "Uploading..."
            self.update_display()
            
            with open(self.current_csv, 'rb') as f:
                files = {'file': (os.path.basename(self.current_csv), f, 'text/csv')}
                auth = (self.config.api_name, self.config.api_token)
                
                response = requests.post(
                    'https://api.wigle.net/api/v2/file/upload',
                    auth=auth,
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.status_msg = "Upload OK"
                    print(f"Upload successful")
                    self.last_upload = datetime.now()
                    
                    self.csv_file.close()
                    self.setup_csv()
                else:
                    self.status_msg = f"Error {response.status_code}"
                    print(f"Upload failed: {response.status_code}")
                    
        except Exception as e:
            self.status_msg = f"Error: {str(e)[:15]}"
            print(f"Upload error: {e}")
        
        self.update_display()
    
    def update_display(self):
        self.display.show_status(
            self.devices_found,
            self.total_scans,
            self.last_upload,
            self.status_msg
        )
    
    def run(self):
        last_upload_time = time.time()
        
        self.status_msg = "Ready"
        self.update_display()
        
        while True:
            self.scan_bluetooth()
            
            if time.time() - last_upload_time >= UPLOAD_INTERVAL:
                self.upload_to_wigle()
                last_upload_time = time.time()
            
            time.sleep(SCAN_INTERVAL)

def main():
    print("=" * 50)
    print("Wartooth - Bluetooth Wardriving Scanner v2.0")
    print("=" * 50)
    
    config = WigleConfig()
    
    if config.api_name == 'YOUR_WIGLE_API_NAME':
        print(f"\nWARNING: API not configured!")
        print(f"Edit: {CONFIG_FILE}\n")
    
    display = Display()
    if display.available:
        print("Display OK")
    else:
        print("No display")
    
    scanner = BluetoothScanner(config, display)
    
    try:
        scanner.run()
    except KeyboardInterrupt:
        print("\n\nStopped")
        if scanner.csv_file:
            scanner.csv_file.close()
        if display.available:
            GPIO.cleanup()

if __name__ == "__main__":
    main()
