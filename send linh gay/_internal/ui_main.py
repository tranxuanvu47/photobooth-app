from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QFrame, QComboBox, 
                             QSizePolicy, QGridLayout, QTabWidget, QTabBar,
                             QSlider, QCheckBox, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt5.QtGui import QPixmap, QFont, QImage, QPainter, QPen, QColor

class ImagePreviewLabel(QLabel):
    """Custom Label để hiển thị ảnh preview giữ đúng tỉ lệ khi resize cửa sổ"""
    clicked_pos = pyqtSignal(int, int) # Signal phát ra tọa độ x,y khi user click
    zoom_in_signal = pyqtSignal()
    zoom_out_signal = pyqtSignal()

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
        self.setText("Chưa có ảnh📸")
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
        # Tạo layout lơ lửng bên trên màn hình preview
        overlay_layout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(10, 10, 10, 5) # Giảm lề dưới để nút sát mép hơn
        
        # Đẩy nội dung xuống góc dưới bên phải
        overlay_layout.addStretch()
        
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        
        # Nút Zoom +
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(45, 45)
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(self.zoom_in_signal.emit)
        
        # Nút Zoom -
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
        # Tạo khung kích thước 80x80 quay quanh điểm click
        box_size = 80
        self.focus_rect = QRect(int(x - box_size/2), int(y - box_size/2), box_size, box_size)
        self.update() # Gọi paintEvent
        
        # 1.5s sau tự xóa
        self.focus_timer.start(1500)
        
    def clear_focus_box(self):
        self.focus_rect = None
        self.update()

    def set_image(self, image_path):
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
        super().paintEvent(event) # Vẽ ảnh setPixmap bình thường
        
        # Vẽ chồng ô vuông focus màu vàng
        if self.focus_rect:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            pen = QPen(QColor(255, 215, 0)) # Vàng Gold
            pen.setWidth(3)
            pen.setStyle(Qt.DashLine) # Nét đứt
            painter.setPen(pen)
            
            painter.drawRect(self.focus_rect)
            painter.end()

class PhotoboothUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Photobooth App")
        
        # Bật các nút Minimize / Maximize / Close cho Dialog
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        
        # Lấy kích thước màn hình
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        
        # Mở app chiếm 80% màn hình thay vì toàn màn hình để tránh đen viền
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        self.show()
        
        self.setStyleSheet("background-color: #fffaf0; color: #5c4033; font-family: 'Segoe UI';")
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        # --- LEFT PANEL (PREVIEW & COUNTDOWN) ---
        self.left_layout = QVBoxLayout()
        self.main_layout.addLayout(self.left_layout, stretch=4)
        
        self.title_label = QLabel("✨ PHOTOBOOTH STATION ✨")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 42, QFont.Bold))
        self.title_label.setStyleSheet("color: #e67e22; margin-bottom: 20px; letter-spacing: 2px;")
        self.left_layout.addWidget(self.title_label)
        
        # Overlay Layout để nhét Countdown lên trên Preview
        self.preview_container = QWidget()
        self.preview_layout = QGridLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_label = ImagePreviewLabel()
        self.preview_layout.addWidget(self.preview_label, 0, 0)
        
        # Countdown hiển thị đè lên chính giữa Preview
        self.countdown_label = QLabel("")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setFont(QFont("Segoe UI", 130, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #fff; background-color: rgba(255, 153, 102, 180); padding: 30px; border-radius: 40px;")
        self.countdown_label.hide()
        self.preview_layout.addWidget(self.countdown_label, 0, 0, Qt.AlignCenter)
        
        self.left_layout.addWidget(self.preview_container, stretch=1)
        
        # --- RIGHT PANEL (CONTROLS & TABS) ---
        self.right_layout = QVBoxLayout()
        self.main_layout.addLayout(self.right_layout, stretch=1)
        
        # Tabs Container
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 2px solid #ffcc99; border-radius: 8px; background: white; }
            QTabBar::tab { background: #ffe6cc; color: #d35400; padding: 10px 20px; margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background: #ff9955; color: white; }
        """)
        
        self.tab_photobooth = QWidget()
        self.tab_admin = QWidget()
        
        self.tabs.addTab(self.tab_photobooth, "📸 Photobooth")
        self.tabs.addTab(self.tab_admin, "⚙️ Admin Setup")
        
        self.right_layout.addWidget(self.tabs)
        
        # --- TAB 1: PHOTOBOOTH ---
        self.pb_layout = QVBoxLayout(self.tab_photobooth)
        
        # --- SESSION/USER MANAGEMENT ---
        session_group = QWidget()
        session_vbox = QVBoxLayout(session_group)
        session_vbox.setContentsMargins(0, 0, 0, 10)
        
        session_label = QLabel("Khách chụp (Session):")
        session_label.setStyleSheet("color: #2980b9; font-weight: bold; font-size: 16px;")
        session_vbox.addWidget(session_label)
        
        session_toolbar = QHBoxLayout()
        self.session_selector = QComboBox()
        self.session_selector.setFont(QFont("Segoe UI", 12))
        self.session_selector.setStyleSheet("""
            QComboBox { background-color: #fff; color: #2c3e50; border: 2px solid #3498db; padding: 6px; border-radius: 5px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #fff; color: #2c3e50; selection-background-color: #ebf5fb; }
        """)
        session_toolbar.addWidget(self.session_selector, stretch=1)
        
        # New Session Action Dropdown to replace buttons
        self.session_action_selector = QComboBox()
        self.session_action_selector.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.session_action_selector.setStyleSheet("""
            QComboBox { 
                background-color: #eaf2f8; 
                color: #21618c; 
                border: 2px solid #3498db; 
                padding: 6px; 
                border-radius: 5px; 
            }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #fff; color: #2c3e50; selection-background-color: #d4e6f1; }
        """)
        self.session_action_selector.addItems([
            "--- Thao tác ---", 
            "📋 Copy Đường Dẫn", 
            "➕ Khách Mới", 
            "✏️ Đổi Tên", 
            "🗑 Xóa"
        ])
        session_toolbar.addWidget(self.session_action_selector)
        
        session_vbox.addLayout(session_toolbar)
        self.pb_layout.addWidget(session_group)
        
        # --- CAMERA CONFIG ---
        cam_label = QLabel("Chọn Camera:")
        cam_label.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 18px;")
        self.pb_layout.addWidget(cam_label)
        
        cam_toolbar = QHBoxLayout()
        
        self.camera_selector = QComboBox()
        self.camera_selector.setFont(QFont("Segoe UI", 12))
        self.camera_selector.setStyleSheet("""
            QComboBox { background-color: #fff; color: #d35400; border: 2px solid #ffb380; padding: 8px; border-radius: 5px; margin-bottom: 5px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #fff; color: #d35400; selection-background-color: #ffe6cc; }
        """)
        self.camera_selector.addItem("Tìm kiếm máy ảnh...")
        cam_toolbar.addWidget(self.camera_selector, stretch=1)
        
        self.btn_connect = self.create_button("🔌 Kết Nối", "#ffd1b3", "#ffb380", "#d35400", padding="10px")
        self.btn_connect.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        cam_toolbar.addWidget(self.btn_connect)
        
        self.pb_layout.addLayout(cam_toolbar)
        
        capture_layout = QHBoxLayout()
        self.btn_capture = self.create_button("📸 Chụp Ảnh", "#ffb380", "#ff9955", "white", padding="10px")
        
        self.countdown_selector = QComboBox()
        self.countdown_selector.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.countdown_selector.setStyleSheet("""
            QComboBox { 
                background-color: #ff9966; 
                color: white; 
                border: 2px solid #fff; 
                padding: 10px; 
                border-radius: 8px;
            }
            QComboBox::drop-down { border: 0px; }
            QComboBox::down-arrow { image: none; border: 0px; }
            QComboBox QAbstractItemView { background-color: #ff9966; color: white; selection-background-color: #ff7733; }
        """)
        self.countdown_selector.addItems(["📸 Chụp ngay", "⏳ 1s", "⏳ 3s", "⏳ 5s", "⏳ 10s"])
        self.countdown_selector.setCurrentIndex(2) # Mặc định 3s
        
        capture_layout.addWidget(self.btn_capture, stretch=3)
        capture_layout.addWidget(self.countdown_selector, stretch=1)
        self.pb_layout.addLayout(capture_layout)

        self.btn_gallery = self.create_button("🖼 Thư Viện Ảnh Lịch Sử", "#ffc299", "#ffa366", "white", padding="10px")
        for btn in [self.btn_gallery]:
            self.pb_layout.addWidget(btn)
            
        self.pb_layout.addStretch()
            
        # --- TAB 2: ADMIN SETUP ---
        self.admin_layout = QVBoxLayout(self.tab_admin)
        
        # Thêm Layout Mới Button
        self.btn_add_layout = self.create_button("➕ Thêm Layout Cấu Hình", "#ffebcc", "#ffc266", "#d35400", padding="14px")
        self.admin_layout.addWidget(self.btn_add_layout)
        
        self.admin_layout.addSpacing(20)
        
        # Sửa Layout Cũ Combobox & Button
        edit_label = QLabel("Quản Lý Layout Hiện Có:")
        edit_label.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 14px;")
        self.admin_layout.addWidget(edit_label)
        
        self.admin_layout_selector = QComboBox()
        self.admin_layout_selector.setFont(QFont("Segoe UI", 12))
        self.admin_layout_selector.setStyleSheet(self.camera_selector.styleSheet())
        self.admin_layout_selector.addItem("Chọn layout cần sửa...")
        self.admin_layout.addWidget(self.admin_layout_selector)
        
        self.btn_edit_layout = self.create_button("✏️ Chỉnh Sửa Layout Này", "#f2e6d9", "#e6ccb3", "#d35400", padding="14px")
        self.admin_layout.addWidget(self.btn_edit_layout)
        
        self.admin_layout.addStretch()
        
        self.right_layout.addSpacing(10)
        
        # STATUS / LOG AREA
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 11))
        self.log_area.setStyleSheet("""
            background-color: #fff; 
            color: #d35400; 
            border: 2px solid #ffcc99; 
            border-radius: 10px; 
            padding: 12px;
        """)
        self.right_layout.addWidget(self.log_area)

    def create_button(self, text, color, hover_color, text_color="white", padding="16px"):
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {color}; 
                color: {text_color}; 
                border-radius: 8px; 
                padding: {padding}; 
                margin-bottom: 4px;
                border: 2px solid #fff;
            }}
            QPushButton:hover {{ 
                background-color: {hover_color}; 
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{ 
                background-color: #f2e6d9; 
                color: #b3a296; 
                border: 2px solid #e6d9cc;
            }}
        """)
        return btn

    def log(self, message):
        self.log_area.append(f"» {message}")
        # Tự cuộn xuống dưới cùng
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
