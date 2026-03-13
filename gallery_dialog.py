import os
import shutil
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QListWidget, QListWidgetItem, 
                             QMessageBox, QWidget, QGridLayout, QSizePolicy, QFileDialog)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont, QImage
from config import RAW_DIR, LUTS_DIR
from image_processor import ImageProcessor
from printer_service import PrinterService

class ImagePreviewLabel(QLabel):
    """Custom Label để hiển thị ảnh preview giữ đúng tỉ lệ khi resize cửa sổ"""
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            background-color: #fff5e6; 
            border: 4px dashed #ffb380; 
            border-radius: 20px;
            color: #d35400; 
            font-size: 28px;
            font-weight: bold;
        """)
        self.setText("Chưa chọn ảnh📸")
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(400, 300)
        self.pixmap_img = None

    def set_image(self, image_path):
        self.pixmap_img = QPixmap(image_path)
        self.update_preview()

    def set_opencv_image(self, qt_image):
        self.pixmap_img = QPixmap.fromImage(qt_image)
        self.update_preview()

    def clear_image(self):
        self.pixmap_img = None
        self.clear()
        self.setText("Chưa chọn ảnh📸")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview()

    def update_preview(self):
        if self.pixmap_img and not self.pixmap_img.isNull():
            scaled = self.pixmap_img.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            super().setPixmap(scaled)

class GalleryDialog(QDialog):
    def __init__(self, parent=None, layout_manager=None, pre_select_path=None, session_name="Khach_Mac_Dinh"):
        super().__init__(parent)
        self.setWindowTitle(f"Thư Viện Ảnh Chụp (RAW) - Khách: {session_name}")
        
        # Bật các nút Minimize / Maximize / Close cho Dialog
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Set kích thước bằng 80% màn hình thay vì FullScreen
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        
        self.setStyleSheet("background-color: #fffaf0; color: #5c4033; font-family: 'Segoe UI';")
        
        self.layout_manager = layout_manager
        self.session_name = session_name
        self.session_dir = os.path.join(RAW_DIR, self.session_name)
        os.makedirs(self.session_dir, exist_ok=True)
        
        self.current_image_path = None
        self.processed_image_path = None
        
        # --- UI SETUP ---
        main_layout = QHBoxLayout(self)
        
        # LEFT PANEL (Preview Focus & Tools)
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, stretch=4)
        
        # Preview Focus
        self.preview_label = ImagePreviewLabel()
        self.preview_label.setMinimumSize(720, 540) # Tăng kích thước tối thiểu thêm 20%
        left_layout.addWidget(self.preview_label, stretch=1)
        
        # Tool Bar Layout 1 (LUT Selection)
        lut_toolbar_layout = QHBoxLayout()
        left_layout.addLayout(lut_toolbar_layout)
        
        lut_label = QLabel("Chọn Màu LUT:")
        lut_label.setStyleSheet("color: #8e44ad; font-weight: bold; font-size: 14px;")
        lut_toolbar_layout.addWidget(lut_label)
        
        self.lut_selector = QComboBox()
        self.lut_selector.setFont(QFont("Segoe UI", 12))
        self.lut_selector.setStyleSheet("""
            QComboBox { background-color: #fff; color: #8e44ad; border: 2px solid #d2b4de; padding: 6px; border-radius: 5px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #fff; color: #8e44ad; selection-background-color: #f4ecf7; }
        """)
        lut_toolbar_layout.addWidget(self.lut_selector, stretch=1)
        
        self.btn_apply_lut = self._create_button("🎨 Áp Màu", "#d2b4de", "#bb8fce", "#5b2c6f")
        self.btn_apply_lut.clicked.connect(self.apply_lut)
        lut_toolbar_layout.addWidget(self.btn_apply_lut)
        
        self.btn_import_lut = self._create_button("📥 Nhập LUT", "#f4ecf7", "#e8daef", "#5b2c6f")
        self.btn_import_lut.clicked.connect(self.import_lut)
        lut_toolbar_layout.addWidget(self.btn_import_lut)
        
        self.btn_delete_lut = self._create_button("❌ Xóa LUT", "#fadbd8", "#f1948a", "#c0392b")
        self.btn_delete_lut.clicked.connect(self.delete_lut)
        lut_toolbar_layout.addWidget(self.btn_delete_lut)
        
        # Tool Bar Layout 1.5 (Sharpening Selection) - NEW
        sharpen_toolbar_layout = QHBoxLayout()
        left_layout.addLayout(sharpen_toolbar_layout)
        
        sharpen_label = QLabel("Độ Sắc Nét:")
        sharpen_label.setStyleSheet("color: #16a085; font-weight: bold; font-size: 14px;")
        sharpen_toolbar_layout.addWidget(sharpen_label)
        
        self.sharpen_selector = QComboBox()
        self.sharpen_selector.setFont(QFont("Segoe UI", 12))
        self.sharpen_selector.setStyleSheet("""
            QComboBox { background-color: #fff; color: #16a085; border: 2px solid #a3e4d7; padding: 6px; border-radius: 5px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #fff; color: #16a085; selection-background-color: #e8f8f5; }
        """)
        self.sharpen_selector.addItems(["Tắt (Gốc)", "Thấp", "Vừa (Nên dùng)", "Cao"])
        # Mặc định chọn "Vừa" vì ảnh DSLR thường cần sharpening
        self.sharpen_selector.setCurrentIndex(2) 
        sharpen_toolbar_layout.addWidget(self.sharpen_selector, stretch=1)
        
        self.btn_apply_sharpen = self._create_button("✨ Làm Nét", "#a3e4d7", "#76d7c4", "#0e6251")
        self.btn_apply_sharpen.clicked.connect(self.apply_sharpen)
        sharpen_toolbar_layout.addWidget(self.btn_apply_sharpen)
        
        # Tool Bar Layout 2 (Frame Selection)
        toolbar_layout = QHBoxLayout()
        left_layout.addLayout(toolbar_layout)
        
        layout_label = QLabel("Chọn Layout Khung:")
        layout_label.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 14px;")
        toolbar_layout.addWidget(layout_label)
        
        self.layout_selector = QComboBox()
        self.layout_selector.setFont(QFont("Segoe UI", 12))
        self.layout_selector.setStyleSheet("""
            QComboBox { background-color: #fff; color: #d35400; border: 2px solid #ffb380; padding: 6px; border-radius: 5px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #fff; color: #d35400; selection-background-color: #ffe6cc; }
        """)
        toolbar_layout.addWidget(self.layout_selector, stretch=1)
        
        self.btn_apply_frame = self._create_button("🖼 Chèn Khung", "#ffc299", "#ffa366")
        self.btn_apply_frame.clicked.connect(self.apply_frame)
        toolbar_layout.addWidget(self.btn_apply_frame)
        
        self.btn_print = self._create_button("🖨 In Ảnh", "#ffdab3", "#ffc280")
        self.btn_print.clicked.connect(self.print_image)
        toolbar_layout.addWidget(self.btn_print)
        
        self.btn_save = self._create_button("💾 Lưu Mới", "#ffe6cc", "#ffd1b3")
        self.btn_save.clicked.connect(self.save_image)
        toolbar_layout.addWidget(self.btn_save)
        
        # RIGHT PANEL (Thumbnails)
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, stretch=1)
        
        # Thêm combobox chọn Session vào đây
        session_label = QLabel("Khách chụp (Session):")
        session_label.setStyleSheet("color: #2980b9; font-weight: bold; font-size: 16px; margin-top: 5px;")
        right_layout.addWidget(session_label)
        
        self.session_selector = QComboBox()
        self.session_selector.setFont(QFont("Segoe UI", 12))
        self.session_selector.setStyleSheet("""
            QComboBox { background-color: #fff; color: #2c3e50; border: 2px solid #3498db; padding: 6px; border-radius: 5px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #fff; color: #2c3e50; selection-background-color: #ebf5fb; }
        """)
        self.load_sessions_into_combobox()
        self.session_selector.currentIndexChanged.connect(self.change_session)
        right_layout.addWidget(self.session_selector)
        
        right_title = QLabel("Lịch sử chụp (RAW)")
        right_title.setAlignment(Qt.AlignCenter)
        right_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #d35400; margin-top: 15px; margin-bottom: 5px;")
        right_layout.addWidget(right_title)
        
        # Thêm button thao tác thư mục phụ
        import_refresh_layout = QHBoxLayout()
        
        self.btn_import_raw = self._create_button("📥 Nhập ảnh", "#e6f2ff", "#cce6ff", "#0066cc")
        self.btn_import_raw.clicked.connect(self.import_external_images)
        import_refresh_layout.addWidget(self.btn_import_raw)
        
        self.btn_refresh = self._create_button("🔄 Làm mới", "#e8f8f5", "#d1f2eb", "#117a65")
        self.btn_refresh.clicked.connect(lambda: self.load_thumbnails())
        import_refresh_layout.addWidget(self.btn_refresh)
        
        right_layout.addLayout(import_refresh_layout)
        
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(140, 140)) # Tăng size thumbnail lên xíu
        self.thumbnail_list.setSpacing(10)
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setSelectionMode(QListWidget.ExtendedSelection) # Bật chế độ chọn nhiều item
        self.thumbnail_list.setStyleSheet("""
            QListWidget { background-color: #fff; border: 2px solid #ffcc99; border-radius: 8px; outline: 0; }
            QListWidget::item:selected { background-color: #ffb380; border-radius: 5px; border: 2px solid #d35400; }
        """)
        self.thumbnail_list.itemSelectionChanged.connect(self.on_thumbnail_selected)
        right_layout.addWidget(self.thumbnail_list, stretch=1)
        
        # Delete Buttons
        del_layout = QHBoxLayout()
        self.btn_del_selected = self._create_button("🗑 Xóa chọn", "#ffcccc", "#ff9999", "#c0392b")
        self.btn_del_selected.clicked.connect(self.delete_selected)
        del_layout.addWidget(self.btn_del_selected)
        
        self.btn_del_all = self._create_button("Xóa tất cả", "#f2e6d9", "#e6ccb3", "#d35400")
        self.btn_del_all.clicked.connect(self.delete_all)
        del_layout.addWidget(self.btn_del_all)
        
        right_layout.addLayout(del_layout)

        # Trạng thái khởi tạo Data
        self.load_luts_into_combobox()
        self.refresh_layouts()
        self.load_thumbnails(pre_select_path)
        
        # Thêm QTimer tự động làm mới Gallery mỗi 3 giây
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.check_for_new_images)
        self.auto_refresh_timer.start(3000)
        
        # Lưu trữ danh sách file hiện tại để so sánh
        self._current_file_set = set()
        self._cache_file_set()

    def load_sessions_into_combobox(self):
        self.session_selector.blockSignals(True)
        self.session_selector.clear()
        
        if not os.path.exists(RAW_DIR):
            os.makedirs(RAW_DIR, exist_ok=True)
            
        sessions = [d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d))]
        if not sessions:
            sessions = ["Khach_Mac_Dinh"]
            os.makedirs(os.path.join(RAW_DIR, "Khach_Mac_Dinh"), exist_ok=True)
            
        sessions.sort()
        self.session_selector.addItems(sessions)
        
        if self.session_name in sessions:
            idx = self.session_selector.findText(self.session_name)
            self.session_selector.setCurrentIndex(idx)
        else:
            self.session_selector.setCurrentIndex(0)
            
        self.session_selector.blockSignals(False)

    def change_session(self, index):
        if index >= 0:
            new_session = self.session_selector.currentText()
            self.session_name = new_session
            self.session_dir = os.path.join(RAW_DIR, self.session_name)
            self.setWindowTitle(f"Thư Viện Ảnh Chụp (RAW) - Khách: {self.session_name}")
            os.makedirs(self.session_dir, exist_ok=True)
            
            # Quét và load lại ảnh với session mới
            self._current_file_set.clear()
            self._cache_file_set()
            self.load_thumbnails()

    def _cache_file_set(self):
        """Lưu lại trạng thái file hiện tại trong thư mục"""
        if os.path.exists(self.session_dir):
            files = [f for f in os.listdir(self.session_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            self._current_file_set = set(files)
            
    def check_for_new_images(self):
        """Quét Background xem có file nào mới thả vào không, nếu có thì tự Refresh"""
        if not os.path.exists(self.session_dir):
            return
            
        current_files = [f for f in os.listdir(self.session_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        new_file_set = set(current_files)
        
        # Nếu số lượng hoặc tên file khác biệt => có file mới / bị xóa
        if new_file_set != self._current_file_set:
            self._current_file_set = new_file_set
            
            # Lưu lại trạng thái Selected Item hiện tại để không làm mất focus của người dùng đang chỉnh ảnh
            selected_path = None
            if self.thumbnail_list.selectedItems():
                selected_path = self.thumbnail_list.selectedItems()[0].data(Qt.UserRole)
                
            # Hàm refresh
            self.load_thumbnails(pre_select_path=selected_path)
        
    def _create_button(self, text, color, hover_color, text_color="#d35400"):
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {color}; color: {text_color}; border-radius: 5px; padding: 10px; border: 1px solid rgba(0,0,0,0.1); }}
            QPushButton:hover {{ background-color: {hover_color}; margin-top: -1px; margin-bottom: 1px; }}
        """)
        return btn

    def load_luts_into_combobox(self):
        self.lut_selector.blockSignals(True)
        self.lut_selector.clear()
        
        if not os.path.exists(LUTS_DIR):
            os.makedirs(LUTS_DIR, exist_ok=True)
            
        self.lut_selector.addItem("Bản gốc (Không Màu)")
        
        luts = [f for f in os.listdir(LUTS_DIR) if f.lower().endswith(('.cube', '.xmp'))]
        if not luts:
            # Vẫn giữ option Default, không cần thông báo "Chưa có file" nữa vì đã có nút Import
            pass
        else:
            self.lut_selector.addItems(luts)
            
        self.lut_selector.blockSignals(False)

    def import_lut(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file Màu (.cube, .xmp)", "", "Preset Files (*.cube *.xmp);;LUT Files (*.cube);;XMP Files (*.xmp);;All Files (*)"
        )
        if file_paths:
            try:
                imported_count = 0
                last_filename = ""
                for file_path in file_paths:
                    filename = os.path.basename(file_path)
                    target_path = os.path.join(LUTS_DIR, filename)
                    shutil.copy2(file_path, target_path)
                    
                    # Nếu là XMP, thử convert sang .cube ngay
                    if filename.lower().endswith('.xmp'):
                        cube_filename = os.path.splitext(filename)[0] + ".cube"
                        cube_path = os.path.join(LUTS_DIR, cube_filename)
                        if ImageProcessor.convert_xmp_to_cube(target_path, cube_path):
                            last_filename = cube_filename
                            imported_count += 1
                        else:
                            last_filename = filename
                    else:
                        last_filename = filename
                    
                    imported_count += 1
                
                QMessageBox.information(self, "Thành công", f"Đã nhập thành công {imported_count} file màu!")
                self.load_luts_into_combobox()
                
                if last_filename:
                    idx = self.lut_selector.findText(last_filename)
                    if idx >= 0:
                        self.lut_selector.setCurrentIndex(idx)
                    
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể nhập màu!\nChi tiết: {e}")

    def apply_lut(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn 1 ảnh RAW từ Lịch sử để ám màu!")
            return
            
        selected_lut = self.lut_selector.currentText()
        if selected_lut == "Bản gốc (Không Màu)":
            self.processed_image_path = None
            self.preview_label.set_image(self.current_image_path)
            return
            
        lut_path = os.path.join(LUTS_DIR, selected_lut)
        
        # Nếu chọn file .xmp, kiểm tra xem đã có file .cube tương ứng chưa
        if lut_path.lower().endswith('.xmp'):
            cube_path = os.path.splitext(lut_path)[0] + ".cube"
            if os.path.exists(cube_path):
                lut_path = cube_path
            else:
                # Thử convert nóng nếu chưa có
                if ImageProcessor.convert_xmp_to_cube(lut_path, cube_path):
                    lut_path = cube_path
                else:
                    QMessageBox.warning(self, "Thông báo", f"File XMP '{selected_lut}' không chứa dữ liệu 3D LUT để áp dụng trực tiếp.")
                    return

        # Luôn lấy ảnh RAW ban đầu để apply LUT (tránh đè LUT lên nhau nếu chọn nhiều lần)
        src_image = self.current_image_path
        
        try:
            self.btn_apply_lut.setText("Đang Áp...")
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            
            out_path = ImageProcessor.apply_lut(src_image, lut_path)
            
            self.processed_image_path = out_path
            self.preview_label.set_image(self.processed_image_path)
            self.btn_apply_lut.setText("🎨 Áp Màu")
        except Exception as e:
            self.btn_apply_lut.setText("🎨 Áp Màu")
            if selected_lut.lower().endswith('.xmp'):
                QMessageBox.information(self, "Thông báo", f"Đã nhận diện file XMP: {selected_lut}.\n\nLưu ý: File XMP chứa thông số chỉnh sửa ảnh thô. Hiện tại hệ thống đang hỗ trợ liệt kê, việc áp dụng màu phức tạp từ XMP đang được phát triển.")
            else:
                QMessageBox.critical(self, "Lỗi xử lý", f"Không thể áp màu!\n{e}")

    def delete_lut(self):
        selected_lut = self.lut_selector.currentText()
        if selected_lut == "Bản gốc (Không Màu)":
            QMessageBox.warning(self, "Lỗi", "Không thể xóa tùy chọn Bản gốc!")
            return
            
        lut_path = os.path.join(LUTS_DIR, selected_lut)
        if not os.path.exists(lut_path):
            return
            
        reply = QMessageBox.question(
            self, 'Xóa Màu LUT',
            f'Bạn có chắc chắn muốn xóa màu "{selected_lut}" không?\n(Không thể khôi phục!)',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(lut_path)
                QMessageBox.information(self, "Thành công", "Đã xóa màu!")
                self.load_luts_into_combobox()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa file!\nLý do: {e}")

    def apply_sharpen(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn 1 ảnh RAW để làm nét!")
            return
            
        level_map = {
            "Thấp": "low",
            "Vừa (Nên dùng)": "normal",
            "Cao": "high"
        }
        selection = self.sharpen_selector.currentText()
        if selection == "Tắt (Gốc)":
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn mức độ làm nét muốn áp dụng.")
            return
            
        level = level_map.get(selection, "normal")
        
        try:
            self.btn_apply_sharpen.setText("Đang xử lý...")
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            
            if selection == "Tắt (Gốc)":
                success = ImageProcessor.restore_original(self.current_image_path)
                if not success:
                    QMessageBox.warning(self, "Thông báo", "Không tìm thấy bản sao lưu gốc để khôi phục.")
                    self.btn_apply_sharpen.setText("✨ Làm Nét")
                    return
            else:
                # Ghi đè trực tiếp lên file đang chọn
                ImageProcessor.sharpen_image(self.current_image_path, level=level)
            
            # Refresh preview
            self.preview_label.set_image(self.current_image_path)
            # Refresh thumbnail icon
            selected_items = self.thumbnail_list.selectedItems()
            if selected_items:
                selected_items[0].setIcon(QIcon(self.current_image_path))

            self.btn_apply_sharpen.setText("✨ Làm Nét")
            QMessageBox.information(self, "Thành công", f"Đã làm nét ảnh ở mức: {selection}")
        except Exception as e:
            self.btn_apply_sharpen.setText("✨ Làm Nét")
            QMessageBox.critical(self, "Lỗi", f"Không thể làm nét ảnh!\n{e}")

    def refresh_layouts(self):
        self.layout_selector.clear()
        if not self.layout_manager:
            return
            
        layouts = self.layout_manager.get_all_layouts()
        if not layouts:
            self.layout_selector.addItem("Chưa có layout nào")
            self.layout_selector.setEnabled(False)
            self.btn_apply_frame.setEnabled(False)
        else:
            for layout in layouts:
                self.layout_selector.addItem(layout["name"], userData=layout)
            self.layout_selector.setEnabled(True)
            self.btn_apply_frame.setEnabled(True)

    def load_thumbnails(self, pre_select_path=None):
        self.thumbnail_list.clear()
        if not os.path.exists(self.session_dir):
            return
            
        # Nạp tất cả file trong session_dir (sắp xếp mới nhất trên cùng)
        files = [f for f in os.listdir(self.session_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.session_dir, x)), reverse=True)
        
        target_item = None
        for filename in files:
            full_path = os.path.join(self.session_dir, filename)
            icon = QIcon(full_path)
            item = QListWidgetItem(icon, filename)
            item.setData(Qt.UserRole, full_path)
            self.thumbnail_list.addItem(item)
            
            # Đánh dấu item nếu cần select sẵn
            if pre_select_path and os.path.normpath(full_path) == os.path.normpath(pre_select_path):
                target_item = item

        # Tự động chọn file
        if target_item:
            self.thumbnail_list.setCurrentItem(target_item)
        elif self.thumbnail_list.count() > 0:
            self.thumbnail_list.setCurrentRow(0)
        else:
            self.preview_label.clear_image()
            self.current_image_path = None
            self.processed_image_path = None

    def on_thumbnail_selected(self):
        selected = self.thumbnail_list.selectedItems()
        if selected:
            path = selected[0].data(Qt.UserRole)
            self.current_image_path = path
            self.processed_image_path = None # Reset state xử lý
            
            # Reset ComboBox LUT về mặc định để khớp giao diện
            self.lut_selector.blockSignals(True)
            idx = self.lut_selector.findText("Bản gốc (Không Màu)")
            if idx >= 0:
                self.lut_selector.setCurrentIndex(idx)
            self.lut_selector.blockSignals(False)
            
            # Reset ComboBox Sharpen về mặc định
            self.sharpen_selector.blockSignals(True)
            self.sharpen_selector.setCurrentIndex(2) # Normal
            self.sharpen_selector.blockSignals(False)
            
            self.preview_label.set_image(path)

    def apply_frame(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một ảnh để chèn khung!")
            return
            
        if self.layout_selector.count() == 0 or not self.layout_selector.itemData(self.layout_selector.currentIndex()):
            QMessageBox.warning(self, "Lỗi", "Chưa có cấu hình layout nào được chọn.")
            return
            
        layout_config = self.layout_selector.currentData()
        
        self.btn_apply_frame.setEnabled(False)
        try:
            # Ưu tiên dùng ảnh đã qua xử lý (ví dụ: đã áp LUT) để chèn khung
            img_to_process = self.processed_image_path or self.current_image_path
            out_path = ImageProcessor.apply_frame(img_to_process, layout_config)
            self.processed_image_path = out_path
            self.preview_label.set_image(out_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Ghép Khung", str(e))
        finally:
            self.btn_apply_frame.setEnabled(True)

    def print_image(self):
        img_to_print = self.processed_image_path or self.current_image_path
        if not img_to_print:
            QMessageBox.warning(self, "Lỗi", "Không có ảnh nào để in!")
            return
            
        try:
            PrinterService.print_image(img_to_print)
            QMessageBox.information(self, "Thành công", "Lệnh in đã được đẩy vào hàng chờ.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Máy In", str(e))

    def save_image(self):
        img_to_save = self.processed_image_path or self.current_image_path
        if not img_to_save:
            QMessageBox.warning(self, "Lỗi", "Không có ảnh nào để lưu!")
            return
            
        from PyQt5.QtWidgets import QFileDialog
        import shutil
        
        default_name = f"PhotoboothOutput_{os.path.basename(img_to_save)}"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu file thiết kế", default_name, "Images (*.png *.jpg *.jpeg)"
        )
        
        if save_path:
            try:
                shutil.copy2(img_to_save, save_path)
                QMessageBox.information(self, "Thành công", f"Đã lưu ra {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Lưu File", str(e))

    def delete_selected(self):
        selected_items = self.thumbnail_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn ít nhất một ảnh để xóa.")
            return
            
        count = len(selected_items)
        reply = QMessageBox.question(self, "Xác nhận xóa", f"Bạn có chắc chắn muốn xóa {count} Bức Ảnh RAW này?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                for item in selected_items:
                    path = item.data(Qt.UserRole)
                    if os.path.exists(path):
                        os.remove(path)
                self.load_thumbnails()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Xóa", f"Không thể xóa tệp tin:\n{e}")

    def delete_all(self):
        if self.thumbnail_list.count() == 0:
            return
            
        reply = QMessageBox.question(self, "CẢNH BÁO", "Xóa TOÀN BỘ Lịch sử chụp RAW?\nHành động này không thể hoàn tác!",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                for idx in range(self.thumbnail_list.count()):
                    item = self.thumbnail_list.item(idx)
                    path = item.data(Qt.UserRole)
                    if os.path.exists(path):
                        os.remove(path)
                self.load_thumbnails()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Xóa Thư Mục", str(e))

    def import_external_images(self):
        from PyQt5.QtWidgets import QFileDialog
        import shutil
        import time
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh muốn thêm vào Thư Viện", "", "Images (*.png *.jpg *.jpeg)"
        )
        
        if not file_paths:
            return
            
        success_count = 0
        try:
            for path in file_paths:
                if not os.path.exists(path):
                    continue
                    
                filename = os.path.basename(path)
                # Đảm bảo tên không bị trùng nếu import nhiều file cùng tên từ các nguồn khác nhau
                safe_name = f"imported_{int(time.time()*1000)}_{filename}"
                dest = os.path.join(self.session_dir, safe_name)
                
                shutil.copy2(path, dest)
                success_count += 1
                
            if success_count > 0:
                self.load_thumbnails()
                QMessageBox.information(self, "Thành công", f"Đã nhập {success_count} ảnh vào Thư viện RAW.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Nhập Ảnh", str(e))
