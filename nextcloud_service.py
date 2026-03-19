import os
import threading
from webdav3.client import Client

class NextcloudUploader:
    def __init__(self, username, password, base_url="https://drive.congchunghoangvanviet.com/remote.php/webdav/"):
        self.options = {
            'webdav_hostname': base_url,
            'webdav_login':    username,
            'webdav_password': password
        }
        self.client = Client(self.options)
        self.root_folder = "Photobooth"
        self._ensure_folder(self.root_folder)

    def _ensure_folder(self, folder_name):
        try:
            if not self.client.check(folder_name):
                self.client.mkdir(folder_name)
        except Exception as e:
            print(f"Lỗi tạo thư mục cơ sở {folder_name}: {e}")

    def upload_multiple_bg(self, local_paths, session_name, callback=None):
        def _task():
            try:
                # Đảm bảo có thư mục con của phiên làm việc
                remote_folder = f"{self.root_folder}/{session_name}"
                self._ensure_folder(remote_folder)
                
                uploaded_paths = []
                for local_path in local_paths:
                    if not os.path.exists(local_path):
                        continue
                        
                    # Tải file lên
                    filename = os.path.basename(local_path)
                    remote_path = f"{remote_folder}/{filename}"
                    self.client.upload_sync(remote_path=remote_path, local_path=local_path)
                    uploaded_paths.append(remote_path)
                    print(f"[Nextcloud] Upload thành công: {remote_path}")
                
                if callback:
                    callback(True, f"Đã tải {len(uploaded_paths)} file lên Nextcloud")
                    
            except Exception as e:
                print(f"[Nextcloud] Lỗi Upload: {e}")
                if callback:
                    callback(False, str(e))
        
        thread = threading.Thread(target=_task)
        thread.daemon = True
        thread.start()
