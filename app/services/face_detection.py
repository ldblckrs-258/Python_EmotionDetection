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

# Get haarcascade path safely for both runtime and Pylance
try:
    HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
except AttributeError:
    HAAR_CASCADE_PATH = os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml')

# Confidence threshold (scaleFactor and minNeighbors)
FACE_DETECT_CONFIDENCE = float(getattr(settings, "FACE_DETECT_CONFIDENCE", 1.1))  # scaleFactor
FACE_DETECT_MIN_NEIGHBORS = int(getattr(settings, "FACE_DETECT_MIN_NEIGHBORS", 5))
FACE_DETECT_MIN_SIZE = int(getattr(settings, "FACE_DETECT_MIN_SIZE", 32))  # minSize for detectMultiScale

# Load the cascade classifier once
face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)

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
    if isinstance(img, np.ndarray):
        cv_img = img
    else:
        cv_img = pil_to_cv2(img)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=scale_factor,
        minNeighbors=min_neighbors,
        flags=cv2.CASCADE_SCALE_IMAGE,
        minSize=(FACE_DETECT_MIN_SIZE, FACE_DETECT_MIN_SIZE)
    )
    # Return as List[Tuple[int, int, int, int]]
    return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

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
