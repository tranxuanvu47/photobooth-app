from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
from config import CAPTURES_DIR, RAW_DIR
from image_processor import ImageProcessor
from datetime import datetime
import time
import os
import cv2
import numpy as np

# Xác định cờ backend trên Windows.
# ANY (mặc định MSMF trên Win) mở chậm nhưng ổn định dải màu hơn.
# Tuy nhiên MSMF dễ bị crash# Các hằng số cho OpenCV để tránh crash khi Threading / MSMF backend conflict
BACKEND_FLAG = cv2.CAP_DSHOW

# Thử import gphoto2 (PTP mode cho Sony/DSLR)
try:
    import gphoto2 as gp
    HAS_GPHOTO2 = True
except ImportError:
    HAS_GPHOTO2 = False

class CameraWorker(QThread):
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    image_captured_signal = pyqtSignal(str)
    frame_signal = pyqtSignal(QImage)
    camera_list_signal = pyqtSignal(list)
    camera_properties_signal = pyqtSignal(dict)

    def __init__(self, camera_index=0):
        super().__init__()
        self.running = True # Renamed from is_running
        self.action = "idle"
        self.camera_index = str(camera_index) # Ensure it's a string for consistency with existing logic
        self.pool = {}
        self._capture_pending = False
        self.is_paused = False
        self.capture_requested = False # New variable
        self.current_session = "Khach_Mac_Dinh"  # Mặc định
        self.digital_zoom = 1.0 # 1.0 (No Zoom) to 3.0 (3x Zoom)

    def set_session(self, session_name):
        self.current_session = session_name
        self.is_paused = False

    def request_scan(self):
        self.action = "scan"
        
    def change_camera(self, index):
        self.camera_index = str(index)
        self.action = "preview"
        self.is_paused = False

    def request_capture(self):
        self._capture_pending = True
        
    def resume_preview(self):
        self.is_paused = False

    def stop(self):
        self.running = False # Renamed from is_running
        self.action = "stop"

    def run(self):
        while self.running: # Renamed from is_running
            if self.action == "scan":
                self._do_scan()
                if self.action == "scan": # if not overridden
                    self.action = "idle"
            elif self.action == "preview":
                self._do_preview()
            else:
                time.sleep(0.05)
                
        # Cleanup khi thread dừng
        for cap in self.pool.values():
            if isinstance(cap, cv2.VideoCapture): # Only release OpenCV caps
                cap.release()
        self.pool.clear()

    def _do_scan(self):
        start_time = time.time()
        self.status_signal.emit("Đang quét các máy ảnh khả dụng (Lưu ý: Quá trình này có thể mất vài giây lần đầu)...")
        available_cameras = []
        
        # In log kiểm tra môi trường
        if HAS_GPHOTO2:
            self.status_signal.emit("[PTP] Môi trường gphoto2 hợp lệ. Đang kiểm tra PTP Camera...")
        else:
            self.status_signal.emit("[PTP] Không tìm thấy thư viện gphoto2, bỏ qua quét PTP.")
            
        # 1. Quét gphoto2 (PTP Sony Cameras) trước
        if HAS_GPHOTO2:
            try:
                context = gp.Context()
                self.status_signal.emit("[PTP] Đang gọi gp.Camera.autodetect()...")
                camera_list = gp.Camera.autodetect(context)
                for index, (name, addr) in enumerate(camera_list):
                    identifier = f"gphoto2_{index}"
                    available_cameras.append((identifier, f"[PTP] {name}"))
                    self.pool[identifier] = name # Lưu name làm dummy value để verify
            except Exception as e:
                self.error_signal.emit(f"Lỗi quét gphoto2: {e}")
                
        # 2. Quét Webcam / OpenCV thông thường
        for i in range(5):
            idx_str = str(i)
            if not self.running or self.action != "scan":
                break
                
            if idx_str not in self.pool:
                try:
                    # Bắt buộc dùng DSHOW trên Windows để tránh block thread với MSMF/ANY
                    cap = cv2.VideoCapture(i, BACKEND_FLAG)
                        
                    if cap.isOpened():
                        # Đọc nháp 1 frame để test xem camera có thực sự trả về data hay không (tránh crash cv::Mat)
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            self.pool[idx_str] = cap
                        else:
                            cap.release()
                    else:
                        cap.release()
                except Exception as e:
                    pass
                    
            cap = self.pool.get(idx_str)
            if cap and isinstance(cap, cv2.VideoCapture) and cap.isOpened():
                available_cameras.append((idx_str, f"Camera {i}"))
                    
        self.camera_list_signal.emit(available_cameras)
        elapsed = time.time() - start_time
        if available_cameras:
            self.status_signal.emit(f"Tìm thấy {len(available_cameras)} máy ảnh. (Mất {elapsed:.2f}s)")
        else:
            self.error_signal.emit(f"Không tìm thấy máy ảnh nào. (Mất {elapsed:.2f}s)")

    def _do_preview(self):
        # ======= LUỒNG PTP GPHOTO2 =======
        if isinstance(self.camera_index, str) and self.camera_index.startswith("gphoto2_"):
            if not HAS_GPHOTO2: return
            
            self.status_signal.emit(f"Đang hiển thị Live Preview từ PTP {self.pool.get(self.camera_index)}...")
            safe_index = self.camera_index
            try:
                # Khởi tạo camera PTP thực
                camera = gp.check_result(gp.gp_camera_new())
                context = gp.Context()
                gp.check_result(gp.gp_camera_init(camera, context))
            except Exception as e:
                self.error_signal.emit(f"Không thể kết nối PTP Camera: {e}")
                self._emit_mock_frame()
                self.action = "idle"
                return

            while self.action == "preview" and self.camera_index == safe_index and self.running: # Renamed from is_running
                try:
                    if self._capture_pending:
                        self._capture_pending = False
                        self.status_signal.emit("Bắt đầu chụp chất lượng cao qua PTP...")
                        
                        # Chụp & Tải ảnh
                        print("[PTP] Đang yêu cầu chụp ảnh từ GPhoto...")
                        try:
                            file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                            print(f"[PTP] Chụp thành công. Đang tải {file_path.name}...")
                            
                            # Update save path to include Session Directory
                            session_dir = os.path.join(RAW_DIR, self.current_session)
                            os.makedirs(session_dir, exist_ok=True)
                            
                            target_path = os.path.join(session_dir, file_path.name)
                            camera.file_get(
                                file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL, target_path)
                                
                            # Ép tỉ lệ ảnh PTP về 4:3
                            ImageProcessor.crop_to_4_3(target_path)
                            
                            print(f"[PTP] Đã lưu ảnh thô RAW tại: {target_path}")
                            
                            self.status_signal.emit("Tải ảnh PTP hoàn tất!")
                            self.image_captured_signal.emit(target_path) # Emit the new target_path
                            self.is_paused = True
                        except Exception as e:
                            self.error_signal.emit(f"Lỗi khi chụp hoặc tải ảnh PTP: {e}")
                            self.is_paused = False # Resume preview if capture fails
                    
                    if not self.is_paused:
                        # Đọc luồng khung hình nhẹ (Video Streaming PTP)
                        camera_file = gp.check_result(gp.gp_camera_capture_preview(camera, context))
                        file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
                        
                        # Giải mã jpeg memory buffer qua OpenCV
                        image_data = np.frombuffer(memoryview(file_data), dtype=np.uint8)
                        frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                        
                        if frame is not None and frame.size > 0:
                            frame = ImageProcessor.crop_array_to_4_3(frame)
                            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            
                            h, w, ch = rgb_image.shape
                            bytes_per_line = ch * w
                            # Optimize memory layout for QImage
                            if not rgb_image.flags['C_CONTIGUOUS']:
                                rgb_image = np.ascontiguousarray(rgb_image)
                                
                            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
                            self.frame_signal.emit(qt_image)
                            
                    time.sleep(0.015)
                    
                except Exception as e:
                    self.error_signal.emit(f"Lỗi đọc PTP Camera: {e}")
                    self._emit_mock_frame()
                    break
                    
            gp.check_result(gp.gp_camera_exit(camera, context))
            return
            
        # ======= LUỒNG WEBCAM OPENCV =======
        try:
            numeric_idx = int(self.camera_index)
        except ValueError:
            self.error_signal.emit(f"ID Camera không hợp lệ: {self.camera_index}")
            self._emit_mock_frame()
            self.action = "idle"
            return
            
        start_time = time.time()
        cap = self.pool.get(self.camera_index)
        
        # Nếu thiết bị từ pool đã release hoặc không có trong pool thì init lại
        if cap is None or not isinstance(cap, cv2.VideoCapture) or not getattr(cap, 'isOpened', lambda: False)():
            try:
                cap = cv2.VideoCapture(numeric_idx, BACKEND_FLAG)
                if not getattr(cap, 'isOpened', lambda: False)():
                    self.error_signal.emit(f"Không thể mở luồng OpenCV cho camera {numeric_idx}")
                    self._emit_mock_frame()
                    self.action = "idle"
                    return
                # Lưu lại cho lần chạy sau
                self.pool[self.camera_index] = cap
            except Exception as e:
                self.error_signal.emit(f"Lỗi khởi tạo OpenCV: {e}")
                self._emit_mock_frame()
                self.action = "idle"
                return
                
            open_time = time.time() - start_time
            self.status_signal.emit(f"[Debug] Kết nối luồng Camera {self.camera_index} mất {open_time:.2f}s")

        self.status_signal.emit(f"Đang hiển thị Live Preview từ Camera {self.camera_index}...")
        
        # Đọc Cấu hình Phần cứng Camera (Zoom, Focus) và gửi lên UI
        try:
            props = {
                'zoom': cap.get(cv2.CAP_PROP_ZOOM),
                'focus': cap.get(cv2.CAP_PROP_FOCUS),
                'autofocus': cap.get(cv2.CAP_PROP_AUTOFOCUS)
            }
            self.camera_properties_signal.emit(props)
        except Exception as e:
            print(f"Warning: Không đọc được hardware props: {e}")
        
        safe_index = self.camera_index
        while self.action == "preview" and self.camera_index == safe_index and self.running: # Renamed from is_running
            try:
                ret, frame = cap.read()
                if not ret or frame is None or getattr(frame, 'size', 0) == 0:
                    raise Exception("Failed to read frame")
                
                # Lật ngang (Mirror effect)
                frame = cv2.flip(frame, 1)

                # --- DIGITAL SOFTWARE ZOOM ---
                if self.digital_zoom > 1.0:
                    h, w = frame.shape[:2]
                    new_h, new_w = int(h / self.digital_zoom), int(w / self.digital_zoom)
                    y1, x1 = (h - new_h) // 2, (w - new_w) // 2
                    y2, x2 = y1 + new_h, x1 + new_w
                    frame = frame[y1:y2, x1:x2]

                # Cắt Crop tỉ lệ 4:3
                frame = ImageProcessor.crop_array_to_4_3(frame)
            except Exception as e:
                self.error_signal.emit(f"Lỗi phần cứng camera: {e}")
                self._emit_mock_frame()
                break
                
            if self._capture_pending:
                self._capture_pending = False
                self.status_signal.emit("Bắt đầu chụp ảnh chất lượng cao qua OpenCV...")
                
                from datetime import datetime
                filename = datetime.now().strftime("IMG_%Y%m%d_%H%M%S.jpg")
                
                session_dir = os.path.join(RAW_DIR, self.current_session)
                os.makedirs(session_dir, exist_ok=True)
                
                target_path = os.path.join(session_dir, filename)
                cv2.imwrite(target_path, frame)
                print(f"[OpenCV] Đã chụp và lưu ảnh thô RAW (chuẩn 4:3): {target_path}")
                self.status_signal.emit("Tải ảnh hoàn tất!")
                self.image_captured_signal.emit(target_path)
                self.is_paused = True
                
            if not self.is_paused:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                bytes_per_line = ch * w
                
                if not frame_rgb.flags['C_CONTIGUOUS']:
                    frame_rgb = np.ascontiguousarray(frame_rgb)
                    
                qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
                self.frame_signal.emit(qt_image)

            else:
                self.error_signal.emit("Lỗi đọc tín hiệu frame từ camera (Mất kết nối hoặc thiết bị bị chiếm).")
                self._emit_mock_frame()
                break
                
            time.sleep(0.015)

    def _emit_mock_frame(self):
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (1280, 720), color=(50, 50, 50))
            d = ImageDraw.Draw(img)
            d.text((500, 350), "CAMERA ERROR / MOCK MODE", fill=(255, 0, 0))
            cv_img = np.array(img)
            h, w, ch = cv_img.shape
            bytes_per_line = ch * w
            qt_image = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            self.frame_signal.emit(qt_image)
        except:
            pass

    def zoom_in(self):
        self.digital_zoom = min(self.digital_zoom + 0.2, 3.0)
        self.status_signal.emit(f"Digital Zoom: {self.digital_zoom:.1f}x")

    def zoom_out(self):
        self.digital_zoom = max(self.digital_zoom - 0.2, 1.0)
        self.status_signal.emit(f"Digital Zoom: {self.digital_zoom:.1f}x")

    def trigger_autofocus(self):
        cap = self.pool.get(self.camera_index)
        if cap and isinstance(cap, cv2.VideoCapture) and getattr(cap, 'isOpened', lambda: False)():
            # Force AF sweep by toggling property
            try:
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                time.sleep(0.1)
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except:
                pass


    def _create_mock_image(self, path):
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (1920, 1080), color=(30, 144, 255))
        d = ImageDraw.Draw(img)
        try:
            d.text((100, 500), "DUMMY IMAGE - CAMERA MOCK", fill=(255, 255, 0))
        except:
            pass
        img.save(path)
