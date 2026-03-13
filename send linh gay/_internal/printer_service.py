import os
import sys

class PrinterService:
    @staticmethod
    def print_image(image_path):
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError("Không tìm thấy file ảnh thành phẩm.")
            
            if sys.platform == "win32":
                # Cơ chế startfile của windows gọi phần mềm in mặc định
                os.startfile(image_path, "print")
                return True
            else:
                raise NotImplementedError("Module này thiết kế đặc thù cho Windows.")
        except Exception as e:
            raise Exception(f"Không thể gửi lệnh in: {e}")
