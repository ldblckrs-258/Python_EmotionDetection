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
# Padding factor to expand the detected face regions
FACE_PADDING_FACTOR = float(getattr(settings, "FACE_PADDING_FACTOR", 0.15))  # 20% expansion by default

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

def expand_bounding_box(x, y, w, h, padding_factor=FACE_PADDING_FACTOR, img_width=None, img_height=None) -> Tuple[int, int, int, int]:
    """
    Expands the face bounding box by the specified padding factor.
    Also ensures the box doesn't go outside image boundaries if dimensions are provided.
    
    Args:
        x, y, w, h: Original bounding box coordinates
        padding_factor: Factor by which to expand the box (e.g., 0.2 means 20% larger)
        img_width, img_height: Optional image dimensions to constrain the box
        
    Returns:
        Tuple of (x, y, w, h) for the expanded box
    """
    # Calculate padding amount
    padding_w = int(w * padding_factor)
    padding_h = int(h * padding_factor)
    
    # Thêm nhiều padding ở phía dưới để bao gồm cả cằm và phần dưới mặt
    # Cân bằng lại padding giữa trên và dưới
    top_padding = int(padding_h * 0.8)     # Giảm padding phía trên
    bottom_padding = int(padding_h * 1.2)  # Tăng padding phía dưới
    
    # Calculate new box
    new_x = max(0, x - padding_w // 2)
    new_y = max(0, y - top_padding)
    new_w = w + padding_w
    new_h = h + top_padding + bottom_padding
    
    # Ensure box doesn't exceed image boundaries if dimensions are provided
    if img_width is not None and img_height is not None:
        if new_x + new_w > img_width:
            new_w = img_width - new_x
        if new_y + new_h > img_height:
            new_h = img_height - new_y
    
    return (int(new_x), int(new_y), int(new_w), int(new_h))

def detect_faces(
    img,
    scale_factor: float = FACE_DETECT_CONFIDENCE,
    min_neighbors: int = FACE_DETECT_MIN_NEIGHBORS,
    padding_factor: float = FACE_PADDING_FACTOR
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
        
        # Lấy kích thước ảnh để giới hạn bounding box
        img_height, img_width = cv_img.shape[:2]
        
        # Chuyển đổi sang grayscale cho detection
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        brightness_corrected = cv2.convertScaleAbs(gray, alpha=1.1, beta=5)
        
        min_face_size = max(FACE_DETECT_MIN_SIZE, 64)
        
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=max(scale_factor, 1.1), 
            minNeighbors=max(min_neighbors, 5),
            flags=cv2.CASCADE_SCALE_IMAGE,
            minSize=(min_face_size, min_face_size)
        )
        
        # Nếu không tìm thấy khuôn mặt, thử với cascade alt2 - tham số vẫn chặt chẽ
        if len(faces) == 0:
            faces = alt_face_cascade.detectMultiScale(
                gray,
                scaleFactor=max(scale_factor, 1.1),
                minNeighbors=max(min_neighbors - 1, 4),
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size, min_face_size)
            )
        
        # Nếu vẫn không tìm thấy, thử với alt cascade và giảm ngưỡng một chút
        if len(faces) == 0:
            faces = alt_face_cascade2.detectMultiScale(
                gray,
                scaleFactor=1.08,
                minNeighbors=4,
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
                scaleFactor=1.05,
                minNeighbors=4,
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size // 2, min_face_size // 2)
            )
        
        # Mở rộng các bounding box để bao quát toàn bộ phần đầu
        expanded_faces = [
            expand_bounding_box(x, y, w, h, padding_factor, img_width, img_height)
            for (x, y, w, h) in faces
        ]
        
        # Trả về kết quả với các box được convert sang integer
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in expanded_faces]
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
