# Triển khai Socket.IO cho Emotion Detection Realtime

## Cấu trúc triển khai

Thành phần Socket.IO được triển khai với cấu trúc sau:

```
app/
  api/
    socketio.py  # Quản lý Socket.IO
  auth/
    auth_utils.py  # Xác thực JWT
  main.py  # Tích hợp Socket.IO vào FastAPI
```

## Cài đặt thư viện

Trong requirements.txt đã thêm các thư viện sau:

```
python-socketio>=5.8.0
python-engineio>=4.4.0
```

## Quản lý kết nối Socket.IO

`SocketManager` là lớp xử lý chính cho việc quản lý kết nối Socket.IO. Lớp này:

- Khởi tạo Socket.IO server với AsyncServer
- Đăng ký các event handlers cho các sự kiện WebSocket
- Quản lý xác thực và phiên làm việc
- Xử lý kết nối và ngắt kết nối

```python
class SocketManager:
    def __init__(self):
        # Khởi tạo Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',
            logger=True,
            engineio_logger=True
        )

        # Tạo ASGI app và namespace
        self.app = socketio.ASGIApp(self.sio)
        self.namespace = '/emotion-detection'

        # Đăng ký handlers
        self._register_handlers()
```

## Xác thực JWT

Xác thực được thực hiện thông qua JWT token từ client:

```python
@self.sio.event(namespace=self.namespace)
async def connect(sid, environ, auth):
    if not auth or 'token' not in auth:
        raise ConnectionRefusedError('Authentication required')

    try:
        # Xác thực JWT token
        user_data = verify_token(auth['token'])
        user_id = user_data.get('sub')

        # Lưu thông tin session
        await self.sio.save_session(sid, {
            'user_id': user_id,
            'connected_at': time.time(),
            'is_processing': False,
            'config': {}
        }, namespace=self.namespace)

        return True
    except Exception:
        raise ConnectionRefusedError('Authentication failed')
```

## Sự kiện (Events)

### Sự kiện từ client đến server:

1. **initialize**: Khởi tạo phiên làm việc và cấu hình
2. **control**: Điều khiển xử lý (start, stop, configure)
3. **video_frame**: Gửi frame video để phân tích
4. **join_room**: Tham gia vào room cụ thể (cho tính năng chia sẻ kết quả)

### Sự kiện từ server đến client:

1. **initialized**: Phản hồi sau khi khởi tạo
2. **detection_result**: Kết quả phân tích cảm xúc
3. **status**: Thông báo trạng thái
4. **error_message**: Thông báo lỗi

## Xử lý Frame Video

```python
@self.sio.event(namespace=self.namespace)
async def video_frame(sid, data):
    try:
        session = await self.sio.get_session(sid, namespace=self.namespace)

        # Kiểm tra trạng thái xử lý
        if not session.get('is_processing', False):
            await self.sio.emit('error_message', {
                'code': 400,
                'message': 'Processing not started',
                'timestamp': time.time()
            }, room=sid, namespace=self.namespace)
            return

        # Lấy thông tin frame
        frame_id = data.get('frame_id')
        timestamp = data.get('timestamp', time.time())
        resolution = data.get('resolution', [640, 480])
        image_data = data.get('data')

        if not image_data:
            raise ValueError('No image data provided')

        # Xử lý frame
        await self._process_frame(sid, frame_id, timestamp)

    except Exception as e:
        # Xử lý lỗi
        await self.sio.emit('error_message', {
            'code': 500,
            'message': f'Error processing frame: {str(e)}',
            'timestamp': time.time()
        }, room=sid, namespace=self.namespace)
```

## Tích hợp vào FastAPI

Socket.IO được tích hợp vào ứng dụng FastAPI thông qua việc mount ASGI app:

```python
# Trong app/main.py
from app.api.socketio import socket_manager

# ... các định nghĩa FastAPI ...

# Mount Socket.IO app
app.mount('/ws', socket_manager.app)
```

## Client Socket.IO

Đã tạo một client test để kết nối với Socket.IO server:

```javascript
// Kết nối với Socket.IO server
const socket = io("http://localhost:8000/ws/emotion-detection", {
  auth: { token: jwtToken },
})

// Gửi video frame
socket.emit("video_frame", {
  frame_id: frameCounter++,
  timestamp: Date.now() / 1000,
  resolution: [640, 480],
  data: base64ImageData,
})

// Nhận kết quả
socket.on("detection_result", (data) => {
  // Xử lý kết quả phân tích cảm xúc
})
```

## Mở rộng và phát triển tiếp theo

Phiên bản hiện tại mới chỉ thực hiện phần 1 - kết nối và quản lý Socket.IO. Cần phát triển các phần tiếp theo:

1. **Tối ưu hóa pipeline xử lý video**: Sẽ triển khai trong `app/services/video_emotion_detection.py`
2. **Kiến trúc xử lý đa luồng**: Sẽ triển khai trong `app/services/video_queue.py` và `app/services/worker_pool.py`
3. **Tối ưu hiệu suất**: Sẽ bổ sung cơ chế quản lý tài nguyên và giới hạn kết nối

## Kiểm thử

Sử dụng client test trong thư mục `client_examples/socketio/` để kiểm tra chức năng Socket.IO:

1. Mở file `index.html` trong trình duyệt
2. Nhập JWT token hợp lệ
3. Kết nối tới server
4. Bắt đầu gửi video frame từ webcam

## Lưu ý bảo mật

1. Luôn sử dụng HTTPS trong môi trường production
2. JWT token phải được bảo vệ và có thời hạn sử dụng hợp lý
3. Giới hạn số lượng kết nối đồng thời từ cùng một tài khoản
