import os
from pydantic import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = os.getenv("APP_NAME", "Face Emotion Detection Service")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # MongoDB settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_NAME: str = os.getenv("MONGODB_NAME", "emotion_detection")
    
    # Cloudinary settings
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    # Firebase settings
    FIREBASE_SERVICE_ACCOUNT_KEY: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", "")
    
    # Hugging Face model
    HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "dima806/facial_emotions_image_detection")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    
    # Guest usage limits
    GUEST_MAX_USAGE: int = int(os.getenv("GUEST_MAX_USAGE", "3"))
    
    class Config:
        env_file = ".env"

settings = Settings()
