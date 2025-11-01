import serial
import serial.tools.list_ports
import time
import re
import pygame
import sys
import math
import random
from pygame.locals import *

# ==============================
# CONSTANTS
# ==============================
BAUD = 38400
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
BLACK = (0, 0, 20)
WHITE = (255, 255, 255)
COLOR_WHITE = (255,255,255)
# ==============================
# SERIAL COMMUNICATION
# ==============================
def find_active_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ No COM ports found!")
        return None

    def get_com_num(port):
        try:
            return int(''.join(filter(str.isdigit, port.device)))
        except:
            return 0
    ports.sort(key=get_com_num, reverse=True)

    preferred_keywords = ("HC-05", "Bluetooth", "Arduino", "Serial")
    def port_priority(p):
        desc = (p.description or "").lower()
        for kw in preferred_keywords:
            if kw.lower() in desc:
                return 0
        return 1
    ports.sort(key=port_priority)

    for port in ports:
        ser = None
        try:
            ser = serial.Serial(port.device, BAUD, timeout=0.1)
            time.sleep(0.1)
            ser.reset_input_buffer()
            valid_count = 0
            start = time.time()
            while time.time() - start < 2.0:
                raw = ser.readline()
                if not raw:
                    continue
                data = raw.decode(errors='ignore').strip()
                if data and "X:" in data and "Y:" in data:
                    x, y = parse_xy(data)
                    if x is not None:
                        valid_count +=1
                        if valid_count >=2:
                            print(f"✅ Found joystick on {port.device}")
                            return ser
            if ser:
                ser.close()
        except:
            if ser:
                try: ser.close()
                except: pass
            continue
    print("\n❌ No joystick found!")
    return None

def parse_xy(line):
    pattern = r"(?:X[:=]\s*(\d+))[^\d]*(?:Y[:=]\s*(\d+))"
    match = re.search(pattern, line)
    if match:
        return int(match.group(1)), int(match.group(2))
    numbers = re.findall(r'\b\d{2,4}\b', line)
    return (int(numbers[0]), int(numbers[1])) if len(numbers) >= 2 else (None, None)
