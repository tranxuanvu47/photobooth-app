import os
import shutil
import time
import config

def verify_monitoring():
    # 1. Prepare
    raw_dir = config.RAW_DIR
    current_session = "Khach_Mac_Dinh"  # Default session from main.py
    session_dir = os.path.join(raw_dir, current_session)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(session_dir, exist_ok=True)

    dummy_filename = "test_image_monitor.jpg"
    dummy_path = os.path.join(raw_dir, dummy_filename)
    target_path = os.path.join(session_dir, dummy_filename)

    # 2. Cleanup existing if any
    if os.path.exists(dummy_path): os.remove(dummy_path)
    if os.path.exists(target_path): os.remove(target_path)

    print(f"--- Bắt đầu kiểm tra tính năng theo dõi file ---")
    print(f"Thư mục RAW: {raw_dir}")
    print(f"Thư mục Session mục tiêu: {session_dir}")

    # 3. Create dummy file in raw_dir
    with open(dummy_path, "w") as f:
        f.write("dummy image data")
    
    print(f"1. Đã tạo file giả tại: {dummy_path}")
    print("2. Đang chờ ứng dụng di chuyển file (Yêu cầu ứng dụng đang chạy)...")
    
    # We can't easily auto-start the UI app and wait for it in a script without blocking
    # but we can verify the LOGIC itself if we import it, or just ask the user to test.
    # However, since I am an agent, I will check if the file is gone from raw and moved to session.
    
    # For a real test, the USER should run the app. 
    # But I can "mock" the monitor call to see if it works as intended.
    
    from main import PhotoboothApp
    from PyQt5.QtWidgets import QApplication
    import sys

    # Minimal App for testing logic
    app = QApplication(sys.argv)
    booth = PhotoboothApp()
    booth.current_session = current_session
    
    print("3. Đang giả lập chạy monitor_raw_dir()...")
    booth.monitor_raw_dir()
    
    if os.path.exists(target_path) and not os.path.exists(dummy_path):
        print("✅ THÀNH CÔNG: File đã được di chuyển vào đúng thư mục khách!")
    else:
        print("❌ THẤT BẠI: File không được di chuyển.")

    # Cleanup
    if os.path.exists(target_path): os.remove(target_path)

if __name__ == "__main__":
    verify_monitoring()
