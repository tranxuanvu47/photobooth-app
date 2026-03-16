import os
import json

# Đường dẫn đến file giao diện, khung hình
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(PROJECT_DIR, "data")
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")
RAW_DIR = os.path.join(BASE_DIR, "raw_captures")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
FRAME_PATH = os.path.join(ASSETS_DIR, "frame.png")

# Persistent Settings
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
APP_MODE = "wedding" # Default: wedding, normal

def load_config():
    global APP_MODE, NC_ENABLED, NC_URL, NC_USER, NC_PASS, NC_REMOTE_PATH, NC_SHARE_URL
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                APP_MODE = data.get("app_mode", "normal")
                NC_ENABLED = data.get("nc_enabled", False)
                NC_URL = data.get("nc_url", NC_URL)
                NC_USER = data.get("nc_user", NC_USER)
                NC_PASS = data.get("nc_pass", NC_PASS)
                NC_REMOTE_PATH = data.get("nc_remote_path", "Photobooth")
                NC_SHARE_URL = data.get("nc_share_url", "")
                MIRROR_MODE = data.get("mirror_mode", True)
                CAMERA_QUALITY = data.get("camera_quality", 90)
        except: pass

def save_config():
    try:
        data = {
            "app_mode": APP_MODE,
            "nc_enabled": NC_ENABLED,
            "nc_url": NC_URL,
            "nc_user": NC_USER,
            "nc_pass": NC_PASS,
            "nc_remote_path": NC_REMOTE_PATH,
            "nc_share_url": NC_SHARE_URL,
            "mirror_mode": MIRROR_MODE,
            "camera_quality": CAMERA_QUALITY
        }
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except: pass

# Tự động tạo thư mục nếu chưa tồn tại
LUTS_DIR = os.path.join(OUTPUT_DIR, "luts")
for d in [CAPTURES_DIR, RAW_DIR, OUTPUT_DIR, ASSETS_DIR, LUTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Nextcloud Configuration
NC_ENABLED = True
NC_URL = "https://drive.congchunghoangvanviet.com/remote.php/dav/files/photobooth/"
NC_USER = "photobooth"
NC_PASS = "7daTr-r7zyy-zY6cB-Zeopx-g73kQ"
NC_REMOTE_PATH = "Photobooth" # Thư mục gốc trên Nextcloud
NC_SHARE_URL = "" # Link chia sẻ công khai
MIRROR_MODE = True
CAMERA_QUALITY = 90

load_config()
