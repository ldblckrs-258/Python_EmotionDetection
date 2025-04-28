from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Response, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from jose import jwt, JWTError
import json
import uuid
from app.core.config import settings
from app.domain.models.user import User, FirebaseToken
from app.infrastructure.database.repository import get_refresh_token_repository

router = APIRouter()
oauth2_scheme = HTTPBearer(auto_error=False)

# Initialize Firebase 
firebase_app = None

def init_firebase():
    global firebase_app
    cred_dict = settings.get_firebase_credential_dict()
    if firebase_app is None and cred_dict:
        try:
            cred = credentials.Certificate(cred_dict)
            firebase_app = firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Firebase initialization error: {e}")
            raise

# Call init_firebase at startup
init_firebase()

# Cookie constants
GUEST_COOKIE_NAME = "guest_usage_info"
GUEST_COOKIE_MAX_AGE = 60 * 60 * 24 * 3  # 3 days in seconds

def create_access_token(user_data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tạo một JWT access token cho API, luôn có 'sub' (user_id) và 'exp'.
    """
    to_encode = user_data.copy()
    if "sub" not in to_encode and "user_id" in to_encode:
        to_encode["sub"] = to_encode["user_id"]
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tạo một JWT refresh token cho API, luôn có 'sub' (user_id), 'exp' và 'type'.
    """
    to_encode = user_data.copy()
    if "sub" not in to_encode and "user_id" in to_encode:
        to_encode["sub"] = to_encode["user_id"]
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_or_create_guest_user(
    response: Response, 
    guest_cookie: Optional[str] = None
) -> User:
    """
    Lấy thông tin người dùng từ cookie hoặc tạo một guest user mới.
    """
    guest_info = {}
    guest_id = None
    
    # Try to parse the cookie if it exists
    if guest_cookie:
        try:
            guest_info = json.loads(guest_cookie)
            guest_id = guest_info.get("guest_id")
        except (json.JSONDecodeError, ValueError):
            # Invalid cookie, we'll create a new one
            pass
    
    # Create a new guest ID if needed
    if not guest_id:
        guest_id = f"guest_{uuid.uuid4()}"
        
    # Update and set the cookie
    guest_info = {
        "guest_id": guest_id,
        "last_used": datetime.now().isoformat()
    }
    
    # Set/update the cookie
    response.set_cookie(
        key=GUEST_COOKIE_NAME,
        value=json.dumps(guest_info),
        max_age=GUEST_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax"
    )
    
    return User(
        user_id=guest_id,
        email="guest@example.com",  # Placeholder email for guests
        is_guest=True,
        usage_count=0,  # Always 0 for guests, not tracked
        last_used=datetime.now()
    )

def verify_firebase_token(id_token: str) -> dict:
    """
    Xác thực token từ Firebase.
    """
    try:
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
    """
    Lấy thông tin người dùng từ Firebase bằng user ID.
    """
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
    """
    Format data từ Firebase user thành định dạng của ứng dụng.
    """
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

async def get_current_user(
    response: Response,
    token: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    guest_cookie: Optional[str] = Cookie(None, alias=GUEST_COOKIE_NAME)
) -> User:
    """
    Lấy thông tin người dùng hiện tại từ token hoặc cookie.
    """
    if not token:
        # If no token, create or get a guest user
        return get_or_create_guest_user(response, guest_cookie)
    token_value = token.credentials
    try:
        # Try to decode JWT first
        try:
            payload = jwt.decode(token_value, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            firebase_user = get_user_from_firebase(user_id)
            return format_firebase_user(firebase_user)
        # If JWT decode fails, try Firebase token
        except JWTError:
            firebase_data = verify_firebase_token(token_value)
            firebase_user = get_user_from_firebase(firebase_data["uid"])
            return format_firebase_user(firebase_user)
    except Exception as e:
        print(f"Authentication error: {e}")
        # If authentication fails, fall back to guest user
        return get_or_create_guest_user(response, guest_cookie)

# In-memory store for refresh tokens (demo, nên thay bằng DB ở production)
refresh_token_store = {}

@router.post("/verify-token")
async def verify_token(token_data: FirebaseToken):
    """
    Verify Firebase token và trả về thông tin người dùng.
    Use this endpoint after client-side authentication with Firebase.
    """
    try:
        decoded_token = verify_firebase_token(token_data.id_token)
        user = get_user_from_firebase(decoded_token["uid"])
        # Nếu user là dict (trường hợp đặc biệt), lấy uid từ dict, nếu không thì từ object
        user_uid = user["uid"] if isinstance(user, dict) and "uid" in user else getattr(user, "uid", None)
        if not user_uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user object returned from Firebase"
            )
        access_token = create_access_token({"sub": user_uid})
        refresh_token = create_refresh_token({"sub": user_uid})
        # Lưu refresh_token vào MongoDB
        repo = get_refresh_token_repository()
        await repo.create({
            "refresh_token": refresh_token,
            "user_id": user_uid,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7)
        })
        return {
            "message": "Token verified",
            "user": format_firebase_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        print(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

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
        "usage_count": 0 if current_user.is_guest else current_user.usage_count,
        "max_usage": None if not current_user.is_guest else settings.GUEST_MAX_USAGE
    }

@router.post("/refresh-token")
async def refresh_token(
    refresh_token: str = Body(..., embed=True)
):
    """
    Nhận refresh token, xác thực và trả về access token mới.
    Chỉ chấp nhận refresh_token đã phát hành và còn trong MongoDB.
    """
    from jose import ExpiredSignatureError
    repo = get_refresh_token_repository()
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        # Kiểm tra token_type
        if not user_id or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        # Kiểm tra refresh_token có trong MongoDB
        token_doc = await repo.get_by_token(refresh_token)
        if not token_doc or token_doc.get("user_id") != user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        access_token = create_access_token({"sub": user_id})
        return {"access_token": access_token, "token_type": "bearer"}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/refresh-token/reset")
async def reset_refresh_tokens(current_user: User = Depends(get_current_user)):
    """
    Xóa tất cả refresh_token của user hiện tại khỏi MongoDB.
    """
    repo = get_refresh_token_repository()
    # Xóa tất cả token theo user_id
    collection = repo.collection
    result = await collection.delete_many({"user_id": current_user.user_id})
    return {"message": f"Deleted {result.deleted_count} refresh tokens for user {current_user.user_id}"}
