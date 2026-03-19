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
from nextcloud_utils import upload_to_nextcloud, nc_get_public_link
from printer_service import PrinterService
from image_processor import ImageProcessor
import re
import json
import sys
import subprocess
import traceback
from PIL import Image as PILImage
import httpx

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
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.horizontal_alignment = ft.CrossAxisAlignment.START
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        
        # --- Window Configuration ---
        # Explicitly set dimensions and position to avoid layout race conditions on startup
        self.page.window.width = 1600
        self.page.window.height = 1000
        self.page.window.min_width = 1200
        self.page.window.min_height = 800
        self.page.window.resizable = True
        self.page.window.maximized = False
        self.page.window.center()
        self.page.window.to_front()
        self.page.update()
        
        # Give the OS a moment to apply window sizing before we start building the UI
        time.sleep(0.3) # Increased slightly for better reliability on slower systems
        self.page.update() 
        
        # --- Application State ---
        self.current_session = "vows_08_march"
        self.sessions = []
        self.camera_list = []
        self.captured_sequence_paths = []
        self.remaining_captures = 0
        self.total_captures = 1
        self.is_capturing = False
        self.payment_completed = False
        self.payment_timestamp = 0
        self.current_order_id = None
        
        # Gallery State
        self.selected_slot_images = []
        self.current_layout = None
        self.processed_image = None
        self.layout_manager = FrameLayoutManager(
            config_dir=config.COORDINATES_DIR, 
            frames_dir=config.FRAMES_DIR
        )
        self.layout_manager.load_layouts()
        
        # File Picker for frames
        self.fp_frames = ft.FilePicker(on_result=self.on_frame_pick_result)
        self.page.overlay.append(self.fp_frames)
        self.active_layout_dialog_dropdown = None # Ref to update dropdown after pick
        
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
        
        # Final startup sequence: Wait, Go, Force Update
        time.sleep(0.1)
        self.page.go("/")
        self.page.update()
        
        # Current Tab State
        self.active_tab = "Classic"
        
        # Delayed Worker Startup
        threading.Thread(target=self.start_backend, daemon=True).start()

    def setup_ui_references(self):
        # Home Screen Elements
        # Placeholder 1x1 transparent gif to avoid red error box
        self.camera_view = ft.Image(
            src_base64="R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
            fit=ft.ImageFit.COVER,
            expand=True,
            gapless_playback=True
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
        self.qr_code_img = ft.Image(src_base64="R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", width=160, height=160, fit=ft.ImageFit.CONTAIN) # Even smaller QR
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
                ft.Text(self._get_capture_btn_label(), size=18, weight="bold", color="white"),
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
        self.gallery_preview = ft.Image(src_base64="R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", fit=ft.ImageFit.CONTAIN) # Target: Center and Fit
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
        # Ensure default session directory exists
        os.makedirs(os.path.join(config.RAW_DIR, "vows_08_march"), exist_ok=True)
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
            if config.ADMIN_PASSWORD_ENABLED:
                self.show_admin_password_dialog()
            else:
                self.page.go("/admin")
        elif e.alt and e.key == "Enter":
            self.page.window_full_screen = not self.page.window_full_screen
            self.safe_update()

    def route_change(self, e):
        try:
            print(f"DEBUG: Route changing to {self.page.route}")
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
        except Exception as ex:
            print(f"ERROR in route_change: {ex}")
            traceback.print_exc()
            self.page.views.append(ft.View("/error", controls=[ft.Text(f"Lỗi chuyển trang: {ex}", color="red")]))
            self.safe_update()

    # --- Feature: Session & QR ---
    def load_sessions(self, select_name=None):
        os.makedirs(config.RAW_DIR, exist_ok=True)
        dirs = [d for d in os.listdir(config.RAW_DIR) if os.path.isdir(os.path.join(config.RAW_DIR, d))]
        if not dirs: dirs = ["Khach_Mac_Dinh"]
        self.sessions = sorted(dirs)
        self.session_dropdown.options = [ft.dropdown.Option(s) for s in self.sessions]
        
        # Priority: select_name > "vows_08_march" > "Khach_Mac_Dinh" > first alphabetically
        if select_name and select_name in self.sessions:
            self.current_session = select_name
        elif "vows_08_march" in self.sessions:
            self.current_session = "vows_08_march"
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

    def show_admin_password_dialog(self):
        pw_input = ft.TextField(
            label="Nhập mật khẩu Admin",
            password=True,
            can_reveal_password=True,
            autofocus=True,
            on_submit=lambda _: do_verify()
        )
        
        def do_verify():
            if pw_input.value == "08032026":
                self.page.close(self.active_dialog)
                self.page.go("/admin")
            else:
                pw_input.error_text = "Sai mật khẩu!"
                pw_input.update()

        kb = VirtualKeyboard(pw_input, on_submit=do_verify, on_cancel=lambda: self.page.close(self.active_dialog))
        
        self.active_dialog = ft.AlertDialog(
            title=ft.Text("🔒 XÁC THỰC QUYỀN ADMIN", weight="bold"),
            content=ft.Container(
                width=600,
                content=ft.Column([
                    pw_input,
                    ft.Divider(),
                    kb
                ], tight=True)
            ),
            modal=True
        )
        self.page.open(self.active_dialog)
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

    def on_frame_pick_result(self, e: ft.FilePickerResultEvent):
        if e.files:
            file = e.files[0]
            dest = os.path.join(self.layout_manager.frames_dir, file.name).replace("\\", "/")
            if not os.path.exists(dest):
                shutil.copy2(file.path, dest)
            
            # Update the dropdown if it exists
            if self.active_layout_dialog_dropdown:
                self.active_layout_dialog_dropdown.options.append(ft.dropdown.Option(dest, text=file.name))
                self.active_layout_dialog_dropdown.value = dest
                self.active_layout_dialog_dropdown.update()
                # Trigger internal logic for frame preview change
                self.active_layout_dialog_dropdown.on_change(ft.ControlEvent("", "change", dest, self.active_layout_dialog_dropdown, self.page))

    # --- Helpers ---
    def _get_capture_btn_label(self):
        return "📷 CHỤP C1" if config.CAPTURE_ONE_MODE else "CHỤP ẢNH NGAY"

    def _update_capture_btn_label(self):
        """Refresh the capture button text to match current mode."""
        row = self.btn_capture.content
        row.controls[0].value = self._get_capture_btn_label()
        try:
            self.btn_capture.update()
        except:
            pass

    # --- Feature: Capture Sequence ---
    def on_capture_click(self, e):
        # ── Payment Check ──
        if config.PAYMENT_ENABLED and not self.is_session_active():
            self.show_payment_dialog()
            return

        # Route to Capture One flow if mode is active
        if config.CAPTURE_ONE_MODE:
            self.on_capture_one_click()
            return

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

    def is_session_active(self):
        if not config.PAYMENT_ENABLED: return True
        if not self.payment_completed: return False
        # Session valid for 5 mins (300 seconds)
        if time.time() - self.payment_timestamp > 300:
            self.payment_completed = False
            return False
        return True

    def show_payment_dialog(self):
        qr_img = ft.Image(src_base64="R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", width=300, height=300, fit="contain")
        order_id_text = ft.Text("", selectable=True, weight="bold", size=16, color="blue")
        status_text = ft.Text("ĐANG KHỞI TẠO THANH TOÁN...", weight="bold", color=COLOR_TEAL_DARK)
        progress = ft.ProgressBar(width=300, color=COLOR_PEACH_PRIMARY)
        
        def close_dialog(_):
            self.page.close(self.active_dialog)
            self.stop_polling = True

        self.active_dialog = ft.AlertDialog(
            title=ft.Text("💳 THANH TOÁN ĐỂ CHỤP ẢNH", weight="bold", text_align="center"),
            content=ft.Container(
                width=400,
                content=ft.Column([
                    ft.Text(f"Số tiền: {config.PAYMENT_AMOUNT:,} VNĐ", size=20, weight="bold", color=COLOR_PEACH_PRIMARY),
                    ft.Container(qr_img, alignment=ft.alignment.center, padding=10),
                    ft.Row([ft.Text("Mã đơn hàng: ", size=12), order_id_text], alignment="center"),
                    status_text,
                    progress,
                    ft.Text("Vui lòng quét mã QR để thanh toán. Hệ thống sẽ tự động bắt đầu khi nhận được tiền.", 
                            size=12, color=COLOR_TEXT_MUTED, text_align="center"),
                ], horizontal_alignment="center", tight=True)
            ),
            actions=[
                ft.TextButton("Hủy", on_click=close_dialog)
            ],
            modal=True
        )
        self.page.open(self.active_dialog)
        self.safe_update()

        # Logic gọi Server
        self.stop_polling = False
        def payment_thread():
            try:
                # 1. Create order
                res = httpx.post(f"{config.PAYMENT_URL}/payments/create", json={
                    "package_id": config.PAYMENT_PACKAGE_ID,
                    "amount": config.PAYMENT_AMOUNT,
                    "description": f"Chụp ảnh Photobooth - {self.current_session}"
                }, timeout=10)
                
                if res.status_code == 200:
                    data = res.json()
                    self.current_order_id = data["order_id"]
                    order_id_text.value = self.current_order_id
                    
                    # Tạo QR code từ chuỗi trả về
                    # Mock server trả về string "PAYMENT://...", ta cần tạo image
                    import qrcode
                    qr = qrcode.QRCode(box_size=10, border=1)
                    qr.add_data(data["qr_code"])
                    qr.make(fit=True)
                    qr_pil = qr.make_image(fill_color="black", back_color="white")
                    
                    buff = BytesIO()
                    qr_pil.save(buff, format="PNG")
                    qr_img.src_base64 = base64.b64encode(buff.getvalue()).decode()
                    status_text.value = "⏳ ĐANG CHỜ THANH TOÁN..."
                    self.safe_update()

                    # 2. Polling
                    start_time = time.time()
                    while not self.stop_polling and (time.time() - start_time < 300): # 5 mins timeout
                        poll_res = httpx.get(f"{config.PAYMENT_URL}/payments/{self.current_order_id}/status")
                        if poll_res.status_code == 200:
                            p_data = poll_res.json()
                            if p_data["status"] == "paid":
                                status_text.value = "✅ THANH TOÁN THÀNH CÔNG!"
                                status_text.color = "green"
                                progress.visible = False
                                self.safe_update()
                                
                                # Call photobooth/start to confirm
                                httpx.post(f"{config.PAYMENT_URL}/photobooth/start", json={"order_id": self.current_order_id})
                                
                                time.sleep(1.5)
                                self.payment_completed = True
                                self.payment_timestamp = time.time() # Store session start
                                self.page.close(self.active_dialog)
                                # Hide start overlay if present
                                self.start_overlay.visible = False
                                # START CAPTURE AFTER PAID
                                self.on_capture_click(None)
                                break
                            elif p_data["status"] in ["failed", "expired"]:
                                status_text.value = f"❌ THẤT BẠI: {p_data['status'].upper()}"
                                status_text.color = "red"
                                progress.visible = False
                                self.safe_update()
                                break
                        
                        time.sleep(2)
                else:
                    status_text.value = "❌ LỖI KẾT NỐI SERVER"
                    status_text.color = "red"
                    progress.visible = False
                    self.safe_update()
            except Exception as ex:
                print(f"Payment Error: {ex}")
                status_text.value = f"❌ LỖI: {str(ex)[:30]}"
                status_text.color = "red"
                progress.visible = False
                self.safe_update()

        threading.Thread(target=payment_thread, daemon=True).start()

    def _activate_window_fast(self, hwnd):
        """Force-focus a window by HWND using win32 API — much faster than pygetwindow.activate()."""
        try:
            import win32gui
            import win32con
            # Restore if minimized
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            print(f"[C1] ✅ win32 SetForegroundWindow OK (hwnd={hwnd})")
        except Exception as ex:
            print(f"[C1] ⚠️  win32 activate failed: {ex}")

    def _find_capture_one_window(self):
        """Find the Capture One window by searching all open windows. Returns (hwnd, title)."""
        # Build keyword list from config (comma-separated)
        keywords = [kw.strip() for kw in config.CAPTURE_ONE_WINDOW_TITLE.split(",") if kw.strip()]
        try:
            import win32gui
            result = []
            def enum_cb(hwnd, _):
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                if any(kw in title for kw in keywords):
                    result.append((hwnd, title))
            win32gui.EnumWindows(enum_cb, None)
            if result:
                hwnd, title = result[0]
                print(f"[C1] Found window: '{title}' (hwnd={hwnd})")
                return hwnd, title
        except Exception as ex:
            print(f"[C1] win32gui error: {ex}")
        return None, None

    def on_capture_one_click(self):
        """Trigger Capture One instantly: find window → force focus → Ctrl+K → back to gallery."""
        import pyautogui

        def _run():
            try:
                # ── STEP 1: Find Capture One window ──
                hwnd, title = self._find_capture_one_window()

                if hwnd:
                    print(f"[C1] ✅ Capture One đang mở: '{title}' — force focus...")
                    self._activate_window_fast(hwnd)
                    time.sleep(0.15)  # Tối thiểu để Windows xử lý focus
                else:
                    # Chưa mở → launch exe
                    print("[C1] ⚠️  Không thấy Capture One — thử mở ứng dụng...")
                    co_exe_names = ["CaptureOne.exe", "Capture One 23.exe", "Capture One.exe"]
                    for exe in co_exe_names:
                        try:
                            subprocess.Popen(["cmd", "/c", "start", "", exe], shell=True)
                            print(f"[C1] 🚀 Đã launch: {exe}")
                            break
                        except:
                            pass
                    print("[C1] Đợi Capture One khởi động (3s)...")
                    time.sleep(3.0)
                    hwnd, title = self._find_capture_one_window()
                    if hwnd:
                        print(f"[C1] ✅ Tìm thấy sau launch: '{title}'")
                        self._activate_window_fast(hwnd)
                        time.sleep(0.15)
                    else:
                        print("[C1] ❌ Vẫn không tìm thấy Capture One!")

                # ── STEP 2: Gửi Ctrl+K ngay lập tức ──
                print("[C1] Gửi Ctrl+K...")
                pyautogui.hotkey('ctrl', 'k')
                print("[C1] ✅ Đã gửi Ctrl+K.")

                # ── STEP 3: Navigate về gallery ngay (không chờ focus Photobooth) ──
                self.page.go("/gallery")
                self.safe_update()
                print("[C1] ✅ Đã chuyển về Thư viện & Raw.")

            except Exception as ex:
                print(f"[C1] ❌ Lỗi: {ex}")
                traceback.print_exc()

        threading.Thread(target=_run, daemon=True).start()

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
        # Do not reset payment here to allow "Back" and retry within 5 mins
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
            # Filter by Search
            search_query = self.gallery_search.value.lower() if self.gallery_search.value else ""
            if search_query and search_query not in l["name"].lower():
                continue
            
            # Filter by Category Tab
            if self.active_tab and self.active_tab != "Hệ Thống" and l.get("category") != self.active_tab:
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
            # Reset payment session after printing
            self.payment_completed = False
            self.payment_timestamp = 0

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
            # Reset payment session after saving
            self.payment_completed = False
            self.payment_timestamp = 0
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
            chosen = str(cameras[0][0])
            self.camera_dropdown.value = chosen
            # Automatically start preview for the first detected camera
            self.camera_worker.change_camera(chosen)
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
        self.start_overlay = ft.Container(
            bgcolor="rgba(0,0,0,0.7)",
            padding=40,
            border_radius=15,
            alignment=ft.alignment.center,
            visible=not self.is_session_active(),
            content=ft.Column([
                ft.Text("BẮT ĐẦU TRẢI NGHIỆM", size=32, weight="bold", color="white", text_align="center"),
                ft.Text(f"Nhấn vào nút bên dưới để thanh toán ({config.PAYMENT_AMOUNT:,} VNĐ)", color="white70", size=14),
                ft.Container(height=20),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Text("BẮT ĐẦU NGAY", size=20, weight="bold"), 
                        ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED)
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=COLOR_PEACH_PRIMARY,
                    color="white",
                    height=70, width=300,
                    on_click=self.on_capture_click,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15))
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True)
        )

        main_view = ft.Container(
            expand=True, 
            bgcolor="black", 
            border_radius=15,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Stack([
                # Stack fills the container; COVER mode ensures no black bars
                self.camera_view,
                ft.Container(self.countdown_overlay, alignment=ft.alignment.center),
                self.capture_progress_overlay,
                self.start_overlay # Always on top until hidden
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
                    padding=ft.padding.all(15),
                    content=ft.Column([
                        ft.Container(
                            content=ft.Text("🍑 PHOTOBOOTH STATION", size=50, weight="bold", color=COLOR_TEAL_DARK),
                            alignment=ft.alignment.center,
                            margin=ft.margin.only(bottom=15)
                        ),
                        ft.Row([left_glass, right_glass], expand=True, spacing=30)
                    ], expand=True, spacing=15)
                )
            ]
        )

    def create_gallery_view(self):
        # ── 1. TOP BAR (Tabs + Search) ──
        # Load categories from manager
        cats = self.layout_manager.get_all_categories()
        tabs = [] # Removed "Hệ Thống" tab
        for c in cats:
            # Map common names to icons if possible
            icon = "󰏗"
            if "Classic" in c: icon = "󰒄"
            elif "Vintage" in c: icon = "󰄰"
            elif "Trendy" in c: icon = "󰓦"
            elif "Cute" in c: icon = "󰞂"
            elif "Wedding" in c: icon = "💍"
            tabs.append((icon, c))
        
        def on_tab_click(name):
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
        # 1. PHIÊN CHỤP (SESSION) MANAGEMENT
        sessions_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def refresh_session_list():
            sessions_list.controls.clear()
            os.makedirs(config.RAW_DIR, exist_ok=True)
            dirs = sorted([d for d in os.listdir(config.RAW_DIR) if os.path.isdir(os.path.join(config.RAW_DIR, d))])
            if not dirs: dirs = ["Khach_Mac_Dinh"]
            
            for d in dirs:
                is_current = (d == self.current_session)
                sessions_list.controls.append(
                    ft.Container(
                        padding=15,
                        border_radius=15,
                        bgcolor="#90FFFFFF" if is_current else "#40FFFFFF",
                        border=ft.border.all(2, COLOR_PEACH_PRIMARY) if is_current else ft.border.all(1, "#20000000"),
                        content=ft.Row([
                            ft.Icon(ft.Icons.FOLDER_SPECIAL if is_current else ft.Icons.FOLDER_OUTLINED, 
                                   color=COLOR_PEACH_PRIMARY if is_current else COLOR_TEXT_MUTED, size=24),
                            ft.Column([
                                ft.Text(d, size=16, weight="bold", color=COLOR_TEAL_DARK if is_current else "black"),
                                ft.Text("Đang được chọn" if is_current else "Phiên cũ", size=11, color=COLOR_TEXT_MUTED),
                            ], expand=True, spacing=2),
                            ft.Row([
                                ft.IconButton(ft.Icons.CHECK_CIRCLE_OUTLINE, tooltip="Chọn phiên này", icon_color=COLOR_PEACH_PRIMARY, 
                                             on_click=lambda e, s=d: select_session(s), visible=not is_current),
                                ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Đổi tên", icon_color="blue", on_click=lambda e, s=d: on_rename_session_item(s)),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Xóa phiên", icon_color="red", 
                                             on_click=lambda e, s=d: on_delete_session_item(s), visible=(d != "Khach_Mac_Dinh")),
                            ])
                        ])
                    )
                )
            # self.safe_update() - Removed because it can cause issues during initial route view creation

        def select_session(name):
            self.current_session = name
            self.on_session_change(name)
            refresh_session_list()
            self.page.snack_bar = ft.SnackBar(ft.Text(f"🚀 Đã chuyển sang phiên: {name}"), bgcolor=COLOR_TEAL_DARK)
            self.page.snack_bar.open = True
            self.safe_update()

        def on_add_session(_):
            name_input = ft.TextField(label="Tên khách hàng mới", autofocus=True)
            def do_add():
                name = name_input.value.strip()
                if name:
                    safe = "".join([c if c.isalnum() else "_" for c in name]).strip("_")
                    os.makedirs(os.path.join(config.RAW_DIR, safe), exist_ok=True)
                    self.load_sessions(select_name=safe)
                    refresh_session_list()
                    self.page.close(self.active_dialog)
                    self.safe_update()
            
            self.active_dialog = ft.AlertDialog(
                title=ft.Text("Thêm Phiên Mới"),
                content=name_input,
                actions=[
                    ft.TextButton("Hủy", on_click=lambda _: self.page.close(self.active_dialog)),
                    ft.ElevatedButton("Tạo Thư Mục", on_click=lambda _: do_add(), bgcolor=COLOR_PEACH_PRIMARY, color="white")
                ]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        def on_rename_session_item(old_name):
            name_input = ft.TextField(label="Tên mới", value=old_name, autofocus=True)
            def do_rename():
                name = name_input.value.strip()
                if name and name != old_name and old_name != "Khach_Mac_Dinh":
                    safe = "".join([c if c.isalnum() else "_" for c in name]).strip("_")
                    try:
                        os.rename(os.path.join(config.RAW_DIR, old_name), os.path.join(config.RAW_DIR, safe))
                        if self.current_session == old_name:
                            self.current_session = safe
                        self.load_sessions(select_name=self.current_session)
                        refresh_session_list()
                        self.page.close(self.active_dialog)
                    except Exception as ex:
                        self.page.snack_bar = ft.SnackBar(ft.Text(f"Lỗi: {ex}")); self.page.snack_bar.open=True
                self.safe_update()
            
            self.active_dialog = ft.AlertDialog(
                title=ft.Text(f"Đổi Tên Phiên '{old_name}'"),
                content=name_input,
                actions=[
                    ft.TextButton("Hủy", on_click=lambda _: self.page.close(self.active_dialog)),
                    ft.ElevatedButton("Lưu Tên Mới", on_click=lambda _: do_rename(), bgcolor=COLOR_PEACH_PRIMARY, color="white")
                ]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        def on_delete_session_item(name):
            def confirm_delete(_):
                try:
                    shutil.rmtree(os.path.join(config.RAW_DIR, name))
                    if self.current_session == name:
                        self.load_sessions()
                    else:
                        refresh_session_list()
                    self.page.close(self.active_dialog)
                except Exception as ex:
                    self.page.snack_bar = ft.SnackBar(ft.Text(f"Lỗi: {ex}")); self.page.snack_bar.open=True
                self.safe_update()

            self.active_dialog = ft.AlertDialog(
                title=ft.Text("Xác nhận xóa"),
                content=ft.Text(f"Bạn có chắc muốn xóa phiên '{name}'? Dữ liệu ảnh bên trong sẽ bị xóa vĩnh viễn."),
                actions=[
                    ft.TextButton("Hủy", on_click=lambda _: self.page.close(self.active_dialog)),
                    ft.ElevatedButton("Xóa Vĩnh Viễn", bgcolor="red", color="white", on_click=confirm_delete)
                ]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        # 2. LAYOUT MANAGEMENT
        layouts_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def refresh_layout_list():
            layouts_col.controls.clear()
            self.layout_manager.load_layouts() # Reload from disk
            for l in self.layout_manager.get_all_layouts():
                layouts_col.controls.append(
                    ft.Container(
                        padding=15, border_radius=15, bgcolor="#40FFFFFF",
                        border=ft.border.all(1, "#20000000"),
                        content=ft.Row([
                            ft.Icon(ft.Icons.DASHBOARD_ROUNDED, color=COLOR_TEAL_DARK),
                            ft.Column([
                                ft.Text(l["name"], size=16, weight="bold"),
                                ft.Text(f"File: {os.path.basename(l['frame_file'])} | Slots: {len(l.get('slots', []))}", size=11, color=COLOR_TEXT_MUTED),
                            ], expand=True),
                            ft.Row([
                                ft.IconButton(ft.Icons.EDIT_NOTE_ROUNDED, tooltip="Sửa Layout", icon_color="blue", on_click=lambda e, data=l: open_layout_dialog(data)),
                                ft.IconButton(ft.Icons.DELETE_FOREVER_ROUNDED, tooltip="Xóa Layout", icon_color="red", on_click=lambda e, name=l["name"]: delete_layout_confirm(name))
                            ])
                        ])
                    )
                )
            # self.safe_update() - Removed to prevent black screen during initial view construction

        def delete_layout_confirm(name):
            def do_del(_):
                self.layout_manager.delete_layout(name)
                refresh_layout_list()
                self.refresh_gallery_data()
                self.page.close(self.active_dialog)
                self.safe_update()
            
            self.active_dialog = ft.AlertDialog(
                title=ft.Text("Xác nhận xóa Layout"),
                content=ft.Text(f"Bạn có chắc muốn xóa layout '{name}'?"),
                actions=[
                    ft.TextButton("Hủy", on_click=lambda _: self.page.close(self.active_dialog)),
                    ft.ElevatedButton("Xóa", bgcolor="red", color="white", on_click=do_del)
                ]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        def open_layout_dialog(layout_data=None):
            is_edit = layout_data is not None
            
            # Local Editor State
            editor_state = {
                "name": layout_data["name"] if is_edit else "",
                "category": layout_data.get("category", "Classic") if is_edit else "Classic",
                "frame_file": layout_data["frame_file"] if is_edit else None,
                "width": layout_data.get("frame_width", 1800) if is_edit else 1800,
                "height": layout_data.get("frame_height", 1200) if is_edit else 1200,
                "slots": layout_data["slots"] if is_edit else [{
                    "points": {
                        "top_left":     {"x_percent": 0, "y_percent": 0},
                        "top_right":    {"x_percent": 0, "y_percent": 0},
                        "bottom_right": {"x_percent": 0, "y_percent": 0},
                        "bottom_left":  {"x_percent": 0, "y_percent": 0},
                    }
                }],
                "active_slot_idx": 0,
                "mode": "rect", # only rect mode now
                "drag_start": None,
                "drag_end": None
            }

            # UI Elements
            name_input = ft.TextField(label="Tên Layout", value=editor_state["name"], read_only=is_edit, expand=True)
            
            cats = self.layout_manager.get_all_categories()
            cat_dropdown = ft.Dropdown(
                label="Danh mục",
                options=[ft.dropdown.Option(c) for c in cats],
                value=editor_state["category"],
                expand=True
            )
            
            frames = self.layout_manager.get_available_frames()
            
            # Resolve relative frame_file from DB to absolute path for matching in the dropdown
            current_frame = editor_state["frame_file"]
            matched_frame = None
            if current_frame:
                # Try absolute match first
                abs_frame = os.path.abspath(current_frame).replace("\\", "/")
                if abs_frame in frames:
                    matched_frame = abs_frame
                else:
                    # Try matching by filename (basename)
                    base_name = os.path.basename(current_frame)
                    for f in frames:
                        if os.path.basename(f) == base_name:
                            matched_frame = f
                            break
            
            frame_dropdown = ft.Dropdown(
                label="File Khung",
                options=[ft.dropdown.Option(f, text=os.path.basename(f)) for f in frames],
                value=matched_frame if matched_frame in frames else (frames[0] if frames else None),
                expand=True
            )
            self.active_layout_dialog_dropdown = frame_dropdown
            
            slot_count_dd = ft.Dropdown(
                label="Số lượng Slot",
                options=[ft.dropdown.Option(str(n)) for n in [1, 2, 4, 6, 8]],
                value=str(len(editor_state["slots"])) if editor_state["slots"] else "1",
                expand=True
            )

            # --- Architecture: Layered Stack ---
            # Layer 0: Background Image
            preview_img = ft.Image(src_base64="R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", fit=ft.ImageFit.FILL)
            # Layer 1: Existing Slots
            slots_layer = ft.Stack(expand=True)
            # Layer 2: Ghost selection rectangle
            ghost_rect = ft.Container(
                border=ft.border.all(2, ft.Colors.GREEN_ACCENT_400),
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREEN_ACCENT_400),
                visible=False, border_radius=2
            )
            # Layer 3: INVISIBLE TOUCH SURFACE (GestureDetector sits on top)
            # This ensures mouse focus is never lost to moving UI elements
            touch_surface = ft.Container(bgcolor=ft.Colors.TRANSPARENT, expand=True)
            
            canvas_gesture = ft.GestureDetector(
                content=touch_surface,
                expand=True
            )
            
            # The Final Assembly
            overlay_canvas = ft.Stack([preview_img, slots_layer, ghost_rect, canvas_gesture], expand=True)
            
            canvas_container = ft.Container(
                overlay_canvas,
                bgcolor="black", width=800, height=533,
                border_radius=10, alignment=ft.alignment.center
            )

            def safe_update_control(c):
                try:
                    if c and c.page:
                        c.update()
                except: pass

            def update_preview_ui():
                try:
                    # 1. Update Canvas & Image Dimensions (Frame change)
                    fname = frame_dropdown.value
                    if fname and os.path.exists(fname):
                        if not hasattr(update_preview_ui, "_last_file") or update_preview_ui._last_file != fname:
                            with PILImage.open(fname) as img:
                                w_raw, h_raw = img.size
                                editor_state["width"], editor_state["height"] = w_raw, h_raw
                                aspect = w_raw / h_raw
                                if aspect > (800 / 533):
                                    disp_w, disp_h = 800, 800 / aspect
                                else:
                                    disp_h, disp_w = 533, 533 * aspect
                                
                                canvas_container.width = disp_w
                                canvas_container.height = disp_h
                                preview_img.width = disp_w
                                preview_img.height = disp_h
                                # Sync touch surface so click percentages are always 0-100 of the visible image
                                touch_surface.width = disp_w
                                touch_surface.height = disp_h

                                preview_img.src = fname
                                safe_update_control(preview_img)
                                update_preview_ui._last_file = fname
                                safe_update_control(canvas_container)

                    # 2. Rebuild Slots Layer (Converts % back to Pixels for rendering)
                    slots_layer.controls.clear()
                    w_disp = canvas_container.width or 800
                    h_disp = canvas_container.height or 533

                    if editor_state["slots"]:
                        for i, slot in enumerate(editor_state["slots"]):
                            p = slot.get("points", {})
                            tl = p.get("top_left", {"x_percent": 0, "y_percent": 0})
                            br = p.get("bottom_right", {"x_percent": 0, "y_percent": 0})
                            
                            # Chọn màu sắc dựa trên số thứ tự slot
                            colors_list = [
                                ft.Colors.GREEN, ft.Colors.BLUE, ft.Colors.RED, 
                                ft.Colors.AMBER, ft.Colors.PURPLE, ft.Colors.DEEP_ORANGE,
                                ft.Colors.INDIGO, ft.Colors.PINK
                            ]
                            slot_color = colors_list[i % len(colors_list)]
                            
                            is_act = (i == editor_state["active_slot_idx"])
                            
                            # Tính toán tọa độ pixel thực tế
                            left_px = (tl["x_percent"] / 100) * w_disp
                            top_px = (tl["y_percent"] / 100) * h_disp
                            width_px = ((br["x_percent"] - tl["x_percent"]) / 100) * w_disp
                            height_px = ((br["y_percent"] - tl["y_percent"]) / 100) * h_disp

                            slots_layer.controls.append(
                                ft.Container(
                                    left=left_px, 
                                    top=top_px,
                                    width=max(4, width_px), # Đảm bảo tối thiểu 4px để nhìn thấy điểm 0,0
                                    height=max(4, height_px),
                                    border=ft.border.all(3 if is_act else 1, slot_color if is_act else "white"),
                                    bgcolor=ft.Colors.with_opacity(0.4 if is_act else 0.2, slot_color),
                                    content=ft.Text(str(i+1), color="white", weight="bold", size=14),
                                    alignment=ft.alignment.center,
                                    border_radius=3
                                )
                            )
                    safe_update_control(slots_layer)

                    # 3. Synchronize Ghost (Normal/Post-drag state)
                    if not (editor_state["drag_start"] and editor_state["drag_end"]):
                        ghost_rect.visible = False
                    safe_update_control(ghost_rect)

                except Exception as e:
                    print(f"DEBUG Error in update_preview_ui: {e}")
                    traceback.print_exc()
                    sys.stdout.flush()

            def update_all_ui():
                try:
                    update_preview_ui()
                    idx = editor_state["active_slot_idx"]
                    if editor_state["slots"] and idx < len(editor_state["slots"]):
                        update_coord_inputs(editor_state["slots"][idx])
                    self.safe_update()
                except Exception as e:
                    print(f"DEBUG Error in update_all_ui: {e}")
                    sys.stdout.flush()

            def on_frame_change(_):
                editor_state["frame_file"] = frame_dropdown.value
                update_all_ui()

            frame_dropdown.on_change = on_frame_change

            coord_inputs = {}
            for pt in ["top_left", "top_right", "bottom_right", "bottom_left"]:
                row = ft.Row([
                    ft.Text(pt.replace("_", " ").title(), size=12, width=80),
                    ft.TextField(label="X%", value="0", width=70, text_size=12, on_change=lambda e,p=pt: on_coord_text_change(p, "x", e.control.value)),
                    ft.TextField(label="Y%", value="0", width=70, text_size=12, on_change=lambda e,p=pt: on_coord_text_change(p, "y", e.control.value)),
                ], spacing=5)
                coord_inputs[pt] = row

            def set_active_point(pt):
                editor_state["active_point"] = pt
                editor_state["mode"] = "point"
                mode_toggle.selected = {"point"}
                update_all_ui()

            def on_coord_text_change(pt, axis, val):
                try:
                    fval = float(val)
                    idx = editor_state["active_slot_idx"]
                    if idx < len(editor_state["slots"]):
                        editor_state["slots"][idx]["points"][pt][f"{axis}_percent"] = fval
                        update_preview_ui()
                except: pass

            def update_coord_inputs(slot_data):
                pts = slot_data["points"]
                for pt, row in coord_inputs.items():
                    # Update TextField values
                    row.controls[1].value = str(pts[pt]["x_percent"])
                    row.controls[2].value = str(pts[pt]["y_percent"])
                    
                    # Explicitly update input controls to reflect data changes
                    safe_update_control(row.controls[1])
                    safe_update_control(row.controls[2])

            def on_slot_count_change(_):
                count = int(slot_count_dd.value)
                old_slots = editor_state["slots"]
                new_slots = []
                for i in range(count):
                    if i < len(old_slots):
                        new_slots.append(old_slots[i])
                    else:
                        new_slots.append({
                            "points": {
                                "top_left":     {"x_percent": 0, "y_percent": 0},
                                "top_right":    {"x_percent": 0, "y_percent": 0},
                                "bottom_right": {"x_percent": 0, "y_percent": 0},
                                "bottom_left":  {"x_percent": 0, "y_percent": 0}
                            }
                        })
                editor_state["slots"] = new_slots
                editor_state["active_slot_idx"] = 0
                slot_selector.options = [ft.dropdown.Option(str(i), f"Slot {i+1}") for i in range(count)]
                slot_selector.value = "0"
                safe_update_control(slot_selector)
                update_preview_ui()

            slot_count_dd.on_change = on_slot_count_change
            
            def on_slot_select(e):
                editor_state["active_slot_idx"] = int(e.control.value)
                # Force update fields when switching slots
                update_all_ui()

            slot_selector = ft.Dropdown(
                label="Chọn Slot sửa",
                options=[ft.dropdown.Option("0", "Slot 1")],
                value="0",
                on_change=on_slot_select
            )
            # Init options

            # Rect mode interaction handlers
            def handle_pan_start(e: ft.DragStartEvent):
                try:
                    editor_state["drag_start"] = (e.local_x, e.local_y)
                    editor_state["drag_end"] = (e.local_x, e.local_y)
                    print(f"DEBUG: Pan Start at {e.local_x}, {e.local_y}")
                    sys.stdout.flush()
                except Exception as ex:
                    print(f"DEBUG Error in handle_pan_start: {ex}")
                    sys.stdout.flush()

            def handle_pan_update(e: ft.DragUpdateEvent):
                try:
                    if editor_state["drag_start"] is not None:
                        # Update current mouse pos
                        editor_state["drag_end"] = (e.local_x, e.local_y)
                        
                        # Fast Ghost Rect Update (Directly modify persistent control)
                        s = editor_state["drag_start"]
                        x1, y1 = min(s[0], e.local_x), min(s[1], e.local_y)
                        wd, hd = abs(e.local_x - s[0]), abs(e.local_y - s[1])
                        
                        ghost_rect.left = x1
                        ghost_rect.top = y1
                        ghost_rect.width = wd
                        ghost_rect.height = hd
                        ghost_rect.visible = True
                        safe_update_control(ghost_rect) # ONLY update the ghost
                except Exception as ex:
                    print(f"DEBUG Error in handle_pan_update: {ex}")
                    sys.stdout.flush()

            def handle_pan_end(e: ft.DragEndEvent):
                try:
                    if editor_state["drag_start"] and editor_state["drag_end"]:
                        s = editor_state["drag_start"]
                        f = editor_state["drag_end"]
                        x1, y1 = min(s[0], f[0]), min(s[1], f[1])
                        x2, y2 = max(s[0], f[0]), max(s[1], f[1])
                        
                        # Get display size
                        w = canvas_container.width or 800
                        h = canvas_container.height or 533

                        x1_pct = round(x1 / w * 100, 2)
                        y1_pct = round(y1 / h * 100, 2)
                        x2_pct = round(x2 / w * 100, 2)
                        y2_pct = round(y2 / h * 100, 2)
                        
                        idx = editor_state["active_slot_idx"]
                        if idx < len(editor_state["slots"]):
                            editor_state["slots"][idx]["points"] = {
                                "top_left": {"x_percent": x1_pct, "y_percent": y1_pct},
                                "top_right": {"x_percent": x2_pct, "y_percent": y1_pct},
                                "bottom_right": {"x_percent": x2_pct, "y_percent": y2_pct},
                                "bottom_left": {"x_percent": x1_pct, "y_percent": y2_pct}
                            }
                            
                            p = editor_state["slots"][idx]["points"]
                            print(f"DEBUG: Rect Selection Updated for Slot {idx+1}: TL={x1_pct}%,{y1_pct}% BR={x2_pct}%,{y2_pct}%")
                            sys.stdout.flush()

                        editor_state["drag_start"] = None
                        editor_state["drag_end"] = None
                        
                        # Reset visual ghost
                        ghost_rect.visible = False
                        safe_update_control(ghost_rect)

                        update_all_ui()
                        print("DEBUG: SUCCESS - handle_pan_end finished")
                        sys.stdout.flush()
                except Exception as ex:
                    print(f"DEBUG Error in handle_pan_end: {ex}")
                    traceback.print_exc()
                    sys.stdout.flush()

            # canvas_gesture.on_tap_down removed
            canvas_gesture.on_pan_start = handle_pan_start
            canvas_gesture.on_pan_update = handle_pan_update
            canvas_gesture.on_pan_end = handle_pan_end

            # Sidebar for Inputs
            sidebar = ft.Column([
                ft.Text("Thông tin chung", weight="bold"),
                name_input,
                cat_dropdown,
                ft.Row([frame_dropdown, ft.IconButton(ft.Icons.UPLOAD_FILE, on_click=lambda _: self.fp_frames.pick_files())]),
                ft.Divider(),
                ft.Text("Cấu hình vùng ảnh (Slots)", weight="bold"),
                ft.Row([slot_count_dd, slot_selector]),
                ft.Container(height=10),
                coord_inputs["top_left"],
                coord_inputs["top_right"],
                coord_inputs["bottom_right"],
                coord_inputs["bottom_left"],
            ], spacing=10, width=320, scroll=ft.ScrollMode.AUTO)

            def save_layout(_):
                success, msg = self.layout_manager.add_layout(
                    name_input.value.strip(),
                    frame_dropdown.value,
                    int(editor_state["width"]),
                    int(editor_state["height"]),
                    editor_state["slots"],
                    category=cat_dropdown.value
                )
                if success:
                    self.page.snack_bar = ft.SnackBar(ft.Text("✅ Đã lưu layout thành công!"), bgcolor="green")
                    self.page.close(self.active_dialog)
                    refresh_layout_list()
                    self.refresh_gallery_data()
                else:
                    self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ Lỗi: {msg}"), bgcolor="red")
                self.page.snack_bar.open = True
                self.safe_update()

            # Main Dialog Builder
            
            self.active_dialog = ft.AlertDialog(
                title=ft.Text("THIẾT KẾ LAYOUT PHOTOBOOTH", weight="bold"),
                content=ft.Container(
                    width=1200, height=750,
                    content=ft.Row([
                        sidebar,
                        ft.VerticalDivider(),
                        ft.Column([
                            ft.Text("Xem trước & Tương tác (% tọa độ)", size=12, italic=True),
                            canvas_container,
                            ft.Text("Mẹo: Chọn 'Chấm điểm' để click vào 4 góc, hoặc 'Kéo HCN' để quét vùng nhanh.", size=11, color=COLOR_TEXT_MUTED)
                        ], expand=True, horizontal_alignment="center")
                    ])
                ),
                actions=[
                    ft.TextButton("Hủy", on_click=lambda _: self.page.close(self.active_dialog)),
                    ft.ElevatedButton("LƯU LAYOUT", bgcolor=COLOR_PEACH_PRIMARY, color="white", on_click=save_layout)
                ]
            )
            self.page.open(self.active_dialog)
            
            # Initial UI Sync after the dialog is live
            if is_edit: 
                # Synchronize dropdown options with data if editing
                count = len(editor_state["slots"])
                slot_selector.options = [ft.dropdown.Option(str(i), f"Slot {i+1}") for i in range(count)]
                slot_selector.value = "0"
            
            update_all_ui()
            self.safe_update()

        # 3. CATEGORY MANAGEMENT
        cats_list = ft.Column(spacing=5)
        
        def refresh_cats_list():
            cats_list.controls.clear()
            for c in self.layout_manager.get_all_categories():
                cats_list.controls.append(
                    ft.Row([
                        ft.Text(c, expand=True),
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color="blue", on_click=lambda e, name=c: on_rename_cat(name)),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", on_click=lambda e, name=c: delete_cat(name))
                    ])
                )
            # self.safe_update() - Removed to prevent black screen during initial view construction

        def on_rename_cat(old_name):
            def do_rename(e):
                if new_cat_input.value:
                    self.layout_manager.rename_category(old_name, new_cat_input.value.strip())
                    refresh_cats_list()
                    self.page.close(self.active_dialog)
                    self.safe_update()
            new_cat_input = ft.TextField(label="Tên mới", value=old_name, autofocus=True, on_submit=do_rename)
            self.active_dialog = ft.AlertDialog(
                title=ft.Text(f"Đổi Tên Danh Mục '{old_name}'"),
                content=new_cat_input,
                actions=[ft.ElevatedButton("Lưu", on_click=do_rename)]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        def add_cat(_):
            def do_add(e):
                if new_cat_input.value:
                    self.layout_manager.add_category(new_cat_input.value.strip())
                    refresh_cats_list()
                    self.page.close(self.active_dialog)
                    self.safe_update()
            new_cat_input = ft.TextField(label="Tên danh mục mới", autofocus=True, on_submit=do_add)
            self.active_dialog = ft.AlertDialog(
                title=ft.Text("Thêm Danh Mục"),
                content=new_cat_input,
                actions=[ft.ElevatedButton("Thêm", on_click=do_add)]
            )
            self.page.open(self.active_dialog)
            self.safe_update()

        def delete_cat(name):
            self.layout_manager.delete_category(name)
            refresh_cats_list()

        refresh_cats_list()

        # OTHER SETTINGS ... (Nextcloud etc)
        nc_enabled = ft.Checkbox(label="Kích hoạt Nextcloud", value=config.NC_ENABLED)
        nc_url = ft.TextField(label="WebDAV URL", value=config.NC_URL)
        nc_user = ft.TextField(label="Username", value=config.NC_USER)
        nc_pass = ft.TextField(label="App Password", value=config.NC_PASS, password=True, can_reveal_password=True)
        nc_root = ft.TextField(label="Thư mục gốc", value=config.NC_REMOTE_PATH)
        nc_share = ft.TextField(label="Public Share URL", value=config.NC_SHARE_URL)

        mirror_toggle = ft.Switch(label="Chế độ Mirror (Phản chiếu)", value=config.MIRROR_MODE)
        password_toggle = ft.Switch(label="Nút khởi động nhanh Admin (Ctrl+7 không mật khẩu)", value=not config.ADMIN_PASSWORD_ENABLED)
        c1_toggle = ft.Switch(
            label="📷 Chế độ Capture One (Chụp C1)",
            value=config.CAPTURE_ONE_MODE,
            active_color=COLOR_TEAL_BORDER
        )
        c1_window_title = ft.TextField(
            label="Tên cửa sổ cần tìm (cách nhau bằng dấu phẩy)",
            value=config.CAPTURE_ONE_WINDOW_TITLE,
            hint_text="VD: Capture One,CaptureOne,PhotoBooth",
            border_color=COLOR_TEAL_BORDER,
            prefix_icon=ft.Icons.SEARCH_ROUNDED
        )
        quality_dropdown = ft.Dropdown(
            label="Chất lượng ảnh Preview",
            value=str(config.CAMERA_QUALITY),
            options=[ft.dropdown.Option(str(q)) for q in [60, 70, 80, 90, 100]],
            expand=True
        )

        # Payment Settings
        payment_enabled_toggle = ft.Switch(label="Kích hoạt Mock Payment", value=config.PAYMENT_ENABLED)
        payment_url_field = ft.TextField(label="Server URL", value=config.PAYMENT_URL, hint_text="http://localhost:8000")
        payment_package_field = ft.TextField(label="Package ID", value=config.PAYMENT_PACKAGE_ID)
        payment_amount_field = ft.TextField(label="Số tiền (VNĐ)", value=str(config.PAYMENT_AMOUNT), input_filter=ft.NumbersOnlyInputFilter())

        def save_and_exit(_):
            config.NC_ENABLED = nc_enabled.value
            config.NC_URL = nc_url.value; config.NC_USER = nc_user.value; config.NC_PASS = nc_pass.value
            config.NC_REMOTE_PATH = nc_root.value; config.NC_SHARE_URL = nc_share.value
            config.MIRROR_MODE = mirror_toggle.value
            config.ADMIN_PASSWORD_ENABLED = not password_toggle.value
            config.CAMERA_QUALITY = int(quality_dropdown.value)
            config.CAPTURE_ONE_MODE = c1_toggle.value
            config.CAPTURE_ONE_WINDOW_TITLE = c1_window_title.value.strip() or "Capture One,CaptureOne"
            config.PAYMENT_ENABLED = payment_enabled_toggle.value
            config.PAYMENT_URL = payment_url_field.value.strip()
            config.PAYMENT_PACKAGE_ID = payment_package_field.value.strip()
            try:
                config.PAYMENT_AMOUNT = int(payment_amount_field.value)
            except:
                pass
            config.save_config(); self.update_qr_code(); self._update_capture_btn_label(); self.page.go("/")

        def test_nc(_):
            self.page.snack_bar = ft.SnackBar(ft.Text("Đang kiểm tra kết nối Nextcloud..."), bgcolor=COLOR_TEAL_DARK)
            self.page.snack_bar.open = True
            self.safe_update()
            
            # Prepare config dict
            config_dict = {
                'NC_URL': nc_url.value,
                'NC_USER': nc_user.value,
                'NC_PASS': nc_pass.value,
                'NC_REMOTE_PATH': nc_root.value,
                'NC_ENABLED': nc_enabled.value
            }
            
            success, result = nc_get_public_link(config_dict)
            if success:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ Kết nối thành công! Link Share: {result}"), bgcolor="green")
                nc_share.value = result
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ Kết nối thất bại: {result}"), bgcolor="red")
            
            self.page.snack_bar.open = True
            self.safe_update()

        # Camera Controls
        zoom_text = ft.Text(f"Zoom hiện tại: {self.camera_worker.digital_zoom:.1f}x", size=16, weight="bold")
        
        def update_zoom(delta):
            if delta > 0: self.camera_worker.zoom_in()
            else: self.camera_worker.zoom_out()
            zoom_text.value = f"Zoom hiện tại: {self.camera_worker.digital_zoom:.1f}x"
            self.safe_update()

        zoom_controls = ft.Row([
            ft.IconButton(ft.Icons.ZOOM_OUT, on_click=lambda _: update_zoom(-1), icon_size=30),
            zoom_text,
            ft.IconButton(ft.Icons.ZOOM_IN, on_click=lambda _: update_zoom(1), icon_size=30),
        ], alignment="center", spacing=20)

        focus_btn = ft.ElevatedButton("🎯 LẤY NÉT TỰ ĐỘNG (AF)", 
                                     icon=ft.Icons.CENTER_FOCUS_STRONG,
                                     on_click=lambda _: self.camera_worker.trigger_autofocus(),
                                     height=50)

        # Initialize lists
        refresh_session_list()
        refresh_layout_list()

        # --- FINAL ADMIN VIEW ---
        return ft.View(
            "/admin",
            padding=0,
            controls=[
                ft.AppBar(
                    title=ft.Text("🍑 HỆ THỐNG QUẢN TRỊ", weight="bold", color="white"),
                    bgcolor=COLOR_PEACH_PRIMARY,
                    center_title=True,
                    color="white"
                ),
                ft.Container(
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_left,
                        end=ft.alignment.bottom_right,
                        colors=[COLOR_MINT_BG, "white", COLOR_PEACH_BG]
                    ),
                    padding=20,
                    content=ft.Tabs(
                        expand=True,
                        selected_index=0,
                        tabs=[
                            ft.Tab(
                                text="PHIÊN CHỤP",
                                icon=ft.Icons.PEOPLE_ALT_ROUNDED,
                                content=ft.Container(
                                    padding=20,
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Text("Danh Sách Phiên Chụp", size=22, weight="bold", color=COLOR_TEAL_DARK, expand=True),
                                            ft.ElevatedButton("➕ Thêm Phiên Mới", on_click=on_add_session, bgcolor=COLOR_PEACH_PRIMARY, color="white")
                                        ], alignment="spaceBetween"),
                                        ft.Divider(height=20),
                                        ft.Container(sessions_list, expand=True)
                                    ], spacing=10, expand=True)
                                )
                            ),
                            ft.Tab(
                                text="THANH TOÁN",
                                icon=ft.Icons.PAYMENT_ROUNDED,
                                content=ft.Container(
                                    padding=30,
                                    content=ft.Column([
                                        ft.Text("Cấu Hình Thanh Toán (Mock Server)", size=22, weight="bold", color=COLOR_TEAL_DARK),
                                        ft.Divider(),
                                        ft.Container(
                                            padding=20, border_radius=15, bgcolor="white",
                                            content=ft.Column([
                                                payment_enabled_toggle,
                                                ft.Text("Khi bật, chỉ khi thanh toán thành công mới bắt đầu chụp được.", size=12, italic=True),
                                                ft.Divider(),
                                                payment_url_field,
                                                payment_package_field,
                                                payment_amount_field,
                                            ], spacing=15)
                                        )
                                    ], spacing=10, scroll=ft.ScrollMode.AUTO)
                                )
                            ),
                            ft.Tab(
                                text="LAYOUTS",
                                icon=ft.Icons.DASHBOARD_CUSTOMIZE_ROUNDED,
                                content=ft.Container(
                                    padding=20,
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Text("Quản Lý Layout Khung Hình", size=22, weight="bold", color=COLOR_TEAL_DARK, expand=True),
                                            ft.ElevatedButton("➕ Tạo Layout Mới", on_click=lambda _: open_layout_dialog(), bgcolor=COLOR_PEACH_PRIMARY, color="white")
                                        ], alignment="spaceBetween"),
                                        ft.Divider(height=20),
                                        ft.Row([
                                            ft.Column([
                                                ft.Text("Danh Mục", weight="bold"),
                                                cats_list,
                                                ft.ElevatedButton("Thêm danh mục", icon=ft.Icons.ADD, on_click=add_cat)
                                            ], width=200, spacing=10),
                                            ft.VerticalDivider(),
                                            ft.Column([
                                                ft.Text("Danh Sách Layout", weight="bold"),
                                                ft.Container(layouts_col, expand=True)
                                            ], expand=True)
                                        ], expand=True)
                                    ], spacing=10, expand=True)
                                )
                            ),
                            ft.Tab(
                                text="CLOUD",
                                icon=ft.Icons.CLOUD_SYNC_ROUNDED,
                                content=ft.Container(
                                    padding=20,
                                    content=ft.Column([
                                        nc_enabled, nc_url, nc_user, nc_pass, nc_root, nc_share,
                                        ft.ElevatedButton("⚡ Kiểm tra kết nối & Lấy link share", on_click=test_nc)
                                    ], scroll=ft.ScrollMode.AUTO, spacing=15)
                                )
                            ),
                            ft.Tab(
                                text="HỆ THỐNG",
                                icon=ft.Icons.SETTINGS_SUGGEST_ROUNDED,
                                content=ft.Container(
                                    padding=20,
                                    content=ft.Column([
                                        ft.Row([
                                            ft.ElevatedButton("📂 RAW FOLDER", icon=ft.Icons.FOLDER_OPEN, on_click=lambda _: os.startfile(os.path.abspath(config.RAW_DIR)), expand=True),
                                            ft.ElevatedButton("📂 OUTPUT FOLDER", icon=ft.Icons.FOLDER_SPECIAL, on_click=lambda _: os.startfile(os.path.abspath(config.OUTPUT_DIR)), expand=True),
                                        ], spacing=15),
                                        ft.Divider(),
                                        ft.Text("CĂN CHỈNH CAMERA", weight="bold"),
                                        zoom_controls,
                                        ft.Container(focus_btn, alignment=ft.alignment.center),
                                        ft.Divider(),
                                        password_toggle,
                                        mirror_toggle,
                                        quality_dropdown,
                                        ft.Divider(),
                                        ft.Text("CHẾ ĐỘ CHỤP", weight="bold", color=COLOR_TEAL_DARK),
                                        ft.Container(
                                            content=c1_toggle,
                                            bgcolor="#E8F5E9",
                                            border_radius=12,
                                            padding=ft.padding.symmetric(horizontal=16, vertical=10),
                                            border=ft.border.all(1.5, COLOR_TEAL_BORDER)
                                        ),
                                        c1_window_title,
                                        ft.Text(
                                            "Khi bật: nút 'Chụp ảnh' sẽ đổi thành 'Chụp C1'. Nhấn sẽ mở Capture One, gửi phím Ctrl+K và tự động chuyển về màn hình Thư viện.",
                                            size=11, color=COLOR_TEXT_MUTED, italic=True
                                        ),
                                        ft.Divider(),
                                        ft.ElevatedButton(f"🔄 Chế độ App: {config.APP_MODE.upper()}", on_click=self.toggle_mode, height=50, width=float("inf")),
                                        ft.Text("Peach Photobooth Station Pro v2.1", size=14, color=COLOR_TEXT_MUTED, text_align="center")
                                    ], spacing=15, scroll=ft.ScrollMode.AUTO)
                                )
                            )
                        ]
                    )
                ),
                ft.Container(
                    padding=20, 
                    bgcolor="white",
                    content=ft.ElevatedButton("LƯU CẤU HÌNH & QUAY LẠI", height=60, width=float("inf"), bgcolor=COLOR_PEACH_PRIMARY, color="white", on_click=save_and_exit)
                )
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
