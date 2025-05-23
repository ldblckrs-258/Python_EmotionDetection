import cv2
import cv2.data
import numpy as np
from typing import List, Tuple
from PIL import Image
from app.core.config import settings
import os
import logging

logger = logging.getLogger(__name__)

try:
    HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
except AttributeError:
    HAAR_CASCADE_PATH = os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml')

FACE_DETECT_CONFIDENCE = float(getattr(settings, "FACE_DETECT_CONFIDENCE", 1.15))
FACE_DETECT_MIN_NEIGHBORS = int(getattr(settings, "FACE_DETECT_MIN_NEIGHBORS", 6))
FACE_PADDING_FACTOR = float(getattr(settings, "FACE_PADDING_FACTOR", 0.15))

face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)

if face_cascade.empty():
    logger.error(f"Error: Could not load primary face cascade from {HAAR_CASCADE_PATH}")
else:
    logger.info("Face cascade loaded successfully")

def pil_to_cv2(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def cv2_to_pil(arr: np.ndarray) -> Image.Image:
    if arr.ndim == 2:
        return Image.fromarray(arr)
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

def expand_bounding_box(x, y, w, h, padding_factor=FACE_PADDING_FACTOR, img_width=None, img_height=None) -> Tuple[int, int, int, int]:

    padding_w_left = int(w * padding_factor * 1.2)
    padding_w_right = int(w * padding_factor * 0.8)  
    padding_h_top = int(h * padding_factor * 1.2)
    padding_h_bottom = int(h * padding_factor * 1)
    
    new_x = max(0, x - padding_w_left)
    new_y = max(0, y - padding_h_top)
    new_w = w + padding_w_left + padding_w_right
    new_h = h + padding_h_top + padding_h_bottom
    
    if img_width is not None and img_height is not None:
        if new_x + new_w > img_width:
            new_w = img_width - new_x
        if new_y + new_h > img_height:
            new_h = img_height - new_y
    
    return (int(new_x), int(new_y), int(new_w), int(new_h))

def non_max_suppression(boxes, overlapThresh=0.3):

    if len(boxes) == 0:
        return []
    boxes = np.array(boxes).astype(float)
    pick = []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)
    while len(idxs) > 0:
        last = idxs[-1]
        pick.append(last)
        xx1 = np.maximum(x1[last], x1[idxs[:-1]])
        yy1 = np.maximum(y1[last], y1[idxs[:-1]])
        xx2 = np.minimum(x2[last], x2[idxs[:-1]])
        yy2 = np.minimum(y2[last], y2[idxs[:-1]])
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        overlap = (w * h) / area[idxs[:-1]]
        idxs = np.delete(
            idxs, np.concatenate(([len(idxs) - 1], np.where(overlap > overlapThresh)[0]))
        )
    return boxes[pick].astype(int).tolist()

def detect_faces(
    img,
    scale_factor: float = FACE_DETECT_CONFIDENCE,
    min_neighbors: int = FACE_DETECT_MIN_NEIGHBORS,
    padding_factor: float = FACE_PADDING_FACTOR
) -> List[Tuple[int, int, int, int]]:
    try:

        if isinstance(img, np.ndarray):
            cv_img = img
        else:
            cv_img = pil_to_cv2(img)

        img_height, img_width = cv_img.shape[:2]

        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        min_face_size = max(int(min(img_width, img_height) * 0.075), 64)

        scale_factor = max(scale_factor, 1.15)
        min_neighbors = max(min_neighbors, 10)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=scale_factor, 
            minNeighbors=min_neighbors,
            flags=cv2.CASCADE_SCALE_IMAGE,
            minSize=(min_face_size, min_face_size)
        )
        
        if len(faces) == 0:
            brightness_corrected = cv2.convertScaleAbs(gray, alpha=1.1, beta=5)
            faces = face_cascade.detectMultiScale(
                brightness_corrected,
                scaleFactor=1.1,
                minNeighbors=5,
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size, min_face_size)
            )
        
        if len(faces) == 0:
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.08,
                minNeighbors=4,
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_size, min_face_size)
            )

        faces = non_max_suppression(faces, overlapThresh=0.3)

        expanded_faces = [
            expand_bounding_box(x, y, w, h, padding_factor, img_width, img_height)
            for (x, y, w, h) in faces
        ]

        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in expanded_faces]
    except Exception as e:
        logger.error(f"Error in face detection: {str(e)}")
        return []

def crop_faces(img, boxes: List[Tuple[int, int, int, int]]) -> List[Image.Image]:
    faces = []

    if isinstance(img, np.ndarray):
        pil_img = cv2_to_pil(img)
    else:
        pil_img = img
    for (x, y, w, h) in boxes:
        face = pil_img.crop((x, y, x + w, y + h))
        faces.append(face)
    return faces
