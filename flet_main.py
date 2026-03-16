import flet as ft
import os
import time
import threading
import config
import shutil
import base64
import qrcode
from io import BytesIO
from datetime import datetime
from flet_camera import FletCameraWorker
from frame_layout_manager import FrameLayoutManager
from nextcloud_utils import upload_to_nextcloud
from printer_service import PrinterService
from image_processor import ImageProcessor
import re

# Premium Aesthetic Palette
COLOR_TEAL_DARK = "#004D40"      # Font chữ đậm
COLOR_TEAL_BORDER = "#009688"    # Viền Teal đặc trưng (2px)
COLOR_MINT_BG = "#B2DFDB"        # Mint cho gradient nền
COLOR_PEACH_BG = "#FFCCBC"       # Peach cho gradient nền
COLOR_PEACH_PRIMARY = "#E59A84"  # Màu cam đào chủ đạo
COLOR_TEXT_MUTED = "#636E72"

class VirtualKeyboard(ft.Column):
    def __init__(self, target_textfield, on_submit, on_cancel=None):
        super().__init__()
        self.target = target_textfield
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.spacing = 5
        self.build_keys()

    def build_keys(self):
        rows = [
            "1234567890",
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM"
        ]
        for row_str in rows:
            row = ft.Row(spacing=5, alignment=ft.MainAxisAlignment.CENTER)
            for char in row_str:
                row.controls.append(
                    ft.ElevatedButton(
                        char, 
                        on_click=lambda e, c=char: self.add_char(c),
                        width=50, height=50,
                        style=ft.ButtonStyle(padding=0, shape=ft.RoundedRectangleBorder(radius=8))
                    )
                )
            self.controls.append(row)
        
        self.controls.append(ft.Row([
            ft.ElevatedButton("Hủy", icon=ft.Icons.CANCEL, on_click=lambda _: self.on_cancel() if self.on_cancel else None, width=100, bgcolor="#757575", color="white"),
            ft.ElevatedButton("Xóa", icon=ft.Icons.BACKSPACE, on_click=self.backspace, width=100, bgcolor="#E53935", color="white"),
            ft.ElevatedButton("Space", on_click=lambda _: self.add_char("_"), width=150),
            ft.ElevatedButton("OK", icon=ft.Icons.CHECK, on_click=lambda _: self.on_submit(), width=100, bgcolor="#4CAF50", color="white"),
        ], alignment=ft.MainAxisAlignment.CENTER))

    def add_char(self, char):
        self.target.value = (self.target.value or "") + char
        self.target.update()

    def backspace(self, _):
        if self.target.value and len(self.target.value) > 0:
            self.target.value = self.target.value[:-1]
            self.target.update()

    def clear(self, _):
        self.target.value = ""
        self.target.update()

class FletPhotoboothApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Photobooth Station Pro - Flet Edition"
        self.page.bgcolor = "white"
        self.page.padding = 0
        self.page.window_maximized = True
        
        # --- Application State ---
        self.current_session = "Khach_Mac_Dinh"
        self.sessions = []
        self.camera_list = []
        self.captured_sequence_paths = []
        self.remaining_captures = 0
        self.total_captures = 1
        self.is_capturing = False
        
        # Gallery State
        self.selected_slot_images = []
        self.current_layout = None
        self.processed_image = None
        self.layout_manager = FrameLayoutManager()
        self.layout_manager.load_layouts()
        
        # --- UI Build ---
        self.setup_ui_references()
        self.page.on_route_change = self.route_change
        self.page.on_keyboard_event = self.on_keyboard
        
        # Start Backend Workers
        self.camera_worker = FletCameraWorker(camera_index=0)
        self.camera_worker.on_frame = self.on_camera_frame
        self.camera_worker.on_status = self.on_camera_status
        self.camera_worker.on_camera_list = self.on_camera_list
        self.camera_worker.on_image_captured = self.on_image_captured_worker
        
        # Monitor Thread
        threading.Thread(target=self.monitor_raw_dir, daemon=True).start()
        
        self.page.go("/")
        
        # Current Tab State
        self.active_tab = "Classic"
        
        # Delayed Worker Startup
        threading.Thread(target=self.start_backend, daemon=True).start()

    def setup_ui_references(self):
        # Home Screen Elements
        # Placeholder 1x1 transparent gif to avoid red error box
        self.camera_view = ft.Image(
            src_base64="R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
            fit=ft.ImageFit.COVER,  # COVER: fills the area, crops sides if needed (no black bars)
            expand=True,
            width=float("inf"),
            height=float("inf")
        )
        self.countdown_overlay = ft.Container(
            content=ft.Text("", size=120, weight="bold", color="white"),
            bgcolor="rgba(255, 171, 145, 0.7)",
            width=300, height=300, border_radius=40,
            alignment=ft.alignment.center,
            visible=False
        )
        self.capture_progress_overlay = ft.Container(
            content=ft.Text("1 / 1", color="white", size=32, weight="bold"),
            bgcolor="rgba(0,0,0,0.6)",
            padding=ft.padding.only(left=20, right=20, top=10, bottom=10),
            border_radius=ft.border_radius.only(bottom_right=10),
            visible=False,
            top=0, left=0
        )
        
        # Sidebar Controls
        self.qr_code_img = ft.Image(width=160, height=160, fit=ft.ImageFit.CONTAIN) # Even smaller QR
        self.session_dropdown = ft.Dropdown(
            label="Chọn hoặc nhập tên...", expand=True, border_radius=10,
            text_size=12,
            on_change=lambda e: self.on_session_change(e.control.value)
        )
        self.camera_dropdown = ft.Dropdown(
            label="MÁY ẢNH ĐANG DÙNG", expand=True, border_radius=10,
            text_size=12,
            on_change=lambda e: self.camera_worker.change_camera(e.control.value)
        )
        self.countdown_selector = ft.Dropdown(
            label="THỜI GIAN CHỜ CHỤP", expand=True, border_radius=10,
            text_size=12,
            options=[ft.dropdown.Option(k) for k in ["📸 Chụp ngay", "⏳ 1s", "⏳ 3s", "⏳ 5s", "⏳ 10s"]],
            value="📸 Chụp ngay"
        )
        self.num_captures_selector = ft.Dropdown(
            label="SỐ LƯỢNG HÌNH CHỤP", expand=True, border_radius=10,
            text_size=12,
            options=[ft.dropdown.Option(k) for k in ["1 hình", "2 hình", "4 hình", "6 hình", "8 hình"]],
            value="1 hình"
        )
        self.btn_capture = ft.Container(
            content=ft.Row([
                ft.Text("CHỤP ẢNH NGAY", size=18, weight="bold", color="white"),
                ft.Text(" →", size=20, weight="bold", color="white"),
            ], alignment="center", spacing=5),
            height=70, 
            border_radius=15,
            bgcolor=COLOR_PEACH_PRIMARY,
            on_click=self.on_capture_click,
            alignment=ft.alignment.center,
            shadow=ft.BoxShadow(blur_radius=15, color="#50E59A84", offset=ft.Offset(0, 5))
        )
        self.photo_guide = ft.Container(
            padding=15,
            border_radius=15,
            border=ft.border.all(1, "#EEEEEE"),
            bgcolor="#F9F9F9",
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CROP_FREE_ROUNDED, color=COLOR_TEXT_MUTED, size=20),
                    ft.Text("PHOTO GUIDE", size=11, weight="bold", color=COLOR_TEXT_MUTED),
                ], spacing=8),
                ft.Text("Đứng vào khung hình để có ảnh đẹp nhất", size=10, color=COLOR_TEXT_MUTED, italic=True)
            ], spacing=5)
        )

        self.log_status_text = ft.Text("", color="#4CAF50", size=12, weight="bold", visible=False)

        
        # Gallery Elements
        self.gallery_grid = ft.GridView(
            expand=True, 
            runs_count=2, # Back to 2 columns
            spacing=15, 
            run_spacing=15, 
            padding=10,
            child_aspect_ratio=1.33 # Keep 4:3 Landscape Ratio
        )
        self.gallery_preview = ft.Image(fit=ft.ImageFit.CONTAIN) # Target: Center and Fit
        self.frame_selector_grid = ft.Row(
            spacing=15,
            scroll=ft.ScrollMode.ALWAYS,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        self.lut_dropdown = ft.Dropdown(label="MÀU SẮC (LUT)", width=200, border_radius=8, bgcolor="white")
        self.gallery_search = ft.TextField(
            hint_text="🔍   Tìm kiếm khung...",
            width=250,
            height=40,
            border_radius=20,
            bgcolor="white",
            border_color="transparent",
            content_padding=ft.padding.only(left=20, right=20),
            text_size=13
        )

    def start_backend(self):
        time.sleep(1.5)
        self.load_sessions()
        self.update_qr_code()
        self.camera_worker.start()
        self.camera_worker.request_scan()
        self.refresh_gallery_data()

    def safe_update(self):
        try: self.page.update()
        except: pass

    # --- Routing & Input ---
    def on_keyboard(self, e: ft.KeyboardEvent):
        if e.ctrl and e.key == "7":
            self.page.go("/admin")
        elif e.alt and e.key == "Enter":
            self.page.window_full_screen = not self.page.window_full_screen
            self.safe_update()

    def route_change(self, e):
        self.page.views.clear()
        if self.page.route == "/":
            self.page.views.append(self.create_home_view())
        elif self.page.route == "/gallery":
            self.page.views.append(self.create_gallery_view())
            self.refresh_thumbnails()
            self.refresh_gallery_data()
        elif self.page.route == "/admin":
            self.page.views.append(self.create_admin_view())
        self.safe_update()

    # --- Feature: Session & QR ---
    def load_sessions(self, select_name=None):
        os.makedirs(config.RAW_DIR, exist_ok=True)
        dirs = [d for d in os.listdir(config.RAW_DIR) if os.path.isdir(os.path.join(config.RAW_DIR, d))]
        if not dirs: dirs = ["Khach_Mac_Dinh"]
        self.sessions = sorted(dirs)
        self.session_dropdown.options = [ft.dropdown.Option(s) for s in self.sessions]
        
        # Priority: select_name > "Khach_Mac_Dinh" > first alphabetically
        if select_name and select_name in self.sessions:
            self.current_session = select_name
        elif "Khach_Mac_Dinh" in self.sessions:
            self.current_session = "Khach_Mac_Dinh"
        else:
            self.current_session = self.sessions[0]
            
        self.session_dropdown.value = self.current_session
        self.update_qr_code()
        self.safe_update()

    def on_session_change(self, value):
        print(f"DEBUG: Session changed to {value}")
        self.current_session = value
        self.refresh_thumbnails()
        self.update_qr_code()
        self.safe_update()

    def update_qr_code(self):
        url = config.NC_SHARE_URL
        if not url: return # Placeholder text or something?
        
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buff = BytesIO()
        img.save(buff, format="PNG")
        b64 = base64.b64encode(buff.getvalue()).decode()
        self.qr_code_img.src_base64 = b64
        self.safe_update()

    # --- Feature: Capture Sequence ---
    def on_capture_click(self, e):
        print(f"DEBUG: on_capture_click triggered. is_capturing={self.is_capturing}")
        if self.is_capturing: return
        
        # Parse total captures
        num_txt = self.num_captures_selector.value
        m = re.search(r'(\d+)', num_txt)
        self.total_captures = int(m.group(1)) if m else 1
        
        if config.APP_MODE == "wedding":
            self.total_captures = 1
            
        self.remaining_captures = self.total_captures
        self.captured_sequence_paths = []
        self.is_capturing = True
        
        self.trigger_next_shot()

    def trigger_next_shot(self):
        # Update progress overlay
        idx = self.total_captures - self.remaining_captures + 1
        self.capture_progress_overlay.content.value = f"{idx} / {self.total_captures}"
        self.capture_progress_overlay.visible = self.total_captures > 1
        
        # Parse countdown
        selection = self.countdown_selector.value
        print(f"DEBUG: trigger_next_shot selection={selection}")
        if "Chụp ngay" in selection:
            self.camera_worker.request_capture()
        else:
            m = re.search(r'(\d+)s', selection)
            seconds = int(m.group(1)) if m else 3
            threading.Thread(target=self.run_countdown, args=(seconds,), daemon=True).start()

    def run_countdown(self, seconds):
        self.countdown_overlay.visible = True
        for i in range(seconds, 0, -1):
            self.countdown_overlay.content.value = str(i)
            self.safe_update()
            time.sleep(1)
        self.countdown_overlay.visible = False
        self.safe_update()
        self.camera_worker.request_capture()

    def on_image_captured_worker(self, path):
        # Called after single capture
        print(f"DEBUG: on_image_captured_worker called with path={path}")
        self.camera_worker.pause_preview()
        
        # Show Review Dialog
        self.dialog_path = path
        idx = self.total_captures - self.remaining_captures + 1
        
        def on_accept(_):
            self.captured_sequence_paths.append(self.dialog_path)
            # Refresh thumbnails immediately so they see the photo in gallery
            self.refresh_thumbnails()
            
            # Sync to Nextcloud
            threading.Thread(target=lambda: upload_to_nextcloud(vars(config), self.dialog_path, self.current_session), daemon=True).start()
            
            self.remaining_captures -= 1
            self.page.close(self.active_dialog)
            self.safe_update()
            
            if self.remaining_captures > 0:
                self.btn_capture.text = f"📸 CHỤP TIẾP TẤM {idx + 1}"
                print(f"DEBUG: Sequence continues. Remaining={self.remaining_captures}")
                self.is_capturing = False
                self.camera_worker.resume_preview()
            else:
                print("DEBUG: Sequence finished. Calling finish_sequence.")
                self.finish_sequence()
                
        def on_retake(_):
            print(f"DEBUG: on_retake for path={self.dialog_path}")
            try: os.remove(self.dialog_path)
            except: pass
            self.page.close(self.active_dialog)
            self.safe_update()
            self.is_capturing = False
            self.btn_capture.text = f"📸 CHỤP LẠI TẤM {idx}"
            self.camera_worker.resume_preview()

        review_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"ẢNH THỨ {idx} / {self.total_captures}", text_align="center", weight="bold"),
            content=ft.Container(
                content=ft.Image(src=path, fit=ft.ImageFit.CONTAIN),
                width=800, height=600, border_radius=10, border=ft.border.all(1, "#ddd")
            ),
            actions=[
                ft.ElevatedButton("📸 CHỤP LẠI", bgcolor="red", color="white", on_click=on_retake, expand=True),
                ft.ElevatedButton("✅ TIẾP TỤC" if self.remaining_captures > 1 else "🎯 HOÀN THÀNH", bgcolor="green", color="white", on_click=on_accept, expand=True)
            ],
            actions_alignment="center"
        )
        self.active_dialog = review_dialog
        self.page.open(review_dialog)
        self.safe_update()

    def monitor_raw_dir(self):
        last_known_files = set()
        last_session = None
        while True:
            try:
                # 1. Move root files to session folder
                root_files = [f for f in os.listdir(config.RAW_DIR) if os.path.isfile(os.path.join(config.RAW_DIR, f)) and f.lower().endswith(('.png', '.jpg'))]
                if root_files:
                    session_path = os.path.join(config.RAW_DIR, self.current_session)
                    os.makedirs(session_path, exist_ok=True)
                    for f in root_files:
                        shutil.move(os.path.join(config.RAW_DIR, f), os.path.join(session_path, f))
                
                # 2. Watch current session folder for new files
                if self.current_session != last_session:
                    last_known_files = set()
                    last_session = self.current_session
                
                session_path = os.path.join(config.RAW_DIR, self.current_session)
                if os.path.exists(session_path):
                    current_files = set([f for f in os.listdir(session_path) if f.lower().endswith(('.jpg', '.png'))])
                    new_files = current_files - last_known_files
                    
                    if new_files or root_files:
                        self.refresh_thumbnails()
                        
                        # Auto-select the newest file
                        if new_files:
                            newest_file_name = max(new_files, key=lambda x: os.path.getmtime(os.path.join(session_path, x)))
                            newest_file_path = os.path.join(session_path, newest_file_name)
                            self.on_thumb_click(newest_file_path)
                            
                        last_known_files = current_files
            except Exception as e:
                print(f"Monitor error: {e}")
            time.sleep(1.5)

    def finish_sequence(self):
        self.is_capturing = False
        self.btn_capture.text = "📸 CHỤP ẢNH"
        self.capture_progress_overlay.visible = False
        self.camera_worker.resume_preview()
        
        # Auto-fill gallery slots if layout active
        if not self.current_layout:
            layouts = self.layout_manager.get_all_layouts()
            if layouts:
                self.current_layout = layouts[0]
                print(f"DEBUG: Auto-selected layout: {self.current_layout['name']}")

        if self.current_layout:
            slots = len(self.current_layout.get("slots", []))
            self.selected_slot_images = [None] * slots
            for i in range(min(len(self.captured_sequence_paths), slots)):
                self.selected_slot_images[i] = self.captured_sequence_paths[i]
            
            # Prepare preview before navigating
            self.update_processed_preview()
        
        self.page.go("/gallery")

    # --- Gallery & Processing ---
    def refresh_gallery_data(self):
        self.lut_dropdown.options = [ft.dropdown.Option("Gốc (Không màu)")]
        if os.path.exists(config.LUTS_DIR):
            luts = [f for f in os.listdir(config.LUTS_DIR) if f.lower().endswith(('.cube', '.xmp'))]
            self.lut_dropdown.options.extend([ft.dropdown.Option(l) for l in luts])
        
        self.frame_selector_grid.controls.clear()
        # Add "None"
        self.frame_selector_grid.controls.append(self.create_frame_card(None, "Không khung"))
        for l in self.layout_manager.get_all_layouts():
            # Check if search or tab filters apply
            search_query = self.gallery_search.value.lower() if self.gallery_search.value else ""
            if search_query and search_query not in l["name"].lower():
                continue
            
            self.frame_selector_grid.controls.append(self.create_frame_card(l, l["name"]))
        self.safe_update()

    def create_frame_card(self, layout, name):
        frame_file = layout["frame_file"] if layout and layout.get("frame_file") else None
        b64 = None
        if frame_file and os.path.exists(frame_file):
            try:
                with open(frame_file, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
            except: pass

        is_selected = (self.current_layout and layout and self.current_layout.get("name") == layout.get("name")) or (not self.current_layout and not layout)

        return ft.GestureDetector(
            on_tap=lambda _: self.select_layout(layout),
            content=ft.Container(
                width=100,
                height=140,
                border_radius=10, 
                border=ft.border.all(2, COLOR_PEACH_PRIMARY) if is_selected else ft.border.all(1, "#DDD"),
                bgcolor="white",
                padding=5,
                alignment=ft.alignment.center,
                animate=ft.Animation(300, ft.AnimationCurve.DECELERATE),
                content=ft.Column([
                    ft.Container(
                        content=ft.Image(src_base64=b64, fit=ft.ImageFit.CONTAIN) if b64 else ft.Icon(ft.Icons.NOT_INTERESTED_ROUNDED, color="red", size=24),
                        expand=True,
                        alignment=ft.alignment.center
                    ),
                    ft.Text(name, size=10, weight="600", overflow="ellipsis", text_align=ft.TextAlign.CENTER, color=COLOR_TEAL_DARK if is_selected else COLOR_TEXT_MUTED)
                ], horizontal_alignment="center", spacing=2)
            )
        )

    def select_layout(self, layout):
        self.current_layout = layout
        if not layout:
            # Maintain the current selection if possible, otherwise clear
            if not self.selected_slot_images or len(self.selected_slot_images) == 0:
                self.selected_slot_images = [None]
        else:
            slots = len(layout.get("slots", []))
            if len(self.selected_slot_images) != slots:
                old = self.selected_slot_images
                self.selected_slot_images = [None] * slots
                for i in range(min(len(old), slots)): 
                    if i < len(self.selected_slot_images):
                        self.selected_slot_images[i] = old[i]
        
        self.update_processed_preview()
        self.refresh_gallery_data() # Refresh to show selection
        self.refresh_thumbnails() # Refresh to show which thumbnails are in frame

    def update_processed_preview(self):
        if not self.current_layout:
            # Show original if no frame
            if self.selected_slot_images and self.selected_slot_images[0] and os.path.exists(self.selected_slot_images[0]):
                try:
                    with open(self.selected_slot_images[0], "rb") as f:
                        self.gallery_preview.src_base64 = base64.b64encode(f.read()).decode()
                        self.processed_image = self.selected_slot_images[0]
                except: pass
            else:
                self.gallery_preview.src_base64 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                self.processed_image = None
            self.safe_update()
            return

        try:
            # Call ImageProcessor (heavy) - Use preview_mode for fast rendering
            out_path = ImageProcessor.apply_frame(self.selected_slot_images, self.current_layout, preview_mode=True)
            if out_path.startswith("base64:"):
                self.gallery_preview.src_base64 = out_path.replace("base64:", "")
                self.processed_image = None # Dấu hiệu cần generate lại bản high-res
            elif out_path and os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    self.gallery_preview.src_base64 = base64.b64encode(f.read()).decode()
                self.processed_image = out_path
        except Exception as e:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Lỗi xử lý ảnh: {e}"), bgcolor="red")
            self.page.snack_bar.open = True
        self.safe_update()

    def on_preview_click(self):
        # Chạm vào preview sẽ bỏ chọn ảnh cuối cùng dán vào
        if not self.current_layout or not self.selected_slot_images:
            return
        
        for i in range(len(self.selected_slot_images) - 1, -1, -1):
            if self.selected_slot_images[i] is not None:
                self.selected_slot_images[i] = None
                self.update_processed_preview()
                self.refresh_thumbnails()
                break

    def handle_print(self, _):
        out_path = self.processed_image
        if not out_path and self.current_layout:
            try:
                out_path = ImageProcessor.apply_frame(self.selected_slot_images, self.current_layout, preview_mode=False)
                self.processed_image = out_path
            except Exception as e:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Lỗi tạo ảnh in: {e}"), bgcolor="red"); self.page.snack_bar.open=True; self.safe_update()
                return
        elif not out_path and not self.current_layout and self.selected_slot_images:
            out_path = self.selected_slot_images[0]
            
        if out_path:
            self.page.snack_bar = ft.SnackBar(ft.Text("Đang gửi lệnh in... 🖨️", color="white")); self.page.snack_bar.open=True; self.safe_update()
            PrinterService.print_image(out_path)

    def handle_save(self, _):
        out_path = self.processed_image
        if not out_path and self.current_layout:
            try:
                out_path = ImageProcessor.apply_frame(self.selected_slot_images, self.current_layout, preview_mode=False)
                self.processed_image = out_path
            except Exception as e:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Lỗi lưu ảnh: {e}"), bgcolor="red"); self.page.snack_bar.open=True; self.safe_update()
                return
        
        if out_path:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ Đã lưu file chất lượng cao: {os.path.basename(out_path)}"), bgcolor="green")
            self.page.snack_bar.open=True
            self.safe_update()

    def refresh_thumbnails(self):
        self.gallery_grid.controls.clear()
        path = os.path.join(config.RAW_DIR, self.current_session)
        if os.path.exists(path):
            files = sorted([f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.png'))], key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
            for f in files:
                fpath = os.path.join(path, f)
                b64 = None
                try:
                    with open(fpath, "rb") as img_f:
                        b64 = base64.b64encode(img_f.read()).decode()
                except: pass
                
                self.gallery_grid.controls.append(
                    ft.GestureDetector(
                        on_tap=lambda _, p=fpath: self.on_thumb_click(p),
                        content=ft.Container(
                            border_radius=12, 
                            bgcolor="white",
                            border=ft.border.all(4, COLOR_PEACH_PRIMARY if fpath in self.selected_slot_images else "transparent"),
                            content=ft.Image(src_base64=b64, fit=ft.ImageFit.COVER)
                        )
                    )
                )
        self.safe_update()

    def on_thumb_click(self, path):
        # Auto-fill or toggle logic
        if self.current_layout:
            # If already selected, removing it (Toggle off)
            if path in self.selected_slot_images:
                for i in range(len(self.selected_slot_images)):
                    if self.selected_slot_images[i] == path:
                        self.selected_slot_images[i] = None
                self.update_processed_preview()
                self.refresh_thumbnails()
                return

            # Auto-fill next empty slot
            filled = False
            for i in range(len(self.selected_slot_images)):
                if self.selected_slot_images[i] is None:
                    self.selected_slot_images[i] = path
                    filled = True; break
            if not filled and self.selected_slot_images: self.selected_slot_images[0] = path
        else:
            # Single selection mode for "No Frame"
            self.selected_slot_images = [path]
        
        self.update_processed_preview()
        self.refresh_thumbnails()

    # --- Worker Callbacks ---
    def on_camera_frame(self, b64):
        self.camera_view.src_base64 = b64
        if self.camera_view.page:
            self.camera_view.update()

    def on_camera_status(self, msg):
        # Only log to console, do not show in UI
        print(f"[Camera] {msg}")
        # self.log_status_text.value = f"🟢 {msg}"
        # self.safe_update()


    def on_camera_list(self, cameras):
        self.camera_list = cameras
        self.camera_dropdown.options = [ft.dropdown.Option(key=str(k), text=v) for k, v in cameras]
        if cameras and not self.camera_dropdown.value:
            self.camera_dropdown.value = str(cameras[0][0])
        self.safe_update()

    # --- View Creation ---
    def create_home_view(self):
        # Sidebar sections
        qr_block = ft.Container(
            padding=10, border_radius=20, 
            bgcolor="#90FFFFFF", 
            border=ft.border.all(1, "#50FFFFFF"),
            shadow=ft.BoxShadow(blur_radius=15, color="#06000000", offset=ft.Offset(0, 3)),
            alignment=ft.alignment.center,  # Center the whole block content
            content=ft.Column([
                ft.Text("📲 QUÉT ĐỂ NHẬN ẢNH", weight="bold", color=COLOR_TEAL_DARK, size=11,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(
                    content=self.qr_code_img,
                    alignment=ft.alignment.center,
                    width=float("inf")  # Take full width so image centers
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
        )
        
        def open_add_session_dialog(_):
            name_input = ft.TextField(
                label="Tên khách hàng",
                autofocus=True,
                border_color=COLOR_PEACH_PRIMARY,
                text_size=24,
                text_align=ft.TextAlign.CENTER,
                on_submit=lambda e: do_add()
            )
            def do_add():
                name = name_input.value.strip().upper()
                if name:
                    safe = "".join([c if c.isalnum() else "_" for c in name]).strip("_")
                    os.makedirs(os.path.join(config.RAW_DIR, safe), exist_ok=True)
                    self.load_sessions(select_name=safe)
                    self.page.close(self.active_dialog)
                    self.safe_update()
            
            kb = VirtualKeyboard(name_input, on_submit=do_add, on_cancel=lambda: self.page.close(self.active_dialog))
            
            add_dialog = ft.AlertDialog(
                title=ft.Text("📱 NHẬP TÊN KHÁCH HÀNG", text_align=ft.TextAlign.CENTER, weight="bold"),
                modal=True,
                content=ft.Container(
                    width=700,
                    content=ft.Column([
                        name_input,
                        ft.Text("Vui lòng nhập tên viết liền hoặc dùng dấu gạch dưới (_)", size=12, color=COLOR_TEXT_MUTED),
                        ft.Divider(),
                        kb
                    ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
            self.active_dialog = add_dialog
            self.page.open(add_dialog)
            self.safe_update()

        session_block = ft.Container(
            padding=ft.padding.symmetric(horizontal=15, vertical=10), border_radius=15, 
            bgcolor="#90FFFFFF", 
            border=ft.border.all(1, "#50FFFFFF"),
            content=ft.Column([
                ft.Text("TÊN", weight="bold", size=11, color=COLOR_TEAL_DARK),
                ft.Text("Vui lòng nhập tên khách hàng", size=10, color=COLOR_TEXT_MUTED, italic=True),
                ft.Row([
                    ft.Container(self.session_dropdown, height=45, expand=True),
                    ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_color=COLOR_PEACH_PRIMARY, icon_size=22, on_click=open_add_session_dialog)
                ], alignment="spaceBetween"),
            ], spacing=3)
        )
        
        control_block = ft.Container(
            padding=15, border_radius=15, 
            bgcolor="#90FFFFFF", 
            border=ft.border.all(1, "#50FFFFFF"),
            content=ft.Column([
                ft.Container(self.camera_dropdown, height=45),
                ft.Container(self.countdown_selector, height=45),
                ft.Container(self.num_captures_selector, height=45),
                self.btn_capture
            ], spacing=8)
        )
        
        sidebar = ft.Container(
            expand=1, padding=5,
            content=ft.Column([
                qr_block,
                session_block,
                control_block,
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.COLLECTIONS_ROUNDED, size=18, color=COLOR_TEAL_DARK), 
                        ft.Text("THƯ VIỆN & RAW", weight="bold", color=COLOR_TEAL_DARK, size=12)
                    ], spacing=10, alignment="center"),
                    on_click=lambda _: self.page.go("/gallery"),
                    height=55, 
                    bgcolor="white",
                    border_radius=12,
                    border=ft.border.all(1.5, COLOR_TEAL_BORDER),
                    shadow=ft.BoxShadow(blur_radius=10, color="#08000000", offset=ft.Offset(0, 4))
                ),
                ft.Row([self.log_status_text], alignment="center")
            ], horizontal_alignment="center", alignment="start", spacing=8)
        )
        
        # --- NEW: Two-Card Split System for Home (Matching Gallery) ---

        # Camera preview container with forced 3:2 aspect ratio (no black bars)
        main_view = ft.Container(
            expand=True, 
            bgcolor="black", 
            border_radius=15,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Stack([
                # Stack fills the container; COVER mode ensures no black bars
                self.camera_view,
                ft.Container(self.countdown_overlay, alignment=ft.alignment.center),
                self.capture_progress_overlay
            ])
        )
        
        # ── LEFT GLASS CARD (Camera/Preview) ──
        left_glass = ft.Container(
            expand=3,
            bgcolor="#B0FFFFFF", 
            border_radius=30,
            padding=25,
            border=ft.border.all(1, "#60FFFFFF"),
            shadow=[
                ft.BoxShadow(blur_radius=100, color="#15000000", offset=ft.Offset(0, 40), spread_radius=-10),
                ft.BoxShadow(blur_radius=25, color="#08000000", offset=ft.Offset(0, 8))
            ],
            content=ft.Column([
                ft.Text("PREVIEW CAMERA", size=14, weight="bold", color=COLOR_TEAL_DARK),
                ft.Container(
                    content=main_view,
                    expand=True,
                    border_radius=15,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    # Enforce 3:2 aspect ratio by keeping image centered
                    alignment=ft.alignment.center,
                )
            ], spacing=15, expand=True)
        )

        # ── RIGHT GLASS CARD (Controls/QR) ──
        right_glass = ft.Container(
            expand=1,
            bgcolor="#B0FFFFFF", 
            border_radius=30,
            padding=25,
            border=ft.border.all(1, "#60FFFFFF"),
            shadow=[
                ft.BoxShadow(blur_radius=100, color="#15000000", offset=ft.Offset(0, 40), spread_radius=-10),
                ft.BoxShadow(blur_radius=25, color="#08000000", offset=ft.Offset(0, 8))
            ],
            content=ft.Column([
                qr_block,
                ft.Container(height=5),
                session_block,
                ft.Container(height=5),
                control_block,
                ft.Container(height=5),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.COLLECTIONS_ROUNDED, size=18, color=COLOR_TEAL_DARK), 
                        ft.Text("THƯ VIỆN & RAW", weight="bold", color=COLOR_TEAL_DARK, size=12)
                    ], spacing=10, alignment="center"),
                    on_click=lambda _: self.page.go("/gallery"),
                    height=55, 
                    bgcolor="white",
                    border_radius=15,
                    border=ft.border.all(1.5, COLOR_TEAL_BORDER),
                    shadow=ft.BoxShadow(blur_radius=10, color="#08000000", offset=ft.Offset(0, 4))
                ),
                ft.Row([self.log_status_text], alignment="center")
            ], spacing=10, alignment="start")
        )

        return ft.View(
            "/",
            padding=0,
            controls=[
                ft.Container(
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_left,
                        end=ft.alignment.bottom_right,
                        colors=[COLOR_MINT_BG, "white", COLOR_PEACH_BG]
                    ),
                    padding=ft.padding.all(35),
                    content=ft.Column([
                        ft.Container(
                            content=ft.Text("🍑 PHOTOBOOTH STATION", size=40, weight="bold", color=COLOR_TEAL_DARK),
                            alignment=ft.alignment.center,
                            margin=ft.margin.only(bottom=15)
                        ),
                        ft.Row([left_glass, right_glass], expand=True, spacing=30)
                    ], expand=True, spacing=15)
                )
            ]
        )

    def create_gallery_view(self):
        # ── 1. TOP BAR (System + Tabs + Search) ──
        tabs = [("⚙️", "Hệ Thống"), ("󰒄", "Classic"), ("󰄰", "Vintage"), ("󰓦", "Trendy"), ("󰞂", "Cute & Fun")]
        
        def on_tab_click(name):
            if name == "Hệ Thống": self.page.go("/admin")
            else:
                self.active_tab = name
                self.refresh_gallery_data()
            self.safe_update()

        tab_controls = []
        for icon, name in tabs:
            is_active = (name == self.active_tab)
            tab_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(icon, size=14, color=COLOR_TEAL_DARK),
                        ft.Text(name, size=13, weight="600", color=COLOR_TEAL_DARK)
                    ], spacing=5),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=10,
                    bgcolor="white" if not is_active else COLOR_PEACH_BG,
                    border=ft.border.all(1, COLOR_TEAL_BORDER) if is_active else None,
                    on_click=lambda e, n=name: on_tab_click(n),
                )
            )

        top_nav = ft.Row([ft.Row(tab_controls, spacing=10), ft.Container(expand=True), self.gallery_search], alignment=ft.MainAxisAlignment.START)

        left_card = ft.Container(
            expand=3,
            bgcolor="#B0FFFFFF", 
            border_radius=30,
            padding=25,
            border=ft.border.all(1, "#60FFFFFF"), # Stronger Light Edge
            shadow=[
                ft.BoxShadow(
                    blur_radius=120, 
                    color="#1A000000", 
                    offset=ft.Offset(0, 45),
                    spread_radius=-15
                ),
                ft.BoxShadow(
                    blur_radius=30, 
                    color="#08000000", 
                    offset=ft.Offset(0, 10),
                )
            ],
            content=ft.Column([
                # ── 1. PREVIEW BOX (Top) ──
                ft.Container(
                    content=self.gallery_preview,
                    expand=True, 
                    alignment=ft.alignment.center,
                    border_radius=20,
                    bgcolor="#95FFFFFF",
                    border=ft.border.all(1, "#40FFFFFF"),
                    padding=15,
                    shadow=ft.BoxShadow(
                        blur_radius=25, 
                        color="#0F000000", 
                        offset=ft.Offset(0, 5)
                    )
                ),
                
                # ── 2. ACTIONS BOX (Bottom Row: Templates + Back) ──
                ft.Row([
                    # Templates Card
                    ft.Container(
                        expand=True,
                        content=ft.Column([
                            ft.Text("Templates", size=12, weight="600", color=COLOR_TEAL_DARK),
                            self.frame_selector_grid
                        ], spacing=8),
                        bgcolor="#45FFFFFF",
                        padding=ft.padding.all(12),
                        border_radius=20,
                        border=ft.border.all(1, "#35FFFFFF"),
                        height=200,
                        shadow=ft.BoxShadow(
                            blur_radius=20, 
                            color="#0A000000", 
                            offset=ft.Offset(0, 4)
                        )
                    ),
                    # Back Card
                    ft.Container(
                        content=ft.Text("BACK ←", size=13, weight="bold", color=COLOR_TEAL_DARK),
                        padding=ft.padding.symmetric(horizontal=25, vertical=12),
                        border_radius=15,
                        bgcolor="#B0FFFFFF",
                        on_click=lambda _: self.page.go("/"),
                        alignment=ft.alignment.center
                    )
                ], spacing=15, vertical_alignment=ft.CrossAxisAlignment.END)
            ], spacing=20)
        )

        # ── 3. RIGHT GLASS CARD (Library & Processing) ──
        right_card = ft.Container(
            expand=2,
            bgcolor="#B0FFFFFF", 
            border_radius=30,
            padding=25,
            border=ft.border.all(1, "#60FFFFFF"),
            shadow=[
                ft.BoxShadow(
                    blur_radius=120, 
                    color="#1A000000", 
                    offset=ft.Offset(0, 45),
                    spread_radius=-15
                ),
                ft.BoxShadow(
                    blur_radius=30, 
                    color="#08000000", 
                    offset=ft.Offset(0, 10),
                )
            ],
            content=ft.Column([
                ft.Row([
                    # Left Section: Filter selection
                    ft.Column([
                        ft.Row([
                            ft.Text("chọn ảnh", size=24, weight="bold", color=COLOR_TEAL_DARK),
                            ft.Row(expand=True),
                        ]),
                        ft.Text("Choose a filter to style your photo.", size=12, color=COLOR_TEXT_MUTED),
                        ft.Container(self.gallery_grid, expand=True, margin=ft.margin.only(top=10)),
                    ], expand=True, spacing=5),
                    
                    # Right Section: QR & Camera Button (Enlarged to fill space)
                    ft.Column([
                        ft.Text("Quét QR để nhận ảnh", size=14, weight="bold", color=COLOR_TEAL_DARK),
                        ft.Container(
                            content=self.qr_code_img, 
                            width=240, height=240, # Max QR
                            border_radius=25, 
                            bgcolor="#F5FFFFFF", 
                            padding=20,
                            shadow=ft.BoxShadow(blur_radius=30, color="#15000000", offset=ft.Offset(0, 8))
                        ),
                        ft.Container(
                            content=ft.Icon(ft.Icons.CAMERA_ALT_ROUNDED, color="white", size=60), # Hero Icon
                            width=240,
                            expand=True, # Fill all vertical red space
                            bgcolor=COLOR_PEACH_PRIMARY,
                            border_radius=25,
                            on_click=self.on_capture_click,
                            alignment=ft.alignment.center,
                            shadow=ft.BoxShadow(blur_radius=15, color="#40E59A84", offset=ft.Offset(0, 6)),
                        ),
                    ], spacing=25, horizontal_alignment="center")
                ], expand=True, spacing=15),
                
                # Footer Action Buttons (Redesigned for compact iOS-style)
                ft.Row([
                    # Print Button (Styled like "BACK ←")
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.PRINT_ROUNDED, size=18, color=COLOR_TEAL_DARK), 
                            ft.Text("IN ẢNH", weight="bold", color=COLOR_TEAL_DARK)
                        ], spacing=8, alignment="center"),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                        border_radius=15,
                        border=ft.border.all(1.5, COLOR_TEAL_BORDER),
                        on_click=self.handle_print,
                        bgcolor="white",
                        alignment=ft.alignment.center
                    ),
                    # Save Button (Styled like "NEXT →")
                    ft.Container(
                        content=ft.Row([
                            ft.Text("HOÀN THÀNH & LƯU", size=14, weight="bold", color="white"),
                            ft.Text(" →", size=16, weight="bold", color="white"),
                        ], alignment="center", spacing=5),
                        padding=ft.padding.symmetric(horizontal=35, vertical=15),
                        border_radius=15,
                        bgcolor=COLOR_PEACH_PRIMARY,
                        on_click=self.handle_save,
                        alignment=ft.alignment.center,
                        shadow=ft.BoxShadow(
                            blur_radius=15, 
                            color="#50E59A84", 
                            offset=ft.Offset(0, 5)
                        )
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ])
        )

        return ft.View(
            "/gallery",
            padding=0,
            controls=[
                ft.Container(
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_left,
                        end=ft.alignment.bottom_right,
                        colors=[COLOR_MINT_BG, "white", COLOR_PEACH_BG]
                    ),
                    padding=ft.padding.all(35),
                    content=ft.Column([
                        ft.Container(
                            content=ft.Text("THƯ VIỆN & XỬ LÝ ẢNH", size=28, weight="bold", color=COLOR_TEAL_DARK),
                            alignment=ft.alignment.center,
                            margin=ft.margin.only(bottom=15)
                        ),
                        top_nav,
                        ft.Row([left_card, right_card], expand=True, spacing=30)
                    ], expand=True, spacing=15)
                )
            ]
        )

    def create_admin_view(self):
        # Local state for dialogs
        def on_add_session(_):
            name_input = ft.TextField(label="Tên khách hàng mới", on_submit=lambda e: do_add())
            def do_add():
                name = name_input.value.strip()
                if name:
                    safe = "".join([c if c.isalnum() else "_" for c in name]).strip("_")
                    os.makedirs(os.path.join(config.RAW_DIR, safe), exist_ok=True)
                    self.load_sessions(select_name=safe)
                    self.page.close(self.active_dialog)
                    self.safe_update()
            self.active_dialog = ft.AlertDialog(
                title=ft.Text("Thêm Phiên Mới"), 
                content=name_input, 
                actions=[ft.ElevatedButton("Thêm", on_click=lambda _: do_add())]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        def on_rename_session(_):
            name_input = ft.TextField(label="Tên mới", value=self.current_session)
            def do_rename():
                name = name_input.value.strip()
                if name and name != self.current_session and self.current_session != "Khach_Mac_Dinh":
                    safe = "".join([c if c.isalnum() else "_" for c in name]).strip("_")
                    os.rename(os.path.join(config.RAW_DIR, self.current_session), os.path.join(config.RAW_DIR, safe))
                    self.load_sessions(select_name=safe)
                    self.page.close(self.active_dialog)
                    self.safe_update()
            self.active_dialog = ft.AlertDialog(
                title=ft.Text("Đổi Tên Phiên"), 
                content=name_input, 
                actions=[ft.ElevatedButton("Lưu", on_click=lambda _: do_rename())]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        def copy_path(_):
            self.page.set_clipboard(os.path.abspath(os.path.join(config.RAW_DIR, self.current_session)))
            self.page.snack_bar = ft.SnackBar(ft.Text("Đã copy đường dẫn!")); self.page.snack_bar.open = True; self.safe_update()

        # Layout list
        layouts_col = ft.Column(spacing=10)
        def refresh_layout_list():
            layouts_col.controls.clear()
            for l in self.layout_manager.get_all_layouts():
                layouts_col.controls.append(ft.Row([
                    ft.Text(l["name"], expand=True, size=18),
                    ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, name=l["name"]: delete_layout(name))
                ]))
            self.safe_update()

        def delete_layout(name):
            self.layout_manager.delete_layout(name); refresh_layout_list(); self.refresh_gallery_data()

        refresh_layout_list()

        def test_nc(_):
            self.page.snack_bar = ft.SnackBar(ft.Text("Đang kiểm tra kết nối...")); self.page.snack_bar.open = True; self.safe_update()
            success, result = nc_get_public_link(vars(config))
            if success:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ Thành công! Link: {result}"), bgcolor="green")
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ Thất bại: {result}"), bgcolor="red")
            self.page.snack_bar.open = True; self.safe_update()

        # Cloud Settings
        nc_enabled = ft.Checkbox(label="Kích hoạt Nextcloud", value=config.NC_ENABLED)
        nc_url = ft.TextField(label="WebDAV URL", value=config.NC_URL)
        nc_user = ft.TextField(label="Username", value=config.NC_USER)
        nc_pass = ft.TextField(label="App Password", value=config.NC_PASS, password=True, can_reveal_password=True)
        nc_root = ft.TextField(label="Thư mục gốc", value=config.NC_REMOTE_PATH)
        nc_share = ft.TextField(label="Public Share URL", value=config.NC_SHARE_URL)

        def save_and_exit(_):
            config.NC_ENABLED = nc_enabled.value
            config.NC_URL = nc_url.value; config.NC_USER = nc_user.value; config.NC_PASS = nc_pass.value
            config.NC_REMOTE_PATH = nc_root.value; config.NC_SHARE_URL = nc_share.value
            config.MIRROR_MODE = mirror_toggle.value
            config.CAMERA_QUALITY = int(quality_dropdown.value)
            config.save_config(); self.update_qr_code(); self.page.go("/")

        # System Settings
        mirror_toggle = ft.Switch(label="Chế độ Mirror (Phản chiếu)", value=config.MIRROR_MODE)
        quality_dropdown = ft.Dropdown(
            label="Chất lượng ảnh Preview",
            value=str(config.CAMERA_QUALITY),
            options=[ft.dropdown.Option(str(q)) for q in [60, 70, 80, 90, 100]]
        )

        return ft.View(
            "/admin",
            controls=[
                ft.AppBar(title=ft.Text("ADMIN PANEL"), bgcolor=COLOR_PEACH_PRIMARY, color="white"),
                ft.Tabs(
                    expand=True,
                    selected_index=0,
                    tabs=[
                        ft.Tab(text="PHIÊN CHỤP", content=ft.Container(padding=20, content=ft.Column([
                            ft.Text(f"Phiên hiện tại: {self.current_session}", size=20, weight="bold"),
                            ft.Row([
                                ft.ElevatedButton("➕ Thêm Phiên", on_click=on_add_session, expand=True),
                                ft.ElevatedButton("✏️ Đổi Tên", on_click=on_rename_session, expand=True),
                                ft.ElevatedButton("🗑️ Xóa Phiên", on_click=self.handle_delete_session, bgcolor="red", color="white", expand=True),
                            ]),
                            ft.ElevatedButton("📋 Copy đường dẫn folder", on_click=copy_path),
                        ], spacing=20))),
                        ft.Tab(text="DANH SÁCH LAYOUT", content=ft.Container(padding=20, content=ft.Column([layouts_col], scroll=ft.ScrollMode.AUTO))),
                        ft.Tab(text="NEXTCLOUD CLOUD", content=ft.Container(padding=20, content=ft.Column([
                            nc_enabled, nc_url, nc_user, nc_pass, nc_root, nc_share,
                            ft.ElevatedButton("⚡ Kiểm tra kết nối & Lấy link share", on_click=test_nc)
                        ], scroll=ft.ScrollMode.AUTO, spacing=15))),
                        ft.Tab(text="HỆ THỐNG", content=ft.Container(padding=20, content=ft.Column([
                            ft.ElevatedButton("📂 Thư mục RAW", icon=ft.Icons.FOLDER_OPEN, on_click=lambda _: os.startfile(os.path.abspath(config.RAW_DIR))),
                            ft.ElevatedButton("📂 Thư mục OUTPUT", icon=ft.Icons.FOLDER_SPECIAL, on_click=lambda _: os.startfile(os.path.abspath(config.OUTPUT_DIR))),
                            ft.Divider(),
                            mirror_toggle,
                            quality_dropdown,
                            ft.Divider(),
                            ft.ElevatedButton(f"🔄 Chế độ App: {config.APP_MODE.upper()}", on_click=self.toggle_mode, width=300),
                            ft.Text("Peach Photobooth Station Pro v2.0", size=14, color=COLOR_TEXT_MUTED)
                        ])))
                    ]
                ),
                ft.Container(padding=20, content=ft.ElevatedButton("LƯU VÀ QUAY LẠI", height=60, width=float("inf"), bgcolor=COLOR_PEACH_PRIMARY, color="white", on_click=save_and_exit))
            ]
        )

    def handle_delete_session(self, e):
        if self.current_session == "Khach_Mac_Dinh": return
        def confirm_delete(_):
            shutil.rmtree(os.path.join(config.RAW_DIR, self.current_session))
            self.load_sessions()
            self.page.close(self.active_dialog)
            self.safe_update()

        self.active_dialog = ft.AlertDialog(
            title=ft.Text("Xác nhận xóa"),
            content=ft.Text(f"Bạn có chắc muốn xóa phiên '{self.current_session}'?"),
            actions=[
                ft.TextButton("Hủy", on_click=lambda _: self.page.close(self.active_dialog)), 
                ft.ElevatedButton("Xóa", bgcolor="red", color="white", on_click=confirm_delete)
            ]
        )
        self.page.open(self.active_dialog)
        self.safe_update()

    def toggle_mode(self, e):
        config.APP_MODE = "normal" if config.APP_MODE == "wedding" else "wedding"
        e.control.text = f"🔄 Chế độ: {config.APP_MODE.upper()}"
        self.safe_update()

def main(page: ft.Page):
    FletPhotoboothApp(page)

if __name__ == "__main__":
    ft.app(target=main)
