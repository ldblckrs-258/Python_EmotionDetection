from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

class AuthProvider(BaseModel):
    """Authentication provider information"""
    provider_id: str  # 'password', 'google.com', etc.
    provider_uid: Optional[str] = None

class UserCreate(BaseModel):
    """User registration model"""
    email: EmailStr
    password: str
    display_name: Optional[str] = None

class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str

class FirebaseToken(BaseModel):
    """Model for Firebase ID token from client"""
    id_token: str

class User(BaseModel):
    """User model for API responses"""
    user_id: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_guest: bool = False
    is_email_verified: bool = False
    providers: List[str] = []
    usage_count: int = 0
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None

class UserInDB(User):
    """User model for database operations"""
    # class Config:
    #     json_schema_extra = {
    #         "example": {
    #             "user_id": "firebase_user_id",
    #             "email": "user@example.com",
    #             "display_name": "John Doe",
    #             "photo_url": "https://example.com/photo.jpg",
    #             "is_guest": False,
    #             "is_email_verified": True,
    #             "providers": ["password", "google.com"],
    #             "usage_count": 5,
    #             "last_used": "2023-10-10T10:10:10Z",
    #             "created_at": "2023-10-01T10:10:10Z"
    #         }
    #     }
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                    "user_id": "firebase_user_id",
                    "email": "user@example.com",
                    "display_name": "John Doe",
                    "photo_url": "https://example.com/photo.jpg",
                    "is_guest": False,
                    "is_email_verified": True,
                    "providers": ["password", "google.com"],
                    "usage_count": 5,
                    "last_used": "2023-10-10T10:10:10Z",
                    "created_at": "2023-10-01T10:10:10Z"
                }
            }
    )
        