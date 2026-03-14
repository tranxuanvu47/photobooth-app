from PIL import Image, ImageDraw, ImageFilter
from pillow_lut import load_cube_file
import os
import cv2
import numpy as np
from config import OUTPUT_DIR, FRAME_PATH

class ImageProcessor:
    @staticmethod
    def sharpen_image(image_path, level="normal"):
        """
        Làm nét ảnh bằng thuật toán Unsharp Mask (OpenCV).
        Giúp ảnh từ DSLR sắc nét hơn mà không bị noise quá nhiều.
        """
        try:
            if not os.path.exists(image_path):
                return image_path
            
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            # Backup ảnh gốc nếu chưa có (để phục vụ tính năng "Tắt (Gốc)")
            backup_path = image_path + ".orig"
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(image_path, backup_path)
                print(f"[SHARPEN] Đã tạo bản sao lưu gốc tại: {backup_path}")

            # Cấu hình tham số dựa trên mức độ
            # sharpened = original + amount * (original - blurred)
            if level == "low":
                amount, radius, threshold = 0.8, 1.0, 0
            elif level == "high":
                amount, radius, threshold = 2.5, 1.5, 0
            else: # normal
                amount, radius, threshold = 1.5, 1.0, 0
            
            # 1. Tạo bản mờ (Gaussian Blur)
            sigma = radius
            blurred = cv2.GaussianBlur(img, (0, 0), sigma)
            
            # 2. Áp dụng công thức Unsharp Mask: sharpened = original * (1 + amount) + blurred * (-amount)
            sharpened = cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)
            
            # Nếu có threshold, chỉ áp dụng làm nét ở những vùng có sự khác biệt lớn (giảm noise vùng phẳng)
            if threshold > 0:
                low_contrast_mask = cv2.absdiff(img, blurred) < threshold
                np.copyto(sharpened, img, where=low_contrast_mask)

            # Ghi đè trực tiếp lên file gốc để đồng bộ luồng preview/print
            cv2.imwrite(image_path, sharpened, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            print(f"[SHARPEN] Đã làm nét ảnh ({level}): {image_path}")
            return image_path
            
        except Exception as e:
            print(f"[SHARPEN Lỗi] {e}")
            return image_path

    @staticmethod
    def restore_original(image_path):
        """
        Khôi phục ảnh về trạng thái ban đầu từ file .orig
        """
        try:
            backup_path = image_path + ".orig"
            if os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, image_path)
                print(f"[RESTORE] Đã khôi phục ảnh gốc: {image_path}")
                return True
            return False
        except Exception as e:
            print(f"[RESTORE Lỗi] {e}")
            return False

    @staticmethod
    def apply_lut(image_path, lut_path):
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError("Không tìm thấy ảnh gốc để áp dụng LUT.")
            if not os.path.exists(lut_path):
                raise FileNotFoundError(f"Không tìm thấy file LUT: {lut_path}")
                
            base_img = Image.open(image_path).convert("RGB")
            lut_filter = load_cube_file(lut_path)
            
            filtered_img = base_img.filter(lut_filter)
            
            filename = "filtered_" + os.path.basename(image_path)
            out_path = os.path.join(OUTPUT_DIR, filename)
            filtered_img.save(out_path, format="JPEG", quality=98)
            return out_path
        except Exception as e:
            raise Exception(f"Lỗi áp dụng LUT filter: {e}")

    @staticmethod
    def convert_xmp_to_cube(xmp_path, cube_path):
        """
        Chuyển đổi file Adobe XMP (Camera Raw Profile) sang chuẩn .cube (3D LUT).
        Hỗ trợ trích xuất LookTable dữ liệu nhị phân Base64.
        """
        import base64
        import struct
        import xml.etree.ElementTree as ET

        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()

            # Namespaces thường gặp trong XMP
            namespaces = {
                'x': 'adobe:ns:meta/',
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'crs': 'http://ns.adobe.com/camera-raw-settings/1.0/'
            }

            # Tìm tag chứa dữ liệu Table
            # Thường nằm ở crs:LookTable hoặc trong crs:Description
            lut_data_raw = None
            dim = 32

            # 1. Tìm trong các Description tags với namespace crs
            for desc in root.findall(".//rdf:Description", namespaces):
                # Thử lấy attribute trực tiếp (thường thấy trong XMP sidecar)
                for attr_name, attr_val in desc.attrib.items():
                    if 'TableData' in attr_name:
                        lut_data_raw = attr_val
                        break
                if lut_data_raw: break
                
                # Hoặc tìm tag con
                table_tag = desc.find(".//crs:TableData", namespaces)
                if table_tag is not None:
                    lut_data_raw = table_tag.text
                    break
                if lut_data_raw: break

            if not lut_data_raw:
                # 2. Tìm bất kỳ tag nào có tên chứa TableData (fallback cuối cùng)
                for element in root.iter():
                    if 'TableData' in element.tag and element.text:
                        lut_data_raw = element.text
                        break

            if not lut_data_raw:
                # 3. Thử tìm Tone Curve (thường là Sidecar/Develop settings)
                print("[XMP2CUBE] Không thấy TableData, đang thử tìm ToneCurve...")
                curves = {}
                curve_names = {
                    'ToneCurvePV2012': 'RGB',
                    'ToneCurvePV2012Red': 'Red',
                    'ToneCurvePV2012Green': 'Green',
                    'ToneCurvePV2012Blue': 'Blue'
                }
                
                for tag_name, label in curve_names.items():
                    points = []
                    # Tìm trong rdf:Description attributes
                    for desc in root.findall(".//rdf:Description", namespaces):
                        val = desc.get(f'{{http://ns.adobe.com/camera-raw-settings/1.0/}}{tag_name}')
                        if val:
                            points = val # Thường là list trong XMP hoặc string
                            break
                    
                    # Hoặc tìm trong tag con
                    if not points:
                        curve_tag = root.find(f".//crs:{tag_name}/rdf:Seq", namespaces)
                        if curve_tag is not None:
                            points = [li.text for li in curve_tag.findall("rdf:li", namespaces)]
                    
                    if points:
                        # Parse "x, y" strings thành list tuples
                        parsed_points = []
                        if isinstance(points, str):
                            # Adobe đôi khi lưu dạng string "0, 0, 255, 255"
                            parts = [p.strip() for p in points.split(',')]
                            for i in range(0, len(parts), 2):
                                if i+1 < len(parts):
                                    parsed_points.append((float(parts[i]), float(parts[i+1])))
                        else:
                            for p in points:
                                if isinstance(p, str) and ',' in p:
                                    x, y = p.split(',')
                                    parsed_points.append((float(x), float(y)))
                        
                        if parsed_points:
                            curves[label] = sorted(parsed_points)

                if curves:
                    return ImageProcessor._generate_cube_from_curves(curves, cube_path, os.path.basename(xmp_path))

                raise ValueError("Không tìm thấy dữ liệu LookTable hoặc ToneCurve trong file XMP này.")

            # Decode Base64 cho Profile TableData
            binary_data = base64.b64decode(lut_data_raw.strip())
            
            # Adobe TableData Format:
            # - byte 0: ?
            # - byte 1: Dimension (N)
            # - bytes 2...: N*N*N * 3 * 4 bytes (Float32)
            if len(binary_data) > 2:
                dim = binary_data[1]
                float_data = binary_data[2:]
            else:
                raise ValueError("Dữ liệu Profile nhị phân quá ngắn.")

            expected_floats = dim * dim * dim * 3
            if len(float_data) < expected_floats * 4:
                raise ValueError(f"Dữ liệu Profile không đủ cho LUT {dim}x{dim}x{dim}.")

            # Parse floats (Little Endian)
            values = struct.unpack(f'<{expected_floats}f', float_data[:expected_floats * 4])

            # Ghi file .cube
            with open(cube_path, 'w') as f:
                f.write(f"# Created from XMP Profile: {os.path.basename(xmp_path)}\n")
                f.write(f"LUT_3D_SIZE {dim}\n")
                
                for i in range(0, len(values), 3):
                    r, g, b = values[i], values[i+1], values[i+2]
                    f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")

            print(f"[XMP2CUBE] Đã convert Profile thành công: {cube_path} (Size: {dim})")
            return True

        except Exception as e:
            print(f"[XMP2CUBE Lỗi] {e}")
            return False

    @staticmethod
    def _generate_cube_from_curves(curves, cube_path, source_name):
        """
        Tạo 3D LUT từ các đường cong Tone Curves (1D mapping).
        """
        import numpy as np
        
        dim = 32
        # Tạo mảng lookup cho mỗi kênh (0-255 -> 0-1)
        x_new = np.linspace(0, 255, 256)
        
        mappings = {}
        for label in ['RGB', 'Red', 'Green', 'Blue']:
            if label in curves:
                pts = np.array(curves[label])
                # Nội suy tuyến tính
                y_mapped = np.interp(x_new, pts[:, 0], pts[:, 1]) / 255.0
                mappings[label] = y_mapped
            else:
                mappings[label] = x_new / 255.0 # Identity

        # Kết hợp RGB curve với kênh riêng
        lut_r = np.interp(mappings['Red'], x_new/255.0, mappings['RGB'])
        lut_g = np.interp(mappings['Green'], x_new/255.0, mappings['RGB'])
        lut_b = np.interp(mappings['Blue'], x_new/255.0, mappings['RGB'])

        # Build 3D LUT
        try:
            with open(cube_path, 'w') as f:
                f.write(f"# Generated from XMP Sidecar Curves: {source_name}\n")
                f.write(f"LUT_3D_SIZE {dim}\n")
                
                for b_idx in range(dim):
                    b_val = b_idx / (dim - 1)
                    out_b = np.interp(b_val, x_new/255.0, lut_b)
                    for g_idx in range(dim):
                        g_val = g_idx / (dim - 1)
                        out_g = np.interp(g_val, x_new/255.0, lut_g)
                        for r_idx in range(dim):
                            r_val = r_idx / (dim - 1)
                            out_r = np.interp(r_val, x_new/255.0, lut_r)
                            f.write(f"{out_r:.6f} {out_g:.6f} {out_b:.6f}\n")
            
            print(f"[XMP2CUBE] Đã tạo LUT từ Curves thành công: {cube_path}")
            return True
        except Exception as e:
            print(f"[XMP2CUBE Curves Lỗi] {e}")
            return False

    @staticmethod
    def crop_array_to_4_3(img):
        """
        Cắt ảnh numpy array (OpenCV frame) về đúng tỉ lệ 4:3 (canh giữa).
        """
        h, w = img.shape[:2]
        aspect_ratio = w / h
        target_ratio = 4.0 / 3.0
        
        # Sai số nhỏ hơn 0.01 thì coi như đã là 4:3
        if abs(aspect_ratio - target_ratio) <= 0.01:
            return img
            
        if aspect_ratio > target_ratio:
            # Ảnh quá rộng (ví dụ 16:9) -> Cắt bớt chiều ngang (rìa trái & phải)
            new_w = int(h * target_ratio)
            offset = (w - new_w) // 2
            cropped_img = img[:, offset:offset+new_w]
        else:
            # Ảnh quá cao -> Cắt bớt chiều cao (rìa trên & dưới)
            new_h = int(w / target_ratio)
            offset = (h - new_h) // 2
            cropped_img = img[offset:offset+new_h, :]
            
        return cropped_img

    @staticmethod
    def crop_to_4_3(image_path):
        """
        Đảm bảo ảnh thô luôn luôn là tỉ lệ 4:3.
        Nếu tỷ lệ khác (ví dụ: 16:9), nó sẽ cắt (crop) 2 phần rìa ảnh (Canh giữa).
        Thực hiện crop bằng OpenCV để hiệu năng tốt, sau đó ghi đè trực tiếp.
        """
        try:
            if not os.path.exists(image_path):
                return
                
            img = cv2.imread(image_path)
            if img is None:
                return
                
            cropped_img = ImageProcessor.crop_array_to_4_3(img)
            
            # Nếu mảng trả về có khác biệt kích thước thì mới ghi đè
            if cropped_img.shape != img.shape:
                cv2.imwrite(image_path, cropped_img)
                print(f"[CROP] Đã tự động cắt ảnh về tỉ lệ 4:3: {image_path}")
                
        except Exception as e:
            print(f"[CROP Lỗi] Không thể cắt ảnh về tỉ lệ 4:3: {e}")

    @staticmethod
    def apply_frame(image_path, layout_config, icons_data=None):
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError("Không tìm thấy ảnh gốc để chèn khung.")
                
            frame_path = layout_config.get("frame_file", "")
            if not os.path.exists(frame_path):
                raise FileNotFoundError(f"Không tìm thấy file khung: {frame_path}")
                
            frame_w = layout_config["frame_width"]
            frame_h = layout_config["frame_height"]
            points = layout_config["points"]
            
            # Tính toán Bounding Box từ tọa độ %
            min_x = min(points["top_left"]["x_percent"], points["bottom_left"]["x_percent"]) / 100.0 * frame_w
            max_x = max(points["top_right"]["x_percent"], points["bottom_right"]["x_percent"]) / 100.0 * frame_w
            min_y = min(points["top_left"]["y_percent"], points["top_right"]["y_percent"]) / 100.0 * frame_h
            max_y = max(points["bottom_left"]["y_percent"], points["bottom_right"]["y_percent"]) / 100.0 * frame_h
            
            box_x = int(min_x)
            box_y = int(min_y)
            box_w = int(max_x - min_x)
            box_h = int(max_y - min_y)
            
            # Xử lý ảnh base (ảnh chụp được)
            base_img = Image.open(image_path).convert("RGBA")
            
            # Resize image to fit box (Cover / Crop to fill)
            img_aspect = base_img.width / base_img.height
            box_aspect = box_w / box_h
            
            if img_aspect > box_aspect:
                # Ảnh rộng hơn tỷ lệ => crop width
                new_h = box_h
                new_w = int(new_h * img_aspect)
            else:
                # Ảnh cao hơn tỷ lệ => crop height
                new_w = box_w
                new_h = int(new_w / img_aspect)
                
            resized_img = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Cắt phần thừa ra ở giữa tâm
            left = (new_w - box_w) / 2
            top = (new_h - box_h) / 2
            right = (new_w + box_w) / 2
            bottom = (new_h + box_h) / 2
            cropped_img = resized_img.crop((left, top, right, bottom))
            
            # Đọc overlay frame (Đóng vai trò làm nền bên dưới)
            frame_img = Image.open(frame_path).convert("RGBA")
            if frame_img.size != (frame_w, frame_h):
                frame_img = frame_img.resize((frame_w, frame_h), Image.Resampling.LANCZOS)
                
            # Lấy chính cái khung tĩnh làm Gốc (Background)
            result = frame_img.copy()
            
            # Dán chồng ảnh chụp (đã crop xong) LÊN TRÊN cái nền ở đúng tọa độ box
            result.paste(cropped_img, (box_x, box_y))
            
            # 🎨 CHÈN ICONS TRANG TRÍ
            if icons_data:
                for icon in icons_data:
                    try:
                        icon_path = icon['path']
                        if not os.path.exists(icon_path): continue
                        
                        icon_img = Image.open(icon_path).convert("RGBA")
                        
                        # Tính toán size và pos tuyệt đối trên khung
                        iw = int(icon['w_percent'] / 100.0 * frame_w)
                        ih = int(icon['h_percent'] / 100.0 * frame_h)
                        ix = int(icon['x_percent'] / 100.0 * frame_w)
                        iy = int(icon['y_percent'] / 100.0 * frame_h)
                        
                        if iw <= 0 or ih <= 0: continue
                        
                        # Resize icon
                        icon_img = icon_img.resize((iw, ih), Image.Resampling.LANCZOS)
                        
                        # Xoay icon nếu có
                        rot = icon.get('rotation', 0)
                        if rot != 0:
                            icon_img = icon_img.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)
                            # Cân chỉnh lại tọa độ sau khi expanded (rotate expand làm thay đổi anchor)
                            # Tuy nhiên hiện tại IconWidget chưa xoay anchor, ta tạm để mặc định
                        
                        # Dán icon
                        result.alpha_composite(icon_img, (ix, iy))
                    except Exception as icon_err:
                        print(f"[ICON MERGE Lỗi] {icon_err}")

            # Đổi về RGB để save jpg
            rgb_im = result.convert('RGB')
            filename = "print_ready_" + os.path.basename(image_path)
            out_path = os.path.join(OUTPUT_DIR, filename)
            rgb_im.save(out_path, format="JPEG", quality=98)
            return out_path
            
        except Exception as e:
            raise Exception(f"Lý do thất bại: {e}")
