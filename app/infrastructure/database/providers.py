# Service provider for repositories
from app.services.database import get_collection
from app.infrastructure.database.repository import DetectionRepository, UserRepository

# Factory functions for repositories
def get_detection_repository():
    collection = get_collection('detections')
    return DetectionRepository(collection)

def get_user_repository():
    collection = get_collection('users')
    return UserRepository(collection)
