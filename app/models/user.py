from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class User(BaseModel):
    """User model for API responses"""
    user_id: str
    email: str
    is_guest: bool = False
    usage_count: int = 0
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None

class UserInDB(User):
    """User model for database operations"""
    class Config:
        schema_extra = {
            "example": {
                "user_id": "firebase_user_id",
                "email": "user@example.com",
                "is_guest": False,
                "usage_count": 5,
                "last_used": datetime.now(),
                "created_at": datetime.now()
            }
        }
