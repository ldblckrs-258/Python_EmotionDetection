from typing import Dict, List, Optional
from datetime import datetime
import uuid
from app.models.detection import DetectionResponse
from app.services.database import get_collection
import json
from bson import ObjectId

# In-memory storage for guest detections
# Format: {detection_id: DetectionResponse}
detection_storage: Dict[str, DetectionResponse] = {}

# Custom JSON encoder for MongoDB objects
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def detection_to_dict(detection: DetectionResponse) -> dict:
    """Convert DetectionResponse to dictionary for MongoDB"""
    detection_dict = detection.model_dump()
    # Convert nested Pydantic models to dict
    detection_dict["detection_results"] = detection.detection_results.model_dump()
    detection_dict["detection_results"]["emotions"] = [
        emotion.model_dump() for emotion in detection.detection_results.emotions
    ]
    return detection_dict

def dict_to_detection(detection_dict: dict) -> DetectionResponse:
    """Convert dictionary from MongoDB to DetectionResponse"""
    # MongoDB uses _id, convert to detection_id if needed
    if "_id" in detection_dict and "detection_id" not in detection_dict:
        detection_dict["detection_id"] = str(detection_dict.pop("_id"))
    
    # Ensure timestamp is datetime
    if "timestamp" in detection_dict and isinstance(detection_dict["timestamp"], str):
        detection_dict["timestamp"] = datetime.fromisoformat(detection_dict["timestamp"])
    
    return DetectionResponse(**detection_dict)

async def save_detection(detection: DetectionResponse) -> str:
    """
    Save a detection to storage.
    For authenticated users, save to MongoDB.
    For guest users, save to in-memory storage.
    Returns the detection_id.
    """
    # Check if user is guest or authenticated
    if detection.user_id.startswith("guest_"):
        # Guest user - use in-memory storage
        detection_storage[detection.detection_id] = detection
    else:
        # Authenticated user - use MongoDB
        try:
            collection = get_collection("detections")
            detection_dict = detection_to_dict(detection)
            # Use detection_id as MongoDB _id
            detection_dict["_id"] = detection_dict.pop("detection_id")
            await collection.insert_one(detection_dict)
        except Exception as e:
            print(f"Error saving detection to MongoDB: {e}")
    
    return detection.detection_id

async def get_detection(detection_id: str) -> Optional[DetectionResponse]:
    """
    Get a detection by ID.
    Checks both MongoDB and in-memory storage.
    Returns None if not found.
    """
    # First, check in-memory storage
    if detection_id in detection_storage:
        return detection_storage[detection_id]
    
    # Then, check MongoDB
    try:
        collection = get_collection("detections")
        detection_dict = await collection.find_one({"_id": detection_id})
        
        if detection_dict:
            return dict_to_detection(detection_dict)
    except Exception as e:
        print(f"Error retrieving detection from MongoDB: {e}")
    
    return None

async def get_detections_by_user(user_id: str, skip: int = 0, limit: int = 10) -> List[DetectionResponse]:
    """
    Get detections for a specific user.
    For authenticated users, get from MongoDB.
    For guest users, get from in-memory storage.
    """
    detections = []
    
    # Check if user is guest or authenticated
    if user_id.startswith("guest_"):
        # Guest user - use in-memory storage
        user_detections = [
            detection for detection in detection_storage.values() 
            if detection.user_id == user_id
        ]
        
        # Sort by timestamp (newest first)
        user_detections.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply pagination
        detections = user_detections[skip:skip + limit]
    else:
        # Authenticated user - use MongoDB
        try:
            collection = get_collection("detections")
            cursor = collection.find({"user_id": user_id})
            
            # Apply sort and pagination
            cursor = cursor.sort("timestamp", -1).skip(skip).limit(limit)
            
            # Convert to list of DetectionResponse
            async for doc in cursor:
                detections.append(dict_to_detection(doc))
        except Exception as e:
            print(f"Error retrieving detections from MongoDB: {e}")
    
    return detections

async def delete_detection(detection_id: str) -> bool:
    """
    Delete a detection by ID.
    For authenticated users, delete from MongoDB.
    For guest users, delete from in-memory storage.
    Returns True if deleted, False if not found.
    """
    # First check in-memory storage
    if detection_id in detection_storage:
        del detection_storage[detection_id]
        return True
    
    # Then try MongoDB
    try:
        collection = get_collection("detections")
        result = await collection.delete_one({"_id": detection_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting detection from MongoDB: {e}")
    
    return False