# app/services/providers.py
"""
Service provider module for dependency injection.
Provides factory functions for emotion detection and storage services.
"""
from app.services.emotion_detection import detect_emotions
from app.services.storage import (
    get_detections_by_user,
    get_detection,
    delete_detection
)

# Factory function for emotion detection service
def get_emotion_detection_service():
    return detect_emotions

# Factory function for detection history service
def get_detection_history_service():
    return get_detections_by_user

# Factory function for single detection retrieval
def get_single_detection_service():
    return get_detection

# Factory function for detection deletion
def get_delete_detection_service():
    return delete_detection
