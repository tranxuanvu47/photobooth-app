import sys
import os
import json

# Detect if running as a PyInstaller bundle
if getattr(sys, 'frozen', False):
    # If frozen, PROJECT_DIR is the directory where the .exe is located
    PROJECT_DIR = os.path.dirname(sys.executable)
else:
    # If running normally, PROJECT_DIR is the current directory
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_DIR = os.path.join(PROJECT_DIR, "data")
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")
RAW_DIR = os.path.join(BASE_DIR, "raw_captures")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
FRAME_PATH = os.path.join(ASSETS_DIR, "frame.png")
# Layouts and frames should also be relative to EXE
COORDINATES_DIR = os.path.join(PROJECT_DIR, "frame_configs")
FRAMES_DIR = os.path.join(PROJECT_DIR, "frames")

# Persistent Settings
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
APP_MODE = "wedding" # Default: wedding, normal
ADMIN_PASSWORD_ENABLED = True
PAYMENT_ENABLED = False # Mặc định tắt để ko ảnh hưởng flow cũ trừ khi bật
PAYMENT_URL = "http://localhost:8000"
PAYMENT_PACKAGE_ID = "pkg_photobooth"
PAYMENT_AMOUNT = 50000

def load_config():
    global APP_MODE, NC_ENABLED, NC_URL, NC_USER, NC_PASS, NC_REMOTE_PATH, NC_SHARE_URL, CAPTURE_ONE_MODE, CAPTURE_ONE_WINDOW_TITLE
    global PAYMENT_ENABLED, PAYMENT_URL, PAYMENT_PACKAGE_ID, PAYMENT_AMOUNT
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
                ADMIN_PASSWORD_ENABLED = data.get("admin_password_enabled", True)
                CAPTURE_ONE_MODE = data.get("capture_one_mode", False)
                CAPTURE_ONE_WINDOW_TITLE = data.get("capture_one_window_title", "Capture One,CaptureOne")
                PAYMENT_ENABLED = data.get("payment_enabled", False)
                PAYMENT_URL = data.get("payment_url", "http://localhost:8000")
                PAYMENT_PACKAGE_ID = data.get("payment_package_id", "pkg_photobooth")
                PAYMENT_AMOUNT = data.get("payment_amount", 50000)
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
            "camera_quality": CAMERA_QUALITY,
            "admin_password_enabled": ADMIN_PASSWORD_ENABLED,
            "capture_one_mode": CAPTURE_ONE_MODE,
            "capture_one_window_title": CAPTURE_ONE_WINDOW_TITLE,
            "payment_enabled": PAYMENT_ENABLED,
            "payment_url": PAYMENT_URL,
            "payment_package_id": PAYMENT_PACKAGE_ID,
            "payment_amount": PAYMENT_AMOUNT
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
NC_REMOTE_PATH = "/" # Thư mục gốc trên Nextcloud
NC_SHARE_URL = "https://drive.congchunghoangvanviet.com/s/5dHkHrEDdnK9zPH" # Link chia sẻ công khai
MIRROR_MODE = True
CAMERA_QUALITY = 90
CAPTURE_ONE_MODE = False
CAPTURE_ONE_WINDOW_TITLE = "Capture One,CaptureOne"

load_config()
