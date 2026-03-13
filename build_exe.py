import PyInstaller.__main__
import os
import shutil

# Make sure we're in the right directory
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

print("Đang dọn dẹp thư mục build cũ...")
if os.path.exists('build'): shutil.rmtree('build')
if os.path.exists('dist'): shutil.rmtree('dist')

print("Đang khởi tạo tiến trình đóng gói Photobooth.exe...")

PyInstaller.__main__.run([
    'main.py',
    '--name=PhotoboothStation',
    '--windowed', # Ẩn cửa sổ console đen xì lúc chạy
    '--onefile', # Gói tất cả vào 1 file .exe duy nhất
    '--icon=NONE', # Tạm thời chưa có icon
    '--add-data=config.py;.',
    '--add-data=camera_controller.py;.',
    '--add-data=image_processor.py;.',
    '--add-data=printer_service.py;.',
    '--add-data=ui_main.py;.',
    '--hidden-import=PyQt5',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=PIL',
    '--hidden-import=win32print',
    '--hidden-import=win32ui',
    '--hidden-import=win32gui',
    '--clean'
])

print("\n\n✅ ĐÓNG GÓI HOÀN TẤT! File chạy nằm trong thư mục 'dist/PhotoboothStation.exe'")
