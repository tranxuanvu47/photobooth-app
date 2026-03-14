import os
import json

# Base directory
BASE_DIR = r"D:\photobooth-app"
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")
RAW_DIR = os.path.join(BASE_DIR, "raw_captures")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Đường dẫn đến file giao diện, khung hình
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
FRAME_PATH = os.path.join(ASSETS_DIR, "frame.png")

# Persistent Settings
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
APP_MODE = "wedding" # Default: wedding, normal

def load_config():
    global APP_MODE
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                APP_MODE = data.get("app_mode", "normal")
        except: pass

def save_config():
    try:
        data = {"app_mode": APP_MODE}
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except: pass

# Tự động tạo thư mục nếu chưa tồn tại
LUTS_DIR = os.path.join(OUTPUT_DIR, "luts")
for d in [CAPTURES_DIR, RAW_DIR, OUTPUT_DIR, ASSETS_DIR, LUTS_DIR]:
    os.makedirs(d, exist_ok=True)

load_config()
