import time
import traceback
from fastapi import UploadFile, HTTPException, status
import torch
from PIL import Image, UnidentifiedImageError
import io
import imghdr
import uuid
from typing import List

from app.domain.models.detection import DetectionResponse, DetectionResult, EmotionScore, FaceDetection
from app.domain.models.user import User
from app.utils.cloudinary import upload_image_to_cloudinary
from app.services.storage import save_detection
from app.core.validators import is_valid_image_filename, is_non_empty_string
from app.services.face_detection import detect_faces, crop_faces
from app.services.preprocessing import preprocess_face
from app.services.notification import notify_processing_done, notify_processing_failed
from app.services.model_loader import EmotionModelCache
from app.core.metrics import FACE_DETECTION_ACCURACY

MAX_FILE_SIZE = 5 * 1024 * 1024

async def validate_image(image: UploadFile, allow_bytesio: bool = False) -> bytes:
    content_type = getattr(image, 'content_type', None)
    # Kiểm tra tên file không rỗng và hợp lệ
    filename = getattr(image, 'filename', None)
    if not filename or not is_valid_image_filename(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is not a supported image format (jpg, jpeg, png, gif)."
        )
    if not content_type or not content_type.startswith('image/'):
        # Nếu là BytesIO (từ event_stream), cho phép bỏ qua content_type nếu allow_bytesio
        if not (allow_bytesio and isinstance(getattr(image, 'file', None), io.BytesIO)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' is not an image. Got content type: {content_type}"
            )
    try:
        contents = await image.read()
        file_size = len(contents)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image size ({file_size / 1024:.1f} KB) exceeds maximum allowed size ({MAX_FILE_SIZE / 1024:.1f} KB)"
            )
        image_format = imghdr.what(None, contents)
        if not image_format:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' is not a valid image format"
            )
        await image.seek(0)
        return contents
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error processing image: {str(e)}"
            )
        raise

async def detect_emotions(image: UploadFile, user: User, background: bool = False, is_BytesIO: bool = False):
    start_time = time.time()
    try:
        # Nếu là file từ event_stream (io.BytesIO), cho phép validate_image nhận allow_bytesio=True
        contents = await validate_image(image, allow_bytesio=is_BytesIO)
        try:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
        except UnidentifiedImageError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot identify image format in file '{getattr(image, 'filename', None)}'"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error opening image: {str(e)}"
            )
        # Use cached/lazy-loaded model
        image_processor, model = EmotionModelCache.get_model_and_processor()
        try:
            face_boxes = detect_faces(img)
            if not face_boxes:
                face_detections = []
                face_detected = False
                FACE_DETECTION_ACCURACY.set(0)
            else:
                faces = crop_faces(img, face_boxes)
                preprocessed_faces = [preprocess_face(face) for face in faces]
                # --- BATCH INFERENCE: xử lý tất cả khuôn mặt cùng lúc ---
                inputs = image_processor(images=preprocessed_faces, return_tensors="pt")
                with torch.no_grad():
                    outputs = model(**inputs)
                    logits = outputs.logits
                    probabilities = torch.nn.functional.softmax(logits, dim=-1)
                # probabilities shape: (num_faces, num_classes)
                face_detections = []
                if hasattr(model.config, "id2label"):
                    labels = model.config.id2label
                else:
                    labels = {
                        0: "angry", 1: "disgust", 2: "fear", 
                        3: "happy", 4: "sad", 5: "surprise", 6: "neutral"
                    }
                for probs, box in zip(probabilities, face_boxes):
                    emotion_scores = []
                    for idx, prob in enumerate(probs.tolist()):
                        if idx in labels:
                            label = labels[idx]
                            emotion_scores.append({
                                "label": label,
                                "score": prob
                            })
                    emotion_scores.sort(key=lambda x: x["score"], reverse=True)
                    emotions = [
                        EmotionScore(
                            emotion=item["label"],
                            score=item["score"],
                            percentage=item["score"] * 100
                        )
                        for item in emotion_scores
                    ]
                    face_detections.append(FaceDetection(box=box, emotions=emotions))
                face_detected = len(face_detections) > 0
                # Update face detection accuracy metric (simple: 1 if detected, 0 if not)
                FACE_DETECTION_ACCURACY.set(100)
        except Exception as e:
            print(f"Error in emotion detection: {e}")
            print(traceback.format_exc())
            face_detections = []
            face_detected = False
            FACE_DETECTION_ACCURACY.set(0)
        processing_time = time.time() - start_time
        detection_results = DetectionResult(
            faces=face_detections,
            face_detected=face_detected,
            processing_time=processing_time
        )
        detection_id = str(uuid.uuid4())
        response = DetectionResponse(
            detection_id=detection_id,
            user_id=user.user_id,
            image_url=None,  # Sẽ cập nhật sau ở background
            detection_results=detection_results
        )
        # Nếu background=True, chỉ trả về detection_result và đẩy upload/lưu DB vào background
        if background:
            async def background_upload_and_save(response_obj, image_bytes, user_obj):
                try:
                    image_url = await upload_image_to_cloudinary(image_bytes) if not user_obj.is_guest else None
                    if image_url:
                        response_obj.image_url = image_url
                    await save_detection(response_obj)
                    notify_processing_done(response_obj.detection_id)
                except Exception as e:
                    notify_processing_failed(response_obj.detection_id)
            bg_args = {
                "background_func": background_upload_and_save,
                "args": (response, contents, user),
                "kwargs": {}
            }
            return response, bg_args
        # Nếu không chạy background, upload và lưu luôn (giữ nguyên cũ)
        image_url = None
        if not user.is_guest:
            try:
                image_url = await upload_image_to_cloudinary(contents)
                print(f"Image uploaded to Cloudinary: {image_url}")
            except Exception as e:
                print(f"Error uploading image to Cloudinary: {e}")
                print(traceback.format_exc())
        response.image_url = image_url
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

async def detect_emotions_batch(files: List[UploadFile], user: User, background: bool = False):
    """
    Xử lý batch nhiều ảnh, trả về list kết quả (hoặc dùng cho streaming).
    """
    results = []
    bg_tasks = []
    from app.services.emotion_detection import detect_emotions
    for file in files:
        try:
            result, bg_args = await detect_emotions(file, user, background=background)
            results.append(result)
            bg_tasks.append(bg_args)
        except Exception as e:
            results.append({"error": str(e), "filename": getattr(file, 'filename', None)})
    return results, bg_tasks
