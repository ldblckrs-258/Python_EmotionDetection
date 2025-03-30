from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from typing import List, Optional
from app.services.emotion_detection import detect_emotions
from app.models.detection import DetectionCreate, DetectionResponse
from app.auth.router import get_current_user, increment_guest_usage
from app.models.user import User
from app.core.config import settings

router = APIRouter()

@router.post("/detect", response_model=DetectionResponse)
async def detect_emotion(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an image to detect facial emotions.
    The image will be processed and the detected emotions will be returned.
    
    Guest users are limited to GUEST_MAX_USAGE detections.
    """
    # Check if user is a guest and has reached usage limit
    if current_user.is_guest:
        # Get current usage and increment it
        new_usage_count = increment_guest_usage(current_user.user_id)
        
        # Check if user has exceeded the limit
        if new_usage_count > settings.GUEST_MAX_USAGE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Guest users are limited to {settings.GUEST_MAX_USAGE} detections. Please log in for unlimited use."
            )
    
    try:
        result = await detect_emotions(file, current_user)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/history", response_model=List[DetectionResponse])
async def get_detection_history(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10
):
    """
    Retrieve the detection history for the current user.
    """
    # This will be implemented with database connection later
    return []

@router.get("/history/{detection_id}", response_model=DetectionResponse)
async def get_detection_detail(
    detection_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific detection by ID.
    """
    # This will be implemented with database connection later
    return None

@router.delete("/history/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detection(
    detection_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific detection by ID.
    """
    # This will be implemented with database connection later
    return None
