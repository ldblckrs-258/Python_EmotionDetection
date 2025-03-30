from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth
import json
from app.core.config import settings
from app.models.user import User, UserInDB

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Initialize Firebase (will be properly initialized later)
firebase_app = None

def init_firebase():
    global firebase_app
    if firebase_app is None and settings.FIREBASE_SERVICE_ACCOUNT_KEY:
        try:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_KEY)
            firebase_app = firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Firebase initialization error: {e}")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Validate the authentication token and return the current user.
    For now, we'll use a placeholder implementation.
    """
    # For development, return a mock user - will be replaced with Firebase auth
    user = User(
        user_id="mock_user_id",
        email="user@example.com",
        is_guest=False,
        usage_count=0
    )
    return user

@router.post("/register")
async def register_user():
    """
    Register a new user. This will be implemented with Firebase later.
    """
    return {"message": "User registration endpoint (to be implemented)"}

@router.post("/login")
async def login():
    """
    Log in a user. This will be implemented with Firebase later.
    """
    return {"message": "User login endpoint (to be implemented)"}

@router.get("/profile", response_model=User)
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get the profile of the current authenticated user.
    """
    return current_user

@router.get("/usage")
async def get_usage(current_user: User = Depends(get_current_user)):
    """
    Get the usage statistics for the current user.
    """
    return {
        "user_id": current_user.user_id,
        "is_guest": current_user.is_guest,
        "usage_count": current_user.usage_count,
        "max_usage": None if not current_user.is_guest else settings.GUEST_MAX_USAGE
    }
