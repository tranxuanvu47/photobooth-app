import os

# Base directory
BASE_DIR = r"D:\photobooth-app"
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")
RAW_DIR = os.path.join(BASE_DIR, "raw_captures")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Đường dẫn đến file giao diện, khung hình
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
FRAME_PATH = os.path.join(ASSETS_DIR, "frame.png")

# Tự động tạo thư mục nếu chưa tồn tại
LUTS_DIR = os.path.join(OUTPUT_DIR, "luts")
for d in [CAPTURES_DIR, RAW_DIR, OUTPUT_DIR, ASSETS_DIR, LUTS_DIR]:
    os.makedirs(d, exist_ok=True)
