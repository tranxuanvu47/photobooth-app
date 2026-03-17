import json
import os
import shutil

class FrameLayoutManager:
    def __init__(self, config_dir="frame_configs", frames_dir="frames"):
        self.config_dir = config_dir
        self.frames_dir = frames_dir
        self.config_file = os.path.join(self.config_dir, "layouts.json")
        self.layouts = []
        self.categories = ["Classic", "Vintage", "Trendy", "Cute & Fun", "Wedding"]
        
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
                    self.categories = data.get("categories", ["Classic", "Vintage", "Trendy", "Cute & Fun", "Wedding"])
                    
                    # Migration: Convert old 'points' structure to new 'slots' list
                    for layout in self.layouts:
                        if "points" in layout and "slots" not in layout:
                            layout["slots"] = [{"points": layout.pop("points")}]
                        if "category" not in layout:
                            layout["category"] = "Classic"
            except Exception as e:
                print(f"Lỗi đọc file cấu hình: {e}")
                self.layouts = []
                self.categories = ["Classic", "Vintage", "Trendy", "Cute & Fun", "Wedding"]
        else:
            self.layouts = []
            self.save_layouts()

    def save_layouts(self):
        data = {
            "categories": self.categories,
            "layouts": self.layouts
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Lỗi lưu file cấu hình: {e}")
            return False

    def add_layout(self, name, frame_file, width, height, slots, category="Classic"):
        # Validate data
        if not name or not frame_file:
            return False, "Tên layout và file khung không được để trống."
            
        if not isinstance(width, (int, float)) or not isinstance(height, (int, float)) or width <= 0 or height <= 0:
            return False, "Kích thước khung không hợp lệ."
            
        if not slots or not isinstance(slots, list):
            return False, "Danh sách vùng ảnh (slots) không hợp lệ."

        # Kiểm tra trùng tên, nếu trùng thì cập nhật (ghi đè)
        new_layout = {
            "name": name,
            "category": category,
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

    def get_all_categories(self):
        return self.categories

    def add_category(self, name):
        if name and name not in self.categories:
            self.categories.append(name)
            self.save_layouts()
            return True
        return False

    def delete_category(self, name):
        if name in self.categories:
            self.categories.remove(name)
            self.save_layouts()
            return True
        return False

    def rename_category(self, old_name, new_name):
        if old_name in self.categories and new_name and new_name not in self.categories:
            idx = self.categories.index(old_name)
            self.categories[idx] = new_name
            # Update layouts in this category
            for l in self.layouts:
                if l.get("category") == old_name:
                    l["category"] = new_name
            self.save_layouts()
            return True
        return False

    def get_available_frames(self):
        self.ensure_directories()
        valid_extensions = {".png", ".jpg", ".jpeg"}
        frames = []
        for file in os.listdir(self.frames_dir):
            if os.path.splitext(file)[1].lower() in valid_extensions:
                frames.append(os.path.join(self.frames_dir, file).replace("\\", "/"))
        return frames
