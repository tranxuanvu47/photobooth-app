import cv2
import numpy as np
import os

def safe_cv2_imread(path, flags=cv2.IMREAD_COLOR):
    """
    Đọc ảnh bằng OpenCV hỗ trợ đường dẫn có dấu tiếng Việt (Unicode) trên Windows.
    """
    try:
        if not os.path.exists(path):
            return None
        # Sử dụng numpy.fromfile để đọc dữ liệu nhị phân sau đó imdecode
        img_array = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(img_array, flags)
        return img
    except Exception as e:
        print(f"[safe_cv2_imread Error] {e}")
        return None

def safe_cv2_imwrite(path, img, params=None):
    """
    Ghi ảnh bằng OpenCV hỗ trợ đường dẫn có dấu tiếng Việt (Unicode) trên Windows.
    """
    try:
        # Lấy đuôi mở rộng của file
        ext = os.path.splitext(path)[1]
        if not ext:
            ext = ".jpg"
            
        # Encode ảnh vào buffer
        res, img_encode = cv2.imencode(ext, img, params)
        if res:
            # Ghi buffer vào file bằng numpy.tofile
            img_encode.tofile(path)
            return True
        return False
    except Exception as e:
        print(f"[safe_cv2_imwrite Error] {e}")
        return False
