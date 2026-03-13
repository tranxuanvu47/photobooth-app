
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
    QListWidget::item:selected {{
        border: 2px solid {COLOR_PEACH};
        border-radius: 8px;
        background: transparent;
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
