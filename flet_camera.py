import threading
import time
import os
import cv2
import numpy as np
import base64
import config
from config import CAPTURES_DIR, RAW_DIR
from image_processor import ImageProcessor

# Xác định cờ backend trên Windows.
BACKEND_FLAG = cv2.CAP_DSHOW

try:
    import gphoto2 as gp
    HAS_GPHOTO2 = True
except ImportError:
    HAS_GPHOTO2 = False

class FletCameraWorker(threading.Thread):
    def __init__(self, camera_index=0):
        super().__init__(daemon=True)
        self.running = True
        self.action = "idle"
        self.camera_index = str(camera_index)
        self.pool = {}
        self._capture_pending = False
        self.is_paused = False
        self.current_session = "Khach_Mac_Dinh"
        self.digital_zoom = 1.0
        
        # Callbacks to replace pyqtSignal
        self.on_status = None
        self.on_error = None
        self.on_image_captured = None
        self.on_frame = None  # Passes base64 string
        self.on_camera_list = None
        self.on_camera_properties = None

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

    def pause_preview(self):
        self.is_paused = True

    def stop(self):
        self.running = False
        self.action = "stop"

    def run(self):
        while self.running:
            if self.action == "scan":
                self._do_scan()
                if self.action == "scan":
                    self.action = "idle"
            elif self.action == "preview":
                self._do_preview()
            else:
                time.sleep(0.05)
                
        for cap in self.pool.values():
            if isinstance(cap, cv2.VideoCapture):
                cap.release()
        self.pool.clear()

    def _emit_status(self, msg):
        if self.on_status: self.on_status(msg)

    def _emit_error(self, msg):
        if self.on_error: self.on_error(msg)
        
    def _emit_frame(self, frame_bgr):
        if not self.on_frame: return
        
        # Mirroring
        if getattr(config, 'MIRROR_MODE', True):
            frame_bgr = cv2.flip(frame_bgr, 1)

        # Optimize resolution for quality: Match screen size as much as possible
        # Since the app uses large glass cards, we need high-res preview to avoid blur.
        h, w = frame_bgr.shape[:2]
        target_h = 1080 # FULL HD resolution for the preview to match UI size
        if h > target_h:
            scale = target_h / h
            target_w = int(w * scale)
            preview_frame = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            preview_frame = frame_bgr

        # Optimize resolution: 800p provides a bit more detail than 720p while staying smooth
        h, w = frame_bgr.shape[:2]
        target_h = 800 
        if h > target_h:
            scale = target_h / h
            target_w = int(w * scale)
            preview_frame = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            preview_frame = frame_bgr

        # 1. Anti-noise: Median filter to kill grain
        preview_frame = cv2.medianBlur(preview_frame, 3)

        # 2. Stronger Sharpening (approx 20% increase)
        gaussian_blur = cv2.GaussianBlur(preview_frame, (0, 0), 1.5)
        # Increased from 1.2/-0.2 to 1.4/-0.4
        preview_frame = cv2.addWeighted(preview_frame, 1.4, gaussian_blur, -0.4, 0)

        # Use 88 quality for a bit more crispness
        _, buffer = cv2.imencode('.jpg', preview_frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
        b64_str = base64.b64encode(buffer).decode("utf-8")
        self.on_frame(b64_str)

    def _emit_mock_frame(self):
        mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(mock_frame, "CAMERA ERROR / MOCK MODE", (300, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        self._emit_frame(mock_frame)

    def _do_scan(self):
        start_time = time.time()
        self._emit_status("Đang quét các máy ảnh khả dụng (Lưu ý: Quá trình này có thể mất vài giây lần đầu)...")
        available_cameras = []
        
        if HAS_GPHOTO2:
            self._emit_status("[PTP] Môi trường gphoto2 hợp lệ. Đang kiểm tra PTP Camera...")
        else:
            self._emit_status("[PTP] Không tìm thấy thư viện gphoto2, bỏ qua quét PTP.")
            
        if HAS_GPHOTO2:
            try:
                context = gp.Context()
                self._emit_status("[PTP] Đang gọi gp.Camera.autodetect()...")
                camera_list = gp.Camera.autodetect(context)
                for index, (name, addr) in enumerate(camera_list):
                    identifier = f"gphoto2_{index}"
                    available_cameras.append((identifier, f"[PTP] {name}"))
                    self.pool[identifier] = name
            except Exception as e:
                print(f"DEBUG: GPhoto Scan Error: {e}")
                
        for i in range(5):
            idx_str = str(i)
            if not self.running or self.action != "scan":
                break
            if idx_str not in self.pool:
                try:
                    cap = cv2.VideoCapture(i, BACKEND_FLAG)
                    if cap.isOpened():
                        # Force MJPG for high res & high FPS compatibility
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            self.pool[idx_str] = cap
                        else:
                            cap.release()
                    else:
                        cap.release()
                except Exception:
                    pass
            cap = self.pool.get(idx_str)
            if cap and isinstance(cap, cv2.VideoCapture) and cap.isOpened():
                available_cameras.append((idx_str, f"Camera {i}"))
                    
        if self.on_camera_list:
            self.on_camera_list(available_cameras)
        elapsed = time.time() - start_time
        if available_cameras:
            self._emit_status(f"Tìm thấy {len(available_cameras)} máy ảnh. (Mất {elapsed:.2f}s)")
        else:
            print(f"DEBUG: No cameras found (Time: {elapsed:.2f}s)")

    def _do_preview(self):
        if isinstance(self.camera_index, str) and self.camera_index.startswith("gphoto2_"):
            if not HAS_GPHOTO2: return
            self._emit_status(f"Đang hiển thị Live Preview từ PTP {self.pool.get(self.camera_index)}...")
            safe_index = self.camera_index
            try:
                camera = gp.check_result(gp.gp_camera_new())
                context = gp.Context()
                gp.check_result(gp.gp_camera_init(camera, context))
            except Exception as e:
                print(f"DEBUG: PTP Connection Error: {e}")
                self._emit_mock_frame()
                self.action = "idle"
                return

            while self.action == "preview" and self.camera_index == safe_index and self.running:
                try:
                    if self._capture_pending:
                        self._capture_pending = False
                        self._emit_status("Bắt đầu chụp chất lượng cao qua PTP...")
                        print("[PTP] Đang yêu cầu chụp ảnh từ GPhoto...")
                        try:
                            file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                            print(f"[PTP] Chụp thành công. Đang tải {file_path.name}...")
                            session_dir = os.path.join(RAW_DIR, self.current_session)
                            os.makedirs(session_dir, exist_ok=True)
                            target_path = os.path.join(session_dir, file_path.name)
                            camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL, target_path)
                            ImageProcessor.crop_to_4_3(target_path)
                            self._emit_status("Tải ảnh PTP hoàn tất!")
                            if self.on_image_captured: self.on_image_captured(target_path)
                            self.is_paused = True
                        except Exception as e:
                            print(f"DEBUG: PTP Capture Error: {e}")
                            self.is_paused = False
                    
                    if not self.is_paused:
                        camera_file = gp.check_result(gp.gp_camera_capture_preview(camera, context))
                        file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
                        image_data = np.frombuffer(memoryview(file_data), dtype=np.uint8)
                        frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                        if frame is not None and frame.size > 0:
                            frame = ImageProcessor.crop_array_to_4_3(frame)
                            self._emit_frame(frame)
                    time.sleep(0.015)
                except Exception as e:
                    print(f"DEBUG: PTP Error: {e}")
                    self._emit_mock_frame()
                    time.sleep(2.0)
                    break
            gp.check_result(gp.gp_camera_exit(camera, context))
            return
            
        try:
            numeric_idx = int(self.camera_index)
        except ValueError:
            print(f"DEBUG: Invalid Camera ID: {self.camera_index}")
            self._emit_mock_frame()
            self.action = "idle"
            return
            
        start_time = time.time()
        cap = self.pool.get(self.camera_index)
        
        if cap is None or not isinstance(cap, cv2.VideoCapture) or not getattr(cap, 'isOpened', lambda: False)():
            try:
                cap = cv2.VideoCapture(numeric_idx, BACKEND_FLAG)
                if not getattr(cap, 'isOpened', lambda: False)():
                    print(f"DEBUG: OpenCV stream open failed for {numeric_idx}")
                    self._emit_mock_frame()
                    self.action = "idle"
                    return
                # Force MJPG for high res & high FPS compatibility
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                cap.set(cv2.CAP_PROP_FPS, 30)
                self.pool[self.camera_index] = cap
            except Exception as e:
                print(f"DEBUG: OpenCV Init Error: {e}")
                self._emit_mock_frame()
                self.action = "idle"
                return
            open_time = time.time() - start_time
            self._emit_status(f"✅ Đang hiển thị Live Preview từ Camera {self.camera_index} (Kết nối: {open_time:.2f}s)")
        
        try:
            props = {
                'zoom': cap.get(cv2.CAP_PROP_ZOOM),
                'focus': cap.get(cv2.CAP_PROP_FOCUS),
                'autofocus': cap.get(cv2.CAP_PROP_AUTOFOCUS)
            }
            if self.on_camera_properties: self.on_camera_properties(props)
        except Exception as e:
            pass
        
        safe_index = self.camera_index
        while self.action == "preview" and self.camera_index == safe_index and self.running:
            try:
                ret, frame = cap.read()
                if not ret or frame is None or getattr(frame, 'size', 0) == 0:
                    raise Exception("Failed to read frame")
                
                # 1. First crop to 4:3 (efficient)
                frame = ImageProcessor.crop_array_to_4_3(frame)

                # 2. Digital Zoom (if active)
                if self.digital_zoom > 1.0:
                    h, w = frame.shape[:2]
                    new_h, new_w = int(h / self.digital_zoom), int(w / self.digital_zoom)
                    y1, x1 = (h - new_h) // 2, (w - new_w) // 2
                    y2, x2 = y1 + new_h, x1 + new_w
                    frame = frame[y1:y2, x1:x2]
            except Exception as e:
                print(f"DEBUG: Camera Error (Idx {self.camera_index}): {e}")
                self._emit_mock_frame()
                time.sleep(2.0)
                break
                
            if self._capture_pending:
                self._capture_pending = False
                self._emit_status("Bắt đầu chụp ảnh chất lượng cao qua OpenCV...")
                
                from datetime import datetime
                filename = datetime.now().strftime("IMG_%Y%m%d_%H%M%S.jpg")
                session_dir = os.path.join(RAW_DIR, self.current_session)
                os.makedirs(session_dir, exist_ok=True)
                
                target_path = os.path.join(session_dir, filename)
                cv2.imwrite(target_path, frame)
                print(f"[OpenCV] Đã chụp và lưu ảnh thô RAW (chuẩn 4:3): {target_path}")
                self._emit_status("Tải ảnh hoàn tất!")
                if self.on_image_captured: self.on_image_captured(target_path)
                self.is_paused = True
                
            if not self.is_paused:
                self._emit_frame(frame)
                
            # Adaptive sleep: subtract processing time if needed, but 10ms is usually safe for ~30-60fps
            time.sleep(0.01)

    def zoom_in(self):
        self.digital_zoom = min(self.digital_zoom + 0.2, 3.0)
        self._emit_status(f"Digital Zoom: {self.digital_zoom:.1f}x")

    def zoom_out(self):
        self.digital_zoom = max(self.digital_zoom - 0.2, 1.0)
        self._emit_status(f"Digital Zoom: {self.digital_zoom:.1f}x")

    def trigger_autofocus(self):
        cap = self.pool.get(self.camera_index)
        if cap and isinstance(cap, cv2.VideoCapture) and getattr(cap, 'isOpened', lambda: False)():
            try:
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                time.sleep(0.1)
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except: pass
