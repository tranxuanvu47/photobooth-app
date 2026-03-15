import sys
import os
import shutil
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox, QFileDialog, QListWidgetItem, QDialog, QMenu, QAction
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap, QImage
from ui_main import PhotoboothUI
from camera_controller import CameraWorker
from image_processor import ImageProcessor
from printer_service import PrinterService
from frame_layout_manager import FrameLayoutManager
from frame_config_dialog import FrameConfigDialog
from styles import *
import config
import pyautogui
import pygetwindow as gw
import time
import threading
from nextcloud_utils import upload_to_nextcloud
import qrcode
from io import BytesIO

class PhotoboothApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.ui = PhotoboothUI()
        self.ui.set_app_mode(config.APP_MODE)
        
        if config.APP_MODE == "wedding":
            self.ui.num_captures_selector.setCurrentIndex(0) # 1 hình
            self.ui.num_captures_selector.setEnabled(False)
        else:
            self.ui.num_captures_selector.setEnabled(True)
        
        self.current_image = None
        self.processed_image = None
        self.state_pre_frame = None
        self.countdown_val = 0
        self.camera_list = []
        
        self.remaining_captures = 0
        self.total_captures = 0
        self.captured_sequence_paths = []
        self.selected_slot_images = []
        self.current_layout = None
        self.timer = QTimer() # Timer cho countdown
        
        self.layout_manager = FrameLayoutManager()
        self.layout_manager.load_layouts()
        
        self.current_session = "Khach_Mac_Dinh"
        self.load_sessions()
        
        self.camera_worker = CameraWorker()
        self.camera_worker.status_signal.connect(self.log_status)
        self.camera_worker.error_signal.connect(self.log_error)
        self.camera_worker.camera_list_signal.connect(self.on_camera_list_received)
        self.camera_worker.frame_signal.connect(self.ui.preview_label.set_opencv_image)
        self.camera_worker.image_captured_signal.connect(self.on_image_captured)
        self.camera_worker.start()

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_thumbnails)

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_raw_dir)
        self.monitor_timer.start(1000)
        
        self.setup_connections()
        self.refresh_gallery_data()
        self.scan_cameras()
        self.update_qr_code()
        
    def _async_upload(self, local_path, subfolder, remote_name=None):
        if not config.NC_ENABLED:
            self.ui.log("☁️ Nextcloud upload is disabled in config.py")
            return
            
        def run_upload():
            nc_config = {
                'NC_ENABLED': config.NC_ENABLED,
                'NC_URL': config.NC_URL,
                'NC_USER': config.NC_USER,
                'NC_PASS': config.NC_PASS,
                'NC_REMOTE_PATH': config.NC_REMOTE_PATH
            }
            success, msg = upload_to_nextcloud(nc_config, local_path, subfolder, remote_name)
            if success:
                self.ui.log(f"☁️ Nextcloud: Đã upload thành công {os.path.basename(local_path)}")
            else:
                self.ui.log(f"☁️ Nextcloud Error: {msg}")
                
        thread = threading.Thread(target=run_upload)
        thread.daemon = True
        thread.start()
        
    def update_qr_code(self):
        if not hasattr(self.ui, 'qr_code_label'): return
        
        def do_update():
            url = config.NC_SHARE_URL
            
            # Nếu chưa có link nhưng đã bật Nextcloud, tự động thử lấy link
            if not url and config.NC_ENABLED:
                from nextcloud_utils import nc_get_public_link
                success, result = nc_get_public_link({
                    'NC_URL': config.NC_URL,
                    'NC_USER': config.NC_USER,
                    'NC_PASS': config.NC_PASS,
                    'NC_REMOTE_PATH': config.NC_REMOTE_PATH
                })
                if success:
                    config.NC_SHARE_URL = result
                    config.save_config()
                    url = result
                    self.ui.log(f"🔗 Tự động nhận diện share URL: {url}")

            if not url:
                self.ui.qr_code_label.clear()
                self.ui.qr_code_label.setText("Chưa có link\nchia sẻ 🔗")
                return
                
            try:
                qr = qrcode.QRCode(version=1, box_size=10, border=2)
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Convert to QPixmap
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                qimg = QImage.fromData(buffer.getvalue())
                pixmap = QPixmap.fromImage(qimg)
                self.ui.qr_code_label.setPixmap(pixmap)
                if hasattr(self.ui, 'qr_code_label_gallery'):
                    self.ui.qr_code_label_gallery.setPixmap(pixmap)
                self.ui.log("🔄 Đã cập nhật mã QR Nextcloud.")
            except Exception as e:
                self.ui.log(f"🛑 Lỗi tạo QR: {e}")

        # Chạy trong thread để không lock UI khi gọi OCS API
        thread = threading.Thread(target=do_update)
        thread.daemon = True
        thread.start()

    def setup_connections(self):
        self.ui.btn_capture.clicked.connect(self.capture_image)
        self.ui.btn_to_gallery.clicked.connect(self.show_gallery)
        self.ui.btn_admin_setup.clicked.connect(self.open_admin_setup)
        self.ui.session_selector.currentIndexChanged.connect(self.on_session_changed)
        self.ui.camera_selector.currentIndexChanged.connect(self.on_camera_selected)
        # Connect hotkeys for Admin Setup and Full Screen
        self.ui.admin_requested.connect(self.open_admin_setup)
        self.ui.full_screen_requested.connect(self.toggle_full_screen)
        
        self.ui.btn_session_add.clicked.connect(self.handle_new_session)
        self.ui.btn_session_rename.clicked.connect(self.handle_rename_session)
        self.ui.btn_session_delete.clicked.connect(self.handle_delete_session)
        self.ui.btn_copy_session_path.clicked.connect(self.handle_copy_path)
        
        self.ui.preview_label.zoom_in_signal.connect(self.on_zoom_in)
        self.ui.preview_label.zoom_out_signal.connect(self.on_zoom_out)
        self.ui.preview_label.clicked_pos.connect(self.on_tap_focus)
        
        self.ui.btn_back_to_station.clicked.connect(self.show_station)
        # Custom widgets handle their own clicks, so we don't need itemClicked
        self.ui.frame_list.itemClicked.connect(self.on_frame_item_selected)
        self.ui.btn_apply_lut.clicked.connect(self.apply_lut_action)
        self.ui.btn_apply_sharpen.clicked.connect(self.apply_sharpen_action)
        self.ui.btn_print.clicked.connect(self.print_action)
        self.ui.btn_save.clicked.connect(self.save_action)
        self.ui.btn_delete_selected.clicked.connect(self.delete_selected_action)
        self.ui.btn_delete_all.clicked.connect(self.delete_all_action)
        self.ui.btn_import_raw.clicked.connect(self.import_raw_action)
        self.ui.btn_refresh_gallery.clicked.connect(self.refresh_thumbnails)
        self.ui.thumbnail_list.itemClicked.connect(self.on_thumbnail_clicked)
        self.ui.thumbnail_list.itemSelectionChanged.connect(self.update_delete_button_state)
        self.ui.btn_delete_lut.clicked.connect(self.delete_lut_action)
        self.ui.btn_add_lut.clicked.connect(self.import_lut_action)
        self.ui.btn_gallery_capture.clicked.connect(self.trigger_capture_one)
        self.ui.btn_add_icon.clicked.connect(self.add_icon_action)
        self.ui.btn_show_log.clicked.connect(self.show_log_action)

    def toggle_full_screen(self):
        if self.ui.isFullScreen():
            self.ui.showNormal()
        else:
            self.ui.showFullScreen()

    def show_log_action(self):
        from ui_main import LogViewerDialog
        dialog = LogViewerDialog(self.ui, self.ui.log_buffer)
        dialog.exec_()

    def show_station(self):
        self.refresh_timer.stop()
        self.ui.central_widget.setCurrentIndex(0)
        self.camera_worker.resume_preview()
        self.ui.status_dot.setText("🟢 System Ready")

    def show_gallery(self, pre_select_path=None):
        self.ui.central_widget.setCurrentIndex(1)
        self.ui.current_session_label.setText(f"Phiên: {self.current_session}")
        self.refresh_thumbnails(pre_select_path)
        self.refresh_timer.start(1000)
        
        layout_name = self.ui.frame_selector.currentText() if hasattr(self.ui, 'frame_selector') else ""
        if not layout_name:
            layouts = self.layout_manager.get_all_layouts()
            if layouts: layout_name = layouts[0]["name"]
            
        self.current_layout = self.layout_manager.get_layout_by_name(layout_name)
        num_slots = len(self.current_layout.get("slots", [])) if self.current_layout else 1
        
        if len(self.selected_slot_images) != num_slots:
            self.selected_slot_images = [None] * num_slots

        if pre_select_path:
            # Re-check if we need to auto-fill an empty slot when called manually with a path
            for i in range(len(self.selected_slot_images)):
                if self.selected_slot_images[i] is None:
                    self.selected_slot_images[i] = pre_select_path
                    break
        self.refresh_gallery_preview()

    def open_admin_setup(self):
        menu = QMenu(self.ui)
        act_add = QAction("➕ Thêm Layout Mới", self.ui)
        act_add.triggered.connect(self.handle_add_layout)
        act_edit = QAction("✏️ Sửa Layout Hiện Tại", self.ui)
        act_edit.triggered.connect(self.handle_edit_layout)
        act_del = QAction("🗑️ Xóa Layout", self.ui)
        act_del.triggered.connect(self.handle_delete_layout)
        
        menu.addAction(act_add)
        menu.addAction(act_edit)
        menu.addAction(act_del)
        
        menu.addSeparator()
        current_mode_text = "Wedding" if config.APP_MODE == "wedding" else "Normal"
        other_mode_text = "Normal" if config.APP_MODE == "wedding" else "Wedding"
        act_mode = QAction(f"🔄 Chuyển sang chế độ: {other_mode_text}", self.ui)
        act_mode.triggered.connect(self.toggle_app_mode)
        menu.addAction(act_mode)
        
        menu.addSeparator()
        act_nc = QAction("☁️ Cấu hình Nextcloud", self.ui)
        act_nc.triggered.connect(self.handle_nc_config)
        menu.addAction(act_nc)
        
        # Hiện menu ở góc trên cùng bên phải màn hình (hoặc cửa sổ)
        pos = self.ui.rect().topRight()
        global_pos = self.ui.mapToGlobal(pos)
        # Lùi lại một chút để không bị dính sát mép
        global_pos.setX(global_pos.x() - menu.sizeHint().width())
        menu.exec_(global_pos)

    def handle_nc_config(self):
        from ui_main import NextcloudConfigDialog
        from PyQt5.QtWidgets import QMessageBox
        dialog = NextcloudConfigDialog(self.ui)
        
        def run_auto_share():
            from nextcloud_utils import nc_get_public_link
            import config
            # Lấy tạm cấu hình từ các ô input
            tmp_config = {
                'NC_URL': dialog.txt_url.text().strip(),
                'NC_USER': dialog.txt_user.text().strip(),
                'NC_PASS': dialog.txt_pass.text().strip(),
                'NC_REMOTE_PATH': dialog.txt_root.text().strip()
            }
            self.ui.log("⌛ Đang tự động thiết lập chia sẻ Nextcloud...")
            success, result = nc_get_public_link(tmp_config)
            if success:
                dialog.txt_share_url.setText(result)
                self.ui.log(f"✅ Tự động lấy link thành công: {result}")
            else:
                QMessageBox.warning(dialog, "Lỗi", f"Không thể lấy link tự động:\n{result}")
                self.ui.log(f"🛑 Lỗi tự động chia sẻ: {result}")

        dialog.btn_auto_share.clicked.connect(run_auto_share)
        
        if dialog.exec_():
            self.update_qr_code()

    def handle_add_layout(self):
        dialog = FrameConfigDialog(self.ui)
        if dialog.exec_(): self.refresh_gallery_data()

    def handle_edit_layout(self):
        layouts = self.layout_manager.get_all_layouts()
        if not layouts: return
        names = [l["name"] for l in layouts]
        name, ok = QInputDialog.getItem(self.ui, "Sửa Layout", "Chọn layout:", names, 0, False)
        if ok and name:
            layout_data = next((l for l in layouts if l["name"] == name), None)
            if layout_data:
                dialog = FrameConfigDialog(self.ui, layout_data=layout_data)
                if dialog.exec_(): self.refresh_gallery_data()

    def handle_delete_layout(self):
        layouts = self.layout_manager.get_all_layouts()
        if not layouts:
            QMessageBox.information(self.ui, "Thông báo", "Chưa có layout nào để xóa.")
            return
            
        names = [l["name"] for l in layouts]
        name, ok = QInputDialog.getItem(self.ui, "Xóa Layout", "Chọn layout muốn xóa:", names, 0, False)
        
        if ok and name:
            confirm = QMessageBox.question(
                self.ui, "Xác nhận xóa",
                f"Bạn có chắc chắn muốn xóa layout '{name}' không?\nHành động này không thể hoàn tác.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                success, msg = self.layout_manager.delete_layout(name)
                if success:
                    QMessageBox.information(self.ui, "Thành công", msg)
                    self.refresh_gallery_data()
                else:
                    QMessageBox.critical(self.ui, "Lỗi", msg)

    def toggle_app_mode(self):
        config.APP_MODE = "normal" if config.APP_MODE == "wedding" else "wedding"
        config.save_config()
        self.ui.set_app_mode(config.APP_MODE)
        
        # Ràng buộc mới cho chế độ Wedding: Luôn là 1 tấm
        if config.APP_MODE == "wedding":
            self.ui.num_captures_selector.setCurrentIndex(0) # 1 hình
            self.ui.num_captures_selector.setEnabled(False)
        else:
            self.ui.num_captures_selector.setEnabled(True)

        msg = "Đã chuyển sang chế độ Wedding!" if config.APP_MODE == "wedding" else "Đã chuyển sang chế độ Normal!"
        self.ui.log(msg)

    def scan_cameras(self): self.camera_worker.request_scan()

    def on_camera_list_received(self, cameras):
        self.camera_list = cameras
        self.ui.camera_selector.blockSignals(True)
        self.ui.camera_selector.clear()
        if not cameras:
            self.ui.camera_selector.addItem("Không tìm thấy máy ảnh!")
        else:
            for idx, name in cameras: self.ui.camera_selector.addItem(name, userData=idx)
            self.ui.camera_selector.setCurrentIndex(0)
            self.start_preview(cameras[0][0])
        self.ui.camera_selector.blockSignals(False)

    def on_camera_selected(self, index):
        if index >= 0 and self.camera_list:
            cam_idx = self.ui.camera_selector.itemData(index)
            self.start_preview(cam_idx)

    def start_preview(self, idx): self.camera_worker.change_camera(idx)
    def on_zoom_in(self): self.camera_worker.zoom_in()
    def on_zoom_out(self): self.camera_worker.zoom_out()
    def on_tap_focus(self, x, y): self.camera_worker.trigger_autofocus()

    def capture_image(self):
        # Nếu đang trong chuỗi chụp (đang chờ nhấn nút để chụp tiếp/lại)
        if self.remaining_captures > 0:
            self.trigger_next_capture()
            return
            
        # Bắt đầu chuỗi mới
        if config.APP_MODE == "wedding":
            self.total_captures = 1
        else:
            num_txt = self.ui.num_captures_selector.currentText()
            import re
            match_num = re.search(r'(\d+)', num_txt)
            self.total_captures = int(match_num.group(1)) if match_num else 1
            
        self.remaining_captures = self.total_captures
        self.captured_sequence_paths = []
        
        # Show progress label only if more than 1 image
        if self.total_captures > 1:
            self.ui.capture_progress_label.setText(f"1 / {self.total_captures}")
            self.ui.capture_progress_label.show()
        else:
            self.ui.capture_progress_label.hide()
            
        if self.current_layout:
            num_slots = len(self.current_layout.get("slots", []))
            self.selected_slot_images = [None] * num_slots
        else:
            self.selected_slot_images = []
            
        self.trigger_next_capture()

    def trigger_next_capture(self):
        selection = self.ui.countdown_selector.currentText()
        if "Chụp ngay" in selection:
            self.camera_worker.request_capture()
        else:
            import re
            match = re.search(r'(\d+)s', selection)
            if match: self.start_countdown(int(match.group(1)))
            else: self.camera_worker.request_capture()

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
        if self.countdown_val > 0: self.ui.countdown_label.setText(str(self.countdown_val))
        else:
            self.timer.stop()
            self.ui.countdown_label.hide()
            if self.remaining_captures <= 1: self.ui.btn_capture.setEnabled(True)
            self.camera_worker.request_capture()

    def on_image_captured(self, path):
        from ui_main import CaptureReviewDialog
        
        self.camera_worker.pause_preview()
        
        # Hiện Dialog review
        current_idx = self.total_captures - self.remaining_captures + 1
        pix = QPixmap(path)
        dialog = CaptureReviewDialog(self.ui, pix, current_idx, self.total_captures)
        
        if dialog.exec_() == QDialog.Accepted:
            # OK -> Chấp nhận tấm này
            self.captured_sequence_paths.append(path)
            
            # Upload to Nextcloud asynchronously (Raw)
            self._async_upload(path, self.current_session)
            
            self.remaining_captures -= 1
            
            if self.remaining_captures > 0:
                next_idx = self.total_captures - self.remaining_captures + 1
                self.ui.capture_progress_label.setText(f"{next_idx} / {self.total_captures}")
                self.ui.log(f"Chấp nhận ảnh {current_idx}. Chờ chụp tiếp...")
                
                # Setup nút để chụp tiếp
                self.ui.btn_capture.setText(f"📸 CHỤP TIẾP TẤM {next_idx}")
                self.ui.btn_capture.setEnabled(True)
                self.camera_worker.resume_preview()
            else:
                # Hoàn thành tất cả
                self.ui.capture_progress_label.hide()
                self.ui.btn_capture.setText("📸 CHỤP ẢNH")
                self.ui.btn_capture.setEnabled(True)
                self.ui.log("Hoàn thành chuỗi chụp.")
                
                if self.current_layout:
                    num_slots = len(self.current_layout.get("slots", []))
                    for i in range(min(len(self.captured_sequence_paths), num_slots)):
                        if i < len(self.selected_slot_images):
                            self.selected_slot_images[i] = self.captured_sequence_paths[i]
                
                self.camera_worker.resume_preview()
                self.show_gallery()
        else:
            # Chụp lại tấm vừa rồi
            self.ui.log(f"Yêu cầu chụp lại tấm thứ {current_idx}...")
            try:
                if os.path.exists(path): os.remove(path)
            except: pass
            
            # Setup nút để chụp lại
            self.ui.btn_capture.setText(f"📸 CHỤP LẠI TẤM {current_idx}")
            self.ui.btn_capture.setEnabled(True)
            self.camera_worker.resume_preview()

    def on_thumbnail_clicked(self, item_or_path):
        if isinstance(item_or_path, str):
            path = item_or_path
        else:
            path = item_or_path.data(Qt.UserRole)
            
        if not path: return

        # Chỉ chọn item nếu user click từ widget
        for i in range(self.ui.thumbnail_list.count()):
            it = self.ui.thumbnail_list.item(i)
            if it.data(Qt.UserRole) == path:
                it.setSelected(True)
                self.ui.thumbnail_list.setCurrentItem(it)
                break
        
        # Cập nhật preview to ở giữa ngay lập tức
        self.ui.update_preview_image(path)
        
        # Logic tự động điền vào khung (giữ nguyên)
        found_empty = False
        for i in range(len(self.selected_slot_images)):
            if self.selected_slot_images[i] is None:
                self.selected_slot_images[i] = path
                found_empty = True
                break
        if not found_empty:
            if len(self.selected_slot_images) > 0:
                self.selected_slot_images[0] = path
            else:
                self.selected_slot_images = [path]
        self.refresh_gallery_preview()

    def update_delete_button_state(self):
        selected = self.ui.thumbnail_list.selectedItems()
        self.ui.btn_delete_selected.setEnabled(len(selected) > 0)

    def on_remove_from_frame_path(self, path):
        """Xóa tất cả các instance của path khỏi các slot trong khung hiện tại."""
        changed = False
        for i in range(len(self.selected_slot_images)):
            if self.selected_slot_images[i] == path:
                self.selected_slot_images[i] = None
                changed = True
        if changed:
            self.refresh_gallery_preview()

    def on_remove_slot_image(self, slot_index):
        if 0 <= slot_index < len(self.selected_slot_images):
            self.selected_slot_images[slot_index] = None
            self.refresh_gallery_preview()

    def refresh_gallery_data(self):
        self.ui.lut_selector.clear()
        self.ui.lut_selector.addItem("Gốc (Không màu)")
        if os.path.exists(config.LUTS_DIR):
            self.ui.lut_selector.addItems([f for f in os.listdir(config.LUTS_DIR) if f.lower().endswith(('.cube', '.xmp'))])
        self.ui.frame_list.clear()
        self.layout_manager.load_layouts()
        none_item = QListWidgetItem("❌ Không khung")
        none_item.setData(Qt.UserRole, None)
        self.ui.frame_list.addItem(none_item)
        for l in self.layout_manager.get_all_layouts():
            frame_path = l.get("frame_file")
            if frame_path and os.path.exists(frame_path):
                item = QListWidgetItem(QIcon(frame_path), l["name"])
                item.setData(Qt.UserRole, l)
                self.ui.frame_list.addItem(item)

    def refresh_thumbnails(self, pre_select_path=None):
        session_dir = os.path.join(config.RAW_DIR, self.current_session)
        if not os.path.exists(session_dir): os.makedirs(session_dir)
        files = [f for f in os.listdir(session_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(session_dir, x)), reverse=True)
        
        # Sửa lỗi so sánh để không bị refresh liên tục mỗi giây
        current_files = []
        for i in range(self.ui.thumbnail_list.count()):
            it = self.ui.thumbnail_list.item(i)
            p = it.data(Qt.UserRole)
            if p: current_files.append(os.path.basename(p))
            
        if files == current_files and not pre_select_path: return 
        self.ui.thumbnail_list.blockSignals(True)
        self.ui.thumbnail_list.clear()
        from ui_main import ThumbnailWidget
        for f in files:
            full_path = os.path.join(session_dir, f)
            item = QListWidgetItem(self.ui.thumbnail_list)
            # Bỏ chặn selection để cho phép chọn ảnh xóa
            item.setSizeHint(QSize(215, 215))
            item.setData(Qt.UserRole, full_path)
            
            thumb = ThumbnailWidget(full_path)
            thumb.remove_signal.connect(self.on_remove_from_frame_path)
            thumb.click_signal.connect(self.on_thumbnail_clicked)
            in_frame = full_path in self.selected_slot_images
            thumb.set_in_frame(in_frame)
            
            self.ui.thumbnail_list.addItem(item)
            self.ui.thumbnail_list.setItemWidget(item, thumb)
        self.ui.thumbnail_list.blockSignals(False)

    def refresh_gallery_preview(self):
        if not self.current_layout: return
        self.ui.show_loading("Đang áp khung...")
        
        # Sử dụng QTimer để nhường main thread cho UI vẽ overlay trước khi xử lý nặng
        QTimer.singleShot(50, self._do_heavy_refresh)

    def _do_heavy_refresh(self):
        try:
            out_path = ImageProcessor.apply_frame(self.selected_slot_images, self.current_layout)
            self.ui.update_preview_image(out_path)
            self.processed_image = out_path
            self.ui.update_slot_delete_buttons(self.selected_slot_images, self.on_remove_slot_image)
            
            # Update thumbnail 'in_frame' status
            for i in range(self.ui.thumbnail_list.count()):
                item = self.ui.thumbnail_list.item(i)
                widget = self.ui.thumbnail_list.itemWidget(item)
                if widget:
                    path = item.data(Qt.UserRole)
                    widget.set_in_frame(path in self.selected_slot_images)
        except Exception as e: self.ui.log(f"Lỗi preview: {e}")
        finally:
            self.ui.hide_loading()

    def on_frame_item_selected(self, item):
        layout_data = item.data(Qt.UserRole)
        if layout_data is None:
            self.current_layout = None
            self.selected_slot_images = []
            self.processed_image = None
            self.ui.update_preview_image(None)
            self.ui.update_slot_delete_buttons([], self.on_remove_slot_image)
            return
        self.current_layout = layout_data
        num_slots = len(layout_data.get("slots", []))
        if len(self.selected_slot_images) != num_slots:
            new_list = [None] * num_slots
            for i in range(min(len(self.selected_slot_images), num_slots)): new_list[i] = self.selected_slot_images[i]
            self.selected_slot_images = new_list
        self.refresh_gallery_preview()

    def apply_lut_action(self): QMessageBox.information(self.ui, "Feature", "Nâng cấp cho đa slot...")
    def apply_sharpen_action(self): QMessageBox.information(self.ui, "Feature", "Nâng cấp cho đa slot...")
    def print_action(self):
        if self.processed_image:
            self.ui.show_loading("Đang gửi lệnh in...")
            try:
                PrinterService.print_image(self.processed_image)
                # Upload to Nextcloud asynchronously (Output)
                self._async_upload(self.processed_image, self.current_session)
                QMessageBox.information(self.ui, "Máy in", "Đã gửi in.")
            finally:
                self.ui.hide_loading()
    def save_action(self):
        if self.processed_image:
            target, _ = QFileDialog.getSaveFileName(self.ui, "Lưu ảnh", f"PRO_{os.path.basename(self.processed_image)}", "Images (*.jpg)")
            if target:
                self.ui.show_loading("Đang lưu ảnh...")
                try:
                    shutil.copy2(self.processed_image, target)
                    # Upload to Nextcloud asynchronously (Output)
                    self._async_upload(self.processed_image, self.current_session)
                finally:
                    self.ui.hide_loading()

    def delete_selected_action(self):
        selected = self.ui.thumbnail_list.selectedItems()
        if selected and QMessageBox.question(self.ui, "Xóa", f"Xóa {len(selected)} ảnh?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            for item in selected:
                p = item.data(Qt.UserRole)
                if os.path.exists(p): os.remove(p)
            self.refresh_thumbnails()

    def delete_all_action(self):
        session_dir = os.path.join(config.RAW_DIR, self.current_session)
        files = [f for f in os.listdir(session_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if files and QMessageBox.question(self.ui, "Xóa hết", "Xóa hết phiên này?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            for f in files: os.remove(os.path.join(session_dir, f))
            self.refresh_thumbnails()

    def import_raw_action(self):
        files, _ = QFileDialog.getOpenFileNames(self.ui, "Nhập ảnh", "", "Images (*.png *.jpg)")
        if files:
            for f in files: shutil.copy2(f, os.path.join(config.RAW_DIR, self.current_session, f"import_{os.path.basename(f)}"))
            self.refresh_thumbnails()

    def delete_lut_action(self):
        lut = self.ui.lut_selector.currentText()
        if lut != "Gốc (Không màu)" and QMessageBox.question(self.ui, "Xóa", "Xóa LUT?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            os.remove(os.path.join(config.LUTS_DIR, lut))
            self.refresh_gallery_data()
            
    def import_lut_action(self):
        files, _ = QFileDialog.getOpenFileNames(self.ui, "Nhập LUT", "", "Presets (*.cube *.xmp)")
        if files:
            for f in files: shutil.copy2(f, os.path.join(config.LUTS_DIR, os.path.basename(f)))
            self.refresh_gallery_data()

    def add_icon_action(self):
        from ui_main import IconSelectionDialog, IconWidget
        dialog = IconSelectionDialog(self.ui)
        if dialog.exec_():
            path = dialog.selected_path
            if path:
                icon = IconWidget(self.ui.gallery_preview_label, path)
                icon.deleted.connect(lambda obj: self.ui.log("Đã xóa icon"))
                self.ui.log("Đã thêm icon trang trí")

    def trigger_capture_one(self):
        target = self.find_capture_one()
        if target:
            try:
                target.activate()
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'k')
                wins = gw.getWindowsWithTitle("Photobooth Station Pro")
                if wins: wins[0].activate()
            except: pass
        else: QMessageBox.warning(self.ui, "Lỗi", "Không thấy Capture One!")

    def find_capture_one(self):
        for win in gw.getAllWindows():
            for key in ["Capture One", "PhotoBooth"]:
                if key in win.title: return win
        return None

    def monitor_raw_dir(self):
        try:
            files = [f for f in os.listdir(config.RAW_DIR) if os.path.isfile(os.path.join(config.RAW_DIR, f)) and f.lower().endswith(('.png', '.jpg'))]
            if not files: return
            for f in files: shutil.move(os.path.join(config.RAW_DIR, f), os.path.join(config.RAW_DIR, self.current_session, f))
            self.refresh_thumbnails()
        except: pass

    def load_sessions(self, select_name=None):
        self.ui.session_selector.blockSignals(True)
        self.ui.session_selector.clear()
        dirs = [d for d in os.listdir(config.RAW_DIR) if os.path.isdir(os.path.join(config.RAW_DIR, d))] if os.path.exists(config.RAW_DIR) else []
        if not dirs: dirs = ["Khach_Mac_Dinh"]
        self.ui.session_selector.addItems(sorted(dirs))
        self.current_session = select_name if select_name in dirs else self.ui.session_selector.currentText()
        if select_name: self.ui.session_selector.setCurrentText(select_name)
        self.ui.session_selector.blockSignals(False)

    def on_session_changed(self, index):
        self.current_session = self.ui.session_selector.currentText()
        if hasattr(self, 'camera_worker'): self.camera_worker.set_session(self.current_session)

    def handle_new_session(self):
        from ui_main import VirtualKeyboardDialog
        dialog = VirtualKeyboardDialog(self.ui)
        if dialog.exec_():
            text = dialog.get_text()
            if text:
                safe = "".join([c if c.isalnum() else "_" for c in text]).strip("_")
                if safe:
                    os.makedirs(os.path.join(config.RAW_DIR, safe), exist_ok=True)
                    self.load_sessions(select_name=safe)

    def handle_copy_path(self):
        path = os.path.abspath(os.path.join(config.RAW_DIR, self.current_session))
        QApplication.clipboard().setText(path)
        self.ui.log(f"📋 Đã copy đường dẫn: {path}")

    def handle_rename_session(self):
        if self.current_session == "Khach_Mac_Dinh": return
        text, ok = QInputDialog.getText(self.ui, "Đổi Tên", "Tên mới:", text=self.current_session)
        if ok and text:
            safe = "".join([c if c.isalnum() else "_" for c in text]).strip("_")
            if safe and safe != self.current_session:
                os.rename(os.path.join(config.RAW_DIR, self.current_session), os.path.join(config.RAW_DIR, safe))
                self.load_sessions(select_name=safe)

    def handle_delete_session(self):
        if self.current_session != "Khach_Mac_Dinh" and QMessageBox.question(self.ui, "Xóa", "Xóa phiên?") == QMessageBox.Yes:
            shutil.rmtree(os.path.join(config.RAW_DIR, self.current_session))
            self.load_sessions()

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
    PhotoboothApp().run()
