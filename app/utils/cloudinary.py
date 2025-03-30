import cloudinary
import cloudinary.uploader
from app.core.config import settings
import uuid

# Initialize Cloudinary with credentials
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_image_to_cloudinary(image_data: bytes) -> str:
    """
    Upload an image to Cloudinary and return the URL.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        URL of the uploaded image
    """
    # Generate a unique public_id for the image
    public_id = f"emotion_detection/{uuid.uuid4()}"
    
    try:
        # Upload the image to Cloudinary
        # This is configured to return when the upload is complete (not async)
        upload_result = cloudinary.uploader.upload(
            image_data,
            public_id=public_id,
            folder="emotion_detection",
            resource_type="image"
        )
        
        # Return the secure URL of the uploaded image
        return upload_result.get('secure_url')
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return None
