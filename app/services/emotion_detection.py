import time
import traceback
from fastapi import UploadFile, HTTPException, status
import torch
from PIL import Image, UnidentifiedImageError
import io
import imghdr
from transformers import AutoFeatureExtractor, AutoModelForImageClassification
import uuid

from app.core.config import settings
from app.models.user import User
from app.models.detection import DetectionResponse, DetectionResult, EmotionScore
from app.utils.cloudinary import upload_image_to_cloudinary
from app.services.storage import save_detection

# Khởi tạo trong lần đầu tiên chạy
feature_extractor = None
model = None

# Max file size (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

async def initialize_model():
    global feature_extractor, model
    if feature_extractor is None or model is None:
        try:
            print(f"Loading model: {settings.HUGGINGFACE_MODEL}")
            # Load the feature extractor and model
            feature_extractor = AutoFeatureExtractor.from_pretrained(settings.HUGGINGFACE_MODEL)
            model = AutoModelForImageClassification.from_pretrained(settings.HUGGINGFACE_MODEL)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading emotion detection model: {e}")
            print(traceback.format_exc())
            raise
    return feature_extractor, model

async def validate_image(image: UploadFile) -> bytes:
    # Check định dạng file
    content_type = image.content_type
    if not content_type or not content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{image.filename}' is not an image. Got content type: {content_type}"
        )
    
    # Check file size
    try:
        contents = await image.read()
        file_size = len(contents)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image size ({file_size / 1024:.1f} KB) exceeds maximum allowed size ({MAX_FILE_SIZE / 1024:.1f} KB)"
            )
            
        # Check image sử dụng imghdr
        image_format = imghdr.what(None, contents)
        if not image_format:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{image.filename}' is not a valid image format"
            )
            
        # Reset file pointer
        await image.seek(0)
        return contents
    
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error processing image: {str(e)}"
            )
        raise

async def detect_emotions(image: UploadFile, user: User) -> DetectionResponse:
    # Băt đầu thời gian xử lý
    start_time = time.time()
    
    try:
        # Validate and read image
        contents = await validate_image(image)
        
        # Load ảnh bằng PIL
        try:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
        except UnidentifiedImageError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot identify image format in file '{image.filename}'"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error opening image: {str(e)}"
            )
        
        # Khởi tạo feature extractor và model nếu chưa khởi tạo
        feature_extractor, model = await initialize_model()
        
        # Chạy mô hình phát hiện cảm xúc
        try:
            
            # Extract features
            inputs = feature_extractor(images=img, return_tensors="pt")
            
            # Prediction
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.nn.functional.softmax(logits, dim=-1)
            
            # Convert to list of emotion scores
            probs = probabilities[0].tolist()
            emotion_scores = []
            
            # Lấy labels từ model config
            if hasattr(model.config, "id2label"):
                labels = model.config.id2label
            else:
                # Nếu không có id2label, sử dụng labels mặc định
                labels = {
                    0: "angry", 1: "disgust", 2: "fear", 
                    3: "happy", 4: "sad", 5: "surprise", 6: "neutral"
                }
            
            for idx, prob in enumerate(probs):
                if idx in labels:
                    label = labels[idx]
                    emotion_scores.append({
                        "label": label,
                        "score": prob
                    })
            
            # Săp xếp theo điểm số
            emotion_scores.sort(key=lambda x: x["score"], reverse=True)
            print(f"Detection result: {emotion_scores}")
            
            emotions = [
                EmotionScore(
                    emotion=item["label"],
                    score=item["score"],
                    percentage=item["score"] * 100
                )
                for item in emotion_scores
            ]
            
            face_detected = len(emotions) > 0
        except Exception as e:
            print(f"Error in emotion detection: {e}")
            print(traceback.format_exc())
            emotions = []
            face_detected = False
        
        # Tính thời gian xử lý
        processing_time = time.time() - start_time
        
        # Upload ảnh lên Cloudinary nếu là người dùng đã xác thực
        image_url = None
        if not user.is_guest:
            try:
                image_url = await upload_image_to_cloudinary(contents)
                print(f"Image uploaded to Cloudinary: {image_url}")
            except Exception as e:
                print(f"Error uploading image to Cloudinary: {e}")
                print(traceback.format_exc())
        
        # Tạo result object
        detection_results = DetectionResult(
            emotions=emotions,
            face_detected=face_detected,
            processing_time=processing_time
        )
        
        #  Tạo response
        response = DetectionResponse(
            detection_id=str(uuid.uuid4()),
            user_id=user.user_id,
            image_url=image_url,
            detection_results=detection_results
        )
        
        # Lưu vào database
        await save_detection(response)
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in detect_emotions: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
