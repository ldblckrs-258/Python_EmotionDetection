import time
from fastapi import UploadFile
import torch
from PIL import Image
import io
from transformers import pipeline
import uuid
from typing import List, Dict, Any

from app.core.config import settings
from app.models.user import User
from app.models.detection import DetectionResponse, DetectionResult, EmotionScore
from app.utils.cloudinary import upload_image_to_cloudinary

# Will be initialized on first request
emotion_classifier = None

async def get_emotion_classifier():
    """
    Initialize and return the emotion detection model.
    """
    global emotion_classifier
    if emotion_classifier is None:
        # Initialize the Hugging Face emotion detection model
        emotion_classifier = pipeline(
            "image-classification",
            model=settings.HUGGINGFACE_MODEL
        )
    return emotion_classifier

async def detect_emotions(image: UploadFile, user: User) -> DetectionResponse:
    """
    Process an image to detect emotions.
    """
    # Start timing
    start_time = time.time()
    
    # Read image content
    contents = await image.read()
    img = Image.open(io.BytesIO(contents))
    
    # Get the emotion classifier
    classifier = await get_emotion_classifier()
    
    # Predict emotions
    try:
        result = classifier(img)
        emotions = [
            EmotionScore(
                emotion=item["label"],
                score=item["score"],
                percentage=item["score"] * 100
            )
            for item in result
        ]
        face_detected = len(emotions) > 0
    except Exception as e:
        print(f"Error in emotion detection: {e}")
        emotions = []
        face_detected = False
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Upload image to Cloudinary
    # This is a placeholder - actual implementation will come later
    image_url = None  # await upload_image_to_cloudinary(contents)
    
    # Create detection result
    detection_results = DetectionResult(
        emotions=emotions,
        face_detected=face_detected,
        processing_time=processing_time
    )
    
    # Create and return response
    response = DetectionResponse(
        detection_id=str(uuid.uuid4()),
        user_id=user.user_id,
        image_url=image_url,
        detection_results=detection_results
    )
    
    # In a real implementation, we would save this detection to the database
    
    return response
