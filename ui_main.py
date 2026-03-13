import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QFrame, QComboBox, 
                             QSizePolicy, QGridLayout, QTabWidget, QTabBar,
                             QSlider, QCheckBox, QGraphicsDropShadowEffect,
                             QStackedWidget, QLineEdit, QListWidget, QListWidgetItem,
                             QListView)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect, QSize
from PyQt5.QtGui import QPixmap, QFont, QImage, QPainter, QPen, QColor, QIcon
from styles import *

class ImagePreviewLabel(QLabel):
    """Custom Label để hiển thị ảnh preview giữ đúng tỉ lệ khi resize cửa sổ"""
    clicked_pos = pyqtSignal(int, int) # Signal phát ra tọa độ x,y khi user click
    zoom_in_signal = pyqtSignal()
    zoom_out_signal = pyqtSignal()

    def __init__(self, placeholder="Chưa có ảnh📸"):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText(placeholder)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(400, 300)
        self.pixmap_img = None
        
        # Biến phục vụ vẽ focus box
        self.focus_rect = None
        self.focus_timer = QTimer(self)
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self.clear_focus_box)
        
        self._setup_overlay_ui()

    def _setup_overlay_ui(self):
        overlay_layout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(10, 10, 10, 5)
        overlay_layout.addStretch()
        
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(45, 45)
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(self.zoom_in_signal.emit)
        
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(45, 45)
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.clicked.connect(self.zoom_out_signal.emit)
        
        zoom_style = """
            QPushButton {
                background-color: rgba(0, 0, 0, 60%);
                color: white;
                font-weight: bold;
                font-size: 24px;
                border-radius: 22px;
                border: 2px solid rgba(255, 255, 255, 50%);
            }
            QPushButton:hover { background-color: rgba(255, 153, 51, 80%); }
            QPushButton:pressed { background-color: rgba(211, 84, 0, 90%); }
        """
        self.btn_zoom_in.setStyleSheet(zoom_style)
        self.btn_zoom_out.setStyleSheet(zoom_style)
        
        bottom_row.addWidget(self.btn_zoom_out)
        bottom_row.addWidget(self.btn_zoom_in)
        overlay_layout.addLayout(bottom_row)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.x()
            y = event.y()
            self.show_focus_box(x, y)
            self.clicked_pos.emit(x, y)
        super().mousePressEvent(event)

    def show_focus_box(self, x, y):
        box_size = 80
        self.focus_rect = QRect(int(x - box_size/2), int(y - box_size/2), box_size, box_size)
        self.update()
        self.focus_timer.start(1500)
        
    def clear_focus_box(self):
        self.focus_rect = None
        self.update()

    def set_image(self, image_path):
        if not image_path or not os.path.exists(image_path):
            self.clear_image()
            return
        self.pixmap_img = QPixmap(image_path)
        self.update_preview()

    def set_opencv_image(self, qt_image):
        self.pixmap_img = QPixmap.fromImage(qt_image)
        self.update_preview()

    def clear_image(self):
        self.pixmap_img = None
        self.clear()
        self.setText("Chưa có ảnh📸")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview()

    def update_preview(self):
        if self.pixmap_img and not self.pixmap_img.isNull():
            scaled = self.pixmap_img.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            super().setPixmap(scaled)
            
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.focus_rect:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(255, 215, 0))
            pen.setWidth(3)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.focus_rect)
            painter.end()

class ModernFrame(QFrame):
    def __init__(self, style_str=None):
        super().__init__()
        if style_str:
            self.setStyleSheet(style_str)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)

class PhotoboothUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photobooth Station Pro")
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        
        # UI Styling
        self.setStyleSheet(GLOBAL_STYLE)
        
        # Screen size and position
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        self.resize(int(screen.width() * 0.9), int(screen.height() * 0.9))
        
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Screens
        self.station_screen = QWidget()
        self.gallery_screen = QWidget()
        
        self.central_widget.addWidget(self.station_screen)
        self.central_widget.addWidget(self.gallery_screen)
        
        self._setup_station_ui()
        self._setup_gallery_ui()
        
    def _setup_station_ui(self):
        layout = QVBoxLayout(self.station_screen)
        layout.setContentsMargins(40, 20, 40, 40)
        layout.setSpacing(20)
        
        # --- HEADER ---
        header = QHBoxLayout()
        self.logo_label = QLabel("🍑 PHOTOBOOTH STATION")
        self.logo_label.setStyleSheet(STYLE_STATION_HEADER)
        header.addWidget(self.logo_label)
        header.addStretch()
        
        self.btn_admin_setup = QPushButton("⚙️ Admin Setup")
        self.btn_admin_setup.setStyleSheet(STYLE_ADMIN_GHOST_BTN)
        self.btn_admin_setup.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.btn_admin_setup)
        layout.addLayout(header)
        
        # --- MAIN AREA (75/25) ---
        main_area = QHBoxLayout()
        main_area.setSpacing(30)
        layout.addLayout(main_area, stretch=1)
        
        # LEFT: Preview (75%)
        self.preview_container = ModernFrame(STYLE_PREVIEW_CONTAINER)
        preview_vbox = QVBoxLayout(self.preview_container)
        preview_vbox.setContentsMargins(0, 0, 0, 0)
        
        preview_grid = QGridLayout()
        preview_vbox.addLayout(preview_grid)
        
        self.preview_label = ImagePreviewLabel("Khung hình sẵn sàng 📸")
        preview_grid.addWidget(self.preview_label, 0, 0)
        
        self.countdown_label = QLabel("")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setFont(QFont("Segoe UI", 120, QFont.Bold))
        self.countdown_label.setStyleSheet("color: white; background-color: rgba(255, 171, 145, 180); border-radius: 40px; padding: 20px;")
        self.countdown_label.setFixedSize(300, 300)
        self.countdown_label.hide()
        preview_grid.addWidget(self.countdown_label, 0, 0, Qt.AlignCenter)
        
        main_area.addWidget(self.preview_container, stretch=3)
        
        # RIGHT: Sidebar (25%)
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(10, 20, 10, 20)
        sidebar.setSpacing(15) # Gần nhau hơn
        main_area.addLayout(sidebar, stretch=1)
        
        # Thêm stretch ở trên để đẩy content vào giữa
        sidebar.addStretch()
        
        # Block 1: Phiên chụp
        block_session = QFrame()
        block_session.setStyleSheet(STYLE_SIDEBAR_BLOCK)
        vbox_s = QVBoxLayout(block_session)
        vbox_s.setContentsMargins(15, 15, 15, 15)
        
        lbl_s = QLabel("PHIÊN CHỤP / TÊN KHÁCH")
        lbl_s.setStyleSheet("font-weight: bold; color: #555;")
        vbox_s.addWidget(lbl_s)
        
        row_s = QHBoxLayout()
        self.session_selector = QComboBox()
        self.session_selector.setFixedHeight(50) # To hơn
        row_s.addWidget(self.session_selector, stretch=1)
        
        self.btn_session_add = QPushButton("➕")
        self.btn_session_add.setFixedSize(50, 50) # To hơn
        self.btn_session_add.setStyleSheet(STYLE_ADMIN_GHOST_BTN + "font-size: 22px; padding: 0;")
        self.btn_session_add.setToolTip("Thêm khách mới")
        row_s.addWidget(self.btn_session_add)
        
        vbox_s.addLayout(row_s)
        
        row_s_tools = QHBoxLayout()
        row_s_tools.setSpacing(10)
        self.btn_session_rename = QPushButton("✏️ Đổi tên")
        self.btn_session_rename.setStyleSheet(STYLE_ADMIN_GHOST_BTN)
        self.btn_session_rename.setFixedHeight(45) # Tăng height lên đáng kể
        row_s_tools.addWidget(self.btn_session_rename)
        
        self.btn_session_delete = QPushButton("🗑️ Xóa")
        self.btn_session_delete.setStyleSheet(STYLE_ADMIN_GHOST_BTN + "color: #e57373;")
        self.btn_session_delete.setFixedHeight(45) # Tăng height
        row_s_tools.addWidget(self.btn_session_delete)
        
        self.btn_copy_session_path = QPushButton("📋 Path") # Rút ngắn text để đỡ chật
        self.btn_copy_session_path.setStyleSheet(STYLE_ADMIN_GHOST_BTN)
        self.btn_copy_session_path.setFixedHeight(45) # Tăng height
        row_s_tools.addWidget(self.btn_copy_session_path)
        
        vbox_s.addLayout(row_s_tools)
        sidebar.addWidget(block_session)
        
        # Block 2: Camera
        block_cam = QFrame()
        block_cam.setStyleSheet(STYLE_SIDEBAR_BLOCK)
        vbox_c = QVBoxLayout(block_cam)
        vbox_c.setContentsMargins(15, 15, 15, 15)
        
        lbl_c = QLabel("MÁY ẢNH ĐANG DÙNG")
        lbl_c.setStyleSheet("font-weight: bold; color: #555;")
        vbox_c.addWidget(lbl_c)
        
        cam_row = QHBoxLayout()
        self.camera_selector = QComboBox()
        self.camera_selector.setFixedHeight(50)
        self.camera_selector.addItem("Đang quét máy ảnh...")
        cam_row.addWidget(self.camera_selector, stretch=1)
        
        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setStyleSheet(STYLE_SECONDARY_BTN)
        self.btn_connect.setFixedSize(100, 50) # To hơn
        cam_row.addWidget(self.btn_connect)
        vbox_c.addLayout(cam_row)
        sidebar.addWidget(block_cam)
        
        # Block 3: Primary Action
        block_capture = QFrame()
        block_capture.setStyleSheet(STYLE_SIDEBAR_BLOCK)
        vbox_cap = QVBoxLayout(block_capture)
        vbox_cap.setContentsMargins(15, 15, 15, 15)
        
        self.btn_capture = QPushButton("📸 CHỤP ẢNH")
        self.btn_capture.setStyleSheet(STYLE_PRIMARY_BTN)
        self.btn_capture.setCursor(Qt.PointingHandCursor)
        self.btn_capture.setFixedHeight(100)
        vbox_cap.addWidget(self.btn_capture)
        
        vbox_cap.addSpacing(10)
        
        lbl_countdown = QLabel("THỜI GIAN CHỜ CHỤP")
        lbl_countdown.setStyleSheet("font-size: 14px; font-weight: bold; color: #555;")
        vbox_cap.addWidget(lbl_countdown)
        
        self.countdown_selector = QComboBox()
        self.countdown_selector.addItems(["📸 Chụp ngay", "⏳ 1s", "⏳ 3s", "⏳ 5s", "⏳ 10s"])
        self.countdown_selector.setCurrentIndex(0) # Đưa chụp ngay làm default
        self.countdown_selector.setFixedHeight(50)
        self.countdown_selector.setStyleSheet("font-size: 20px;")
        vbox_cap.addWidget(self.countdown_selector)
        
        sidebar.addWidget(block_capture)
        
        # Block 4: Secondary Action
        self.btn_to_gallery = QPushButton("🖼️ THƯ VIỆN & RAW")
        self.btn_to_gallery.setStyleSheet(STYLE_SECONDARY_BTN)
        self.btn_to_gallery.setCursor(Qt.PointingHandCursor)
        self.btn_to_gallery.setFixedHeight(60)
        sidebar.addWidget(self.btn_to_gallery)
        
        sidebar.addStretch()
        
        footer = QHBoxLayout()
        self.status_msg = QLabel("Hệ thống đã sẵn sàng.")
        self.status_msg.setStyleSheet("color: #757575; font-size: 18px;")
        footer.addWidget(self.status_msg)
        
        footer.addStretch()
        self.status_dot = QPushButton("🟢 System OK")
        self.status_dot.setStyleSheet("border: none; color: #4CAF50; font-weight: bold; font-size: 18px; background: transparent;")
        self.status_dot.setCursor(Qt.PointingHandCursor)
        footer.addWidget(self.status_dot)
        layout.addLayout(footer)

    def _setup_gallery_ui(self):
        layout = QVBoxLayout(self.gallery_screen)
        layout.setContentsMargins(40, 20, 40, 40)
        layout.setSpacing(20)
        
        # --- HEADER ---
        header = QHBoxLayout()
        self.btn_back_to_station = QPushButton("⬅️ Trở về Trạm Chụp")
        self.btn_back_to_station.setStyleSheet(STYLE_SECONDARY_BTN)
        header.addWidget(self.btn_back_to_station)
        
        header.addSpacing(20)
        self.gallery_title = QLabel("THƯ VIỆN & XỬ LÝ ẢNH")
        self.gallery_title.setStyleSheet(STYLE_STATION_HEADER)
        header.addWidget(self.gallery_title)
        
        header.addStretch()
        self.current_session_label = QLabel("Phiên: Khach_Mac_Dinh")
        self.current_session_label.setStyleSheet("color: #757575; font-size: 22px; font-weight: bold;")
        header.addWidget(self.current_session_label)
        layout.addLayout(header)
        
        # --- MAIN AREA (75/25) ---
        main_area = QHBoxLayout()
        main_area.setSpacing(30)
        layout.addLayout(main_area, stretch=1)
        
        # LEFT: Image Preview & Toolbar
        preview_vbox = QVBoxLayout()
        
        self.gallery_preview_container = ModernFrame(STYLE_PREVIEW_CONTAINER)
        gp_layout = QVBoxLayout(self.gallery_preview_container)
        gp_layout.setContentsMargins(0, 0, 0, 0)
        
        self.gallery_preview_label = ImagePreviewLabel("Chưa chọn ảnh📸")
        gp_layout.addWidget(self.gallery_preview_label)
        preview_vbox.addWidget(self.gallery_preview_container, stretch=1)
        
        # New: Horizontal Frame Selector
        self.frame_list = QListWidget()
        self.frame_list.setViewMode(QListView.IconMode)
        self.frame_list.setFlow(QListView.LeftToRight)
        self.frame_list.setMovement(QListView.Static)
        self.frame_list.setSpacing(10)
        self.frame_list.setFixedHeight(180) # Cao gấp rưỡi (120 * 1.5)
        self.frame_list.setIconSize(QSize(210, 140)) # Tỉ lệ 3:2 to hơn
        self.frame_list.setStyleSheet(STYLE_FRAME_SELECTOR)
        self.frame_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frame_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        preview_vbox.addWidget(self.frame_list)
        
        # BOTTOM TOOLBAR
        toolbar_container = QFrame()
        toolbar_container.setStyleSheet(f"background: white; border: 1px solid {COLOR_BORDER}; border-radius: 12px; padding: 10px;")
        toolbar = QHBoxLayout(toolbar_container)
        
        # Group 1: Color (LUT)
        vbox_lut = QVBoxLayout()
        lbl_lut = QLabel("MÀU SẮC (LUT)")
        lbl_lut.setStyleSheet("font-weight: bold; font-size: 18px; color: #444;")
        vbox_lut.addWidget(lbl_lut)
        row_lut = QHBoxLayout()
        self.lut_selector = QComboBox()
        self.lut_selector.setMinimumWidth(200)
        row_lut.addWidget(self.lut_selector)
        
        self.btn_add_lut = QPushButton("➕")
        self.btn_add_lut.setFixedSize(40, 40)
        self.btn_add_lut.setStyleSheet(STYLE_ADMIN_GHOST_BTN + "font-size: 20px; padding: 0;")
        self.btn_add_lut.setToolTip("Thêm mẫu màu (.cube, .xmp)")
        row_lut.addWidget(self.btn_add_lut)
        
        self.btn_apply_lut = QPushButton("✨ Áp màu")
        self.btn_apply_lut.setStyleSheet(STYLE_SECONDARY_BTN + "padding: 5px 15px; font-size: 18px;")
        row_lut.addWidget(self.btn_apply_lut)
        
        self.btn_delete_lut = QPushButton("✕")
        self.btn_delete_lut.setFixedSize(30, 30)
        self.btn_delete_lut.setStyleSheet("color: #757575; border: none; font-size: 20px;")
        row_lut.addWidget(self.btn_delete_lut)
        vbox_lut.addLayout(row_lut)
        toolbar.addLayout(vbox_lut)
        
        toolbar.addSpacing(20)
        
        # Group 2: Sharpen
        vbox_sharp = QVBoxLayout()
        lbl_sharp = QLabel("ĐỘ NÉT")
        lbl_sharp.setStyleSheet("font-weight: bold; font-size: 18px; color: #444;")
        vbox_sharp.addWidget(lbl_sharp)
        row_sharp = QHBoxLayout()
        self.sharpen_selector = QComboBox()
        self.sharpen_selector.addItems(["Tắt (Gốc)", "Thấp", "Vừa (Nên dùng)", "Cao"])
        row_sharp.addWidget(self.sharpen_selector)
        self.btn_apply_sharpen = QPushButton("Làm Nét")
        self.btn_apply_sharpen.setStyleSheet(STYLE_SECONDARY_BTN + "padding: 5px 15px; font-size: 18px;")
        row_sharp.addWidget(self.btn_apply_sharpen)
        vbox_sharp.addLayout(row_sharp)
        toolbar.addLayout(vbox_sharp)
        
        toolbar.addSpacing(20)
        
        toolbar.addStretch()
        
        # Group 4: Export (Important)
        self.btn_print = QPushButton("🖨 IN ẢNH")
        self.btn_print.setStyleSheet(STYLE_PRIMARY_BTN + "font-size: 24px; padding: 10px 30px;")
        toolbar.addWidget(self.btn_print)
        
        self.btn_save = QPushButton("💾 Lưu Mới")
        self.btn_save.setStyleSheet(STYLE_SECONDARY_BTN + "padding: 10px 20px;")
        toolbar.addWidget(self.btn_save)
        
        toolbar.addSpacing(20)
        
        preview_vbox.addWidget(toolbar_container)
        main_area.addLayout(preview_vbox, stretch=5) # Sử dụng số nguyên (5:2 thay vì 3:1.2)
        
        # RIGHT: Gallery Sidebar (nới rộng ra để đủ 2 cột)
        sidebar_vbox = QVBoxLayout()
        main_area.addLayout(sidebar_vbox, stretch=2)
        
        # Gallery Header: 2 hàng (2x2 grid)
        gallery_header_grid = QGridLayout()
        gallery_header_grid.setSpacing(5)
        
        self.btn_import_raw = QPushButton("⬇️ Nhập ảnh")
        self.btn_import_raw.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 15px; padding: 5px;")
        gallery_header_grid.addWidget(self.btn_import_raw, 0, 0)
        
        self.btn_refresh_gallery = QPushButton("🔄 Làm mới")
        self.btn_refresh_gallery.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 15px; padding: 5px;")
        gallery_header_grid.addWidget(self.btn_refresh_gallery, 0, 1)
        
        self.btn_delete_selected = QPushButton("🗑️ Xóa")
        self.btn_delete_selected.setEnabled(False) # Disable by default
        self.btn_delete_selected.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 15px; padding: 5px; color: #e57373;")
        gallery_header_grid.addWidget(self.btn_delete_selected, 1, 0)
        
        self.btn_delete_all = QPushButton("🧨 Xóa Hết")
        self.btn_delete_all.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 15px; padding: 5px; color: #ff5252;")
        gallery_header_grid.addWidget(self.btn_delete_all, 1, 1)
        
        sidebar_vbox.addLayout(gallery_header_grid)
        
        self.btn_gallery_capture = QPushButton("📸 CHỤP ẢNH (C1)")
        self.btn_gallery_capture.setStyleSheet(STYLE_PRIMARY_BTN + "font-size: 20px; height: 60px; margin-top: 5px;")
        self.btn_gallery_capture.setCursor(Qt.PointingHandCursor)
        sidebar_vbox.addWidget(self.btn_gallery_capture)
        
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setStyleSheet(STYLE_THUMBNAIL_LIST)
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(180, 180)) # To hơn để tận dụng chiều rộng (cũ 120)
        self.thumbnail_list.setSpacing(12)
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setSelectionMode(QListWidget.ExtendedSelection)
        sidebar_vbox.addWidget(self.thumbnail_list)
        
        main_area.addLayout(sidebar_vbox, stretch=1)

    def log(self, message):
        self.status_msg.setText(message)
        print(f"» {message}")
