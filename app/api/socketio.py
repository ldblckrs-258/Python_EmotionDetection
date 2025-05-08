"""
Socket.IO handler for realtime emotion detection.
"""
import socketio
import jwt
import time
import asyncio
import base64
import numpy as np
import copy
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging

from app.core.config import settings
from app.auth.auth_utils import verify_token
from app.services.video_emotion_detection import VideoEmotionDetector
from app.core.metrics import realtime_connections_gauge

logger = logging.getLogger(__name__)

# Khởi tạo Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=settings.DEBUG,
    engineio_logger=False,
)

class SocketManager:
    """Manager for Socket.IO connections and event handling."""
    
    def __init__(self):
        # Tạo ASGI app
        self.app = socketio.ASGIApp(
            socketio_server=sio,
            socketio_path='socket.io'
        )
        
        # Tạo namespace
        self.namespace = '/emotion-detection'
        
        # Lưu trữ detector instances cho mỗi kết nối
        self.detectors: Dict[str, VideoEmotionDetector] = {}
        
        # Lưu trữ số lượng kết nối đồng thời
        self.connection_count = 0
        
        # Maximum concurrent connections
        self.MAX_CONCURRENT_CONNECTIONS = 20
        
        # Để theo dõi frame đang được xử lý cho mỗi client
        self.processing_frames: Dict[str, bool] = {}
        
        # Lưu trữ frame mới nhất cho mỗi client
        self.latest_frames: Dict[str, Dict[str, Any]] = {}
        
        # Đăng ký các event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all Socket.IO event handlers."""
        # Kết nối và xác thực
        @sio.event(namespace=self.namespace)
        async def connect(sid, environ, auth):
            """Handle new connection with authentication."""
            if self.connection_count >= self.MAX_CONCURRENT_CONNECTIONS:
                logger.warning(f"Connection limit reached ({self.connection_count}/{self.MAX_CONCURRENT_CONNECTIONS})")
                raise ConnectionRefusedError('Server is at capacity, please try again later')
                
            if not auth or 'token' not in auth:
                logger.warning(f"Authentication required for {sid}")
                raise ConnectionRefusedError('Authentication required')

            try:
                # Xác thực JWT token
                user_data = verify_token(auth['token'])
                user_id = user_data.get('sub')
                
                if not user_id:
                    logger.warning(f"Invalid token for {sid}")
                    raise ConnectionRefusedError('Invalid authentication token')

                # Lưu thông tin session
                await sio.save_session(sid, {
                    'user_id': user_id,
                    'connected_at': time.time(),
                    'is_processing': False,
                    'config': {}
                }, namespace=self.namespace)
                
                # Tăng connection count
                self.connection_count += 1
                realtime_connections_gauge.set(self.connection_count)
                
                logger.info(f"Client connected: {sid} (user: {user_id})")
                return True
                
            except Exception as e:
                logger.error(f"Authentication error: {str(e)}")
                raise ConnectionRefusedError('Authentication failed')
        
        @sio.event(namespace=self.namespace)
        async def disconnect(sid):
            """Handle client disconnection."""
            try:
                session = await sio.get_session(sid, namespace=self.namespace)
                user_id = session.get('user_id', 'unknown')
                
                # Giảm connection count
                self.connection_count -= 1
                realtime_connections_gauge.set(self.connection_count)
                
                # Xóa detector nếu tồn tại
                if sid in self.detectors:
                    del self.detectors[sid]
                
                logger.info(f"Client disconnected: {sid} (user: {user_id})")
                
            except Exception as e:
                logger.error(f"Disconnect error: {str(e)}")
        
        @sio.event(namespace=self.namespace)
        async def initialize(sid, data):
            """Initialize session with configuration."""
            try:
                session = await sio.get_session(sid, namespace=self.namespace)
                client_id = data.get('client_id', sid)
                config = data.get('config', {})
                
                # Cập nhật session
                session['client_id'] = client_id
                session['config'] = config
                await sio.save_session(sid, session, namespace=self.namespace)
                
                # Khởi tạo VideoEmotionDetector cho kết nối này
                self.detectors[sid] = VideoEmotionDetector(config=config)
                
                # Gửi phản hồi
                await sio.emit('initialized', {
                    'session_id': sid,
                    'timestamp': time.time(),
                    'config': {
                        'max_frame_rate': 10,  # Giới hạn khung hình tối đa
                        'max_resolution': [640, 480],  # Độ phân giải tối đa
                        'supported_actions': ['start', 'stop', 'configure']
                    }
                }, room=sid, namespace=self.namespace)
                
                logger.info(f"Client initialized: {sid} (client_id: {client_id})")
                
            except Exception as e:
                logger.error(f"Initialization error: {str(e)}")
                await sio.emit('error_message', {
                    'code': 500,
                    'message': f'Failed to initialize: {str(e)}',
                    'timestamp': time.time()
                }, room=sid, namespace=self.namespace)
        
        @sio.event(namespace=self.namespace)
        async def control(sid, data):
            """Handle control commands: start, stop, configure."""
            try:
                session = await sio.get_session(sid, namespace=self.namespace)
                action = data.get('action')
                
                if action == 'start':
                    # Bắt đầu xử lý
                    session['is_processing'] = True
                    await sio.save_session(sid, session, namespace=self.namespace)
                    
                    await sio.emit('status', {
                        'code': 200,
                        'message': 'Processing started',
                        'timestamp': time.time()
                    }, room=sid, namespace=self.namespace)
                    
                elif action == 'stop':
                    # Dừng xử lý
                    session['is_processing'] = False
                    await sio.save_session(sid, session, namespace=self.namespace)
                    
                    await sio.emit('status', {
                        'code': 200,
                        'message': 'Processing stopped',
                        'timestamp': time.time()
                    }, room=sid, namespace=self.namespace)
                    
                elif action == 'configure':
                    # Cập nhật cấu hình
                    config = data.get('config', {})
                    session['config'].update(config)
                    await sio.save_session(sid, session, namespace=self.namespace)
                    
                    # Cập nhật cấu hình cho detector
                    if sid in self.detectors:
                        self.detectors[sid].update_config(config)
                    
                    await sio.emit('status', {
                        'code': 200,
                        'message': 'Configuration updated',
                        'timestamp': time.time()
                    }, room=sid, namespace=self.namespace)
                    
                else:
                    await sio.emit('error_message', {
                        'code': 400,
                        'message': f'Unknown action: {action}',
                        'timestamp': time.time()
                    }, room=sid, namespace=self.namespace)
                    
            except Exception as e:
                logger.error(f"Control error: {str(e)}")
                await sio.emit('error_message', {
                    'code': 500,
                    'message': f'Control error: {str(e)}',
                    'timestamp': time.time()
                }, room=sid, namespace=self.namespace)
        
        @sio.event(namespace=self.namespace)
        async def join_room(sid, data):
            """Join a room to share detection results."""
            try:
                room = data.get('room')
                if room:
                    await sio.enter_room(sid, room, namespace=self.namespace)
                    await sio.emit('status', {
                        'code': 200,
                        'message': f'Joined room: {room}',
                        'timestamp': time.time()
                    }, room=sid, namespace=self.namespace)
                else:
                    await sio.emit('error_message', {
                        'code': 400,
                        'message': 'Room name is required',
                        'timestamp': time.time()
                    }, room=sid, namespace=self.namespace)
                    
            except Exception as e:
                logger.error(f"Join room error: {str(e)}")
                await sio.emit('error_message', {
                    'code': 500, 
                    'message': f'Error joining room: {str(e)}',
                    'timestamp': time.time()
                }, room=sid, namespace=self.namespace)
        
        @sio.event(namespace=self.namespace)
        async def video_frame(sid, data):
            """Process video frame and return detection results."""
            try:
                session = await sio.get_session(sid, namespace=self.namespace)
                
                # Kiểm tra trạng thái xử lý
                if not session.get('is_processing', False):
                    await sio.emit('error_message', {
                        'code': 400,
                        'message': 'Processing not started',
                        'timestamp': time.time()
                    }, room=sid, namespace=self.namespace)
                    return
                
                # Kiểm tra dữ liệu frame
                if not data or 'data' not in data:
                    logger.warning(f"No frame data provided from client {sid}")
                    return
                
                # Log thông tin nhận frame một cách ngắn gọn
                frame_id = data.get('frame_id', 'unknown')
                
                # Lưu frame mới nhất
                self.latest_frames[sid] = data
                
                # Nếu đang xử lý frame khác, bỏ qua frame hiện tại
                # để ưu tiên xử lý frame mới nhất khi xong
                if self.processing_frames.get(sid, False):
                    logger.debug(f"Skipping frame {frame_id} for client {sid}, another frame is being processed")
                    return
                    
                # Đánh dấu đang xử lý frame
                self.processing_frames[sid] = True
                
                # Xử lý frame
                try:
                    # Lấy frame mới nhất
                    latest_frame = self.latest_frames[sid]
                    latest_frame_id = latest_frame.get('frame_id', 'unknown')
                    
                    # Xử lý frame với VideoEmotionDetector
                    result = await self._process_frame(sid, latest_frame)
                    
                    if result:
                        face_count = len(result.get('faces', []))
                        proc_time = result.get('processing_time', 0)
                        
                        # Chỉ log khi phát hiện được khuôn mặt hoặc định kỳ
                        if face_count > 0:
                            logger.info(f"Frame {latest_frame_id}: DETECTED {face_count} faces, time={proc_time:.4f}s")
                        elif int(latest_frame_id) % 30 == 0:
                            logger.debug(f"Frame {latest_frame_id}: Stats - time={proc_time:.4f}s")
                        
                        # Gửi kết quả về client
                        await sio.emit('detection_result', result, room=sid, namespace=self.namespace)
                        
                        # Định kỳ gửi thông tin hiệu suất và đề xuất tối ưu
                        if self.detectors[sid].frame_count % 30 == 0:
                            metrics = self.detectors[sid].get_performance_metrics()
                            
                            # Kiểm tra độ trễ quá cao
                            average_processing_time = metrics.get('average_processing_time', 0)
                            if average_processing_time > 0.5:  # Nếu xử lý trung bình > 500ms
                                suggested_config = {}
                                current_width, current_height = self.detectors[sid].config['processing_resolution']
                                
                                # Đề xuất giảm độ phân giải
                                if current_width > 320:
                                    suggested_config['processing_resolution'] = (
                                        int(current_width * 0.7),
                                        int(current_height * 0.7)
                                    )
                                    
                                    await sio.emit('performance_suggestion', {
                                        'code': 200,
                                        'message': 'High latency detected. Consider reducing resolution for better realtime performance.',
                                        'suggested_config': suggested_config,
                                        'timestamp': time.time()
                                    }, room=sid, namespace=self.namespace)
                            
                            # Gửi metrics
                            await sio.emit('status', {
                                'code': 200,
                                'message': 'Processing metrics',
                                'timestamp': time.time(),
                                'metrics': metrics
                            }, room=sid, namespace=self.namespace)
                finally:
                    # Đánh dấu đã xong xử lý frame
                    self.processing_frames[sid] = False
                    
                    # Nếu có frame mới đến trong lúc xử lý, xử lý tiếp frame mới nhất
                    if sid in self.latest_frames and self.latest_frames[sid] != latest_frame:
                        logger.debug(f"Processing next frame immediately for client {sid}")
                        asyncio.create_task(self.video_frame(sid, self.latest_frames[sid]))
                    
            except Exception as e:
                logger.error(f"Video frame error: {str(e)}")
                self.processing_frames[sid] = False
                await sio.emit('error_message', {
                    'code': 500,
                    'message': f'Error processing frame: {str(e)}',
                    'frame_id': data.get('frame_id') if isinstance(data, dict) else 'unknown',
                    'timestamp': time.time()
                }, room=sid, namespace=self.namespace)

    async def emit_to_room(self, room: str, event: str, data: Dict[str, Any]):
        """
        Gửi sự kiện đến tất cả clients trong một room
        """
        await sio.emit(event, data, room=room, namespace=self.namespace)
    
    async def emit_to_all(self, event: str, data: Dict[str, Any]):
        """
        Gửi sự kiện đến tất cả clients
        """
        await sio.emit(event, data, namespace=self.namespace)
    
    async def get_connected_clients(self) -> List[str]:
        """
        Lấy danh sách các client đang kết nối
        """
        return list(self.detectors.keys())

    async def _process_frame(self, sid: str, frame_data: Dict[str, Any]):
        """Process video frame using VideoEmotionDetector."""
        # Nếu detector chưa được khởi tạo, tạo mới với cấu hình mặc định
        if sid not in self.detectors:
            session = await sio.get_session(sid, namespace=self.namespace)
            config = session.get('config', {})
            self.detectors[sid] = VideoEmotionDetector(config=config)
            logger.info(f"Initialized new VideoEmotionDetector for client {sid} with config: {config}")
            
        # Kiểm tra định dạng video frame
        if not self._validate_frame_data(frame_data, sid):
            # Đã báo lỗi trong _validate_frame_data, không cần xử lý tiếp
            return None
            
        # Xử lý frame
        try:
            result = await self.detectors[sid].process_frame(frame_data)
            
            # Gửi kết quả về client
            await sio.emit('detection_result', result, room=sid, namespace=self.namespace)
            
            # Định kỳ gửi thông tin hiệu suất (sau mỗi 30 frames)
            if self.detectors[sid].frame_count % 30 == 0:
                metrics = self.detectors[sid].get_performance_metrics()
                await sio.emit('status', {
                    'code': 200,
                    'message': 'Processing metrics',
                    'timestamp': time.time(),
                    'metrics': metrics
                }, room=sid, namespace=self.namespace)
                
                # Kiểm tra hiệu suất và đề xuất điều chỉnh nếu cần
                if metrics['current_fps'] < 3 and metrics['processed_frames'] > 60:
                    # Đề xuất giảm độ phân giải hoặc tăng detection_interval
                    suggested_config = {}
                    
                    current_width, current_height = self.detectors[sid].config['processing_resolution']
                    if current_width > 320:  # Không giảm quá thấp
                        suggested_config['processing_resolution'] = (
                            int(current_width * 0.7),
                            int(current_height * 0.7)
                        )
                    
                    if suggested_config:
                        await sio.emit('performance_suggestion', {
                            'code': 200,
                            'message': 'Performance optimization suggestion',
                            'suggested_config': suggested_config,
                            'timestamp': time.time()
                        }, room=sid, namespace=self.namespace)
            
            # Trả về kết quả để có thể sử dụng sau này
            return result
        except Exception as e:
            logger.error(f"Error processing frame for client {sid}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def _validate_frame_data(self, frame_data: Dict[str, Any], sid: str) -> bool:
        """Validate incoming frame data format."""
        if not isinstance(frame_data, dict):
            logger.error(f"Invalid frame data type from client {sid}: not a dictionary")
            return False
            
        # Kiểm tra các trường bắt buộc
        required_fields = ['data', 'frame_id']
        for field in required_fields:
            if field not in frame_data:
                logger.error(f"Missing required field '{field}' in frame data from client {sid}")
                return False
                
        # Kiểm tra định dạng base64
        base64_data = frame_data.get('data', '')
        if not base64_data:
            logger.error(f"Empty base64 data from client {sid}")
            return False
            
        # Kiểm tra xem dữ liệu base64 có đúng định dạng không
        try:
            # Xử lý data URI
            if ',' in base64_data:
                # Ví dụ: "data:image/jpeg;base64,/9j/4AAQ..."
                header, base64_data = base64_data.split(',', 1)
                if not header.startswith('data:image'):
                    logger.warning(f"Unusual data URI header from client {sid}: {header}")
                    
            # Kiểm tra độ dài tối thiểu (đủ để chứa một hình ảnh cơ bản)
            if len(base64_data) < 100:
                logger.warning(f"Suspiciously short base64 data from client {sid}: {len(base64_data)} bytes")
                return False
                
            # Thử decode một phần nhỏ để xác minh định dạng
            import base64
            base64.b64decode(base64_data[:20])
            
            return True
        except Exception as e:
            logger.error(f"Invalid base64 data from client {sid}: {str(e)}")
            return False

# Khởi tạo một instance để sử dụng trong ứng dụng
socket_manager = SocketManager() 