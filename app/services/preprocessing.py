import numpy as np
from PIL import Image
from typing import Tuple

def preprocess_face(face_img, size: Tuple[int, int] = (224, 224)):
    """
    Resize and normalize a face image for model input.
    - Resize to the given size (default 224x224)
    - Normalize pixel values to [0, 1]
    Trả về cùng kiểu với input (PIL hoặc numpy array).
    """
    from app.services.face_detection import cv2_to_pil
    import numpy as np
    if isinstance(face_img, np.ndarray):
        # Nếu là numpy array (BGR hoặc RGB), chuyển sang PIL để resize
        pil_img = cv2_to_pil(face_img) if face_img.shape[-1] == 3 else Image.fromarray(face_img)
    else:
        pil_img = face_img
    face_resized = pil_img.resize(size, resample=Image.Resampling.BILINEAR)
    arr = np.array(face_resized).astype(np.float32) / 255.0
    # Nếu input là numpy thì trả về numpy, còn lại trả về PIL
    if isinstance(face_img, np.ndarray):
        return arr
    else:
        face_normalized = Image.fromarray((arr * 255).astype(np.uint8))
        return face_normalized
