from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QFormLayout, 
                             QDoubleSpinBox, QSpinBox, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt
from frame_layout_manager import FrameLayoutManager
import os
import shutil

class FrameConfigDialog(QDialog):
    def __init__(self, parent=None, layout_data=None):
        super().__init__(parent)
        self.layout_data = layout_data
        
        if self.layout_data:
            self.setWindowTitle(f"Chỉnh sửa Layout: {layout_data['name']}")
        else:
            self.setWindowTitle("Thêm Cấu Hình Khung Ảnh")
            
        self.setMinimumWidth(500)
        self.layout_manager = FrameLayoutManager()
        
        main_layout = QVBoxLayout(self)

        # 1. Chọn file khung
        form_layout = QFormLayout()
        
        frame_file_layout = QHBoxLayout()
        self.frame_combo = QComboBox()
        self.frame_combo.setMinimumWidth(200)
        self.refresh_frames()
        
        self.btn_browse = QPushButton("📁 Tải ảnh lên...")
        self.btn_browse.setStyleSheet("padding: 5px; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;")
        self.btn_browse.clicked.connect(self.browse_external_frame)
        
        frame_file_layout.addWidget(self.frame_combo, stretch=1)
        frame_file_layout.addWidget(self.btn_browse)
        
        form_layout.addRow("1. Chọn File Khung (.png/.jpg):", frame_file_layout)

        # 2. Tên layout
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("valentine_march")
        form_layout.addRow("2. Tên Layout (Lưu ý: Không dấu, viết liền):", self.name_input)

        # 3. Kích thước khung
        size_layout = QHBoxLayout()
        self.width_input = QSpinBox()
        self.width_input.setRange(100, 10000)
        self.width_input.setValue(1800)
        self.height_input = QSpinBox()
        self.height_input.setRange(100, 10000)
        self.height_input.setValue(1200)
        
        size_layout.addWidget(QLabel("W:"))
        size_layout.addWidget(self.width_input)
        size_layout.addWidget(QLabel(" x H:"))
        size_layout.addWidget(self.height_input)
        form_layout.addRow("3. Kích thước khung gốc (px):", size_layout)

        main_layout.addLayout(form_layout)

        # 4. Tọa độ 4 góc (%)
        coord_layout = QFormLayout()
        coord_layout.addRow(QLabel("<b>4. Tọa độ vùng ảnh chèn (Phần trăm %):</b>"))
        
        def create_coord_inputs():
            layout = QHBoxLayout()
            x_spin = QDoubleSpinBox()
            x_spin.setRange(0, 100)
            x_spin.setDecimals(2)
            y_spin = QDoubleSpinBox()
            y_spin.setRange(0, 100)
            y_spin.setDecimals(2)
            layout.addWidget(QLabel("x (%):"))
            layout.addWidget(x_spin)
            layout.addWidget(QLabel("y (%):"))
            layout.addWidget(y_spin)
            return layout, x_spin, y_spin

        self.tl_layout, self.tl_x, self.tl_y = create_coord_inputs()
        coord_layout.addRow("- Top Left (Góc trên trái):", self.tl_layout)

        self.tr_layout, self.tr_x, self.tr_y = create_coord_inputs()
        coord_layout.addRow("- Top Right (Góc trên phải):", self.tr_layout)

        self.br_layout, self.br_x, self.br_y = create_coord_inputs()
        coord_layout.addRow("- Bottom Right (Góc dưới phải):", self.br_layout)

        self.bl_layout, self.bl_x, self.bl_y = create_coord_inputs()
        coord_layout.addRow("- Bottom Left (Góc dưới trái):", self.bl_layout)

        main_layout.addLayout(coord_layout)

        # Nút submit
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Lưu cấu hình")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_config)
        
        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setStyleSheet("padding: 10px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        main_layout.addLayout(btn_layout)
        
        # Tiền điền dữ liệu nếu đây là chế độ Edit
        if self.layout_data:
            self.prefill_data(self.layout_data)

    def prefill_data(self, data):
        self.name_input.setText(data["name"])
        self.name_input.setReadOnly(True)
        self.name_input.setStyleSheet("background-color: #e0e0e0; color: #555;")
        
        # Chọn đúng dòng chứa file path cũ
        frame_file = data.get("frame_file", "")
        index = self.frame_combo.findData(frame_file)
        if index >= 0:
            self.frame_combo.setCurrentIndex(index)
            
        self.width_input.setValue(data.get("frame_width", 1800))
        self.height_input.setValue(data.get("frame_height", 1200))
        
        pts = data.get("points", {})
        tl = pts.get("top_left", {})
        tr = pts.get("top_right", {})
        br = pts.get("bottom_right", {})
        bl = pts.get("bottom_left", {})
        
        self.tl_x.setValue(tl.get("x_percent", 0.0))
        self.tl_y.setValue(tl.get("y_percent", 0.0))
        
        self.tr_x.setValue(tr.get("x_percent", 0.0))
        self.tr_y.setValue(tr.get("y_percent", 0.0))
        
        self.br_x.setValue(br.get("x_percent", 0.0))
        self.br_y.setValue(br.get("y_percent", 0.0))
        
        self.bl_x.setValue(bl.get("x_percent", 0.0))
        self.bl_y.setValue(bl.get("y_percent", 0.0))

    def refresh_frames(self, select_path=None):
        self.frame_combo.clear()
        frames = self.layout_manager.get_available_frames()
        if not frames:
            self.frame_combo.addItem("Chưa có file nào trong thư mục 'frames/'")
            if hasattr(self, 'btn_save'):
                self.btn_save.setEnabled(False)
        else:
            for f in frames:
                self.frame_combo.addItem(os.path.basename(f), userData=f) # path
            if hasattr(self, 'btn_save'):
                self.btn_save.setEnabled(True)
                
            # Tự động chọn file vừa upload (nếu có)
            if select_path:
                index = self.frame_combo.findData(select_path)
                if index >= 0:
                    self.frame_combo.setCurrentIndex(index)

    def browse_external_frame(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Chọn file khung ảnh từ máy tính", 
            "", 
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            try:
                # Đảm bảo thư mục frames tồn tại
                self.layout_manager.ensure_directories()
                
                # Tạo đường dẫn đích trong folder frames/
                filename = os.path.basename(file_path)
                dest_path = os.path.join(self.layout_manager.frames_dir, filename).replace("\\", "/")
                
                # Nếu file chưa nằm trong folder frames/, thì copy vào
                if os.path.abspath(file_path) != os.path.abspath(dest_path):
                    # Check xem bị trùng tên ko
                    if os.path.exists(dest_path):
                        reply = QMessageBox.question(self, "Trùng file", 
                            f"File '{filename}' đã có sẵn trong hệ thống.\nBạn có muốn copy đè lên không?",
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if reply == QMessageBox.No:
                            return
                            
                    shutil.copy2(file_path, dest_path)
                    QMessageBox.information(self, "Thành công", f"Đã tải khung ảnh '{filename}' vào hệ thống!")
                
                # Refresh lại list và tự động focus vào file vừa lấy
                self.refresh_frames(select_path=dest_path)
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Copy File", f"Không thể copy ảnh vào thư mục frames/:\n{e}")

    def save_config(self):
        name = self.name_input.text().strip()
        frame_file = self.frame_combo.currentData()
        width = self.width_input.value()
        height = self.height_input.value()
        
        if not name:
            QMessageBox.warning(self, "Lỗi Input", "Tên layout không được để trống!")
            return
            
        points = {
            "top_left": {"x_percent": self.tl_x.value(), "y_percent": self.tl_y.value()},
            "top_right": {"x_percent": self.tr_x.value(), "y_percent": self.tr_y.value()},
            "bottom_right": {"x_percent": self.br_x.value(), "y_percent": self.br_y.value()},
            "bottom_left": {"x_percent": self.bl_x.value(), "y_percent": self.bl_y.value()}
        }

        # Kiểm tra trùng tên (Chỉ khi Thêm Mới)
        if not self.layout_data:
            existing = self.layout_manager.get_layout_by_name(name)
            if existing:
                reply = QMessageBox.question(self, "Trùng tên", 
                    f"Layout '{name}' đã tồn tại.\nBạn có muốn cập nhật (ghi đè) cấu hình này không?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

        success, msg = self.layout_manager.add_layout(name, frame_file, width, height, points)
        if success:
            QMessageBox.information(self, "Thành công", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Lỗi Lưu Cấu Hình", msg)
