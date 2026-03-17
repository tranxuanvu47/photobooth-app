import PyInstaller.__main__
import os
import shutil

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

print("Cleaning old build...")

try:
    if os.path.exists("build"):
        shutil.rmtree("build")

    if os.path.exists("dist"):
        # Try to remove files in dist, but catch if they are locked
        shutil.rmtree("dist")
except PermissionError as e:
    print(f"\n❌ LỖI QUYỀN TRUY CẬP: {e}")
    print("----------------------------------------------------------------")
    print("Ứng dụng PhotoboothStation.exe đang được mở hoặc đang chạy ngầm.")
    print("Vui lòng ĐÓNG ỨNG DỤNG trước khi chạy lệnh build mới.")
    print("----------------------------------------------------------------")
    exit(1)
except Exception as e:
    print(f"Lỗi không xác định khi dọn dẹp: {e}")
    exit(1)

print("Building PhotoboothStation.exe...")

build_args = [
    "flet_main.py",
    "--name=PhotoboothStation",
    "--onefile",
    "--windowed",
    "--clean",
    "--hidden-import=flet",
    "--hidden-import=cv2",
    "--hidden-import=numpy",
    "--hidden-import=PIL",
]

if os.path.exists("assets/icon.ico"):
    build_args.append("--icon=assets/icon.ico")

PyInstaller.__main__.run(build_args)

# Thêm bước copy các thư mục cần thiết vào dist sau khi build xong
print("\nCopying resource folders to dist...")
dist_path = os.path.join(current_dir, "dist")
folders_to_copy = ["assets", "frames", "frame_configs", "data"]

for folder in folders_to_copy:
    src = os.path.join(current_dir, folder)
    dst = os.path.join(dist_path, folder)
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"✅ Copied {folder} to dist/")

print("\n✅ Build completed!")
print("File location: dist/PhotoboothStation.exe")
print("Lưu ý: Bạn phải mang theo cả bộ thư mục trong 'dist' (gồm file .exe và các thư mục bên cạnh) để app hoạt động đầy đủ.")