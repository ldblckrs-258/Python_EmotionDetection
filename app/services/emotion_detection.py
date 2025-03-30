import time
import traceback
from fastapi import UploadFile
import torch
from PIL import Image
import io
import numpy as np
from transformers import pipeline, AutoFeatureExtractor, AutoModelForImageClassification
import uuid
from typing import List, Dict, Any

from app.core.config import settings
from app.models.user import User
from app.models.detection import DetectionResponse, DetectionResult, EmotionScore
from app.utils.cloudinary import upload_image_to_cloudinary

# Will be initialized on first request
feature_extractor = None
model = None

# Mapping of model output to emotion categories 
# For age classification, we're using age groups but in a production system
# you would use a proper emotion classification model
EMOTION_MAPPING = {
    "0-2": "neutral",
    "3-9": "happy",
    "10-19": "excited",
    "20-29": "confident",
    "30-39": "relaxed",
    "40-49": "thoughtful",
    "50-59": "mature",
    "60-69": "wise",
    "more than 70": "serene"
}

async def initialize_model():
    """
    Initialize and return the emotion detection model components.
    """
    global feature_extractor, model
    if feature_extractor is None or model is None:
        try:
            print(f"Loading model: {settings.HUGGINGFACE_MODEL}")
            # Load feature extractor and model separately for more control
            feature_extractor = AutoFeatureExtractor.from_pretrained(settings.HUGGINGFACE_MODEL)
            model = AutoModelForImageClassification.from_pretrained(settings.HUGGINGFACE_MODEL)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading emotion detection model: {e}")
            print(traceback.format_exc())
            raise
    return feature_extractor, model

async def detect_emotions(image: UploadFile, user: User) -> DetectionResponse:
    """
    Process an image to detect emotions.
    """
    # Start timing
    start_time = time.time()
    
    try:
        # Read image content
        contents = await image.read()
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Get the model components
        feature_extractor, model = await initialize_model()
        
        # Predict emotions
        try:
            print("Running emotion detection on image")
            
            # Extract features from image
            inputs = feature_extractor(images=img, return_tensors="pt")
            
            # Make prediction
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.nn.functional.softmax(logits, dim=-1)
            
            # Convert to list of emotion scores
            probs = probabilities[0].tolist()
            emotion_scores = []
            
            # Get class labels from model config or use default mapping
            if hasattr(model.config, "id2label"):
                labels = model.config.id2label
            else:
                labels = {i: label for i, label in enumerate(EMOTION_MAPPING.values())}
            
            for idx, prob in enumerate(probs):
                label = labels.get(idx, f"LABEL_{idx}")
                # Map to human-readable emotion if needed
                if label.startswith("LABEL_"):
                    label = EMOTION_MAPPING.get(label, label)
                
                emotion_scores.append({
                    "label": label,
                    "score": prob
                })
            
            # Sort by score and convert to EmotionScore objects
            emotion_scores.sort(key=lambda x: x["score"], reverse=True)
            print(f"Detection result: {emotion_scores}")
            
            emotions = [
                EmotionScore(
                    emotion=item["label"],
                    score=item["score"],
                    percentage=item["score"] * 100
                )
                for item in emotion_scores
            ]
            
            face_detected = len(emotions) > 0
        except Exception as e:
            print(f"Error in emotion detection: {e}")
            print(traceback.format_exc())
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
    except Exception as e:
        print(f"Unexpected error in detect_emotions: {e}")
        print(traceback.format_exc())
        raise
