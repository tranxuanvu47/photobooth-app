
# --- COLOR PALETTE ---
COLOR_PEACH = "#FFAB91"
COLOR_PEACH_HOVER = "#FF8A65"
COLOR_PEACH_PRESSED = "#F4511E"
COLOR_PEACH_LIGHT = "#FFF0EB"

COLOR_BG = "#FFFFFF"
COLOR_SIDEBAR_BG = "#FAFAFA"
COLOR_TEXT = "#212121"
COLOR_TEXT_MUTED = "#757575"
COLOR_BORDER = "#E0E0E0"

# --- GLOBAL STYLES ---
GLOBAL_STYLE = f"""
    QMainWindow, QDialog {{
        background-color: {COLOR_BG};
        font-family: 'Segoe UI', sans-serif;
        font-size: 18px;
    }}

    QLabel {{
        color: {COLOR_TEXT};
    }}

    QLineEdit, QComboBox {{
        background-color: white;
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 8px;
        color: {COLOR_TEXT};
        font-size: 20px;
    }}

    /* Dropdown specific */
    QComboBox::drop-down {{
        border: 0px;
    }}
    QComboBox QAbstractItemView {{
        background-color: white;
        border: 1px solid {COLOR_BORDER};
        selection-background-color: {COLOR_PEACH_LIGHT};
        selection-color: {COLOR_PEACH_PRESSED};
    }}
"""

# --- COMPONENT STYLES ---
STYLE_STATION_HEADER = f"""
    QLabel {{
        font-size: 38px;
        font-weight: bold;
        color: {COLOR_TEXT};
        letter-spacing: 1px;
    }}
"""

STYLE_ADMIN_GHOST_BTN = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 8px 15px;
        color: {COLOR_TEXT_MUTED};
        font-size: 16px;
    }}
    QPushButton:hover {{
        background: rgba(0,0,0,0.05);
        color: {COLOR_TEXT};
    }}
"""

STYLE_PRIMARY_BTN = f"""
    QPushButton {{
        background-color: {COLOR_PEACH};
        color: white;
        border-radius: 12px;
        font-size: 28px;
        font-weight: bold;
        padding: 10px;
        border: none;
    }}
    QPushButton:hover {{
        background-color: {COLOR_PEACH_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_PEACH_PRESSED};
    }}
"""

STYLE_SECONDARY_BTN = f"""
    QPushButton {{
        background-color: white;
        color: {COLOR_PEACH};
        border: 2px solid {COLOR_PEACH};
        border-radius: 8px;
        font-size: 20px;
        font-weight: bold;
        padding: 12px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_PEACH_LIGHT};
    }}
"""

STYLE_PREVIEW_CONTAINER = f"""
    QFrame {{
        background-color: #f0f0f0;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
    }}
"""

STYLE_SIDEBAR_BLOCK = f"""
    QFrame {{
        background-color: {COLOR_SIDEBAR_BG};
        border-radius: 10px;
        padding: 10px;
    }}
    QLabel {{
        font-size: 15px;
        color: {COLOR_TEXT_MUTED};
        text-transform: uppercase;
        font-weight: bold;
    }}
"""

STYLE_THUMBNAIL_LIST = f"""
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: 0;
    }}
    QListWidget::item {{
        background: transparent;
        border: none;
        padding: 0px;
        margin: 0px;
        outline: none;
    }}
    QListWidget::item:selected {{
        background-color: #FFF0EB;
        border: 2px solid #FFAB91;
        border-radius: 8px;
    }}
    QListWidget::item:hover {{
        background-color: rgba(0,0,0,0.03);
    }}
"""

STYLE_FRAME_SELECTOR = f"""
    QListWidget {{
        background-color: #f9f9f9;
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 5px;
    }}
    QListWidget::item {{
        background-color: white;
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        margin: 5px;
        padding: 5px;
    }}
    QListWidget::item:selected {{
        border: 3px solid {COLOR_PEACH};
        background-color: {COLOR_PEACH_LIGHT};
    }}
"""

# ============================================================
# NEW GALLERY REDESIGN STYLES
# ============================================================

# Gallery screen gradient background
STYLE_GALLERY_SCREEN = """
    QWidget#galleryScreen {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 #FFE8D6,
            stop:0.5 #F8F8F8,
            stop:1 #C8F0E8
        );
    }
"""

# Top bar pill container
STYLE_TOPBAR_CONTAINER = """
    QFrame#topBarContainer {
        background: rgba(255, 255, 255, 0.88);
        border-radius: 22px;
        border: 1px solid rgba(255, 171, 145, 0.3);
    }
"""

# Tab navigation button - inactive state
STYLE_TAB_BTN_INACTIVE = """
    QPushButton {
        background: transparent;
        border: none;
        border-radius: 16px;
        padding: 8px 18px;
        font-size: 15px;
        font-weight: bold;
        color: #888888;
        font-family: 'Segoe UI', sans-serif;
    }
    QPushButton:hover {
        background: rgba(255, 171, 145, 0.15);
        color: #FF8A65;
    }
"""

# Tab navigation button - active state
STYLE_TAB_BTN_ACTIVE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #FFAB91, stop:1 #FF8A65);
        border: none;
        border-radius: 16px;
        padding: 8px 18px;
        font-size: 15px;
        font-weight: bold;
        color: white;
        font-family: 'Segoe UI', sans-serif;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #FF8A65, stop:1 #F4511E);
    }
"""

# Search bar
STYLE_SEARCH_BAR = """
    QLineEdit {
        background: rgba(255, 255, 255, 0.9);
        border: 1.5px solid rgba(255, 171, 145, 0.5);
        border-radius: 16px;
        padding: 6px 14px;
        font-size: 14px;
        color: #555;
        font-family: 'Segoe UI', sans-serif;
    }
    QLineEdit:focus {
        border-color: #FFAB91;
        background: white;
    }
"""

# Left column panel - frame selector
STYLE_LEFT_PANEL = """
    QFrame#leftPanel {
        background: rgba(255, 255, 255, 0.80);
        border-radius: 18px;
        border: 1px solid rgba(255, 171, 145, 0.20);
    }
"""

# Right column panel - photo library
STYLE_RIGHT_PANEL = """
    QFrame#rightPanel {
        background: rgba(255, 255, 255, 0.80);
        border-radius: 18px;
        border: 1px solid rgba(200, 240, 232, 0.50);
    }
"""

# Frame preview banner
STYLE_FRAME_BANNER = """
    QFrame#frameBanner {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #FFE0D0, stop:1 #D0F2E8);
        border-radius: 12px;
        border: none;
    }
"""

# Back button
STYLE_BACK_BTN = """
    QPushButton {
        background: rgba(255, 255, 255, 0.9);
        border: 2px solid #E0E0E0;
        border-radius: 12px;
        padding: 8px 20px;
        font-size: 15px;
        font-weight: bold;
        color: #666;
        font-family: 'Segoe UI', sans-serif;
    }
    QPushButton:hover {
        background: #FFF0EB;
        border-color: #FFAB91;
        color: #FF7043;
    }
    QPushButton:pressed {
        background: #FFE0D0;
    }
"""

# Right panel title
STYLE_RIGHT_PANEL_TITLE = """
    QLabel {
        font-size: 22px;
        font-weight: bold;
        color: #333333;
        font-family: 'Segoe UI', sans-serif;
        letter-spacing: 0.5px;
        background: transparent;
        border: none;
    }
"""

# Filter name label
STYLE_FILTER_NAME_LABEL = """
    QLabel {
        font-size: 11px;
        color: #999;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 500;
        background: transparent;
        border: none;
    }
"""

# Camera action button (large peach block)
STYLE_CAMERA_BTN = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #FFAB91, stop:1 #FF8A65);
        border: none;
        border-radius: 14px;
        color: white;
        font-size: 30px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #FF8A65, stop:1 #F4511E);
    }
    QPushButton:pressed {
        background: #F4511E;
    }
"""

# Print button
STYLE_PRINT_BTN = """
    QPushButton {
        background: white;
        border: 2px solid #CCCCCC;
        border-radius: 12px;
        padding: 10px 18px;
        font-size: 15px;
        font-weight: bold;
        color: #555;
        font-family: 'Segoe UI', sans-serif;
    }
    QPushButton:hover {
        background: #F5F5F5;
        border-color: #FFAB91;
        color: #FF7043;
    }
    QPushButton:pressed {
        background: #FFF0EB;
    }
"""

# Finish & Save button (peach gradient)
STYLE_FINISH_BTN = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #FF8A65, stop:0.6 #FF7043, stop:1 #F4511E);
        border: none;
        border-radius: 12px;
        padding: 10px 18px;
        font-size: 15px;
        font-weight: bold;
        color: white;
        font-family: 'Segoe UI', sans-serif;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #FF7043, stop:1 #E64A19);
    }
    QPushButton:pressed {
        background: #E64A19;
    }
"""

# QR code block
STYLE_QR_BLOCK = """
    QFrame#qrBlock {
        background: white;
        border-radius: 12px;
        border: 1px solid #EEEEEE;
    }
"""

# Scroll area for frame grid
STYLE_FRAME_SCROLL = """
    QScrollArea {
        border: none;
        background: transparent;
    }
    QScrollBar:vertical {
        width: 6px;
        background: transparent;
    }
    QScrollBar::handle:vertical {
        background: #FFAB91;
        border-radius: 3px;
        min-height: 20px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        height: 6px;
        background: transparent;
    }
    QScrollBar::handle:horizontal {
        background: #FFAB91;
        border-radius: 3px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""

# Timer label style
STYLE_TIMER_LABEL = """
    QLabel {
        font-size: 13px;
        font-weight: bold;
        color: #FFAB91;
        font-family: 'Segoe UI', sans-serif;
        background: transparent;
        border: none;
    }
"""
