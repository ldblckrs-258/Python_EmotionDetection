"""
Face detection service using OpenCV Haar cascades.
- Supports detection of faces in images (PIL Image or bytes)
- Configurable confidence threshold
"""
import cv2
import cv2.data
import numpy as np
from typing import List, Tuple, Optional
from PIL import Image
from app.core.config import settings
import os
import logging

# Thiết lập logging
logger = logging.getLogger(__name__)

# Get haarcascade path safely for both runtime and Pylance
try:
    HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
except AttributeError:
    HAAR_CASCADE_PATH = os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml')

# Confidence threshold (scaleFactor and minNeighbors)
FACE_DETECT_CONFIDENCE = float(getattr(settings, "FACE_DETECT_CONFIDENCE", 1.15))  # scaleFactor
FACE_DETECT_MIN_NEIGHBORS = int(getattr(settings, "FACE_DETECT_MIN_NEIGHBORS", 7))
FACE_DETECT_MIN_SIZE = int(getattr(settings, "FACE_DETECT_MIN_SIZE", 64))  # minSize for detectMultiScale

# Tạo một alternative cascade để thử nghiệm nếu detection không tốt
ALT_HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
ALT_HAAR_CASCADE_PATH2 = cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'

# Load các cascade classifiers
face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
alt_face_cascade = cv2.CascadeClassifier(ALT_HAAR_CASCADE_PATH)
alt_face_cascade2 = cv2.CascadeClassifier(ALT_HAAR_CASCADE_PATH2)

# Kiểm tra xem haarcascade đã được load thành công chưa
if face_cascade.empty():
    logger.error(f"Error: Could not load primary face cascade from {HAAR_CASCADE_PATH}")
if alt_face_cascade.empty():
    logger.error(f"Error: Could not load alternate face cascade from {ALT_HAAR_CASCADE_PATH}")
if alt_face_cascade2.empty():
    logger.error(f"Error: Could not load alternate face cascade 2 from {ALT_HAAR_CASCADE_PATH2}")
else:
    logger.info("Face cascades loaded successfully")

def pil_to_cv2(img: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR image."""
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def cv2_to_pil(arr: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR image (numpy array) to PIL Image (RGB)."""
    if arr.ndim == 2:
        return Image.fromarray(arr)
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

def detect_faces(
    img,
    scale_factor: float = FACE_DETECT_CONFIDENCE,
    min_neighbors: int = FACE_DETECT_MIN_NEIGHBORS
) -> List[Tuple[int, int, int, int]]:
    """
    Detect faces in a PIL image or numpy array.
    Returns a list of bounding boxes (x, y, w, h).
    """
    try:
        # Chuyển đổi sang cv2 image nếu cần
        if isinstance(img, np.ndarray):
            cv_img = img
        else:
            cv_img = pil_to_cv2(img)
        
        # Chuyển đổi sang grayscale cho detection
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        
        # Cải thiện độ tương phản
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Tăng độ sáng nhẹ - không quá nhiều để tránh noise
        brightness_corrected = cv2.convertScaleAbs(gray, alpha=1.1, beta=5)
        
        # Kích thước tối thiểu cho khuôn mặt - tăng lên để giảm false positives
        min_face_size = max(FACE_DETECT_MIN_SIZE, 64)
        
        # Thực hiện detection với cascade mặc định - tham số chặt chẽ hơn
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=max(scale_factor, 1.1),  # Đảm bảo ít nhất 1.1
            minNeighbors=max(min_neighbors, 5),   # Đảm bảo ít nhất 5
            flags=cv2.CASCADE_SCALE_IMAGE,
            minSize=(min_face_size, min_face_size)
        )
        
        # Nếu không tìm thấy khuôn mặt, thử với cascade alt2 - tham số vẫn chặt chẽ
        if len(faces) == 0:
            faces = alt_face_cascade.detectMultiScale(
                gray,
                scaleFactor=max(scale_factor, 1.1),
                minNeighbors=max(min_neighbors - 1, 4),  # Giảm minNeighbors một chút nhưng vẫn giữ ngưỡng cao
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size, min_face_size)
            )
        
        # Nếu vẫn không tìm thấy, thử với alt cascade và giảm ngưỡng một chút
        if len(faces) == 0:
            faces = alt_face_cascade2.detectMultiScale(
                gray,
                scaleFactor=1.08,  # Giảm một chút nhưng vẫn cao
                minNeighbors=4,    # Vẫn giữ ngưỡng hợp lý
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size, min_face_size)
            )
            
        # Thử với ảnh đã tăng độ sáng nếu vẫn không tìm thấy khuôn mặt
        if len(faces) == 0:
            faces = face_cascade.detectMultiScale(
                brightness_corrected,
                scaleFactor=1.08,
                minNeighbors=4,
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size, min_face_size)
            )
        
        # Nếu vẫn không tìm thấy khuôn mặt, thử lần cuối với cấu hình nhạy hơn một chút
        if len(faces) == 0:
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,  # Nhạy hơn nhưng vẫn hợp lý
                minNeighbors=4,    # Giữ ngưỡng để tránh false positives
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size // 2, min_face_size // 2)  # Giảm kích thước tối thiểu
            )
            
        # Loại bỏ bước cuối cùng với cài đặt quá nhạy để tránh false positives
        
        # Trả về kết quả với các box được convert sang integer
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]
    except Exception as e:
        logger.error(f"Error in face detection: {str(e)}")
        return []

def crop_faces(img, boxes: List[Tuple[int, int, int, int]]) -> List[Image.Image]:
    """
    Crop faces from the image given bounding boxes.
    Returns a list of PIL Images.
    """
    faces = []
    # Chuyển sang PIL nếu là numpy array
    if isinstance(img, np.ndarray):
        pil_img = cv2_to_pil(img)
    else:
        pil_img = img
    for (x, y, w, h) in boxes:
        face = pil_img.crop((x, y, x + w, y + h))
        faces.append(face)
    return faces
