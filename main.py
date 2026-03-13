import sys
import os
import shutil
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox, QFileDialog, QListWidgetItem
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QIcon
from ui_main import PhotoboothUI
from camera_controller import CameraWorker
from image_processor import ImageProcessor
from printer_service import PrinterService
from frame_layout_manager import FrameLayoutManager
from frame_config_dialog import FrameConfigDialog
import config

class PhotoboothApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.ui = PhotoboothUI()
        
        self.current_image = None # Path RAW gốc đang chọn
        self.processed_image = None # Path ảnh đã qua xử lý (LUT/Frame)
        self.state_pre_frame = None # Trạng thái ảnh trước khi chèn khung (LUT/Sharpen)
        self.countdown_val = 0
        self.camera_list = []
        
        self.layout_manager = FrameLayoutManager()
        
        self.current_session = "Khach_Mac_Dinh"
        self.load_sessions()
        
        # CHỈ TẠO 1 LUỒNG CAMERA DUY NHẤT
        self.camera_worker = CameraWorker()
        self.camera_worker.status_signal.connect(self.log_status)
        self.camera_worker.error_signal.connect(self.log_error)
        self.camera_worker.camera_list_signal.connect(self.on_camera_list_received)
        self.camera_worker.frame_signal.connect(self.ui.preview_label.set_opencv_image)
        self.camera_worker.image_captured_signal.connect(self.on_image_captured)
        self.camera_worker.start()

        # Timer tự động refresh gallery (1 giây)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_thumbnails)

        # Timer tự động theo dõi và copy ảnh từ raw_captures vào session hiện tại (1 giây)
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_raw_dir)
        self.monitor_timer.start(1000)
        
        self.setup_connections()
        self.refresh_gallery_data() # Load LUTs, Frames, Thumbnails
        
        # Bắt đầu quét các camera ngay khi mở app
        self.scan_cameras()
        
    def setup_connections(self):
        # --- STATION SCREEN ---
        self.ui.btn_capture.clicked.connect(self.capture_image)
        self.ui.btn_to_gallery.clicked.connect(self.show_gallery)
        self.ui.btn_admin_setup.clicked.connect(self.open_admin_setup)
        self.ui.session_selector.currentIndexChanged.connect(self.on_session_changed)
        self.ui.camera_selector.currentIndexChanged.connect(self.on_camera_selected)
        self.ui.btn_connect.clicked.connect(self.scan_cameras)
        
        # Session Management
        self.ui.btn_session_add.clicked.connect(self.handle_new_session)
        self.ui.btn_session_rename.clicked.connect(self.handle_rename_session)
        self.ui.btn_session_delete.clicked.connect(self.handle_delete_session)
        self.ui.btn_copy_session_path.clicked.connect(self.handle_copy_path)
        
        # Hardware controls
        self.ui.preview_label.zoom_in_signal.connect(self.on_zoom_in)
        self.ui.preview_label.zoom_out_signal.connect(self.on_zoom_out)
        self.ui.preview_label.clicked_pos.connect(self.on_tap_focus)
        
        # --- GALLERY SCREEN ---
        self.ui.btn_back_to_station.clicked.connect(self.show_station)
        self.ui.thumbnail_list.itemSelectionChanged.connect(self.on_thumbnail_selected)
        self.ui.frame_list.itemClicked.connect(self.on_frame_item_selected)
        self.ui.btn_apply_lut.clicked.connect(self.apply_lut_action)
        self.ui.btn_apply_sharpen.clicked.connect(self.apply_sharpen_action)
        self.ui.btn_print.clicked.connect(self.print_action)
        self.ui.btn_save.clicked.connect(self.save_action)
        self.ui.btn_delete_selected.clicked.connect(self.delete_selected_action)
        self.ui.btn_delete_all.clicked.connect(self.delete_all_action)
        self.ui.btn_import_raw.clicked.connect(self.import_raw_action)
        self.ui.btn_refresh_gallery.clicked.connect(self.refresh_thumbnails)
        self.ui.btn_delete_lut.clicked.connect(self.delete_lut_action)
        self.ui.btn_add_lut.clicked.connect(self.import_lut_action)

    # --- NAVIGATION ---
    def show_station(self):
        self.refresh_timer.stop() # Dừng refresh khi ở trạm chụp
        self.ui.central_widget.setCurrentIndex(0)
        self.camera_worker.resume_preview()
        self.ui.status_dot.setText("🟢 System Ready")

    def show_gallery(self, pre_select_path=None):
        self.ui.central_widget.setCurrentIndex(1)
        self.ui.current_session_label.setText(f"Phiên: {self.current_session}")
        self.refresh_thumbnails(pre_select_path)
        self.refresh_timer.start(1000) # Chạy timer refresh (1s)
        self.ui.status_dot.setText("📝 Editing Mode")

    def open_admin_setup(self):
        # Mở dialog config layout (Admin side)
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self.ui)
        act_add = QAction("➕ Thêm Layout Mới", self.ui)
        act_add.triggered.connect(self.handle_add_layout)
        act_edit = QAction("✏️ Sửa Layout Hiện Tại", self.ui)
        act_edit.triggered.connect(self.handle_edit_layout)
        menu.addAction(act_add)
        menu.addAction(act_edit)
        menu.exec_(self.ui.btn_admin_setup.mapToGlobal(self.ui.btn_admin_setup.rect().bottomLeft()))

    def handle_add_layout(self):
        dialog = FrameConfigDialog(self.ui)
        if dialog.exec_():
            self.refresh_gallery_data()
            self.ui.log("Đã tạo thêm Layout Khung Ảnh.")

    def handle_edit_layout(self):
        # Lấy layout đang chọn ở Gallery screen (nếu có combobox) hoặc hỏi input
        layouts = self.layout_manager.get_all_layouts()
        if not layouts: return
        
        from PyQt5.QtWidgets import QInputDialog
        names = [l["name"] for l in layouts]
        name, ok = QInputDialog.getItem(self.ui, "Sửa Layout", "Chọn layout cần sửa:", names, 0, False)
        if ok and name:
            layout_data = next((l for l in layouts if l["name"] == name), None)
            if layout_data:
                dialog = FrameConfigDialog(self.ui, layout_data=layout_data)
                if dialog.exec_():
                    self.refresh_gallery_data()

    # --- STATION LOGIC ---
    def scan_cameras(self):
        self.camera_worker.request_scan()

    def on_camera_list_received(self, cameras):
        self.camera_list = cameras
        self.ui.camera_selector.blockSignals(True)
        self.ui.camera_selector.clear()
        if not cameras:
            self.ui.camera_selector.addItem("Không tìm thấy máy ảnh!")
        else:
            for idx, name in cameras:
                self.ui.camera_selector.addItem(name, userData=idx)
            self.ui.camera_selector.setCurrentIndex(0)
            self.start_preview(cameras[0][0])
        self.ui.camera_selector.blockSignals(False)

    def on_camera_selected(self, index):
        if index >= 0 and self.camera_list:
            cam_idx = self.ui.camera_selector.itemData(index)
            self.start_preview(cam_idx)

    def start_preview(self, idx):
        self.camera_worker.change_camera(idx)

    def on_zoom_in(self): self.camera_worker.zoom_in()
    def on_zoom_out(self): self.camera_worker.zoom_out()
    def on_tap_focus(self, x, y): self.camera_worker.trigger_autofocus()

    def capture_image(self):
        selection = self.ui.countdown_selector.currentText()
        if "Chụp ngay" in selection:
            self.camera_worker.request_capture()
        else:
            import re
            match = re.search(r'(\d+)s', selection)
            if match:
                self.start_countdown(int(match.group(1)))
            else:
                self.camera_worker.request_capture()

    def start_countdown(self, seconds):
        self.countdown_val = seconds
        self.ui.countdown_label.setText(str(self.countdown_val))
        self.ui.countdown_label.show()
        self.ui.btn_capture.setEnabled(False)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)

    def update_countdown(self):
        self.countdown_val -= 1
        if self.countdown_val > 0:
            self.ui.countdown_label.setText(str(self.countdown_val))
        else:
            self.timer.stop()
            self.ui.countdown_label.hide()
            self.ui.btn_capture.setEnabled(True)
            self.camera_worker.request_capture()

    def on_image_captured(self, path):
        self.ui.log(f"Đã chụp ảnh: {path}")
        # Chuyển sang màn hình Gallery và pre-select ảnh vừa chụp
        self.show_gallery(pre_select_path=path)

    # --- GALLERY LOGIC ---
    def refresh_gallery_data(self):
        # Load LUTs
        self.ui.lut_selector.clear()
        self.ui.lut_selector.addItem("Gốc (Không màu)")
        if os.path.exists(config.LUTS_DIR):
            luts = [f for f in os.listdir(config.LUTS_DIR) if f.lower().endswith(('.cube', '.xmp'))]
            self.ui.lut_selector.addItems(luts)
        
        # Load Frames (New: Visual List)
        self.ui.frame_list.clear()
        self.layout_manager.load_layouts()
        layouts = self.layout_manager.get_all_layouts()
        
        # Add a "No Frame" option
        none_item = QListWidgetItem("❌ Không khung")
        none_item.setData(Qt.UserRole, None)
        none_item.setTextAlignment(Qt.AlignCenter)
        self.ui.frame_list.addItem(none_item)

        for l in layouts:
            frame_path = l.get("frame_file")
            if frame_path and os.path.exists(frame_path):
                icon = QIcon(frame_path)
                item = QListWidgetItem(icon, l["name"])
                item.setData(Qt.UserRole, l)
                item.setToolTip(l["name"])
                self.ui.frame_list.addItem(item)
            
        # Thumbnails handled in show_gallery/refresh_thumbnails

    def refresh_thumbnails(self, pre_select_path=None):
        session_dir = os.path.join(config.RAW_DIR, self.current_session)
        if not os.path.exists(session_dir): os.makedirs(session_dir)
        
        files = [f for f in os.listdir(session_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        # Sort newest-to-oldest
        files.sort(key=lambda x: os.path.getmtime(os.path.join(session_dir, x)), reverse=True)
        
        # Kiểm tra nếu list file không đổi
        current_files = [self.ui.thumbnail_list.item(i).text() for i in range(self.ui.thumbnail_list.count())]
        if files == current_files and not pre_select_path:
            return 

        # 1. Lưu trạng thái trước khi xóa
        old_top_path = None
        if self.ui.thumbnail_list.count() > 0:
            old_top_path = self.ui.thumbnail_list.item(0).data(Qt.UserRole)
            
        current_path = None
        selected = self.ui.thumbnail_list.selectedItems()
        if selected:
            current_path = selected[0].data(Qt.UserRole)

        # 2. Rebuild list
        self.ui.thumbnail_list.blockSignals(True)
        self.ui.thumbnail_list.clear()
        
        def norm(p):
            return os.path.abspath(p).lower().replace('/', '\\')

        target_item = None
        for f in files:
            full_path = os.path.join(session_dir, f)
            icon = QIcon(full_path)
            item = QListWidgetItem(icon, f)
            item.setData(Qt.UserRole, full_path)
            self.ui.thumbnail_list.addItem(item)
            
            # Ưu tiên dán selection:
            # - A: Nếu là ảnh vừa chụp xong (pre_select_path)
            # - B: Nếu user đang ở ảnh top cũ, nhảy lên top mới (vị trí 0)
            # - C: Nếu user đang chọn ảnh khác (không phải top), tìm và chọn lại ảnh đó
            
            if pre_select_path and norm(full_path) == norm(pre_select_path):
                target_item = item
            elif not pre_select_path:
                if current_path and norm(full_path) == norm(current_path):
                    if old_top_path and norm(current_path) != norm(old_top_path):
                        target_item = item

        # 3. Áp dụng selection cuối cùng
        # Nếu có target_item hoặc cần nhảy lên top, ta unblock signals để UI cập nhật Preview
        # Sửa lỗi: Nếu old_top_path là None (Lần đầu mở), cũng cần unblock để hiện ảnh đầu tiên
        should_trigger_preview = (target_item is not None) or (not pre_select_path and (old_top_path is not None or self.ui.thumbnail_list.count() > 0))
        
        if should_trigger_preview:
            self.ui.thumbnail_list.blockSignals(False)

        if target_item:
            self.ui.thumbnail_list.setCurrentItem(target_item)
        elif self.ui.thumbnail_list.count() > 0:
            self.ui.thumbnail_list.setCurrentRow(0)
            
        self.ui.thumbnail_list.blockSignals(False)

    def on_thumbnail_selected(self):
        selected = self.ui.thumbnail_list.selectedItems()
        if selected:
            self.ui.btn_delete_selected.setEnabled(True)
            path = selected[0].data(Qt.UserRole)
            self.current_image = path
            self.processed_image = None
            self.state_pre_frame = path # Reset trạng thái pre-frame
            self.ui.gallery_preview_label.set_image(path)
            # Reset selectors
            self.ui.lut_selector.setCurrentIndex(0)
            self.ui.sharpen_selector.setCurrentIndex(0)
        else:
            self.ui.btn_delete_selected.setEnabled(False)

    def apply_lut_action(self):
        if not self.current_image: return
        lut_name = self.ui.lut_selector.currentText()
        if lut_name == "Gốc (Không màu)":
            self.processed_image = None
            self.state_pre_frame = self.current_image
            self.ui.gallery_preview_label.set_image(self.current_image)
            return
        
        lut_path = os.path.join(config.LUTS_DIR, lut_name)
        # Handle XMP convert
        if lut_path.lower().endswith('.xmp'):
            cube_path = os.path.splitext(lut_path)[0] + ".cube"
            if not os.path.exists(cube_path):
                if not ImageProcessor.convert_xmp_to_cube(lut_path, cube_path):
                    QMessageBox.warning(self.ui, "Lỗi XMP", "File XMP không chứa bảng màu tương thích.")
                    return
            lut_path = cube_path
        
        try:
            self.ui.status_dot.setText("✨ Processing LUT...")
            res = ImageProcessor.apply_lut(self.current_image, lut_path)
            self.processed_image = res
            self.state_pre_frame = res # Lưu trạng thái sau khi LUT
            self.ui.gallery_preview_label.set_image(res)
            self.ui.status_dot.setText("🟢 LUT Applied")
        except Exception as e:
            QMessageBox.critical(self.ui, "Lỗi", f"Không thể áp màu: {e}")

    def apply_sharpen_action(self):
        if not self.current_image: return
        level_txt = self.ui.sharpen_selector.currentText()
        if "Tắt" in level_txt:
            ImageProcessor.restore_original(self.current_image)
        else:
            level = "low" if "Thấp" in level_txt else "normal" if "Vừa" in level_txt else "high"
            ImageProcessor.sharpen_image(self.current_image, level=level)
        
        # Luôn để pre_frame là current_image (hoặc kết quả LUT nếu có)
        # Ở đây đơn giản nhất là reset lại trạng thái pre-frame để user áp lại LUT nếu muốn
        self.state_pre_frame = self.current_image 
        self.processed_image = None 
        self.ui.gallery_preview_label.set_image(self.current_image)
        # Update thumbnail
        selected = self.ui.thumbnail_list.selectedItems()
        if selected: selected[0].setIcon(QIcon(self.current_image))

    def on_frame_item_selected(self, item):
        layout_data = item.data(Qt.UserRole)
        # Nếu là layout_data là None thì xóa khung (về state_pre_frame)
        if layout_data is None:
            self.processed_image = None
            # Nếu có kết quả LUT thì show LUT, ko thì show RAW
            self.ui.gallery_preview_label.set_image(self.state_pre_frame or self.current_image)
            return

        self.apply_frame_action(layout_data)

    def apply_frame_action(self, layout_data=None):
        # QUAN TRỌNG: Luôn lấy từ state_pre_frame thay vì processed_image 
        # để tránh việc chèn chồng khung lên nhau
        img = self.state_pre_frame or self.current_image
        if not img: return
        
        # Nếu layout_data không truyền vào (legacy call), cố lấy từ đâu đó? 
        # Thực tế bây giờ chỉ gọi qua on_frame_item_selected
        if not layout_data: return
        
        try:
            res = ImageProcessor.apply_frame(img, layout_data)
            self.processed_image = res
            self.ui.gallery_preview_label.set_image(res)
        except Exception as e:
            QMessageBox.critical(self.ui, "Lỗi", f"Lỗi ghép khung: {e}")

    def print_action(self):
        img = self.processed_image or self.current_image
        if not img: return
        PrinterService.print_image(img)
        QMessageBox.information(self.ui, "Máy in", "Ảnh đã được gửi đến máy in.")

    def save_action(self):
        img = self.processed_image or self.current_image
        if not img: return
        target, _ = QFileDialog.getSaveFileName(self.ui, "Lưu ảnh", f"PRO_{os.path.basename(img)}", "Images (*.png *.jpg *.jpeg)")
        if target:
            shutil.copy2(img, target)
            QMessageBox.information(self.ui, "Lưu", f"Đã lưu tại: {target}")

    def delete_selected_action(self):
        selected = self.ui.thumbnail_list.selectedItems()
        if not selected: return
        if QMessageBox.question(self.ui, "Xóa", f"Xóa {len(selected)} ảnh đã chọn?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            try:
                for item in selected:
                    p = item.data(Qt.UserRole)
                    if os.path.exists(p): os.remove(p)
                self.ui.log(f"🗑️ Đã xóa {len(selected)} ảnh.")
                self.ui.btn_delete_selected.setEnabled(False)
                self.refresh_thumbnails()
            except Exception as e:
                self.ui.log(f"🛑 Lỗi khi xóa: {str(e)}")

    def delete_all_action(self):
        session_dir = os.path.join(config.RAW_DIR, self.current_session)
        if not os.path.exists(session_dir): return
        
        files = [f for f in os.listdir(session_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not files:
            QMessageBox.information(self.ui, "Thông báo", "Thư mục hiện tại không có ảnh để xóa.")
            return

        reply = QMessageBox.question(self.ui, "Xác nhận xóa hết", 
                                     f"Bạn có chắc muốn xóa TẤT CẢ {len(files)} ảnh trong phiên này không?\n(Hành động này không thể hoàn tác)",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                for f in files:
                    os.remove(os.path.join(session_dir, f))
                self.ui.log(f"🧨 Đã xóa toàn bộ {len(files)} ảnh trong phiên {self.current_session}")
                self.ui.gallery_preview_label.clear()
                self.ui.btn_delete_selected.setEnabled(False)
                self.refresh_thumbnails()
            except Exception as e:
                self.ui.log(f"🛑 Lỗi khi xóa hết: {str(e)}")

    def import_raw_action(self):
        files, _ = QFileDialog.getOpenFileNames(self.ui, "Nhập ảnh RAW", "", "Images (*.png *.jpg *.jpeg)")
        if files:
            session_dir = os.path.join(config.RAW_DIR, self.current_session)
            for f in files:
                shutil.copy2(f, os.path.join(session_dir, f"import_{os.path.basename(f)}"))
            self.refresh_thumbnails()

    def delete_lut_action(self):
        lut = self.ui.lut_selector.currentText()
        if lut == "Gốc (Không màu)": return
        if QMessageBox.question(self.ui, "Xóa LUT", f"Xóa file màu {lut}?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            os.remove(os.path.join(config.LUTS_DIR, lut))
            self.refresh_gallery_data()
            
    def import_lut_action(self):
        files, _ = QFileDialog.getOpenFileNames(self.ui, "Nhập mẫu màu (Preset)", "", "Presets (*.cube *.xmp)")
        if files:
            if not os.path.exists(config.LUTS_DIR): os.makedirs(config.LUTS_DIR)
            for f in files:
                shutil.copy2(f, os.path.join(config.LUTS_DIR, os.path.basename(f)))
            self.refresh_gallery_data()
            self.ui.log(f"Đã nhập {len(files)} mẫu màu mới.")

    def monitor_raw_dir(self):
        """Theo dõi folder raw_captures, nếu có file ảnh lẻ thì copy vào session hiện tại."""
        try:
            # Chỉ lấy các file trong root RAW_DIR, không lấy trong folder con
            files = [f for f in os.listdir(config.RAW_DIR) 
                    if os.path.isfile(os.path.join(config.RAW_DIR, f)) 
                    and f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if not files:
                return

            session_dir = os.path.join(config.RAW_DIR, self.current_session)
            if not os.path.exists(session_dir):
                os.makedirs(session_dir, exist_ok=True)

            for f in files:
                old_path = os.path.join(config.RAW_DIR, f)
                new_name = f
                # Tránh trùng tên nếu file đã tồn tại trong session
                count = 1
                while os.path.exists(os.path.join(session_dir, new_name)):
                    name, ext = os.path.splitext(f)
                    new_name = f"{name}_{count}{ext}"
                    count += 1
                
                new_path = os.path.join(session_dir, new_name)
                
                try:
                    # Di chuyển file thay vì copy để tránh lặp lại
                    shutil.move(old_path, new_path)
                    self.ui.log(f"📸 Tự động nhận ảnh: {new_name} -> {self.current_session}")
                except Exception as e:
                    self.ui.log(f"🛑 Lỗi di chuyển ảnh {f}: {e}")
                    
            # Nếu đang ở gallery thì refresh tự động
            if self.ui.central_widget.currentIndex() == 1:
                self.refresh_thumbnails()
                
        except Exception as e:
            # Im lặng lỗi định kỳ để ko làm phiền user nếu chỉ là lỗi truy cập file nhất thời
            pass

    # --- SESSION MANAGEMENT ---
    def load_sessions(self, select_name=None):
        self.ui.session_selector.blockSignals(True)
        self.ui.session_selector.clear()
        if not os.path.exists(config.RAW_DIR): os.makedirs(config.RAW_DIR)
        dirs = [d for d in os.listdir(config.RAW_DIR) if os.path.isdir(os.path.join(config.RAW_DIR, d))]
        if not dirs:
            dirs = ["Khach_Mac_Dinh"]
            os.makedirs(os.path.join(config.RAW_DIR, "Khach_Mac_Dinh"), exist_ok=True)
        dirs.sort()
        self.ui.session_selector.addItems(dirs)
        if select_name and select_name in dirs:
            self.ui.session_selector.setCurrentText(select_name)
            self.current_session = select_name
        else:
            self.current_session = self.ui.session_selector.currentText()
        self.ui.session_selector.blockSignals(False)

    def on_session_changed(self, index):
        self.current_session = self.ui.session_selector.currentText()
        if hasattr(self, 'camera_worker'):
            self.camera_worker.set_session(self.current_session)
        self.ui.log(f"Chuyển session: {self.current_session}")

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
        session_path = os.path.abspath(os.path.join(config.RAW_DIR, self.current_session))
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
                self.load_sessions()
            except Exception as e:
                self.log_error(f"Lỗi khi xóa xóa thư mục: {e}")

    def log_status(self, msg): self.ui.log(msg)
    def log_error(self, msg): self.ui.log(f"🛑 [LỖI] {msg}")

    def run(self):
        self.ui.show()
        self.app.aboutToQuit.connect(self.cleanup)
        sys.exit(self.app.exec_())

    def cleanup(self):
        self.camera_worker.stop()
        self.camera_worker.wait(2000)

if __name__ == "__main__":
    app = PhotoboothApp()
    app.run()
