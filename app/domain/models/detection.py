from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class EmotionScore(BaseModel):
    """Model for emotion detection scores"""
    emotion: str
    score: float
    percentage: float

class FaceDetection(BaseModel):
    """Model for a single detected face and its emotions"""
    box: tuple[int, int, int, int]  # (x, y, w, h)
    emotions: List[EmotionScore]

class DetectionResult(BaseModel):
    """Model for detection results (multi-face)"""
    faces: List[FaceDetection]
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
    """Model for detection API responses (multi-face)"""
    detection_id: str
    detection_results: DetectionResult
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detection_id": "123456abcdef",
                "user_id": "user123",
                "timestamp": "2024-01-01T00:00:00",
                "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
                "detection_results": {
                    "faces": [
                        {
                            "box": [10, 20, 100, 100],
                            "emotions": [
                                {"emotion": "happy", "score": 0.92, "percentage": 92.0},
                                {"emotion": "sad", "score": 0.05, "percentage": 5.0}
                            ]
                        }
                    ],
                    "face_detected": True,
                    "processing_time": 0.235
                }
            }
        }
    )
