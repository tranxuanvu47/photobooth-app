import os
import math
import time
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QGridLayout, QScrollArea, QListWidget, 
                             QListWidgetItem, QAbstractItemView, QGraphicsDropShadowEffect, 
                             QProgressBar, QStyledItemDelegate, QStyle, QTextEdit, QComboBox, 
                             QSizePolicy, QTabWidget, QTabBar, QSlider, QCheckBox, 
                             QStackedWidget, QLineEdit, QListView, QDialog, QApplication, QShortcut)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPoint, QRect, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QPixmap, QFont, QImage, QPainter, QPen, QColor, QIcon, QTransform, QMovie, QKeySequence
from styles import *

class NoSelectionDelegate(QStyledItemDelegate):
    """Delegate để triệt tiêu hoàn toàn khung chọn (focus rect) và highlight mặc định của QListWidget."""
    def paint(self, painter, option, index):
        # Đảm bảo state không chứa Selected hoặc HasFocus trước khi gọi super
        option.state &= ~QStyle.State_Selected
        option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, index)

class LoadingOverlay(QWidget):
    """Overlay hiển thị hiệu ứng loading mờ đè lên giao diện."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False) # Chặn click vào bên dưới
        self.setObjectName("loadingOverlay")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)
        
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 70%);
                border-radius: 20px;
                padding: 40px;
            }}
        """)
        c_layout = QVBoxLayout(container)
        
        self.spinner = QLabel("✨")
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setStyleSheet("font-size: 60px; color: white;")
        
        self.label = QLabel("Đang xử lý...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 24px; font-weight: bold; margin-top: 20px;")
        
        c_layout.addWidget(self.spinner)
        c_layout.addWidget(self.label)
        self.layout.addWidget(container)
        
        self.setStyleSheet("#loadingOverlay { background-color: rgba(255, 255, 255, 30%); }")
        self.hide()

    def set_message(self, text):
        self.label.setText(text)

    def resizeToParent(self):
        if self.parent():
            self.resize(self.parent().size())
            self.raise_()
class LogViewerDialog(QDialog):
    """Hộp thoại hiển thị lịch sử Log của ứng dụng."""
    def __init__(self, parent=None, logs=None):
        super().__init__(parent)
        self.setWindowTitle("Nhật ký hệ thống (Logs) 📜")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 12))
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        # Format logs
        if logs:
            self.log_area.setPlainText("\n".join(logs))
        else:
            self.log_area.setPlainText("Chưa có nhật ký nào.")
            
        layout.addWidget(self.log_area)
        
        # Nút đóng and Clear
        btn_layout = QHBoxLayout()
        self.btn_close = QPushButton("Đóng")
        self.btn_close.setStyleSheet(STYLE_SECONDARY_BTN)
        self.btn_close.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)
        
        # Scroll to bottom
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

class CaptureReviewDialog(QDialog):
    """Hộp thoại xem lại ảnh ngay sau khi chụp."""
    def __init__(self, parent=None, pixmap=None, current_idx=1, total=1):
        super().__init__(parent)
        self.setWindowTitle("Xem lại ảnh vừa chụp")
        
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        # Phình to dialog ra (tầm 80% chiều cao và 60% chiều rộng màn hình)
        # để đảm bảo phần preview ảnh chiếm được ít nhất 50% diện tích nhìn thấy
        self.setFixedSize(int(screen.width() * 0.6), int(screen.height() * 0.8))
        self.setModal(True)
        # Bỏ khung viền mặc định để làm modern UI nếu muốn, nhưng ở đây tạm để standard modal
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        title_lbl = QLabel(f"ẢNH THỨ {current_idx} / {total}")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        if pixmap:
            # Scale ảnh to ra cho vừa khung mới (trừ đi khoảng lề và nút bấm)
            pw, ph = self.width() - 80, self.height() - 170
            scaled_pix = pixmap.scaled(pw, ph, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled_pix)
        else:
            self.img_label.setText("Không thể tải ảnh")
        
        # Border cho ảnh
        self.img_label.setStyleSheet("border: 2px solid #ddd; border-radius: 8px; background: #f9f9f9;")
        layout.addWidget(self.img_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        
        self.btn_retake = QPushButton("📸 Chụp lại tấm này")
        self.btn_retake.setStyleSheet("""
            QPushButton {
                background-color: #f44336; color: white; padding: 15px; 
                font-size: 18px; font-weight: bold; border-radius: 10px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.btn_retake.setCursor(Qt.PointingHandCursor)
        self.btn_retake.clicked.connect(lambda: self.done(QDialog.Rejected))
        
        self.btn_next = QPushButton("✅ Tiếp tục" if current_idx < total else "🎯 Hoàn thành")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; padding: 15px; 
                font-size: 18px; font-weight: bold; border-radius: 10px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_retake, stretch=1)
        btn_layout.addWidget(self.btn_next, stretch=1)
        layout.addLayout(btn_layout)

class ThumbnailWidget(QWidget):
    """Widget cho mỗi item trong hàng đợi ảnh RAW, có nút X để xóa khỏi khung."""
    remove_signal = pyqtSignal(str) # Phát ra path khi bấm X
    click_signal = pyqtSignal(str)  # Phát ra path khi bấm vào ảnh
    
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.setObjectName("thumbWidget")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True) # Cho phép QWidget vẽ bộ máy Style
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20) # Tăng lề để nút X có chỗ đứng, không bị clipping
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedSize(170, 170)
        self.img_label.setStyleSheet("""
            background-color: #f0f0f0; 
            border-radius: 4px;
            border: none;
        """)
        pix = QPixmap(path).scaled(170, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_label.setPixmap(pix)
        self.layout.addWidget(self.img_label)
        
        # Nút X xóa khỏi khung (Đưa ra tuyệt đối ở ngoài)
        self.btn_remove = QPushButton("✕", self)
        self.btn_remove.setFixedSize(30, 30)
        self.btn_remove.setCursor(Qt.PointingHandCursor)
        self.btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #ff5252;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 15px;
                border: 2px solid white;
            }
            QPushButton:hover { background-color: #ff1744; }
        """)
        self.btn_remove.move(175, 5) # Vị trí mới để không bị ẩn 1 phần
        self.btn_remove.raise_() # Đảm bảo luôn nằm trên cùng
        self.btn_remove.hide()
        self.btn_remove.clicked.connect(lambda: self.remove_signal.emit(self.path))
        
        # Style mặc định: Không viền
        self.setStyleSheet("""
            #thumbWidget {
                border-radius: 8px;
                background: transparent;
                border: none;
            }
        """)

    def set_in_frame(self, in_frame):
        if in_frame:
            self.btn_remove.show()
            self.btn_remove.raise_() # Nổi lên trên khung viền
            self.setStyleSheet("""
                #thumbWidget {
                    border: 4px solid #FFAB91;
                    border-radius: 8px;
                    background: rgba(255, 171, 145, 10%);
                }
            """)
        else:
            self.btn_remove.hide()
            self.setStyleSheet("""
                #thumbWidget {
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                }
            """)

    def mousePressEvent(self, event):
        self.click_signal.emit(self.path)
        super().mousePressEvent(event)

class ImagePreviewLabel(QLabel):
    """Custom Label để hiển thị ảnh preview giữ đúng tỉ lệ khi resize cửa sổ"""
    clicked_pos = pyqtSignal(int, int) # Signal phát ra tọa độ x,y khi user click
    zoom_in_signal = pyqtSignal()
    zoom_out_signal = pyqtSignal()

    def __init__(self, placeholder="Chưa có ảnh📸", interactive=True):
        super().__init__()
        self.interactive = interactive
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
        self.overlay_layout = QVBoxLayout(self)
        self.overlay_layout.setContentsMargins(10, 10, 10, 10)
        
        self.top_layout = QVBoxLayout()
        self.top_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
        self.overlay_layout.addLayout(self.top_layout)
        
        self.overlay_layout.addStretch()
        
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        self.overlay_layout.addLayout(self.bottom_layout)
        
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
        
        self.bottom_layout.addWidget(self.btn_zoom_out)
        self.bottom_layout.addWidget(self.btn_zoom_in)
        
        if not self.interactive:
            self.btn_zoom_in.hide()
            self.btn_zoom_out.hide()

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

    def deselect_all_icons(self, exclude=None):
        for icon in self.findChildren(IconWidget):
            if icon != exclude:
                icon.set_selected(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Chỉ deselect nếu click vào vùng trống của label (không trúng icon nào)
            # childAt trả về widget con sâu nhất tại vị trí đó
            child = self.childAt(event.pos())
            is_icon_click = False
            if child:
                # Kiểm tra xem child có phải là IconWidget hoặc con của IconWidget không
                parent = child
                while parent:
                    if isinstance(parent, IconWidget):
                        is_icon_click = True
                        break
                    parent = parent.parent()
            
            if not is_icon_click:
                self.deselect_all_icons()
            
            if self.interactive:
                x = event.x()
                y = event.y()
                self.show_focus_box(x, y)
                self.clicked_pos.emit(x, y)
                
        super().mousePressEvent(event)

    def clear_all_icons(self):
        for icon in self.findChildren(IconWidget):
            icon.close()

    def get_icons_data(self):
        """Trả về dữ liệu icon để ImageProcessor dùng cho render cao nhất."""
        data = []
        pw, ph = self.width(), self.height()
        if pw == 0 or ph == 0: return []
        
        for icon in self.findChildren(IconWidget):
            # Tính toán vị trí và kích thước tương đối (%) trên preview label
            data.append({
                'path': icon.icon_path,
                'x_percent': icon.x() / pw * 100,
                'y_percent': icon.y() / ph * 100,
                'w_percent': icon.width() / pw * 100,
                'h_percent': icon.height() / ph * 100,
                'rotation': icon.rotation
            })
        return data

class IconWidget(QFrame):
    """Widget đại diện cho một icon có thể di chuyển, phóng to/thu nhỏ, xoay trên ảnh."""
    deleted = pyqtSignal(object)
    
    def __init__(self, parent, icon_path, size=150):
        super().__init__(parent)
        self.icon_path = icon_path
        self.orig_pixmap = QPixmap(icon_path)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground)
        
        self.rotation = 0.0 # Độ xoay (degrees)
        self.is_selected = False
        
        # UI Elements
        self.label = QLabel(self)
        self.label.setScaledContents(True)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.update_pixmap()
        
        self.btn_delete = QPushButton("✕", self)
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setStyleSheet("background: #ff5252; color: white; border-radius: 12px; font-weight: bold; border: none;")
        self.btn_delete.clicked.connect(self.request_delete)
        self.btn_delete.hide()
        
        # Sizing handle (Bottom Right)
        self.size_handle = QFrame(self)
        self.size_handle.setFixedSize(16, 16)
        self.size_handle.setStyleSheet("background: #FFAB91; border-radius: 8px; border: 2px solid white;")
        self.size_handle.setCursor(Qt.SizeFDiagCursor)
        self.size_handle.hide()

        # Rotation handle (Top Center)
        self.rot_handle = QFrame(self)
        self.rot_handle.setFixedSize(16, 16)
        self.rot_handle.setStyleSheet("background: #4CAF50; border-radius: 8px; border: 2px solid white;")
        self.rot_handle.setCursor(Qt.PointingHandCursor)
        self.rot_handle.hide()

        self.mouse_pressed = False
        self.mode = "" # 'move', 'resize', 'rotate'
        self.drag_start_pos = QPoint()
        self.resize_start_size = None
        self.rotate_start_angle = 0.0
        
        self.update_handles()
        self.set_selected(True)
        
        # Center in parent
        if parent:
            pw, ph = parent.width(), parent.height()
            self.move((pw - self.width()) // 2, (ph - self.height()) // 2)
            
        self.show()
        self.raise_()

    def update_pixmap(self):
        if self.orig_pixmap.isNull():
            print(f"DEBUG: Pixmap is NULL for {self.icon_path}")
            return
            
        # Tạo pixmap xoay để preview
        if self.rotation == 0:
            self.label.setPixmap(self.orig_pixmap)
        else:
            transform = QTransform().rotate(self.rotation)
            rotated = self.orig_pixmap.transformed(transform, Qt.SmoothTransformation)
            self.label.setPixmap(rotated)
        
        self.label.show()
        # Center the label in the widget
        margin = 20
        self.label.setGeometry(margin, margin, self.width()-2*margin, self.height()-2*margin)

    def update_handles(self):
        w, h = self.width(), self.height()
        self.btn_delete.move(w-26, 2)
        self.size_handle.move(w-18, h-18)
        self.rot_handle.move(w//2 - 8, 2)

    def set_selected(self, selected):
        self.is_selected = selected
        if selected:
            self.setStyleSheet("QFrame { border: 2px dashed #FFAB91; background: transparent; }")
            self.btn_delete.show()
            self.size_handle.show()
            self.rot_handle.show()
        else:
            self.setStyleSheet("QFrame { border: none; background: transparent; }")
            self.btn_delete.hide()
            self.size_handle.hide()
            self.rot_handle.hide()

    def request_delete(self):
        self.deleted.emit(self)
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.size_handle.geometry().contains(event.pos()):
                self.mode = 'resize'
                self.resize_start_size = self.size()
            elif self.rot_handle.geometry().contains(event.pos()):
                self.mode = 'rotate'
                center = self.rect().center()
                delta = event.pos() - center
                self.rotate_start_angle = math.degrees(math.atan2(delta.y(), delta.x())) - self.rotation
            else:
                self.mode = 'move'
                
            self.mouse_pressed = True
            self.drag_start_pos = event.globalPos()
            self.raise_()
            if hasattr(self.parent(), "deselect_all_icons"):
                self.parent().deselect_all_icons(exclude=self)
            
            event.accept() # Chặn không cho lan truyền lên cha (ImagePreviewLabel)
            return # Tránh gọi super()
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mouse_pressed:
            curr_global_pos = event.globalPos()
            
            if self.mode == 'resize':
                diff = curr_global_pos - self.drag_start_pos
                new_w = max(50, self.resize_start_size.width() + diff.x())
                new_h = max(50, self.resize_start_size.height() + diff.y())
                self.setFixedSize(new_w, new_h)
                self.update_pixmap()
                self.update_handles()
            elif self.mode == 'rotate':
                center = self.rect().center()
                delta = event.pos() - center
                current_angle = math.degrees(math.atan2(delta.y(), delta.x()))
                self.rotation = current_angle - self.rotate_start_angle
                self.update_pixmap()
            elif self.mode == 'move':
                diff = curr_global_pos - self.drag_start_pos
                new_pos = self.pos() + diff
                pw, ph = self.parent().width(), self.parent().height()
                nx = max(-self.width()//2, min(new_pos.x(), pw - self.width()//2))
                ny = max(-self.height()//2, min(new_pos.y(), ph - self.height()//2))
                self.move(nx, ny)
                self.drag_start_pos = curr_global_pos
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.mouse_pressed = False
        self.mode = ""
        super().mouseReleaseEvent(event)

class IconSelectionDialog(QDialog):
    """Dialog hiển thị thư viện icon được phân loại theo Style."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = None
        self.setWindowTitle("Thư viện Icon Trang trí")
        self.setFixedSize(800, 600)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        # Header
        header = QLabel("🎨 Chọn Icon để trang trí")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(header)
        
        # Tabs for categories
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E0E0E0; border-radius: 8px; background: white; }
            QTabBar::tab { background: #F5F5F5; padding: 10px 20px; margin-right: 5px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-size: 16px; }
            QTabBar::tab:selected { background: white; border: 1px solid #E0E0E0; border-bottom: none; font-weight: bold; color: #FFAB91; }
        """)
        
        self.categories = {
            "Modern Color": "color",
            "Soft Pastel": "pastel",
            "Hand Doodle": "doodle",
            "Sweet Cute": "cute"
        }
        
        for label, folder in self.categories.items():
            tab = QWidget()
            vbox = QVBoxLayout(tab)
            list_widget = QListWidget()
            list_widget.setViewMode(QListWidget.IconMode)
            list_widget.setIconSize(QSize(120, 120))
            list_widget.setResizeMode(QListWidget.Adjust)
            list_widget.setSpacing(15)
            list_widget.setMovement(QListWidget.Static)
            list_widget.setStyleSheet(STYLE_FRAME_SELECTOR) # Reuse existing style
            
            # Load icons
            path = os.path.join("assets", "icons", folder)
            if os.path.exists(path):
                files = [f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.ico'))]
                for f in files:
                    full_path = os.path.abspath(os.path.join(path, f))
                    item = QListWidgetItem(QIcon(full_path), "")
                    item.setData(Qt.UserRole, full_path)
                    item.setSizeHint(QSize(140, 140))
                    list_widget.addItem(item)
            
            list_widget.itemClicked.connect(self.on_item_clicked)
            vbox.addWidget(list_widget)
            self.tabs.addTab(tab, label)
            
        self.layout.addWidget(self.tabs)
        
        # Cancel Button
        self.btn_cancel = QPushButton("Đóng")
        self.btn_cancel.setStyleSheet(STYLE_SECONDARY_BTN)
        self.btn_cancel.clicked.connect(self.reject)
        self.layout.addWidget(self.btn_cancel, 0, Qt.AlignRight)

    def on_item_clicked(self, item):
        self.selected_path = item.data(Qt.UserRole)
        self.accept()

class NextcloudConfigDialog(QDialog):
    """Hộp thoại cấu hình Nextcloud (URL, Account, Root Folder)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cấu hình Nextcloud ☁️")
        self.setFixedSize(600, 560)
        import config
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        header = QLabel("☁️ Cài đặt Nextcloud")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #1976D2;")
        layout.addWidget(header)
        
        # Form
        form = QGridLayout()
        form.setSpacing(10)
        
        self.cb_enabled = QCheckBox("Kích hoạt Upload Nextcloud")
        self.cb_enabled.setChecked(config.NC_ENABLED)
        self.cb_enabled.setStyleSheet("font-size: 16px; font-weight: bold;")
        form.addWidget(self.cb_enabled, 0, 0, 1, 2)
        
        form.addWidget(QLabel("WebDAV URL:"), 1, 0)
        self.txt_url = QLineEdit(config.NC_URL)
        form.addWidget(self.txt_url, 1, 1)
        
        form.addWidget(QLabel("Username:"), 2, 0)
        self.txt_user = QLineEdit(config.NC_USER)
        form.addWidget(self.txt_user, 2, 1)
        
        form.addWidget(QLabel("App Password:"), 3, 0)
        self.txt_pass = QLineEdit(config.NC_PASS)
        self.txt_pass.setEchoMode(QLineEdit.Password)
        form.addWidget(self.txt_pass, 3, 1)
        
        form.addWidget(QLabel("Thư mục gốc:"), 4, 0)
        self.txt_root = QLineEdit(config.NC_REMOTE_PATH)
        self.txt_root.setPlaceholderText("Mặc định: Photobooth")
        form.addWidget(self.txt_root, 4, 1)
        
        form.addWidget(QLabel("Public Share URL:"), 5, 0)
        self.txt_share_url = QLineEdit(config.NC_SHARE_URL)
        self.txt_share_url.setPlaceholderText("Link chia sẻ công khai...")
        form.addWidget(self.txt_share_url, 5, 1)
        
        self.btn_auto_share = QPushButton("🪄 Tự động lấy Link chia sẻ")
        self.btn_auto_share.setStyleSheet(STYLE_ADMIN_GHOST_BTN + "background-color: #E3F2FD; color: #1976D2;")
        form.addWidget(self.btn_auto_share, 6, 1)
        
        layout.addLayout(form)
        
        tip = QLabel("💡 Thư mục khách hàng sẽ được tạo bên trong thư mục gốc này.")
        tip.setStyleSheet("color: #666; font-style: italic;")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Lưu cấu hình")
        self.btn_save.setStyleSheet(STYLE_PRIMARY_BTN)
        self.btn_save.clicked.connect(self.save_and_close)
        
        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setStyleSheet(STYLE_SECONDARY_BTN)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def save_and_close(self):
        import config
        config.NC_ENABLED = self.cb_enabled.isChecked()
        config.NC_URL = self.txt_url.text().strip()
        config.NC_USER = self.txt_user.text().strip()
        config.NC_PASS = self.txt_pass.text().strip()
        root = self.txt_root.text().strip()
        config.NC_REMOTE_PATH = root if root else "Photobooth"
        config.NC_SHARE_URL = self.txt_share_url.text().strip()
        config.save_config()
        self.accept()

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
    admin_requested = pyqtSignal()
    full_screen_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photobooth Station Pro")
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        
        # UI Styling
        self.setStyleSheet(GLOBAL_STYLE)
        
        # Screen size and position
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry() # availableGeometry trừ thanh taskbar
        self.resize(int(screen.width() * 0.9), int(screen.height() * 0.9))
        
        # Căn giữa cửa sổ chính
        qr = self.frameGeometry()
        cp = screen.center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
        # Setup Global Shortcuts
        self.shortcut_admin = QShortcut(QKeySequence("Ctrl+7"), self)
        self.shortcut_admin.activated.connect(self.admin_requested.emit)
        
        self.shortcut_fullscreen = QShortcut(QKeySequence("Alt+Return"), self)
        self.shortcut_fullscreen.activated.connect(self.full_screen_requested.emit)
        
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Screens
        self.station_screen = QWidget()
        self.gallery_screen = QWidget()
        
        self.central_widget.addWidget(self.station_screen)
        self.central_widget.addWidget(self.gallery_screen)
        
        self._setup_station_ui()
        self._setup_gallery_ui()
        
        # Loading Overlay
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()
        
        # Log buffer for viewing
        self.log_buffer = []
        
        # --- LOG BUTTON (Global - Floating at Bottom Right) ---
        self.btn_show_log = QPushButton("📜 Xem Log", self)
        self.btn_show_log.setFixedSize(120, 40)
        self.btn_show_log.setCursor(Qt.PointingHandCursor)
        self.btn_show_log.setStyleSheet("""
            QPushButton {
                background-color: rgba(33, 33, 33, 60%);
                color: white;
                font-weight: bold;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 20%);
            }
            QPushButton:hover { background-color: rgba(33, 33, 33, 90%); }
        """)
        self.btn_show_log.raise_()

    def show_loading(self, message="Đang xử lý..."):
        self.loading_overlay.resizeToParent()
        self.loading_overlay.set_message(message)
        self.loading_overlay.show()
        # Ép vẽ ngay lập tức lên màn hình
        self.loading_overlay.repaint()
        QApplication.processEvents()
        QApplication.processEvents()

    def hide_loading(self):
        self.loading_overlay.hide()        
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
        self.btn_admin_setup.hide() # Ẩn nút theo yêu cầu
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
        self.preview_label = ImagePreviewLabel("Máy ảnh đang khởi động...🎥")
        self.preview_label.setStyleSheet("background-color: #000; border-radius: 12px;")
        
        # Capture progress overlay (Top Left)
        self.capture_progress_label = QLabel(self.preview_label)
        self.capture_progress_label.setText("1 / 1")
        self.capture_progress_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 150);
            color: white;
            font-size: 32px;
            font-weight: bold;
            padding: 10px 20px;
            border-bottom-right-radius: 10px;
        """)
        self.capture_progress_label.move(0, 0)
        self.capture_progress_label.hide()
        
        preview_vbox.addWidget(self.preview_label, stretch=1)
        
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
        
        # --- QR CODE BLOCK (Top of Sidebar) ---
        self.qr_container = ModernFrame() # Dùng ModernFrame để có shadow
        self.qr_container.setStyleSheet(STYLE_SIDEBAR_BLOCK + "padding: 5px;")
        # Vô hiệu hóa hand cursor và tooltip để ẩn tính năng nhấn vào
        
        qr_vbox = QVBoxLayout(self.qr_container)
        qr_vbox.setContentsMargins(10, 10, 10, 10)
        qr_vbox.setSpacing(5)
        
        lbl_qr_title = QLabel("📲 QUÉT ĐỂ NHẬN ẢNH")
        lbl_qr_title.setAlignment(Qt.AlignCenter)
        lbl_qr_title.setStyleSheet("font-weight: bold; color: #E91E63; font-size: 14px;")
        qr_vbox.addWidget(lbl_qr_title)
        
        self.qr_code_label = QLabel()
        self.qr_code_label.setFixedSize(220, 220)
        self.qr_code_label.setScaledContents(True)
        self.qr_code_label.setAlignment(Qt.AlignCenter)
        self.qr_code_label.setStyleSheet("background-color: white; border: 1px dashed #ddd; border-radius: 8px; color: #888; font-size: 16px;")
        qr_vbox.addWidget(self.qr_code_label, 0, Qt.AlignCenter)
        
        lbl_qr_hint = QLabel("Nhấn vào để cài đặt Link 🔗")
        lbl_qr_hint.setAlignment(Qt.AlignCenter)
        lbl_qr_hint.setStyleSheet("color: #999; font-size: 11px; font-style: italic;")
        qr_vbox.addWidget(lbl_qr_hint)
        
        sidebar.addWidget(self.qr_container)
        
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
        self.session_selector.setCursor(Qt.PointingHandCursor)
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
        
        self.btn_session_rename.setCursor(Qt.PointingHandCursor)
        self.btn_session_delete.setCursor(Qt.PointingHandCursor)
        self.btn_copy_session_path.setCursor(Qt.PointingHandCursor)
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
        
        vbox_c.addLayout(cam_row)
        self.camera_selector.setCursor(Qt.PointingHandCursor)
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
        
        # Container cho "Thời gian chờ" để có thể ẩn/hiện theo Mode
        self.timer_container = QWidget()
        timer_layout = QVBoxLayout(self.timer_container)
        timer_layout.setContentsMargins(0, 0, 0, 0)
        timer_layout.setSpacing(10)
        
        lbl_countdown = QLabel("THỜI GIAN CHỜ CHỤP")
        lbl_countdown.setStyleSheet("font-size: 14px; font-weight: bold; color: #555;")
        timer_layout.addWidget(lbl_countdown)
        
        self.countdown_selector = QComboBox()
        self.countdown_selector.addItems(["📸 Chụp ngay", "⏳ 1s", "⏳ 3s", "⏳ 5s", "⏳ 10s"])
        self.countdown_selector.setCurrentIndex(0)
        self.countdown_selector.setFixedHeight(50)
        self.countdown_selector.setStyleSheet("font-size: 20px;")
        self.countdown_selector.setCursor(Qt.PointingHandCursor)
        timer_layout.addWidget(self.countdown_selector)
        
        vbox_cap.addWidget(self.timer_container)

        vbox_cap.addSpacing(10)
        
        # Container cho "Số lượng hình chụp" để có thể ẩn/hiện theo Mode
        self.num_captures_container = QWidget()
        num_caps_layout = QVBoxLayout(self.num_captures_container)
        num_caps_layout.setContentsMargins(0, 0, 0, 0)
        num_caps_layout.setSpacing(10)
        
        lbl_num_caps = QLabel("SỐ LƯỢNG HÌNH CHỤP")
        lbl_num_caps.setStyleSheet("font-size: 14px; font-weight: bold; color: #555;")
        num_caps_layout.addWidget(lbl_num_caps)
        
        self.num_captures_selector = QComboBox()
        self.num_captures_selector.addItems(["1 hình", "2 hình", "4 hình", "6 hình", "8 hình"])
        self.num_captures_selector.setCurrentIndex(0)
        self.num_captures_selector.setFixedHeight(50)
        self.num_captures_selector.setStyleSheet("font-size: 20px;")
        self.num_captures_selector.setCursor(Qt.PointingHandCursor)
        num_caps_layout.addWidget(self.num_captures_selector)
        
        vbox_cap.addWidget(self.num_captures_container)
        
        sidebar.addWidget(block_capture)
        
        # Block 4: Secondary Action
        self.btn_to_gallery = QPushButton("🖼️ THƯ VIỆN & RAW")
        self.btn_to_gallery.setStyleSheet(STYLE_SECONDARY_BTN)
        self.btn_to_gallery.setCursor(Qt.PointingHandCursor)
        self.btn_to_gallery.setFixedHeight(60)
        sidebar.addWidget(self.btn_to_gallery)
        
        sidebar.addStretch()
        
        footer = QHBoxLayout()
        footer.addStretch()
        
        self.status_dot = QPushButton("🟢 System Ready")
        self.status_dot.setStyleSheet("border: none; color: #4CAF50; font-weight: bold; font-size: 18px; background: transparent;")
        self.status_dot.setCursor(Qt.PointingHandCursor)
        footer.addWidget(self.status_dot)
        layout.addLayout(footer)

    def _setup_gallery_ui(self):
        """
        Giao diện Thư viện & Xử lý ảnh - Thiết kế Modern / Minimalist.
        Bố cục: Top Bar (tabs + search) → 2 cột chính (Left: frame selector | Right: ảnh + nút)
        """
        # Đặt object name để áp CSS gradient lên đúng widget
        self.gallery_screen.setObjectName("galleryScreen")
        self.gallery_screen.setStyleSheet(STYLE_GALLERY_SCREEN)

        root_layout = QVBoxLayout(self.gallery_screen)
        root_layout.setContentsMargins(16, 12, 16, 16)
        root_layout.setSpacing(10)

        # ════════════════════════════════════════════════════
        # TOP BAR: Logo pill + Category tabs + Search bar
        # ════════════════════════════════════════════════════
        top_bar_frame = QFrame()
        top_bar_frame.setObjectName("topBarContainer")
        top_bar_frame.setStyleSheet(STYLE_TOPBAR_CONTAINER)
        top_bar_frame.setFixedHeight(50)

        shadow_top = QGraphicsDropShadowEffect()
        shadow_top.setBlurRadius(18)
        shadow_top.setXOffset(0)
        shadow_top.setYOffset(4)
        shadow_top.setColor(QColor(255, 171, 145, 60))
        top_bar_frame.setGraphicsEffect(shadow_top)

        top_bar_layout = QHBoxLayout(top_bar_frame)
        top_bar_layout.setContentsMargins(12, 4, 12, 4)
        top_bar_layout.setSpacing(6)

        # Logo / brand mark (nhỏ gọn)
        lbl_brand = QLabel("🍑")
        lbl_brand.setStyleSheet("font-size: 22px; background: transparent; border: none;")
        top_bar_layout.addWidget(lbl_brand)
        top_bar_layout.addSpacing(4)

        # Category tab buttons
        self._tab_buttons = []
        tab_defs = [
            (":: Classic", "classic"),
            ("⊙ Vintage", "vintage"),
            ("🔥 Trendy", "trendy"),
            ("😊 Cute & Fun", "cute"),
        ]
        self._active_tab = "classic"

        for label_text, tab_id in tab_defs:
            btn = QPushButton(label_text)
            btn.setCheckable(False)
            btn.setCursor(Qt.PointingHandCursor)
            # Active tab mặc định là đầu tiên
            if tab_id == self._active_tab:
                btn.setStyleSheet(STYLE_TAB_BTN_ACTIVE)
            else:
                btn.setStyleSheet(STYLE_TAB_BTN_INACTIVE)
            btn.setProperty("tab_id", tab_id)
            btn.clicked.connect(lambda checked, tid=tab_id, b=btn: self._on_tab_clicked(tid, b))
            top_bar_layout.addWidget(btn)
            self._tab_buttons.append(btn)

        top_bar_layout.addSpacing(8)

        # Search bar
        self.gallery_search_bar = QLineEdit()
        self.gallery_search_bar.setPlaceholderText("🔍   Tìm kiếm khung...")
        self.gallery_search_bar.setStyleSheet(STYLE_SEARCH_BAR)
        self.gallery_search_bar.setFixedWidth(220)
        self.gallery_search_bar.setFixedHeight(34)
        top_bar_layout.addWidget(self.gallery_search_bar)

        top_bar_layout.addStretch()

        # Session label (nhỏ bên phải)
        self.current_session_label = QLabel("Phiên: Khach_Mac_Dinh")
        self.current_session_label.setStyleSheet(
            "color: #AAAAAA; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        top_bar_layout.addWidget(self.current_session_label)

        root_layout.addWidget(top_bar_frame)

        # ════════════════════════════════════════════════════
        # MAIN AREA: 2 cột (Left = frame selector | Right = photo library)
        # ════════════════════════════════════════════════════
        main_row = QHBoxLayout()
        main_row.setSpacing(12)
        root_layout.addLayout(main_row, stretch=1)

        # ─────────────── CỘT TRÁI: Frame Selector ───────────────
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setStyleSheet(STYLE_LEFT_PANEL)

        shadow_left = QGraphicsDropShadowEffect()
        shadow_left.setBlurRadius(22)
        shadow_left.setXOffset(0)
        shadow_left.setYOffset(5)
        shadow_left.setColor(QColor(255, 171, 145, 45))
        left_panel.setGraphicsEffect(shadow_left)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        # ── Banner preview (dải ngang hiển thị ảnh đã chọn) ──
        self.gallery_preview_container = QFrame()
        self.gallery_preview_container.setObjectName("frameBanner")
        self.gallery_preview_container.setStyleSheet(STYLE_FRAME_BANNER)
        self.gallery_preview_container.setFixedHeight(170)

        banner_layout = QVBoxLayout(self.gallery_preview_container)
        banner_layout.setContentsMargins(0, 0, 0, 0)

        self.gallery_preview_label = ImagePreviewLabel("Chưa chọn ảnh 📸", interactive=False)
        self.gallery_preview_label.setStyleSheet(
            "background: transparent; border: none; border-radius: 12px;")
        banner_layout.addWidget(self.gallery_preview_label)

        left_layout.addWidget(self.gallery_preview_container)

        # Slot delete buttons overlay (kept for controller compatibility)
        self.slot_delete_layout = self.gallery_preview_label.top_layout

        # ── Frame grid (lưới các khung ảnh) ──
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(STYLE_FRAME_SCROLL)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        self._frame_grid_layout = QGridLayout(grid_container)
        self._frame_grid_layout.setSpacing(8)
        self._frame_grid_layout.setContentsMargins(4, 4, 4, 4)
        scroll_area.setWidget(grid_container)
        left_layout.addWidget(scroll_area, stretch=1)

        # ── QListWidget ẩn (kept for controller compatibility) ──
        self.frame_list = QListWidget()
        self.frame_list.setViewMode(QListView.IconMode)
        self.frame_list.setFlow(QListView.LeftToRight)
        self.frame_list.setMovement(QListView.Static)
        self.frame_list.setSpacing(10)
        self.frame_list.setFixedHeight(0)  # Ẩn nhưng vẫn tồn tại cho controller
        self.frame_list.setIconSize(QSize(210, 140))
        self.frame_list.setStyleSheet("border: none; background: transparent;")
        self.frame_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frame_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_layout.addWidget(self.frame_list)

        # ── BACK button ──
        back_row = QHBoxLayout()
        self.btn_back_to_station = QPushButton("BACK ←")
        self.btn_back_to_station.setStyleSheet(STYLE_BACK_BTN)
        self.btn_back_to_station.setCursor(Qt.PointingHandCursor)
        self.btn_back_to_station.setFixedHeight(38)
        back_row.addWidget(self.btn_back_to_station)
        back_row.addStretch()
        left_layout.addLayout(back_row)

        main_row.addWidget(left_panel, stretch=3)

        # ─────────────── CỘT PHẢI: Photo Library & Controls ───────────────
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setStyleSheet(STYLE_RIGHT_PANEL)

        shadow_right = QGraphicsDropShadowEffect()
        shadow_right.setBlurRadius(22)
        shadow_right.setXOffset(0)
        shadow_right.setYOffset(5)
        shadow_right.setColor(QColor(200, 240, 232, 60))
        right_panel.setGraphicsEffect(shadow_right)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        # ── Right panel title + Timer ──
        title_row = QHBoxLayout()
        self.gallery_title = QLabel("THƯ VIỆN & XỬ LÝ ẢNH")
        self.gallery_title.setStyleSheet(STYLE_RIGHT_PANEL_TITLE)
        title_row.addWidget(self.gallery_title)
        title_row.addStretch()

        self._timer_label = QLabel("⏱ 00:00")
        self._timer_label.setStyleSheet(STYLE_TIMER_LABEL)
        title_row.addWidget(self._timer_label)
        right_layout.addLayout(title_row)

        # ── Top row: Filter photo grid (left) + QR code (right) ──
        top_content_row = QHBoxLayout()
        top_content_row.setSpacing(12)

        # Filter photo grid (ảnh đã chụp với các bộ lọc)
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.thumbnail_list.setFocusPolicy(Qt.ClickFocus)
        self.thumbnail_list.setStyleSheet(STYLE_THUMBNAIL_LIST)
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(100, 80))
        self.thumbnail_list.setSpacing(6)
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setMaximumHeight(220)
        self.thumbnail_list.setCursor(Qt.PointingHandCursor)
        top_content_row.addWidget(self.thumbnail_list, stretch=1)

        # QR Code block
        qr_block = QFrame()
        qr_block.setObjectName("qrBlock")
        qr_block.setStyleSheet(STYLE_QR_BLOCK)
        qr_block.setFixedWidth(130)

        qr_block_shadow = QGraphicsDropShadowEffect()
        qr_block_shadow.setBlurRadius(14)
        qr_block_shadow.setXOffset(0)
        qr_block_shadow.setYOffset(3)
        qr_block_shadow.setColor(QColor(0, 0, 0, 25))
        qr_block.setGraphicsEffect(qr_block_shadow)

        qr_vbox = QVBoxLayout(qr_block)
        qr_vbox.setContentsMargins(8, 8, 8, 8)
        qr_vbox.setSpacing(4)

        self.qr_container_gallery = qr_block   # alias for controller compatibility

        self.qr_code_label_gallery = QLabel()
        self.qr_code_label_gallery.setFixedSize(112, 112)
        self.qr_code_label_gallery.setScaledContents(True)
        self.qr_code_label_gallery.setAlignment(Qt.AlignCenter)
        self.qr_code_label_gallery.setStyleSheet(
            "background: white; border: 1px solid #EEE; border-radius: 8px; color: #CCC; font-size: 11px;")
        qr_vbox.addWidget(self.qr_code_label_gallery, 0, Qt.AlignCenter)

        lbl_scan = QLabel("📲 Quét nhận ảnh")
        lbl_scan.setAlignment(Qt.AlignCenter)
        lbl_scan.setWordWrap(True)
        lbl_scan.setStyleSheet(
            "font-size: 10px; color: #E91E63; font-weight: bold; background: transparent; border: none;")
        qr_vbox.addWidget(lbl_scan)
        qr_vbox.addStretch()

        top_content_row.addWidget(qr_block)
        right_layout.addLayout(top_content_row)
        right_layout.addStretch(1)

        # ── Actions: Camera button + Import/Delete controls ──
        # Row 1: import buttons
        action_grid = QGridLayout()
        action_grid.setSpacing(6)

        self.btn_import_raw = QPushButton("⬇️ Nhập ảnh")
        self.btn_import_raw.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 13px; padding: 5px;")
        self.btn_import_raw.setCursor(Qt.PointingHandCursor)
        action_grid.addWidget(self.btn_import_raw, 0, 0)

        self.btn_refresh_gallery = QPushButton("🔄 Làm mới")
        self.btn_refresh_gallery.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 13px; padding: 5px;")
        self.btn_refresh_gallery.setCursor(Qt.PointingHandCursor)
        action_grid.addWidget(self.btn_refresh_gallery, 0, 1)

        self.btn_delete_selected = QPushButton("🗑️ Xóa")
        self.btn_delete_selected.setEnabled(False)
        self.btn_delete_selected.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 13px; padding: 5px; color: #e57373;")
        self.btn_delete_selected.setCursor(Qt.PointingHandCursor)
        action_grid.addWidget(self.btn_delete_selected, 1, 0)

        self.btn_delete_all = QPushButton("🧨 Xóa Hết")
        self.btn_delete_all.setStyleSheet(STYLE_SECONDARY_BTN + "font-size: 13px; padding: 5px; color: #ff5252;")
        self.btn_delete_all.setCursor(Qt.PointingHandCursor)
        action_grid.addWidget(self.btn_delete_all, 1, 1)

        right_layout.addLayout(action_grid)

        # ── Camera button (lớn, peach gradient) ──
        self.btn_gallery_capture = QPushButton("📷")
        self.btn_gallery_capture.setStyleSheet(STYLE_CAMERA_BTN)
        self.btn_gallery_capture.setCursor(Qt.PointingHandCursor)
        self.btn_gallery_capture.setFixedHeight(70)
        self.btn_gallery_capture.setToolTip("Chụp ảnh mới")

        cam_shadow = QGraphicsDropShadowEffect()
        cam_shadow.setBlurRadius(18)
        cam_shadow.setXOffset(0)
        cam_shadow.setYOffset(6)
        cam_shadow.setColor(QColor(255, 138, 101, 120))
        self.btn_gallery_capture.setGraphicsEffect(cam_shadow)

        right_layout.addWidget(self.btn_gallery_capture)

        # ── Bottom row: Print + Finish buttons ──
        bottom_btn_row = QHBoxLayout()
        bottom_btn_row.setSpacing(8)

        self.btn_print = QPushButton("🖨️  IN ẢNH")
        self.btn_print.setStyleSheet(STYLE_PRINT_BTN)
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.setFixedHeight(44)

        print_shadow = QGraphicsDropShadowEffect()
        print_shadow.setBlurRadius(10)
        print_shadow.setXOffset(0)
        print_shadow.setYOffset(3)
        print_shadow.setColor(QColor(0, 0, 0, 20))
        self.btn_print.setGraphicsEffect(print_shadow)

        bottom_btn_row.addWidget(self.btn_print, stretch=1)

        self.btn_save = QPushButton("HOÀN THÀNH & LƯU  →")
        self.btn_save.setStyleSheet(STYLE_FINISH_BTN)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(44)

        finish_shadow = QGraphicsDropShadowEffect()
        finish_shadow.setBlurRadius(16)
        finish_shadow.setXOffset(2)
        finish_shadow.setYOffset(4)
        finish_shadow.setColor(QColor(244, 81, 30, 90))
        self.btn_save.setGraphicsEffect(finish_shadow)

        bottom_btn_row.addWidget(self.btn_save, stretch=1)

        right_layout.addLayout(bottom_btn_row)

        # ── Hidden compatibility widgets (LUT / Sharpen / Add Icon) ──
        self.lut_selector = QComboBox()
        self.lut_selector.hide()
        self.btn_add_lut = QPushButton()
        self.btn_add_lut.hide()
        self.btn_apply_lut = QPushButton()
        self.btn_apply_lut.hide()
        self.btn_delete_lut = QPushButton()
        self.btn_delete_lut.hide()
        self.sharpen_selector = QComboBox()
        self.sharpen_selector.addItems(["Tắt (Gốc)", "Thấp", "Vừa (Nên dùng)", "Cao"])
        self.sharpen_selector.hide()
        self.btn_apply_sharpen = QPushButton()
        self.btn_apply_sharpen.hide()
        self.btn_add_icon = QPushButton()
        self.btn_add_icon.setEnabled(False)
        self.btn_add_icon.hide()

        main_row.addWidget(right_panel, stretch=2)

    def _on_tab_clicked(self, tab_id, clicked_btn):
        """Cập nhật style tab khi người dùng bấm."""
        self._active_tab = tab_id
        for btn in self._tab_buttons:
            if btn is clicked_btn:
                btn.setStyleSheet(STYLE_TAB_BTN_ACTIVE)
            else:
                btn.setStyleSheet(STYLE_TAB_BTN_INACTIVE)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Định vị nút Log ở góc dưới bên phải, tránh che khuất System Ready
        if hasattr(self, 'btn_show_log'):
            self.btn_show_log.move(self.width() - 140, self.height() - 100)
            self.btn_show_log.raise_()

    def update_preview_image(self, image_path):
        if image_path:
            self.gallery_preview_label.set_image(image_path)
            self.btn_add_icon.setEnabled(True)
        else:
            self.gallery_preview_label.clear_image()
            self.btn_add_icon.setEnabled(False)

    def update_slot_delete_buttons(self, selected_slot_images, callback):
        # Clear previous buttons
        for i in reversed(range(self.slot_delete_layout.count())):
            item = self.slot_delete_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Xử lý nếu có layout con (mặc dù hiện tại không có, nhưng để cho chắc)
                pass
        
        # Add new buttons for each filled slot
        for i, path in enumerate(selected_slot_images):
            if path:
                btn = QPushButton(f"Slot {i+1} ✕")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(229, 115, 115, 85%);
                        color: white;
                        font-weight: bold;
                        font-size: 14px;
                        border-radius: 4px;
                        padding: 5px 10px;
                        border: 1px solid rgba(255, 255, 255, 30%);
                    }
                    QPushButton:hover { background-color: rgba(244, 67, 54, 100%); }
                """)
                # Sử dụng default value cho lambda để tránh lỗi closure
                btn.clicked.connect(lambda checked, idx=i: callback(idx))
                self.slot_delete_layout.addWidget(btn)

    def set_app_mode(self, mode):
        """Thiết lập chế độ ứng dụng: 'wedding' hoặc 'normal'"""
        if mode == "wedding":
            self.num_captures_container.hide()
            self.timer_container.hide()
            self.btn_add_icon.hide() # Ẩn theo yêu cầu mới
            self.logo_label.setText("👰🤵 WEDDING PHOTOBOOTH")
        else:
            self.num_captures_container.show()
            self.timer_container.show()
            self.btn_add_icon.show() 
            self.logo_label.setText("🍑 PHOTOBOOTH STATION")

    def log(self, message):
        # Lưu vào buffer và print ra console
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] » {message}"
        self.log_buffer.append(log_msg)
        # Giới hạn buffer tầm 1000 dòng để tránh tốn ram
        if len(self.log_buffer) > 1000:
            self.log_buffer.pop(0)
            
        print(log_msg)

class VirtualKeyboardDialog(QDialog):
    """Bàn phím ảo thuận tiện cho màn hình cảm ứng khi nhập tên khách."""
    def __init__(self, parent=None, title="Nhập Tên Khách", initial_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(900, 500)
        self.is_shift = False
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Input field
        self.input_field = QLineEdit(initial_text)
        self.input_field.setPlaceholderText("Tên khách hàng...")
        self.input_field.setMinimumHeight(60)
        self.input_field.setStyleSheet("""
            QLineEdit {
                font-size: 24px;
                padding: 10px;
                border: 2px solid #FFAB91;
                border_radius: 10px;
                background-color: white;
            }
        """)
        layout.addWidget(self.input_field)
        
        # Keyboard grid
        self.kb_layout = QVBoxLayout()
        self.kb_layout.setSpacing(5)
        
        # Rows definition
        self.rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "BKSP"],
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L", "_"],
            ["SHIFT", "Z", "X", "C", "V", "B", "N", "M", ".", "-"],
            ["SPACE", "OK", "Bỏ qua"]
        ]
        
        self.buttons = []
        for row_data in self.rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(5)
            for key in row_data:
                btn = QPushButton(key)
                btn.setMinimumHeight(65)
                
                # Style cho từng loại nút
                if key in ["BKSP", "SHIFT", "OK", "Bỏ qua"]:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #757575; color: white; font-weight: bold; font-size: 18px; border-radius: 8px; border: none;
                        }
                        QPushButton:hover { background-color: #616161; }
                    """)
                    if key == "OK":
                        btn.setStyleSheet(btn.styleSheet().replace("#757575", "#4CAF50"))
                        btn.clicked.connect(self.accept)
                    elif key == "BKSP":
                        btn.clicked.connect(self.handle_backspace)
                    elif key == "SHIFT":
                        btn.setCheckable(True)
                        btn.clicked.connect(self.handle_shift)
                    elif key == "Bỏ qua":
                        btn.setStyleSheet(btn.styleSheet().replace("#757575", "#f44336"))
                        btn.clicked.connect(self.reject)
                    btn.setMinimumWidth(100)
                elif key == "SPACE":
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e0e0e0; color: #212121; font-size: 18px; border-radius: 8px; border: 1px solid #bdbdbd;
                        }
                        QPushButton:hover { background-color: #d5d5d5; }
                    """)
                    btn.setMinimumWidth(300)
                    btn.clicked.connect(lambda: self.input_field.setText(self.input_field.text() + " "))
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: white; color: #212121; font-size: 22px; font-weight: bold; border-radius: 8px; border: 1px solid #e0e0e0;
                        }
                        QPushButton:hover { background-color: #f5f5f5; }
                    """)
                    btn.clicked.connect(lambda checked, k=key: self.handle_key(k))
                    btn.setMinimumWidth(60)
                
                row_layout.addWidget(btn)
                self.buttons.append(btn)
            self.kb_layout.addLayout(row_layout)
        
        layout.addLayout(self.kb_layout)
        
    def handle_key(self, key):
        txt = key if self.is_shift else key.lower()
        self.input_field.setText(self.input_field.text() + txt)
        # Reset shift sau 1 nốt nếu đang ở chế độ Shift thường (không phải Caps Lock - đơn giản hóa)
        # Nhưng ở đây để đơn giản cho user nhập liệu photo, ta tạm giữ nguyên
        
    def handle_backspace(self):
        self.input_field.setText(self.input_field.text()[:-1])
        
    def handle_shift(self):
        self.is_shift = not self.is_shift
        # Cập nhật hiển thị text trên nút
        for btn in self.buttons:
            t = btn.text()
            if len(t) == 1 and t.isalpha():
                btn.setText(t.upper() if self.is_shift else t.lower())

    def get_text(self):
        return self.input_field.text().strip()
