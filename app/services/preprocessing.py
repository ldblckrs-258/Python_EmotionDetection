import numpy as np
from PIL import Image
from typing import Tuple

def preprocess_face(face_img: Image.Image, size: Tuple[int, int] = (224, 224)) -> Image.Image:
    """
    Resize and normalize a face image for model input.
    - Resize to the given size (default 224x224)
    - Normalize pixel values to [0, 1]
    Returns a PIL Image.
    """
    face_resized = face_img.resize(size, resample=Image.Resampling.BILINEAR)
    # Convert to numpy and normalize
    arr = np.array(face_resized).astype(np.float32) / 255.0
    # Convert back to PIL Image (if needed by pipeline)
    face_normalized = Image.fromarray((arr * 255).astype(np.uint8))
    return face_normalized
