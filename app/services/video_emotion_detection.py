"""
Optimized video emotion detection pipeline for realtime processing.
This module contains the video processing pipeline optimized for Socket.IO streaming.
"""
import time
import cv2
import numpy as np
import base64
import torch
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any, Union
from collections import deque
import os

from app.services.face_detection import detect_faces, crop_faces
from app.services.preprocessing import preprocess_face
from app.services.model_loader import EmotionModelCache
from app.domain.models.detection import DetectionResult, EmotionScore, FaceDetection
from app.core.metrics import realtime_fps_gauge
from app.core.config import settings

# Cấu hình mặc định cho xử lý video frames
DEFAULT_VIDEO_CONFIG = {
    "detection_interval": 1,       # Luôn detect khuôn mặt trên mỗi frame 
    "min_face_size": 64,           # Kích thước tối thiểu khuôn mặt (pixel) - tăng để giảm false positives
    "processing_resolution": (480, 360),  # Giảm độ phân giải xử lý để tăng tốc độ xử lý realtime
    "detection_confidence": 1.1,   # Tăng lên để giảm false positives
    "min_neighbors": 5,            # Tăng lên để giảm false positives 
    "return_bounding_boxes": True, # Trả về bounding box trong kết quả
    "prioritize_realtime": True    # Ưu tiên realtime thay vì FPS cao
}

# Thêm cờ debug để lưu ảnh phát hiện được khuôn mặt (chỉ dùng khi debug)
SAVE_DEBUG_IMAGES = os.environ.get('SAVE_DEBUG_IMAGES', '').lower() == 'true'
DEBUG_IMAGE_DIR = 'logs/debug_images'

if SAVE_DEBUG_IMAGES:
    os.makedirs(DEBUG_IMAGE_DIR, exist_ok=True)

class VideoEmotionDetector:
    """
    Optimized emotion detection pipeline for video frames.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the video emotion detector.
        
        Args:
            config: Configuration parameters, uses DEFAULT_VIDEO_CONFIG if None
        """
        self.config = DEFAULT_VIDEO_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Khởi tạo các biến theo dõi hiệu suất
        self.frame_count = 0
        self.last_detection_time = 0
        self.processing_times = deque(maxlen=30)  # Giữ 30 frame gần nhất
        self.processing_fps = 0
        
        # Dictionary để theo dõi face ID
        self.face_ids = {}
        self.next_face_id = 0
        
    async def process_frame(self, frame_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single video frame and detect emotions.
        
        Args:
            frame_data: Dictionary containing frame information:
                - frame_id: Unique identifier for the frame
                - timestamp: Timestamp of the frame
                - data: Base64 encoded JPEG/PNG image
                - resolution: [width, height] of the original frame
                
        Returns:
            Dictionary containing detection results
        """
        start_time = time.time()
        
        frame_id = frame_data.get("frame_id")
        timestamp = frame_data.get("timestamp", time.time())
        base64_data = frame_data.get("data")
        resolution = frame_data.get("resolution", [640, 480])
        
        # Decode base64 image
        try:
            # Loại bỏ header base64 nếu có
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]

            img_bytes = base64.b64decode(base64_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                raise ValueError("Invalid frame data after decoding")
                
            # Lưu ảnh gốc nếu debug được bật (nhưng chỉ lưu 1 trong 10 frame để giảm I/O)
            if SAVE_DEBUG_IMAGES and int(frame_id) % 10 == 0:
                debug_original_path = os.path.join(DEBUG_IMAGE_DIR, f"original_{frame_id}.jpg")
                cv2.imwrite(debug_original_path, frame)
                
        except Exception as e:
            raise ValueError(f"Failed to decode frame: {str(e)}")
            
        # Resize frame để xử lý nhanh hơn
        try:
            processing_width, processing_height = self.config["processing_resolution"]
            original_height, original_width = frame.shape[:2]
            
            # Đảm bảo không resize quá nhỏ
            if processing_width < 320:
                processing_width = 320
            if processing_height < 240:
                processing_height = 240
                
            scale_factor = min(processing_width / original_width, 
                              processing_height / original_height)
            
            # Resize để xử lý nhanh hơn
            if scale_factor < 1.0:
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                processing_frame = cv2.resize(frame, (new_width, new_height))
                resize_scale = 1.0 / scale_factor
            else:
                processing_frame = frame
                resize_scale = 1.0
                
        except Exception as e:
            processing_frame = frame
            resize_scale = 1.0
        
        # Tăng frame counter
        self.frame_count += 1
        
        # Phát hiện khuôn mặt trong mỗi frame
        face_boxes = []
        face_ids = []
        
        try:
            # Gọi face detector
            face_boxes = detect_faces(
                processing_frame,
                scale_factor=self.config["detection_confidence"],
                min_neighbors=self.config["min_neighbors"]
            )
            
            # Giảm bớt các thử lại nếu ưu tiên realtime
            if len(face_boxes) == 0 and not self.config.get("prioritize_realtime", True):
                # Thử với scale_factor khác một chút nếu không ưu tiên realtime
                face_boxes = detect_faces(
                    processing_frame,
                    scale_factor=1.08,
                    min_neighbors=4
                )
            
            # Chuyển đổi boxes về tỉ lệ gốc
            original_boxes = []
            for idx, (x, y, w, h) in enumerate(face_boxes):
                orig_x = int(x * resize_scale)
                orig_y = int(y * resize_scale)
                orig_w = int(w * resize_scale)
                orig_h = int(h * resize_scale)
                original_boxes.append((orig_x, orig_y, orig_w, orig_h))
                
            # Gán ID cho mỗi khuôn mặt
            current_faces = []
            for idx, (x, y, w, h) in enumerate(original_boxes):
                center_x = x + w // 2
                center_y = y + h // 2
                current_faces.append((idx, (center_x, center_y)))
            
            # Nếu có khuôn mặt được lưu trước đó
            prev_faces = list(self.face_ids.items())
            assigned_ids = []
            
            # Gán ID cho mỗi khuôn mặt dựa trên vị trí gần nhất
            for idx, (center_x, center_y) in current_faces:
                if prev_faces:
                    # Tìm khoảng cách gần nhất
                    best_match = None
                    min_distance = float('inf')
                    
                    for face_id, (prev_x, prev_y) in prev_faces:
                        if face_id in assigned_ids:
                            continue
                            
                        dist = ((center_x - prev_x)**2 + (center_y - prev_y)**2)**0.5
                        if dist < min_distance:
                            min_distance = dist
                            best_match = face_id
                    
                    # Nếu tìm thấy một khuôn mặt đủ gần
                    if best_match is not None and min_distance < 100:  # Ngưỡng khoảng cách
                        face_ids.append(best_match)
                        assigned_ids.append(best_match)
                    else:
                        # Tạo ID mới
                        new_id = f"face_{self.next_face_id}"
                        face_ids.append(new_id)
                        self.next_face_id += 1
                else:
                    # Tạo ID mới nếu không có khuôn mặt trước đó
                    new_id = f"face_{self.next_face_id}"
                    face_ids.append(new_id)
                    self.next_face_id += 1
            
            # Cập nhật vị trí của các ID
            self.face_ids = {}
            for idx, face_id in enumerate(face_ids):
                if idx < len(original_boxes):
                    x, y, w, h = original_boxes[idx]
                    center_x = x + w // 2
                    center_y = y + h // 2
                    self.face_ids[face_id] = (center_x, center_y)
                
        except Exception as e:
            face_boxes = []
            face_ids = []
            original_boxes = []
        
        # Khởi tạo kết quả
        face_detected = len(face_boxes) > 0
        face_detections = []
        
        # Lấy model và processor để phân tích cảm xúc nếu có khuôn mặt
        if face_detected:
            try:
                image_processor, model = EmotionModelCache.get_model_and_processor()
                
                # Cắt khuôn mặt từ ảnh
                faces = crop_faces(processing_frame, face_boxes)
                
                # Tiền xử lý khuôn mặt
                preprocessed_faces = [preprocess_face(face) for face in faces]
                
                # Phân tích cảm xúc
                if preprocessed_faces:
                    inputs = image_processor(images=preprocessed_faces, return_tensors="pt")
                    
                    with torch.no_grad():
                        outputs = model(**inputs)
                        logits = outputs.logits
                        probabilities = torch.nn.functional.softmax(logits, dim=-1)
                    
                    # Lấy labels từ model config
                    if hasattr(model.config, "id2label"):
                        labels = model.config.id2label
                    else:
                        labels = {
                            0: "angry", 1: "disgust", 2: "fear", 
                            3: "happy", 4: "sad", 5: "surprise", 6: "neutral"
                        }
                    
                    # Xử lý kết quả cho mỗi khuôn mặt
                    for i, (probs, box, face_id) in enumerate(zip(probabilities, original_boxes, face_ids)):
                        # Tạo danh sách emotion scores
                        emotion_scores = []
                        for idx, prob in enumerate(probs.tolist()):
                            if idx in labels:
                                label = labels[idx]
                                emotion_scores.append(EmotionScore(
                                    emotion=label,
                                    score=prob,
                                    percentage=prob * 100
                                ))
                        
                        # Sắp xếp theo điểm cao nhất
                        emotion_scores.sort(key=lambda x: x.score, reverse=True)
                        
                        # Tạo FaceDetection object
                        face_detections.append(FaceDetection(
                            box=box if self.config["return_bounding_boxes"] else None,
                            emotions=emotion_scores,
                            face_id=face_id
                        ))
            except Exception as e:
                face_detected = len(face_detections) > 0
        
        # Tính thời gian xử lý
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        # Tính FPS xử lý trung bình (giữ để tương thích với giao diện)
        if len(self.processing_times) > 0:
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
            self.processing_fps = 1.0 / avg_processing_time if avg_processing_time > 0 else 0
            # Cập nhật prometheus metric
            realtime_fps_gauge.set(self.processing_fps)
        
        # Cập nhật thời gian detection
        if face_detected:
            self.last_detection_time = time.time()
        
        # Tạo kết quả trả về
        detection_results = DetectionResult(
            faces=face_detections,
            face_detected=face_detected,
            processing_time=processing_time
        )
        
        # Tính độ trễ từ thời điểm nhận frame đến thời điểm trả kết quả
        latency = time.time() - timestamp if timestamp else processing_time
        
        # Cấu trúc kết quả cho socket.io
        result = {
            "frame_id": frame_id,
            "timestamp": time.time(),
            "processing_time": processing_time,
            "latency": latency,  # Thêm thông tin về độ trễ
            "fps": self.processing_fps,
            "faces": [face.dict() for face in face_detections],
            "face_detected": len(face_detections) > 0,
            "detection_used": True
        }
        
        return result
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update configuration parameters.
        
        Args:
            new_config: Dictionary with new configuration values
        """
        self.config.update(new_config)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            "processed_frames": self.frame_count,
            "current_fps": self.processing_fps,
            "average_processing_time": sum(self.processing_times) / len(self.processing_times) 
                                      if self.processing_times else 0,
            "last_detection_time": self.last_detection_time,
            "tracking_faces": len(self.face_ids)
        } 