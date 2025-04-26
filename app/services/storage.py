from typing import Dict, List, Optional
from datetime import datetime
import uuid
from app.domain.models.detection import DetectionResponse
from app.infrastructure.database.repository import DetectionRepository
from app.services.database import get_collection
import json
from bson import ObjectId

# In-memory storage for guest detections
# Format: {detection_id: DetectionResponse}
detection_storage: Dict[str, DetectionResponse] = {}

# Custom JSON encoder for MongoDB objects
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

def detection_to_dict(detection: DetectionResponse) -> dict:
    """Convert DetectionResponse to dictionary for MongoDB"""
    detection_dict = detection.model_dump()
    # Convert nested Pydantic models to dict
    detection_dict["detection_results"] = detection.detection_results.model_dump()
    # Convert faces and emotions to list of dicts
    if "faces" in detection_dict["detection_results"]:
        faces = []
        for face in detection_dict["detection_results"]["faces"]:
            # If face is a dict, use as is; else, convert
            if hasattr(face, "box") and hasattr(face, "emotions"):
                faces.append({
                    "box": face.box,
                    "emotions": [emotion.model_dump() if hasattr(emotion, "model_dump") else emotion for emotion in face.emotions]
                })
            elif isinstance(face, dict):
                faces.append(face)
        detection_dict["detection_results"]["faces"] = faces
    # Xóa trường emotions ngoài cùng nếu có
    detection_dict["detection_results"].pop("emotions", None)
    return detection_dict

def dict_to_detection(detection_dict: dict) -> DetectionResponse:
    """Convert dictionary from MongoDB to DetectionResponse"""
    # MongoDB uses _id, convert to detection_id if needed
    if "_id" in detection_dict and "detection_id" not in detection_dict:
        detection_dict["detection_id"] = str(detection_dict.pop("_id"))
    # Ensure timestamp is datetime
    if "timestamp" in detection_dict and isinstance(detection_dict["timestamp"], str):
        detection_dict["timestamp"] = datetime.fromisoformat(detection_dict["timestamp"])
    # Convert faces and emotions back to model
    dr = detection_dict["detection_results"]
    if "faces" in dr:
        from app.domain.models.detection import FaceDetection, EmotionScore
        dr["faces"] = [
            FaceDetection(
                box=face["box"],
                emotions=[EmotionScore(**emo) for emo in face["emotions"]]
            ) for face in dr["faces"]
        ]
    # Xóa trường emotions ngoài cùng nếu có
    dr.pop("emotions", None)
    detection_dict["detection_results"] = dr
    return DetectionResponse(**detection_dict)

async def save_detection(detection: DetectionResponse) -> str:
    """
    Save a detection to storage.
    For authenticated users, save to MongoDB using DetectionRepository.
    For guest users, save to in-memory storage.
    Returns the detection_id.
    """
    if detection.user_id.startswith("guest_"):
        detection_storage[detection.detection_id] = detection
    else:
        try:
            repo = DetectionRepository(get_collection("detections"))
            detection_dict = detection_to_dict(detection)
            detection_dict["_id"] = detection_dict.pop("detection_id")
            await repo.create(detection_dict)
        except Exception as e:
            print(f"Error saving detection to MongoDB: {e}")
    return detection.detection_id

async def get_detection(detection_id: str) -> Optional[DetectionResponse]:
    """
    Get a detection by ID using DetectionRepository.
    Checks both MongoDB and in-memory storage.
    Returns None if not found.
    """
    if detection_id in detection_storage:
        return detection_storage[detection_id]
    try:
        repo = DetectionRepository(get_collection("detections"))
        detection_dict = await repo.get_by_id(detection_id)
        if detection_dict:
            return dict_to_detection(detection_dict)
    except Exception as e:
        print(f"Error retrieving detection from MongoDB: {e}")
    return None

async def get_detections_by_user(user_id: str, skip: int = 0, limit: int = 10) -> List[DetectionResponse]:
    """
    Get detections for a specific user using DetectionRepository.
    For authenticated users, get from MongoDB.
    For guest users, get from in-memory storage.
    """
    detections = []
    if user_id.startswith("guest_"):
        user_detections = [
            detection for detection in detection_storage.values() 
            if detection.user_id == user_id
        ]
        user_detections.sort(key=lambda x: x.timestamp, reverse=True)
        detections = user_detections[skip:skip + limit]
    else:
        try:
            collection = get_collection("detections")
            cursor = collection.find({"user_id": user_id})
            cursor = cursor.sort("timestamp", -1).skip(skip).limit(limit)
            async for doc in cursor:
                detections.append(dict_to_detection(doc))
        except Exception as e:
            print(f"Error retrieving detections from MongoDB: {e}")
    return detections

async def delete_detection(detection_id: str) -> bool:
    """
    Delete a detection by ID using DetectionRepository.
    For authenticated users, delete from MongoDB.
    For guest users, delete from in-memory storage.
    Returns True if deleted, False if not found.
    """
    if detection_id in detection_storage:
        del detection_storage[detection_id]
        return True
    try:
        repo = DetectionRepository(get_collection("detections"))
        return await repo.delete(detection_id)
    except Exception as e:
        print(f"Error deleting detection from MongoDB: {e}")
    return False