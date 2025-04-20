from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EmotionScore(BaseModel):
    """Model for emotion detection scores"""
    emotion: str
    score: float
    percentage: float

class DetectionResult(BaseModel):
    """Model for detection results"""
    emotions: List[EmotionScore]
    face_detected: bool
    processing_time: float

class DetectionBase(BaseModel):
    """Base detection model"""
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    image_url: Optional[str] = None

class DetectionCreate(DetectionBase):
    """Model for creating detection records"""
    pass

class DetectionResponse(DetectionBase):
    """Model for detection API responses"""
    detection_id: str
    detection_results: DetectionResult
    
    class Config:
        json_schema_extra = {
            "example": {
                "detection_id": "123456abcdef",
                "user_id": "user123",
                "timestamp": datetime.now(),
                "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
                "detection_results": {
                    "emotions": [
                        {"emotion": "happy", "score": 0.92, "percentage": 92.0},
                        {"emotion": "sad", "score": 0.05, "percentage": 5.0},
                        {"emotion": "angry", "score": 0.03, "percentage": 3.0},
                        {"emotion": "surprised", "score": 0.00, "percentage": 0.0},
                        {"emotion": "disgusted", "score": 0.00, "percentage": 0.0},
                        {"emotion": "neutral", "score": 0.00, "percentage": 0.0},
                        {"emotion": "fear", "score": 0.00, "percentage": 0.0},
                    ],
                    "face_detected": True,
                    "processing_time": 0.235
                }
            }
        }
