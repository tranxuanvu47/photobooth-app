import json
import os
import shutil

class FrameLayoutManager:
    def __init__(self, config_dir="frame_configs", frames_dir="frames"):
        self.config_dir = config_dir
        self.frames_dir = frames_dir
        self.config_file = os.path.join(self.config_dir, "layouts.json")
        self.layouts = []
        
        self.ensure_directories()
        self.load_layouts()

    def ensure_directories(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        if not os.path.exists(self.frames_dir):
            os.makedirs(self.frames_dir)

    def load_layouts(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.layouts = data.get("layouts", [])
                    
                    # Migration: Convert old 'points' structure to new 'slots' list
                    for layout in self.layouts:
                        if "points" in layout and "slots" not in layout:
                            layout["slots"] = [{"points": layout.pop("points")}]
            except Exception as e:
                print(f"Lỗi đọc file cấu hình: {e}")
                self.layouts = []
        else:
            self.layouts = []
            self.save_layouts()

    def save_layouts(self):
        data = {"layouts": self.layouts}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Lỗi lưu file cấu hình: {e}")
            return False

    def add_layout(self, name, frame_file, width, height, slots):
        # Validate data
        if not name or not frame_file:
            return False, "Tên layout và file khung không được để trống."
            
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            return False, "Kích thước khung không hợp lệ."
            
        if not slots or not isinstance(slots, list):
            return False, "Danh sách vùng ảnh (slots) không hợp lệ."

        required_points = ["top_left", "top_right", "bottom_right", "bottom_left"]
        for i, slot in enumerate(slots):
            points = slot.get("points", {})
            for pt in required_points:
                if pt not in points or "x_percent" not in points[pt] or "y_percent" not in points[pt]:
                    return False, f"Thiếu tọa độ cho {pt} ở slot {i+1}."
                
                x = points[pt]["x_percent"]
                y = points[pt]["y_percent"]
                if not (0 <= x <= 100) or not (0 <= y <= 100):
                    return False, f"Tọa độ {pt} ở slot {i+1} phải nằm trong khoảng 0-100%."

        # Kiểm tra trùng tên, nếu trùng thì cập nhật (ghi đè)
        new_layout = {
            "name": name,
            "frame_file": frame_file,
            "frame_width": width,
            "frame_height": height,
            "slots": slots
        }
        
        updated = False
        for i, layout in enumerate(self.layouts):
            if layout["name"] == name:
                self.layouts[i] = new_layout
                updated = True
                break
                
        if not updated:
            self.layouts.append(new_layout)
            
        if self.save_layouts():
            return True, "Lưu cấu hình thành công"
        else:
            return False, "Lỗi khi lưu vào file JSON"

    def delete_layout(self, name):
        """Xóa layout theo tên"""
        original_count = len(self.layouts)
        self.layouts = [l for l in self.layouts if l["name"] != name]
        
        if len(self.layouts) < original_count:
            if self.save_layouts():
                return True, f"Đã xóa layout '{name}' thành công."
            else:
                return False, "Lỗi khi lưu file cấu hình sau khi xóa."
        return False, f"Không tìm thấy layout '{name}' để xóa."

    def get_all_layouts(self):
        return self.layouts

    def get_layout_by_name(self, name):
        for layout in self.layouts:
            if layout["name"] == name:
                return layout
        return None

    def get_available_frames(self):
        self.ensure_directories()
        valid_extensions = {".png", ".jpg", ".jpeg"}
        frames = []
        for file in os.listdir(self.frames_dir):
            if os.path.splitext(file)[1].lower() in valid_extensions:
                frames.append(os.path.join(self.frames_dir, file).replace("\\", "/"))
        return frames
