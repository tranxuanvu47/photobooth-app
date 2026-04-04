"""
PrinterService - In ảnh trực tiếp đến máy in, không qua dialog OS.
Dùng win32print + win32ui + Pillow.ImageWin (chuẩn cho Windows GDI printing).
"""
import os
import sys


class PrinterService:

    @staticmethod
    def get_default_printer() -> str | None:
        """Lấy tên máy in mặc định."""
        try:
            import win32print
            return win32print.GetDefaultPrinter()
        except Exception:
            return None

    @staticmethod
    def get_all_printers() -> list[str]:
        """Danh sách tất cả máy in có trên hệ thống."""
        try:
            import win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return [p[2] for p in printers]
        except Exception:
            return []

    @staticmethod
    def print_image(image_path: str, printer_name: str = None, copies: int = 1) -> bool:
        """
        In ảnh trực tiếp đến máy in - KHÔNG mở dialog OS.

        Dùng ImageWin.Dib (Pillow) để vẽ ảnh lên Printer DC — cách chuẩn
        và đáng tin nhất trên Windows.

        Args:
            image_path:   Đường dẫn file ảnh.
            printer_name: Tên máy in. None = dùng máy in mặc định.
            copies:       Số bản in (1–10).

        Returns:
            True nếu gửi lệnh thành công.
        """
        if sys.platform != "win32":
            raise NotImplementedError("PrinterService chỉ hỗ trợ Windows.")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Không tìm thấy file: {image_path}")

        try:
            import win32print
            import win32ui
            from PIL import Image, ImageWin

            # ── 1. Chọn máy in ───────────────────────────────────────────────
            target_printer = printer_name or win32print.GetDefaultPrinter()

            # ── 2. Tạo Printer DC ────────────────────────────────────────────
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(target_printer)

            # Kích thước trang in (pixel theo DPI máy in)
            page_w = hdc.GetDeviceCaps(110)  # HORZRES
            page_h = hdc.GetDeviceCaps(111)  # VERTRES

            # ── 3. Chuẩn bị ảnh ─────────────────────────────────────────────
            img = Image.open(image_path).convert("RGB")
            img_w, img_h = img.size

            # Auto-rotate: nếu hướng ảnh không khớp hướng trang → xoay 90°
            # Ví dụ: ảnh dọc (portrait) nhưng trang ngang (landscape) → xoay
            img_is_portrait  = img_h >= img_w
            page_is_portrait = page_h >= page_w
            if img_is_portrait != page_is_portrait:
                img = img.rotate(90, expand=True)
                img_w, img_h = img.size

            # Scale tối đa, giữ tỷ lệ
            scale = min(page_w / img_w, page_h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

            # Căn giữa trên trang
            x_off = (page_w - new_w) // 2
            y_off = (page_h - new_h) // 2

            # ── 4. Tạo DIB và in ─────────────────────────────────────────────
            # ImageWin.Dib là cách chuẩn của Pillow để vẽ lên Windows DC
            dib = ImageWin.Dib(img)

            hdc.StartDoc(os.path.basename(image_path))

            for _ in range(copies):
                hdc.StartPage()
                dib.draw(
                    hdc.GetHandleOutput(),
                    (x_off, y_off, x_off + new_w, y_off + new_h)
                )
                hdc.EndPage()

            hdc.EndDoc()
            hdc.DeleteDC()

            return True

        except Exception as e:
            raise Exception(f"Lỗi in ảnh: {e}")
