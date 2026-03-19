import os
import shutil
import math
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QFormLayout, 
                             QDoubleSpinBox, QSpinBox, QMessageBox, QFileDialog,
                             QScrollArea, QWidget, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QBrush, QImage, QCursor
from frame_layout_manager import FrameLayoutManager

class ClickablePreviewLabel(QLabel):
    """Màn hình xem trước tương tác: Click để chọn tọa độ, có kính lúp."""
    coord_clicked = pyqtSignal(float, float) # Trả về tọa độ x,y hệ %
    rect_selected = pyqtSignal(float, float, float, float) # x, y, w, h hệ %
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Vui lòng chọn file khung để xem trước")
        self.setMouseTracking(True)
        self.pixmap_orig = None
        self.pixmap_scaled = None
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.current_slots = [] # Dữ liệu slots để vẽ overlay
        self.active_slot_idx = -1
        self.active_point_key = "" # "tl", "tr", "br", "bl"
        
        self.draw_mode = 0 # 0: Pick Point, 1: Draw Rect
        self.is_dragging = False
        self.drag_start = QPoint()
        self.drag_end = QPoint()
        
        # Biến phục vụ kính lúp
        self.mouse_pos = QPoint(-100, -100)
        self.show_magnifier = False

    def set_frame_image(self, path):
        if not path or not os.path.exists(path):
            self.pixmap_orig = None
            self.setText("Không tìm thấy file khung")
            self.update()
            return
            
        self.pixmap_orig = QPixmap(path)
        self.update_scaling()

    def update_scaling(self):
        if not self.pixmap_orig or self.width() <= 0: return
        
        self.pixmap_scaled = self.pixmap_orig.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.scale_factor = self.pixmap_scaled.width() / self.pixmap_orig.width()
        self.offset_x = (self.width() - self.pixmap_scaled.width()) // 2
        self.offset_y = (self.height() - self.pixmap_scaled.height()) // 2
        self.update()

    def resizeEvent(self, event):
        self.update_scaling()
        super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        if self.is_dragging:
            self.drag_end = event.pos()
            self.update()
            
        # Chỉ hiện kính lúp khi ở chế độ chấm điểm (mode 0) và chuột nằm trên vùng ảnh
        if self.pixmap_scaled and self.draw_mode == 0:
            rect = QRect(self.offset_x, self.offset_y, self.pixmap_scaled.width(), self.pixmap_scaled.height())
            self.show_magnifier = rect.contains(self.mouse_pos)
        else:
            self.show_magnifier = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap_scaled:
            if self.draw_mode == 1: # Draw Rect Mode
                self.is_dragging = True
                self.drag_start = event.pos()
                self.drag_end = event.pos()
            else: # Pick Point Mode
                lx = event.x() - self.offset_x
                ly = event.y() - self.offset_y
                
                if 0 <= lx <= self.pixmap_scaled.width() and 0 <= ly <= self.pixmap_scaled.height():
                    # Chuyển sang tọa độ % của ảnh gốc
                    x_pct = (lx / self.pixmap_scaled.width()) * 100.0
                    y_pct = (ly / self.pixmap_scaled.height()) * 100.0
                    self.coord_clicked.emit(x_pct, y_pct)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            
            # Tính toán Rect theo %
            x1 = min(self.drag_start.x(), self.drag_end.x()) - self.offset_x
            y1 = min(self.drag_start.y(), self.drag_end.y()) - self.offset_y
            x2 = max(self.drag_start.x(), self.drag_end.x()) - self.offset_x
            y2 = max(self.drag_start.y(), self.drag_end.y()) - self.offset_y
            
            # Clamp vào vùng ảnh
            x1 = max(0, min(x1, self.pixmap_scaled.width()))
            y1 = max(0, min(y1, self.pixmap_scaled.height()))
            x2 = max(0, min(x2, self.pixmap_scaled.width()))
            y2 = max(0, min(y2, self.pixmap_scaled.height()))
            
            if x2 - x1 > 5 and y2 - y1 > 5:
                # Chuyển sang tọa độ %
                x_pct = (x1 / self.pixmap_scaled.width()) * 100.0
                y_pct = (y1 / self.pixmap_scaled.height()) * 100.0
                w_pct = ((x2 - x1) / self.pixmap_scaled.width()) * 100.0
                h_pct = ((y2 - y1) / self.pixmap_scaled.height()) * 100.0
                self.rect_selected.emit(x_pct, y_pct, w_pct, h_pct)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if not self.pixmap_scaled:
            super().paintEvent(event) # Vẽ text placeholder nếu chưa có ảnh
            return
            
        # 0. Vẽ ảnh khung nền (Phần quan trọng bị thiếu trước đó)
        painter.drawPixmap(self.offset_x, self.offset_y, self.pixmap_scaled)
        
        # 1. Vẽ các slots hiện tại
        for idx, slot in enumerate(self.current_slots):
            pts = slot.get("points", {})
            try:
                poly = []
                for key in ["top_left", "top_right", "bottom_right", "bottom_left"]:
                    p = pts.get(key, {})
                    px = self.offset_x + (p.get("x_percent", 0) / 100.0 * self.pixmap_scaled.width())
                    py = self.offset_y + (p.get("y_percent", 0) / 100.0 * self.pixmap_scaled.height())
                    poly.append(QPoint(int(px), int(py)))
                
                is_active = (idx == self.active_slot_idx)
                
                # Vẽ vùng mờ
                painter.setPen(QPen(QColor(255, 171, 145), 2 if is_active else 1))
                color = QColor(255, 171, 145, 100) if is_active else QColor(200, 200, 200, 60)
                painter.setBrush(QBrush(color))
                from PyQt5.QtGui import QPolygon
                painter.drawPolygon(QPolygon(poly))
                
                # Vẽ các điểm chốt
                for key_map, pt_key in [("top_left", "tl"), ("top_right", "tr"), ("bottom_right", "br"), ("bottom_left", "bl")]:
                    p = pts.get(key_map, {})
                    px = self.offset_x + (p.get("x_percent", 0) / 100.0 * self.pixmap_scaled.width())
                    py = self.offset_y + (p.get("y_percent", 0) / 100.0 * self.pixmap_scaled.height())
                    
                    dot_color = QColor(0, 255, 12) if (is_active and pt_key == self.active_point_key) else QColor(255, 87, 34)
                    painter.setBrush(QBrush(dot_color))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(QPoint(int(px), int(py)), 5, 5)
            except: pass

        # 2. Vẽ Rect đang kéo
        if self.is_dragging:
            painter.setPen(QPen(QColor(0, 255, 12), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 255, 12, 40)))
            rect = QRect(self.drag_start, self.drag_end).normalized()
            painter.drawRect(rect)
            
        # 3. Vẽ Kính lúp (Magnifier)
        if self.show_magnifier:
            self.draw_magnifier(painter)

    def draw_magnifier(self, painter):
        mag_size = 150
        zoom = 4
        
        # Lấy vùng ảnh gốc tương ứng với vị trí chuột
        lx = (self.mouse_pos.x() - self.offset_x) / self.scale_factor
        ly = (self.mouse_pos.y() - self.offset_y) / self.scale_factor
        
        src_w = mag_size / zoom
        src_h = mag_size / zoom
        src_rect = QRect(int(lx - src_w/2), int(ly - src_h/2), int(src_w), int(src_h))
        
        # Cắt ảnh gốc
        zoomed_img = self.pixmap_orig.copy(src_rect).scaled(mag_size, mag_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Vẽ vòng tròn kính lúp
        painter.save()
        path = QPoint(self.mouse_pos.x(), self.mouse_pos.y() - 100) # Hiện bên trên chuột
        
        painter.setPen(QPen(QColor(0, 255, 12), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(path, mag_size//2, mag_size//2)
        
        from PyQt5.QtGui import QRegion
        painter.setClipRegion(QRegion(QRect(path.x() - mag_size//2, path.y() - mag_size//2, mag_size, mag_size), QRegion.Ellipse))
        painter.drawPixmap(path.x() - mag_size//2, path.y() - mag_size//2, zoomed_img)
        
        # Vẽ tâm kính lúp
        painter.setPen(QPen(QColor(255, 0, 0), 1))
        painter.drawLine(path.x() - 10, path.y(), path.x() + 10, path.y())
        painter.drawLine(path.x(), path.y() - 10, path.x(), path.y() + 10)
        painter.restore()

class FrameConfigDialog(QDialog):
    def __init__(self, parent=None, layout_data=None):
        super().__init__(parent)
        self.layout_data = layout_data
        self.setWindowTitle("Thiết lập Layout Ảnh (Trực quan)")
        self.resize(1400, 900) # To ra để xem preview
        
        self.layout_manager = FrameLayoutManager()
        self.slot_uis = []
        self.focused_widget = None # Spinbox đang được focus để nhận tọa độ click
        
        main_layout = QHBoxLayout(self)
        
        # --- LEFT SIDEBAR (Controls) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(400)
        sidebar_layout = QVBoxLayout(sidebar)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.form_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll)
        
        # 1. Cơ bản
        group_base = QFrame()
        vbox_b = QVBoxLayout(group_base)
        
        self.frame_combo = QComboBox()
        self.frame_combo.currentIndexChanged.connect(self.on_frame_changed)
        vbox_b.addWidget(QLabel("1. Chọn File Khung:"))
        
        row_f = QHBoxLayout()
        row_f.addWidget(self.frame_combo, stretch=1)
        self.btn_browse = QPushButton("📁")
        self.btn_browse.clicked.connect(self.browse_external_frame)
        row_f.addWidget(self.btn_browse)
        vbox_b.addLayout(row_f)
        
        self.name_input = QLineEdit()
        vbox_b.addWidget(QLabel("2. Tên Layout:"))
        vbox_b.addWidget(self.name_input)
        
        row_size = QHBoxLayout()
        self.width_input = QSpinBox()
        self.width_input.setRange(100, 10000)
        self.height_input = QSpinBox()
        self.height_input.setRange(100, 10000)
        row_size.addWidget(QLabel("W:"))
        row_size.addWidget(self.width_input)
        row_size.addWidget(QLabel("H:"))
        row_size.addWidget(self.height_input)
        vbox_b.addLayout(row_size)
        
        # Mode selector
        vbox_b.addWidget(QLabel("4. Chế độ chọn vùng:"))
        row_mode = QHBoxLayout()
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup
        self.mode_group = QButtonGroup(self)
        self.rb_point = QRadioButton("📍 Chấm 4 điểm")
        self.rb_rect = QRadioButton("🟦 Kéo thả HCN")
        self.rb_point.setChecked(True)
        self.mode_group.addButton(self.rb_point, 0)
        self.mode_group.addButton(self.rb_rect, 1)
        self.mode_group.buttonClicked[int].connect(self.on_mode_changed)
        row_mode.addWidget(self.rb_point)
        row_mode.addWidget(self.rb_rect)
        vbox_b.addLayout(row_mode)
        
        # Mode Instruction Note
        self.mode_note_label = QLabel("<i>Lưu ý: Click vào từng ô tọa độ rồi nhấn trên ảnh để lấy vị trí.</i>")
        self.mode_note_label.setWordWrap(True)
        self.mode_note_label.setStyleSheet("color: #666; font-size: 13px; padding: 5px; background: #f9f9f9; border-left: 3px solid #FFAB91;")
        vbox_b.addWidget(self.mode_note_label)
        
        self.form_layout.addWidget(group_base)
        
        # 2. Slots
        row_slot_count = QHBoxLayout()
        self.slot_count_combo = QComboBox()
        self.slot_count_combo.addItems(["1", "2", "3", "4", "6", "8"])
        self.slot_count_combo.currentIndexChanged.connect(self.on_slot_count_changed)
        row_slot_count.addWidget(QLabel("4. Số lượng vùng ảnh:"))
        row_slot_count.addWidget(self.slot_count_combo)
        self.form_layout.addLayout(row_slot_count)
        
        self.slots_container = QVBoxLayout()
        self.form_layout.addLayout(self.slots_container)
        self.form_layout.addStretch()
        
        # Nút lưu
        self.btn_save = QPushButton("💾 LƯU CẤU HÌNH")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; padding: 15px; font-weight: bold; font-size: 16px;")
        self.btn_save.clicked.connect(self.save_config)
        sidebar_layout.addWidget(self.btn_save)
        
        main_layout.addWidget(sidebar)
        
        # --- RIGHT PREVIEW ---
        self.preview = ClickablePreviewLabel()
        self.preview.setStyleSheet("background: #333; border-radius: 8px;")
        self.preview.coord_clicked.connect(self.on_preview_clicked)
        self.preview.rect_selected.connect(self.on_rect_selected)
        main_layout.addWidget(self.preview, stretch=1)
        
        # Khởi tạo data
        self.refresh_frames()
        if self.layout_data:
            self.prefill_data(self.layout_data)
        else:
            self.on_slot_count_changed(0)

    def _find_path_index(self, path):
        if not path: return -1
        # Chuẩn hóa path để so sánh (không phân biệt hoa thường và loại gạch chéo)
        norm_target = os.path.normpath(path).lower()
        for i in range(self.frame_combo.count()):
            data = self.frame_combo.itemData(i)
            if data and os.path.normpath(str(data)).lower() == norm_target:
                return i
        return -1

    def refresh_frames(self, select_path=None):
        self.frame_combo.blockSignals(True)
        self.frame_combo.clear()
        frames = self.layout_manager.get_available_frames()
        for f in frames:
            self.frame_combo.addItem(os.path.basename(f), userData=f)
        
        target_path = select_path
        idx = self._find_path_index(target_path)
        
        if idx >= 0:
            self.frame_combo.setCurrentIndex(idx)
        else:
            self.frame_combo.setCurrentIndex(0)
            
        self.frame_combo.blockSignals(False)
        self.on_frame_changed() # Cập nhật preview thủ công

    def on_frame_changed(self, index=0):
        path = self.frame_combo.currentData()
        self.preview.set_frame_image(path)
        # Tự động lấy size thực của ảnh
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self.width_input.setValue(pix.width())
            self.height_input.setValue(pix.height())

    def on_slot_count_changed(self, index=0):
        count = int(self.slot_count_combo.currentText())
        while self.slots_container.count():
            item = self.slots_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.slot_uis = []
        for i in range(count):
            ui = self.create_slot_ui(i + 1)
            self.slot_uis.append(ui)
            self.slots_container.addWidget(ui["group"])
        self.sync_preview_data()

    def create_slot_ui(self, num):
        from PyQt5.QtWidgets import QGroupBox
        group = QGroupBox(f"Slot {num}")
        layout = QFormLayout(group)
        
        def make_row(label, key):
            row = QHBoxLayout()
            x_spin = QDoubleSpinBox()
            x_spin.setRange(0, 100)
            x_spin.setDecimals(2)
            x_spin.installEventFilter(self) # Để bắt focus
            x_spin.setProperty("slot_idx", num-1)
            x_spin.setProperty("pt_key", key)
            x_spin.setProperty("coord", "x")
            
            y_spin = QDoubleSpinBox()
            y_spin.setRange(0, 100)
            y_spin.setDecimals(2)
            y_spin.installEventFilter(self)
            y_spin.setProperty("slot_idx", num-1)
            y_spin.setProperty("pt_key", key)
            y_spin.setProperty("coord", "y")
            
            x_spin.valueChanged.connect(self.sync_preview_data)
            y_spin.valueChanged.connect(self.sync_preview_data)
            
            row.addWidget(QLabel("x%:"))
            row.addWidget(x_spin)
            row.addWidget(QLabel("y%:"))
            row.addWidget(y_spin)
            layout.addRow(label, row)
            return (x_spin, y_spin)

        tl = make_row("Top Left", "tl")
        tr = make_row("Top Right", "tr")
        br = make_row("Bottom Right", "br")
        bl = make_row("Bottom Left", "bl")
        
        return {"group": group, "tl": tl, "tr": tr, "br": br, "bl": bl}

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.FocusIn:
            self.focused_widget = obj
            self.preview.active_slot_idx = obj.property("slot_idx")
            self.preview.active_point_key = obj.property("pt_key")
            self.preview.update()
        return super().eventFilter(obj, event)

    def on_mode_changed(self, mode_id):
        self.preview.draw_mode = mode_id
        if mode_id == 1:
            self.mode_note_label.setText("<i>Lưu ý: Nhấn giữ và kéo chuột trên ảnh để tạo khung vùng ảnh. Tọa độ 4 góc sẽ tự động được điền.</i>")
        else:
            self.mode_note_label.setText("<i>Lưu ý: Click vào từng ô tọa độ (x% / y%) rồi nhấn trên ảnh để lấy vị trí chính xác của điểm đó.</i>")
        self.preview.update()

    def on_rect_selected(self, x, y, w, h):
        # Nếu chưa focus vào slot nào, mặc định chọn slot 1
        idx = self.preview.active_slot_idx
        if idx < 0 and len(self.slot_uis) > 0:
            idx = 0
            
        if idx >= 0 and idx < len(self.slot_uis):
            ui = self.slot_uis[idx]
            # Tự động điền 4 góc dựa trên HCN
            ui["tl"][0].setValue(x)
            ui["tl"][1].setValue(y)
            ui["tr"][0].setValue(x + w)
            ui["tr"][1].setValue(y)
            ui["br"][0].setValue(x + w)
            ui["br"][1].setValue(y + h)
            ui["bl"][0].setValue(x)
            ui["bl"][1].setValue(y + h)
            self.sync_preview_data()

    def on_preview_clicked(self, x, y):
        if self.focused_widget:
            # Nếu đang focus vào X, điền X và nhảy sang Y
            if self.focused_widget.property("coord") == "x":
                self.focused_widget.setValue(x)
                # Tìm Y spinbox tương ứng để focus vào
                idx = self.focused_widget.property("slot_idx")
                key = self.focused_widget.property("pt_key")
                self.slot_uis[idx][key][1].setFocus()
            else:
                self.focused_widget.setValue(y)
        self.sync_preview_data()

    def sync_preview_data(self):
        # Xuất data từ UI sang dạng json để preview vẽ
        slots = []
        for ui in self.slot_uis:
            slots.append({
                "points": {
                    "top_left": {"x_percent": ui["tl"][0].value(), "y_percent": ui["tl"][1].value()},
                    "top_right": {"x_percent": ui["tr"][0].value(), "y_percent": ui["tr"][1].value()},
                    "bottom_right": {"x_percent": ui["br"][0].value(), "y_percent": ui["br"][1].value()},
                    "bottom_left": {"x_percent": ui["bl"][0].value(), "y_percent": ui["bl"][1].value()}
                }
            })
        self.preview.current_slots = slots
        self.preview.update()

    def prefill_data(self, data):
        self.name_input.setText(data["name"])
        self.name_input.setReadOnly(True)
        self.name_input.setStyleSheet("background-color: #eee;")
        
        path = data.get("frame_file", "")
        idx = self._find_path_index(path)
        if idx >= 0: 
            self.frame_combo.blockSignals(True)
            self.frame_combo.setCurrentIndex(idx)
            self.frame_combo.blockSignals(False)
            self.on_frame_changed()
        
        self.width_input.setValue(data.get("frame_width", 1800))
        self.height_input.setValue(data.get("frame_height", 1200))
        
        slots = data.get("slots", [])
        self.slot_count_combo.setCurrentText(str(len(slots)))
        self.on_slot_count_changed()
        
        for i, s_data in enumerate(slots):
            if i >= len(self.slot_uis): break
            pts = s_data["points"]
            ui = self.slot_uis[i]
            ui["tl"][0].setValue(pts["top_left"]["x_percent"])
            ui["tl"][1].setValue(pts["top_left"]["y_percent"])
            ui["tr"][0].setValue(pts["top_right"]["x_percent"])
            ui["tr"][1].setValue(pts["top_right"]["y_percent"])
            ui["br"][0].setValue(pts["bottom_right"]["x_percent"])
            ui["br"][1].setValue(pts["bottom_right"]["y_percent"])
            ui["bl"][0].setValue(pts["bottom_left"]["x_percent"])
            ui["bl"][1].setValue(pts["bottom_left"]["y_percent"])

    def browse_external_frame(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file khung", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            dest = os.path.join(self.layout_manager.frames_dir, os.path.basename(path)).replace("\\", "/")
            if not os.path.exists(dest):
                shutil.copy2(path, dest)
            self.refresh_frames(select_path=dest)

    def save_config(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên Layout")
            return
            
        slots = []
        for ui in self.slot_uis:
            slots.append({
                "points": {
                    "top_left": {"x_percent": ui["tl"][0].value(), "y_percent": ui["tl"][1].value()},
                    "top_right": {"x_percent": ui["tr"][0].value(), "y_percent": ui["tr"][1].value()},
                    "bottom_right": {"x_percent": ui["br"][0].value(), "y_percent": ui["br"][1].value()},
                    "bottom_left": {"x_percent": ui["bl"][0].value(), "y_percent": ui["bl"][1].value()}
                }
            })
            
        success, msg = self.layout_manager.add_layout(
            name, self.frame_combo.currentData(),
            self.width_input.value(), self.height_input.value(),
            slots
        )
        if success:
            QMessageBox.information(self, "Thành công", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Lỗi", msg)
