# Giao thức Socket.IO cho Realtime Emotion Detection

## Tổng quan giao thức

Giao thức Socket.IO cho tính năng nhận diện cảm xúc realtime là một giao thức bidirectional dựa trên Events, được thiết kế để hỗ trợ việc truyền video frames từ client đến server và nhận kết quả phân tích cảm xúc theo thời gian thực. Socket.IO cung cấp nhiều lợi ích so với WebSocket thuần túy như khả năng tự động kết nối lại, hỗ trợ namespace, room và fallback sang HTTP long-polling nếu cần thiết.

## Thiết lập kết nối

### URL Kết nối

```javascript
// JavaScript client
const socket = io(serverUrl + "/emotion-detection", {
      path: "/socket.io",
      auth: {
        token: token,
      },
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
      transports: ["websocket", "polling"],
    })
```

```python
# Python server (FastAPI integration)
import socketio
from fastapi import FastAPI

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi')
socket_app = socketio.ASGIApp(sio, app)

# Trong app/main.py
app.mount('/', socket_app)
```

### Xác thực

Socket.IO cho phép xác thực thông qua các cách sau:

1. **Auth object**: Truyền token trong object auth khi khởi tạo
2. **Query parameter**: Truyền token trong query parameter khi kết nối
3. **Middleware**: Xác thực qua middleware trên server

#### Ví dụ xác thực trên server

```python
@sio.event
async def connect(sid, environ, auth):
    if not auth or 'token' not in auth:
        raise ConnectionRefusedError('Authentication failed')

    try:
        # Xác thực JWT token
        token = auth['token']
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")

        # Lưu thông tin user vào session
        await sio.save_session(sid, {'user_id': user_id})

        # Cho phép kết nối
        return True
    except Exception:
        raise ConnectionRefusedError('Authentication failed')
```

### Thiết lập kết nối

1. Client khởi tạo kết nối Socket.IO với namespace và thông tin xác thực
2. Server xác thực token và khởi tạo session
3. Client đăng ký các event handlers cho các sự kiện từ server
4. Client gửi event `initialize` để thiết lập cấu hình
5. Server phản hồi với event `initialized` nếu thiết lập thành công

## Sự kiện từ Client đến Server

### Khởi tạo và cấu hình

```javascript
// JavaScript client
socket.emit("initialize", {
  client_id: "unique_client_identifier",
  config: {
    video_source: "webcam",
    detection_interval: 5,
    min_face_size: 64,
    return_face_landmarks: false,
  },
})
```

### Gửi Video Frame

```javascript
// JavaScript client
socket.emit("video_frame", {
  frame_id: 123,
  timestamp: Date.now() / 1000,
  resolution: [640, 480],
  data: "base64_encoded_jpeg_frame",
})
```

### Điều khiển

```javascript
// Bắt đầu xử lý
socket.emit("control", {
  action: "start",
  timestamp: Date.now() / 1000,
})

// Dừng xử lý
socket.emit("control", {
  action: "stop",
  timestamp: Date.now() / 1000,
})

// Cấu hình
socket.emit("control", {
  action: "configure",
  config: {
    detection_interval: 5,
    min_face_size: 64,
    detection_confidence: 0.8,
    return_bounding_boxes: true,
    smooth_emotions: true,
    smooth_window_size: 3,
  },
})
```

## Sự kiện từ Server đến Client

### Khởi tạo thành công

```javascript
// JavaScript client
socket.on("initialized", (data) => {
  console.log(`Connection initialized with session ${data.session_id}`)
  console.log(`Server config: max FPS ${data.config.max_frame_rate}`)
})
```

```python
# Python server
@sio.event
async def initialize(sid, data):
    # Xử lý initial config
    session = await sio.get_session(sid)

    # Phản hồi
    await sio.emit('initialized', {
        'session_id': sid,
        'timestamp': time.time(),
        'config': {
            'max_frame_rate': 10,
            'max_resolution': [640, 480],
            'supported_actions': ['start', 'stop', 'configure']
        }
    }, room=sid)
```

### Kết quả phân tích

```javascript
// JavaScript client
socket.on("detection_result", (data) => {
  console.log(`Received result for frame ${data.frame_id}`)

  // Xử lý kết quả phân tích
  for (const face of data.faces) {
    const dominantEmotion = face.emotions[0]
    console.log(
      `Face at ${face.box}: ${
        dominantEmotion.emotion
      } (${dominantEmotion.percentage.toFixed(1)}%)`
    )
  }
})
```

```python
# Python server
async def process_frame(sid, frame_data):
    # Xử lý frame
    result = {
        'type': 'detection_result',
        'frame_id': frame_data['frame_id'],
        'timestamp': time.time(),
        'processing_time': 0.125,
        'faces': [
            {
                'box': [100, 150, 200, 200],
                'tracking_id': 'face_1',
                'emotions': [
                    {'emotion': 'happy', 'score': 0.92, 'percentage': 92.0},
                    {'emotion': 'sad', 'score': 0.05, 'percentage': 5.0},
                    {'emotion': 'neutral', 'score': 0.03, 'percentage': 3.0}
                ]
            }
        ],
        'face_detected': True
    }

    # Gửi kết quả về client
    await sio.emit('detection_result', result, room=sid)
```

### Thông báo trạng thái

```javascript
// JavaScript client
socket.on("status", (data) => {
  console.log(`Server status: ${data.message}`)

  // Cập nhật UI với metrics
  updateMetricsUI(data.metrics)
})
```

### Thông báo lỗi

```javascript
// JavaScript client
socket.on("error_message", (data) => {
  console.error(`Error (${data.code}): ${data.message}`)

  // Xử lý lỗi
  if (data.code === 429) {
    // Giảm frame rate
    currentFrameRate = data.recommended_value || currentFrameRate / 2
  }
})
```

## Quản lý Rooms và Namespace

Socket.IO cung cấp khả năng quản lý rooms và namespace để tổ chức và phân nhóm các kết nối:

```python
# Python server
# Tạo namespace
ns = sio.namespace('/emotion-detection')

# Thêm client vào room
@sio.event(namespace='/emotion-detection')
async def join_room(sid, data):
    room = data.get('room')
    if room:
        sio.enter_room(sid, room)
        await sio.emit('status', {'message': f'Joined room {room}'}, room=sid)

# Gửi thông báo đến room cụ thể
async def notify_room(room, message):
    await sio.emit('notification', {'message': message}, room=room, namespace='/emotion-detection')
```

## Quy tắc và hạn chế

### Kích thước tin nhắn

- Kích thước tin nhắn tối đa: 1MB
- Định dạng hình ảnh được hỗ trợ: JPEG, PNG (ưu tiên JPEG)
- Nén hình ảnh được khuyến nghị (quality=80 cho JPEG)

### Tần suất tin nhắn

- Frame rate tối đa mặc định: 10 FPS
- Server có thể yêu cầu giảm frame rate nếu quá tải
- Client nên tuân thủ các khuyến nghị của server để tránh bị ngắt kết nối

### Xử lý lỗi và ngắt kết nối

- Socket.IO hỗ trợ tự động kết nối lại khi mất kết nối
- Client nên lắng nghe sự kiện `connect_error` và `disconnect` để xử lý lỗi
- Server sẽ giữ nguyên phiên làm việc trong một khoảng thời gian khi client mất kết nối

## Ví dụ luồng kết nối

### Kết nối và xử lý thành công

1. Client khởi tạo kết nối Socket.IO
2. Client gửi event `initialize`
3. Server phản hồi với event `initialized`
4. Client gửi event `control` với action `start`
5. Client bắt đầu gửi các event `video_frame`
6. Server phản hồi với các event `detection_result` và định kỳ gửi `status`
7. Client gửi event `control` với action `stop` khi hoàn tất
8. Client đóng kết nối

### Xử lý lỗi và khôi phục

1. Client đang gửi video frames
2. Server gửi event `error_message` với code `429` (quá tải) và khuyến nghị giảm frame rate
3. Client điều chỉnh frame rate và tiếp tục gửi frames với tốc độ chậm hơn
4. Server trở lại trạng thái bình thường và gửi thông báo `status`
5. Client có thể tăng frame rate trở lại

## Mã lỗi

| Mã lỗi | Mô tả                  | Hành động khuyến nghị                     |
| ------ | ---------------------- | ----------------------------------------- |
| 400    | Invalid message format | Kiểm tra định dạng dữ liệu                |
| 401    | Unauthorized           | Kiểm tra token xác thực                   |
| 403    | Forbidden              | Kiểm tra quyền truy cập                   |
| 413    | Payload too large      | Giảm kích thước frame hoặc chất lượng nén |
| 429    | Too many requests      | Giảm frame rate                           |
| 500    | Internal server error  | Thử lại sau                               |
| 503    | Service unavailable    | Thử lại sau với backoff strategy          |

## Tối ưu và hiệu suất

### Tối ưu cho client

- Giảm kích thước frame trước khi gửi (resize xuống 640x480 hoặc nhỏ hơn)
- Sử dụng JPEG với chất lượng 70-80% để giảm kích thước truyền
- Không gửi frame nếu không có sự thay đổi đáng kể (phát hiện chuyển động)
- Theo dõi độ trễ mạng và điều chỉnh frame rate phù hợp

### Tối ưu cho server

- Server sẽ drop frames nếu hàng đợi quá 5 frames
- Kết quả có thể được gửi cho các frame đã drop để duy trì tính liên tục
- Server có thể giảm độ phân giải xử lý khi tải cao
- Server sẽ giới hạn số lượng kết nối đồng thời dựa trên tài nguyên

## Ví dụ mã nguồn

### JavaScript Client (Browser)

```javascript
// Kết nối với Socket.IO server
const socket = io("http://api.example.com/emotion-detection", {
  auth: { token: jwtToken },
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 5,
})

// Xử lý sự kiện kết nối
socket.on("connect", () => {
  console.log("Connected to server with id:", socket.id)

  // Khởi tạo session
  socket.emit("initialize", {
    client_id: "browser_client_" + Date.now(),
    config: {
      video_source: "webcam",
      detection_interval: 5,
    },
  })
})

// Xử lý sự kiện khởi tạo thành công
socket.on("initialized", (data) => {
  console.log("Session initialized:", data.session_id)
  startVideoProcessing()
})

// Xử lý kết quả phân tích cảm xúc
socket.on("detection_result", (data) => {
  console.log(`Frame ${data.frame_id}: ${data.faces.length} faces detected`)

  // Hiển thị kết quả
  displayEmotionResults(data.faces)
})

// Xử lý thông báo trạng thái
socket.on("status", (data) => {
  console.log(`Status: ${data.message}`)
  updateStatusDisplay(data)
})

// Xử lý thông báo lỗi
socket.on("error_message", (data) => {
  console.error(`Error (${data.code}): ${data.message}`)

  if (data.code === 429 && data.recommended_value) {
    // Điều chỉnh frame rate
    frameInterval = 1000 / data.recommended_value
    console.log(`Adjusting frame rate to ${data.recommended_value} FPS`)
  }
})

// Xử lý sự kiện ngắt kết nối
socket.on("disconnect", (reason) => {
  console.log("Disconnected from server:", reason)

  if (reason === "io server disconnect") {
    // Server chủ động ngắt kết nối, cần kết nối lại thủ công
    socket.connect()
  }
  // Các trường hợp khác Socket.IO sẽ tự động kết nối lại
})

// Hàm gửi frame video
function sendVideoFrame(videoElement) {
  if (!socket.connected) return

  const canvas = document.createElement("canvas")
  canvas.width = 640
  canvas.height = 480
  const ctx = canvas.getContext("2d")
  ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height)

  // Convert canvas to JPEG base64
  const base64Frame = canvas.toDataURL("image/jpeg", 0.8).split(",")[1]

  // Gửi frame tới server
  socket.emit("video_frame", {
    frame_id: frameCounter++,
    timestamp: Date.now() / 1000,
    resolution: [640, 480],
    data: base64Frame,
  })
}

// Bắt đầu xử lý video
function startVideoProcessing() {
  socket.emit("control", {
    action: "start",
    timestamp: Date.now() / 1000,
  })

  // Bắt đầu gửi video frames
  videoInterval = setInterval(() => {
    if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
      sendVideoFrame(videoElement)
    }
  }, frameInterval) // frameInterval = 1000/10 cho 10 FPS
}

// Dừng xử lý video
function stopVideoProcessing() {
  clearInterval(videoInterval)

  socket.emit("control", {
    action: "stop",
    timestamp: Date.now() / 1000,
  })
}
```

### Python Server

```python
import socketio
import jwt
import time
import asyncio
from fastapi import FastAPI
import base64
import numpy as np
import cv2

# Khởi tạo FastAPI và Socket.IO
app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# Gắn Socket.IO vào FastAPI
app.mount('/', socket_app)

# Lưu trữ session và worker
sessions = {}
worker_tasks = {}

# Xác thực kết nối
@sio.event
async def connect(sid, environ, auth):
    if not auth or 'token' not in auth:
        raise ConnectionRefusedError('Authentication required')

    try:
        # Xác thực token
        token = auth['token']
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('sub')

        if not user_id:
            raise ValueError('Invalid token')

        # Lưu session
        await sio.save_session(sid, {
            'user_id': user_id,
            'connected_at': time.time(),
            'is_processing': False
        })

        print(f"Client connected: {sid} (user: {user_id})")
        return True

    except Exception as e:
        print(f"Authentication error: {e}")
        raise ConnectionRefusedError('Authentication failed')

# Khởi tạo
@sio.event
async def initialize(sid, data):
    try:
        session = await sio.get_session(sid)
        client_id = data.get('client_id', sid)

        # Lưu cấu hình
        session['client_id'] = client_id
        session['config'] = data.get('config', {})
        await sio.save_session(sid, session)

        # Phản hồi
        await sio.emit('initialized', {
            'session_id': sid,
            'timestamp': time.time(),
            'config': {
                'max_frame_rate': 10,
                'max_resolution': [640, 480],
                'supported_actions': ['start', 'stop', 'configure']
            }
        }, room=sid)

    except Exception as e:
        print(f"Initialize error: {e}")
        await sio.emit('error_message', {
            'code': 500,
            'message': 'Failed to initialize session',
            'timestamp': time.time()
        }, room=sid)

# Nhận frame video
@sio.event
async def video_frame(sid, data):
    try:
        session = await sio.get_session(sid)

        if not session.get('is_processing', False):
            await sio.emit('error_message', {
                'code': 400,
                'message': 'Start processing first using control event',
                'timestamp': time.time()
            }, room=sid)
            return

        # Xử lý frame
        frame_id = data.get('frame_id')
        timestamp = data.get('timestamp')
        resolution = data.get('resolution', [640, 480])
        image_data = data.get('data')

        if not image_data:
            raise ValueError('No image data provided')

        # Chuyển base64 thành ảnh
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Đưa vào queue để xử lý
        await process_frame(sid, img, frame_id, timestamp)

    except Exception as e:
        print(f"Video frame error: {e}")
        await sio.emit('error_message', {
            'code': 500,
            'message': f'Error processing frame: {str(e)}',
            'frame_id': data.get('frame_id'),
            'timestamp': time.time()
        }, room=sid)

# Xử lý frame (giả lập)
async def process_frame(sid, img, frame_id, timestamp):
    # Giả lập thời gian xử lý
    await asyncio.sleep(0.1)

    # Giả lập kết quả
    result = {
        'frame_id': frame_id,
        'timestamp': time.time(),
        'processing_time': 0.1,
        'faces': [
            {
                'box': [100, 150, 200, 200],
                'tracking_id': 'face_1',
                'emotions': [
                    {'emotion': 'happy', 'score': 0.92, 'percentage': 92.0},
                    {'emotion': 'sad', 'score': 0.05, 'percentage': 5.0}
                ]
            }
        ],
        'face_detected': True
    }

    # Gửi kết quả về client
    await sio.emit('detection_result', result, room=sid)

# Điều khiển
@sio.event
async def control(sid, data):
    try:
        session = await sio.get_session(sid)
        action = data.get('action')

        if action == 'start':
            # Bắt đầu xử lý
            session['is_processing'] = True
            await sio.save_session(sid, session)

            await sio.emit('status', {
                'code': 200,
                'message': 'Processing started',
                'timestamp': time.time()
            }, room=sid)

        elif action == 'stop':
            # Dừng xử lý
            session['is_processing'] = False
            await sio.save_session(sid, session)

            await sio.emit('status', {
                'code': 200,
                'message': 'Processing stopped',
                'timestamp': time.time()
            }, room=sid)

        elif action == 'configure':
            # Cập nhật cấu hình
            session['config'].update(data.get('config', {}))
            await sio.save_session(sid, session)

            await sio.emit('status', {
                'code': 200,
                'message': 'Configuration updated',
                'timestamp': time.time()
            }, room=sid)

        else:
            await sio.emit('error_message', {
                'code': 400,
                'message': f'Unknown action: {action}',
                'timestamp': time.time()
            }, room=sid)

    except Exception as e:
        print(f"Control error: {e}")
        await sio.emit('error_message', {
            'code': 500,
            'message': f'Control error: {str(e)}',
            'timestamp': time.time()
        }, room=sid)

# Ngắt kết nối
@sio.event
async def disconnect(sid):
    try:
        session = await sio.get_session(sid)
        user_id = session.get('user_id', 'unknown')
        print(f"Client disconnected: {sid} (user: {user_id})")

        # Dọn dẹp tài nguyên nếu cần
        if sid in worker_tasks:
            worker_tasks[sid].cancel()
            del worker_tasks[sid]

    except Exception as e:
        print(f"Disconnect error: {e}")
```
