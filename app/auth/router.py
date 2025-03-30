from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Cookie, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from jose import jwt, JWTError
import json
import uuid
import requests
from app.core.config import settings
from app.models.user import User, UserInDB, UserCreate, UserLogin, FirebaseToken

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# Store for guest users (in memory for now, would use DB in production)
# Format: {"guest_id": {"usage_count": 0, "last_used": datetime}}
guest_users: Dict[str, Dict] = {}

# Initialize Firebase (called on application startup)
firebase_app = None

def init_firebase():
    global firebase_app
    if firebase_app is None and settings.FIREBASE_SERVICE_ACCOUNT_KEY:
        try:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_KEY)
            firebase_app = firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Firebase initialization error: {e}")
            raise

# Call init_firebase at startup
init_firebase()

def create_custom_token(firebase_uid: str) -> str:
    """Create a custom Firebase token for server-to-client auth"""
    try:
        custom_token = firebase_auth.create_custom_token(firebase_uid)
        return custom_token.decode('utf-8')
    except Exception as e:
        print(f"Error creating custom token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create authentication token"
        )

def create_access_token(user_data: dict) -> str:
    """Create a JWT access token for the API"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = user_data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_guest_token(guest_id: str) -> str:
    """Create a token for guest users"""
    expire = datetime.utcnow() + timedelta(days=30)  # Longer expiry for guests
    to_encode = {"sub": guest_id, "exp": expire, "is_guest": True}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_or_create_guest_user(guest_id: Optional[str] = None) -> User:
    """Get existing or create new guest user"""
    if not guest_id:
        guest_id = f"guest_{uuid.uuid4()}"
    
    if guest_id not in guest_users:
        guest_users[guest_id] = {
            "usage_count": 0,
            "last_used": datetime.now()
        }
    
    return User(
        user_id=guest_id,
        email="guest@example.com",  # Placeholder email for guests
        is_guest=True,
        usage_count=guest_users[guest_id]["usage_count"],
        last_used=guest_users[guest_id]["last_used"]
    )

def increment_guest_usage(guest_id: str) -> int:
    """Increment usage count for a guest user and return new count"""
    if guest_id in guest_users:
        guest_users[guest_id]["usage_count"] += 1
        guest_users[guest_id]["last_used"] = datetime.now()
        return guest_users[guest_id]["usage_count"]
    return 0

def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the user data"""
    try:
        # Verify the token with Firebase
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Firebase token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_from_firebase(firebase_user_id: str) -> dict:
    """Get user data from Firebase"""
    try:
        user = firebase_auth.get_user(firebase_user_id)
        return user
    except firebase_auth.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {firebase_user_id}"
        )
    except Exception as e:
        print(f"Error retrieving user from Firebase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve user data"
        )

def format_firebase_user(firebase_user) -> User:
    """Format Firebase user data to our User model"""
    providers = [
        provider.provider_id for provider in getattr(firebase_user, "provider_data", [])
    ]
    
    return User(
        user_id=firebase_user.uid,
        email=getattr(firebase_user, "email", ""),
        display_name=getattr(firebase_user, "display_name", None),
        photo_url=getattr(firebase_user, "photo_url", None),
        is_guest=False,
        is_email_verified=getattr(firebase_user, "email_verified", False),
        providers=providers,
        usage_count=0,  # This would come from our database
        last_used=datetime.now(),
        created_at=datetime.fromtimestamp(firebase_user.user_metadata.creation_timestamp / 1000)
    )

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    """
    Get the current user from token or create guest user if no token
    """
    if not token:
        # No token - create a new guest user
        return get_or_create_guest_user()
    
    try:
        # First try to decode as our own JWT
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            is_guest = payload.get("is_guest", False)
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if is_guest:
                # This is a guest user with a valid token
                return get_or_create_guest_user(user_id)
            
            # This is a regular user with a valid JWT
            firebase_user = get_user_from_firebase(user_id)
            return format_firebase_user(firebase_user)
        
        except JWTError:
            # Not our JWT, try to verify as Firebase token
            try:
                firebase_data = verify_firebase_token(token)
                firebase_user = get_user_from_firebase(firebase_data["uid"])
                return format_firebase_user(firebase_user)
            except Exception:
                # Not a Firebase token either, create a guest user
                return get_or_create_guest_user()
    
    except Exception as e:
        print(f"Authentication error: {e}")
        return get_or_create_guest_user()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Register a new user with email and password.
    """
    try:
        # Validate email format before sending to Firebase
        if not user_data.email or "@" not in user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
            
        # Validate password
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters"
            )
        
        # Create user in Firebase
        user = firebase_auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.display_name
        )
        
        # Send email verification (optional)
        # firebase_auth.generate_email_verification_link(user_data.email)
        
        # Create custom token for client
        custom_token = create_custom_token(user.uid)
        
        # Create access token for our API
        access_token = create_access_token({"sub": user.uid})
        
        return {
            "message": "User registered successfully",
            "user_id": user.uid,
            "custom_token": custom_token,  # For Firebase client SDK
            "access_token": access_token,  # For our API
            "token_type": "bearer"
        }
    
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except firebase_auth.InvalidArgumentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid argument: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login")
async def login(user_data: UserLogin):
    """
    Log in a user with email and password.
    
    Note: This is a server-side login. For client-side login,
    use Firebase Authentication directly in your frontend.
    """
    try:
        # Validate email format
        if not user_data.email or "@" not in user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
            
        # Get user from Firebase by email (for server-side auth only)
        user = firebase_auth.get_user_by_email(user_data.email)
        
        # Create custom token for client to sign in with Firebase
        custom_token = create_custom_token(user.uid)
        
        # Create access token for our API
        access_token = create_access_token({"sub": user.uid})
        
        return {
            "message": "Login successful",
            "user_id": user.uid,
            "custom_token": custom_token,  # For Firebase client SDK
            "access_token": access_token,  # For our API
            "token_type": "bearer"
        }
    
    except firebase_auth.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except firebase_auth.InvalidArgumentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid argument: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/verify-token")
async def verify_token(token_data: FirebaseToken):
    """
    Verify a Firebase ID token and return user info along with an API access token.
    Use this endpoint after client-side authentication with Firebase.
    """
    try:
        # Verify the Firebase ID token
        decoded_token = verify_firebase_token(token_data.id_token)
        
        # Get the user from Firebase
        user = get_user_from_firebase(decoded_token["uid"])
        
        # Create an access token for our API
        access_token = create_access_token({"sub": user.uid})
        
        return {
            "message": "Token verified",
            "user": format_firebase_user(user),
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    except Exception as e:
        print(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.get("/google-auth-url")
async def get_google_auth_url():
    """
    Get the Google OAuth URL for client-side authentication.
    
    This is for documentation purposes. In practice, you would use
    Firebase's client SDK to handle Google authentication directly.
    """
    return {
        "message": "For Google authentication, use Firebase Authentication SDK in your client application",
        "note": "Firebase provides client SDKs for Web, iOS, and Android that handle the OAuth flow",
    }

@router.get("/guest-token")
async def create_guest():
    """
    Create a new guest user and return a token
    """
    guest_user = get_or_create_guest_user()
    token = create_guest_token(guest_user.user_id)
    return {"access_token": token, "token_type": "bearer", "user_id": guest_user.user_id}

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Log out a user.
    
    Note: For Firebase Authentication, the actual logout happens client-side.
    This endpoint is mainly for documentation and potential future server-side actions.
    """
    return {"message": "Logged out successfully"}

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
