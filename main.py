import sys
import os
import shutil
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox
from PyQt5.QtCore import QTimer
from ui_main import PhotoboothUI
from camera_controller import CameraWorker
from image_processor import ImageProcessor
from printer_service import PrinterService
from frame_layout_manager import FrameLayoutManager
from frame_config_dialog import FrameConfigDialog
from gallery_dialog import GalleryDialog
import config

class PhotoboothApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.ui = PhotoboothUI()
        
        self.current_image = None
        self.processed_image = None
        self.countdown_val = 0
        self.camera_list = []
        self.active_camera_index = 0
        
        self.layout_manager = FrameLayoutManager()
        self.refresh_layout_options()
        
        self.current_session = "Khach_Mac_Dinh"
        self.load_sessions()
        
        # CHỈ TẠO 1 LUỒNG CAMERA DUY NHẤT để tránh đụng độ Thread của OpenCV MSMF
        self.camera_worker = CameraWorker()
        self.camera_worker.status_signal.connect(self.ui.log)
        self.camera_worker.error_signal.connect(self.log_error)
        self.camera_worker.camera_list_signal.connect(self.on_camera_list_received)
        self.camera_worker.frame_signal.connect(self.ui.preview_label.set_opencv_image)
        self.camera_worker.image_captured_signal.connect(self.on_image_captured)
        self.camera_worker.camera_properties_signal.connect(self.on_camera_properties_received)
        self.camera_worker.start()

        self.setup_connections()
        self.ui.log("🚀 Hệ thống Photobooth khởi động thành công.")
        self.ui.log(f"Trạng thái thư mục Captures: OK {config.CAPTURES_DIR}")
        
        # Bắt đầu quét các camera ngay khi mở app
        self.scan_cameras()
        
    def setup_connections(self):
        # Photobooth Tab
        self.ui.camera_selector.currentIndexChanged.connect(self.on_camera_selected)
        self.ui.btn_connect.clicked.connect(self.scan_cameras)
        self.ui.btn_capture.clicked.connect(self.capture_image)
        self.ui.btn_gallery.clicked.connect(self.open_gallery)
        
        # Session Management Actions (Dropdown)
        self.ui.session_action_selector.activated.connect(self.handle_session_action)
        self.ui.session_selector.currentIndexChanged.connect(self.on_session_changed)
        
        # Camera Hardware Controls
        self.ui.preview_label.zoom_in_signal.connect(self.on_zoom_in_triggered)
        self.ui.preview_label.zoom_out_signal.connect(self.on_zoom_out_triggered)
        self.ui.preview_label.clicked_pos.connect(self.on_tap_focus_triggered)
        
        # Admin Tab
        self.ui.btn_add_layout.clicked.connect(self.open_layout_dialog)
        self.ui.btn_edit_layout.clicked.connect(self.open_edit_layout_dialog)
        
    def scan_cameras(self):
        self.ui.log("Đang kiểm tra các máy ảnh được kết nối...")
        self.ui.btn_connect.setEnabled(False)
        self.ui.camera_selector.setEnabled(False)
        self.camera_worker.request_scan()

    def on_camera_list_received(self, cameras):
        self.camera_list = cameras
        self.ui.camera_selector.blockSignals(True)
        self.ui.camera_selector.clear()
        
        if not cameras:
            self.ui.camera_selector.addItem("Không tìm thấy máy ảnh!")
            self.ui.btn_connect.setEnabled(True)
            self.ui.camera_selector.setEnabled(True)
        else:
            for idx, name in cameras:
                self.ui.camera_selector.addItem(name, userData=idx)
            # Chọn camera đầu tiên
            self.ui.camera_selector.setCurrentIndex(0)
            self.ui.camera_selector.blockSignals(False)
            
            # Mở khóa input và tự động chạy preview cho camera đầu
            self.ui.btn_connect.setEnabled(True)
            self.ui.camera_selector.setEnabled(True)
            self.start_live_preview(cameras[0][0])

    def on_camera_selected(self, index):
        if index >= 0 and self.camera_list:
            cam_idx = self.ui.camera_selector.itemData(index)
            self.start_live_preview(cam_idx)

    def on_zoom_in_triggered(self):
        if hasattr(self, 'camera_worker'):
            self.camera_worker.zoom_in()
            self.ui.log("Zoom In...")

    def on_zoom_out_triggered(self):
        if hasattr(self, 'camera_worker'):
            self.camera_worker.zoom_out()
            self.ui.log("Zoom Out...")

    def on_tap_focus_triggered(self, x, y):
        # x, y là tọa độ click trên Label
        if hasattr(self, 'camera_worker'):
            self.camera_worker.trigger_autofocus()
            self.ui.log(f"Đang lấy nét tại vị trí chạm...")

    def on_camera_properties_received(self, props):
        # Không còn dùng thanh trượt nên không cần update UI sliders ở đây nữa
        pass

    def start_live_preview(self, camera_index):
        self.active_camera_index = camera_index
        # Ra lệnh cho Thread chuyển sang Camera mới
        self.camera_worker.change_camera(camera_index)
        
    def capture_image(self):
        # Kiểm tra lựa chọn countdown
        selection = self.ui.countdown_selector.currentText()
        
        if "Chụp ngay" in selection:
            self._do_actual_capture()
        else:
            # Trích xuất số giây từ chuỗi "⏳ Xs"
            import re
            match = re.search(r'(\d+)s', selection)
            if match:
                seconds = int(match.group(1))
                self.start_countdown(seconds)
            else:
                self._do_actual_capture()

    def _do_actual_capture(self):
        self.ui.btn_capture.setEnabled(False)
        self.ui.countdown_selector.setEnabled(False)
        self.ui.log("Đang lấy ảnh từ luồng trực tiếp...")
        if hasattr(self, 'camera_worker'):
            self.camera_worker.request_capture()

    def on_image_captured(self, path):
        self.current_image = path
        
        # Tự động làm nét ảnh (Normal) ngay sau khi chụp xong để đảm bảo độ trong trẻo
        self.ui.log("Đang tối ưu độ nét ảnh (Sharpening)...")
        ImageProcessor.sharpen_image(path, level="normal")
        
        self.ui.preview_label.set_image(path)
        self.ui.log("Đã chụp máy xong! Đang gọi thư viện xem trước...")
        self.ui.btn_capture.setEnabled(True)
        self.ui.countdown_selector.setEnabled(True)
        
        # Tự động mở Gallery ngay sau khi có ảnh
        self.open_gallery(pre_select_path=path)

    def start_countdown(self, duration=3):
        self.countdown_val = duration
        self.ui.countdown_label.setText(str(self.countdown_val))
        self.ui.countdown_label.show()
        
        self.ui.btn_capture.setEnabled(False)
        self.ui.countdown_selector.setEnabled(False)
        
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
        self.ui.log(f"Bắt đầu đếm ngược {duration}s...")

    def update_countdown(self):
        self.countdown_val -= 1
        if self.countdown_val > 0:
            self.ui.countdown_label.setText(str(self.countdown_val))
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()
            self.ui.countdown_label.hide()
            self._do_actual_capture()

    def refresh_layout_options(self):
        # Tải lại file JSON phòng trường hợp dialog vừa ghi đè dữ liệu mới
        self.layout_manager.load_layouts()
        
        self.ui.admin_layout_selector.blockSignals(True)
        self.ui.admin_layout_selector.clear()
        
        layouts = self.layout_manager.get_all_layouts()
        if not layouts:
            self.ui.admin_layout_selector.addItem("Chưa có layout nào")
            self.ui.admin_layout_selector.setEnabled(False)
            self.ui.btn_edit_layout.setEnabled(False)
        else:
            for layout in layouts:
                self.ui.admin_layout_selector.addItem(layout["name"], userData=layout)
            self.ui.admin_layout_selector.setEnabled(True)
            self.ui.btn_edit_layout.setEnabled(True)
            
        self.ui.admin_layout_selector.blockSignals(False)

    def open_gallery(self, pre_select_path=None):
        self.ui.log(f"Mở thư viện ảnh chụp RAW của khách: {self.current_session}...")
        dialog = GalleryDialog(self.ui, layout_manager=self.layout_manager, pre_select_path=pre_select_path, session_name=self.current_session)
        dialog.exec_()
        
        # Sau khi tắt library, reset trạng thái camera ready
        self.retake()

    def open_layout_dialog(self):
        dialog = FrameConfigDialog(self.ui)
        if dialog.exec_():
            self.refresh_layout_options()
            self.ui.log("Đã tạo thêm Layout Khung Ảnh.")

    def open_edit_layout_dialog(self):
        if self.ui.admin_layout_selector.count() == 0 or not self.ui.admin_layout_selector.itemData(self.ui.admin_layout_selector.currentIndex()):
            self.ui.log("Lỗi hệ thống: Không có Layout hợp lệ để chỉnh sửa.")
            return
            
        selected_layout_data = self.ui.admin_layout_selector.currentData()
        self.ui.log(f"Đang mở giao diện sửa Layout: '{selected_layout_data['name']}'...")
        
        dialog = FrameConfigDialog(self.ui, layout_data=selected_layout_data)
        if dialog.exec_():
            self.refresh_layout_options()
            self.ui.log(f"Đã cập nhật đè Layout '{selected_layout_data['name']}'.")

    def retake(self):
        self.current_image = None
        self.ui.preview_label.clear_image()
        self.camera_worker.resume_preview()
        self.ui.log("Đã tiếp tục Live Preview.")

    def log_error(self, err_msg):
        self.ui.log(f"🛑 [ERROR] {err_msg}")

    # --- SESSION MANAGEMENT ---
    def load_sessions(self, select_name=None):
        self.ui.session_selector.blockSignals(True)
        self.ui.session_selector.clear()
        
        if not os.path.exists(config.RAW_DIR):
            os.makedirs(config.RAW_DIR, exist_ok=True)
            
        # Get all subdirectories in RAW_DIR
        sessions = [d for d in os.listdir(config.RAW_DIR) if os.path.isdir(os.path.join(config.RAW_DIR, d))]
        if not sessions:
            sessions = ["Khach_Mac_Dinh"]
            os.makedirs(os.path.join(config.RAW_DIR, "Khach_Mac_Dinh"), exist_ok=True)
            
        sessions.sort()
        self.ui.session_selector.addItems(sessions)
        
        if select_name and select_name in sessions:
            idx = self.ui.session_selector.findText(select_name)
            self.ui.session_selector.setCurrentIndex(idx)
            self.current_session = select_name
        else:
            self.ui.session_selector.setCurrentIndex(0)
            self.current_session = self.ui.session_selector.currentText()
            
        self.ui.session_selector.blockSignals(False)
        if hasattr(self, 'camera_worker'):
            self.camera_worker.set_session(self.current_session)
            
    def on_session_changed(self, index):
        if index >= 0:
            self.current_session = self.ui.session_selector.currentText()
            self.camera_worker.set_session(self.current_session)
            self.ui.log(f"Đã chuyển phiên chụp sang khách: {self.current_session}")

    def handle_session_action(self, index):
        if index == 0: return # "--- Thao tác ---"
        
        if index == 1: # 📋 Copy Đường Dẫn
            self.handle_copy_path()
        elif index == 2: # ➕ Khách Mới
            self.handle_new_session()
        elif index == 3: # ✏️ Đổi Tên
            self.handle_rename_session()
        elif index == 4: # 🗑 Xóa
            self.handle_delete_session()
            
        # Reset dropdown to first item
        self.ui.session_action_selector.setCurrentIndex(0)

    def handle_new_session(self):
        text, ok = QInputDialog.getText(self.ui, "Khách Mới", "Nhập tên khách hàng (Viết liền ko dấu_Là Tốt Nhất):")
        if ok and text:
            # Clean safe path string
            safe_name = "".join([c if c.isalnum() else "_" for c in text]).strip("_")
            if not safe_name: return
            
            new_path = os.path.join(config.RAW_DIR, safe_name)
            if not os.path.exists(new_path):
                os.makedirs(new_path, exist_ok=True)
                self.ui.log(f"Đã tạo phiên chụp mới: {safe_name}")
            else:
                self.ui.log(f"Khách hàng {safe_name} đã tồn tại.")
                
            self.load_sessions(select_name=safe_name)

    def handle_copy_path(self):
        # Tính toán đường dẫn tuyệt đối của thư mục lưu ảnh session hiện tại
        session_path = os.path.abspath(os.path.join(config.RAW_DIR, self.current_session))
        # Copy vào clipboard
        QApplication.clipboard().setText(session_path)
        self.ui.log(f"Đã sao chép đường dẫn: {session_path}")
        QMessageBox.information(self.ui, "Copy Path", f"Đã copy đường dẫn vào clipboard:\n\n{session_path}")

    def handle_rename_session(self):
        if self.current_session == "Khach_Mac_Dinh":
            QMessageBox.warning(self.ui, "Cảnh báo", "Không thể đổi tên phiên mặc định!")
            return
            
        text, ok = QInputDialog.getText(self.ui, "Đổi Tên", "Nhập tên mới cho khách hàng:", text=self.current_session)
        if ok and text:
            safe_name = "".join([c if c.isalnum() else "_" for c in text]).strip("_")
            if not safe_name or safe_name == self.current_session: return
            
            old_path = os.path.join(config.RAW_DIR, self.current_session)
            new_path = os.path.join(config.RAW_DIR, safe_name)
            
            if os.path.exists(new_path):
                QMessageBox.warning(self.ui, "Lỗi", f"Tên khách '{safe_name}' đã tồn tại!")
                return
                
            try:
                os.rename(old_path, new_path)
                self.ui.log(f"Đã đổi tên khách {self.current_session} thành {safe_name}")
                self.load_sessions(select_name=safe_name)
            except Exception as e:
                self.log_error(f"Lỗi khi đổi tên thư mục: {e}")

    def handle_delete_session(self):
        if self.current_session == "Khach_Mac_Dinh":
            QMessageBox.warning(self.ui, "Cảnh báo", "Không thể xóa phiên mặc định!")
            return
            
        reply = QMessageBox.question(self.ui, "Xác nhận xóa", 
                                     f"Bạn có chắc muốn xóa TẤT CẢ ảnh của khách: {self.current_session}?\nKhông thể hoàn tác!",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            target_path = os.path.join(config.RAW_DIR, self.current_session)
            try:
                shutil.rmtree(target_path)
                self.ui.log(f"Đã XÓA xong toàn bộ thư mục khách: {self.current_session}")
                self.load_sessions() # Will fallback to first available or recreate Mac Dinh
            except Exception as e:
                self.log_error(f"Lỗi khi xóa xóa thư mục: {e}")

    def run(self):
        self.ui.show()
        self.app.aboutToQuit.connect(self.cleanup_before_exit)
        sys.exit(self.app.exec_())

    def cleanup_before_exit(self):
        self.ui.log("Đang đóng các luồng camera, vui lòng đợi...")
        self.camera_worker.stop()
        # Chờ tối đa 2 giây cho thread tự đóng, nếu không thì ép dừng để thoát app
        if not self.camera_worker.wait(2000):
            self.ui.log("Camera thread không phản hồi, đang ép dừng...")
            self.camera_worker.terminate()
            self.camera_worker.wait()

if __name__ == "__main__":
    app = PhotoboothApp()
    app.run()
