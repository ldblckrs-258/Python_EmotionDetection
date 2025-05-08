# Tính năng nhận diện cảm xúc realtime qua video Socket.IO

## Tổng quan

Tài liệu này mô tả chi tiết kế hoạch triển khai tính năng nhận diện cảm xúc realtime qua video, sử dụng kết nối Socket.IO. Tính năng này sẽ mở rộng API hiện tại, cho phép nhận diện cảm xúc trực tiếp từ webcam hoặc video stream.

## Đặc điểm kỹ thuật

- **Giao thức**: Socket.IO (xây dựng trên WebSocket với fallback tự động)
- **Thư viện Server**: python-socketio với FastAPI
- **Thư viện Client**: socket.io-client (JavaScript)
- **Định dạng dữ liệu**: JSON + Base64 cho video frames
- **Tốc độ xử lý mục tiêu**: 3-5 FPS
- **Độ phân giải xử lý**: 640x480 pixels
- **Độ trễ tối đa**: 300ms (mục tiêu)

## Những thành phần chính cần phát triển

### 1. Kết nối và quản lý Socket.IO

#### Nhiệm vụ

- [x] Triển khai Socket.IO server trên FastAPI
- [x] Tạo namespace để quản lý kết nối (`/emotion-detection`)
- [x] Xây dựng các sự kiện (events) cho việc truyền và nhận video frames
- [x] Triển khai xác thực người dùng qua Socket.IO (JWT token)
- [x] Phát triển cơ chế quản lý kết nối, rooms và các session
- [x] Tận dụng tính năng auto-reconnect của Socket.IO

#### Các bước triển khai

1. Thêm thư viện `python-socketio` và `uvicorn[standard]` vào requirements
2. Tạo module Socket.IO mới trong cấu trúc project
3. Thiết kế lớp quản lý kết nối Socket.IO (`SocketManager`)
4. Tích hợp xác thực qua middleware Socket.IO
5. Tận dụng tính năng quản lý room có sẵn của Socket.IO

#### Các thay đổi trong codebase

- Tạo file mới: `app/api/socketio.py`
- Thêm định nghĩa server SocketIO trong `app/main.py`
- Cập nhật `requirements.txt` thêm `python-socketio>=5.8.0` và `python-engineio>=4.4.0`

### 2. Tối ưu hóa pipeline xử lý video

#### Nhiệm vụ

- [ ] Điều chỉnh pipeline hiện tại để xử lý video frames
- [ ] Bỏ qua các bước lưu trữ không cần thiết (không lưu vào DB hay cloudinary bất kể user)
- [ ] Giảm độ phân giải xử lý để đạt được FPS cao hơn
- [ ] Thêm face tracking để giảm tải cho face detection
- [ ] Triển khai emotion smoothing giữa các frame
- [ ] Xây dựng cơ chế quản lý bộ nhớ và CPU để tránh quá tải

#### Các bước triển khai

1. Tạo phiên bản tối ưu của `detect_emotions` cho video stream
2. Triển khai `OpencvFaceTracker` để theo dõi khuôn mặt giữa các frame
3. Thêm emotion smoothing bằng cách sử dụng window trượt
4. Thiết lập adaptive sampling để điều chỉnh FPS theo tài nguyên hệ thống
5. Thử nghiệm và tinh chỉnh các tham số cho realtime

#### Các thay đổi trong codebase

- Tạo file mới: `app/services/video_emotion_detection.py`
- Tạo file mới: `app/services/face_tracking.py`
- Sửa đổi: `app/services/face_detection.py` để thêm các tham số tối ưu

### 3. Kiến trúc xử lý đa luồng

#### Nhiệm vụ

- [ ] Tách biệt quá trình nhận frames và xử lý emotion
- [ ] Triển khai worker pool để xử lý song song nhiều kết nối
- [ ] Xây dựng cơ chế hàng đợi để điều phối xử lý frames
- [ ] Cài đặt cơ chế back-pressure để tránh quá tải hàng đợi
- [ ] Phát triển giám sát và giới hạn tài nguyên cho mỗi kết nối

#### Các bước triển khai

1. Thiết kế `VideoFrameQueue` để quản lý frames đến
2. Tạo `EmotionDetectionWorker` để xử lý frames từ hàng đợi
3. Triển khai cơ chế để drop frames khi hàng đợi quá tải
4. Thiết lập giới hạn số lượng frame trong hàng đợi
5. Phát triển hệ thống giám sát hiệu suất

#### Các thay đổi trong codebase

- Tạo file mới: `app/services/video_queue.py`
- Tạo file mới: `app/services/worker_pool.py`
- Thêm metrics cho giám sát trong `app/core/metrics.py`

### 4. Cấu trúc sự kiện Socket.IO

#### Nhiệm vụ

- [ ] Thiết kế các sự kiện (events) để gửi/nhận dữ liệu
- [ ] Tối ưu hóa định dạng truyền video frames (base64, binary, compression)
- [ ] Phát triển cơ chế xử lý lỗi và tự động kết nối lại
- [ ] Tạo cơ chế điều khiển từ client (bắt đầu/dừng phân tích, cấu hình)
- [ ] Đảm bảo kích thước message tối ưu

#### Sự kiện từ client đến server

```javascript
// Gửi frame video
socket.emit("video_frame", {
  frame_id: 123,
  timestamp: 1684918345.123,
  resolution: [640, 480],
  data: "base64_encoded_jpeg_frame",
})

// Điều khiển
socket.emit("control", {
  action: "start", // hoặc "stop", "configure"
  config: {
    detection_interval: 5,
    min_face_size: 64,
    return_bounding_boxes: true,
  },
})
```

#### Sự kiện từ server đến client

```javascript
// Kết quả phân tích
socket.on("detection_result", (data) => {
  console.log(`Received result for frame ${data.frame_id}`)
  // data.faces chứa khuôn mặt và cảm xúc
})

// Thông báo trạng thái
socket.on("status", (data) => {
  console.log(`Server status: ${data.message}`)
})

// Thông báo lỗi
socket.on("error", (data) => {
  console.error(`Error: ${data.message}`)
})
```

### 5. Cân nhắc và xử lý vấn đề hiệu năng

#### Nhiệm vụ

- [ ] Thực hiện benchmark và profiling để xác định bottleneck
- [ ] Thiết lập cơ chế tự động scale down chất lượng dựa trên tải
- [ ] Giới hạn số lượng kết nối đồng thời dựa trên tài nguyên server
- [ ] Theo dõi và đánh giá sử dụng GPU (nếu có)
- [ ] Triển khai caching cho các khuôn mặt đã nhận diện

#### Các bước triển khai

1. Tạo công cụ benchmark để đánh giá hiệu suất
2. Thực hiện profiling trên codebase để xác định điểm nghẽn
3. Triển khai cơ chế quản lý tài nguyên tự động
4. Thiết lập thông báo khi hệ thống quá tải
5. Tài liệu hóa các yêu cầu về phần cứng

#### Các thay đổi trong codebase

- Tạo file mới: `app/core/performance_monitor.py`
- Thêm cấu hình môi trường trong `app/core/config.py`
- Thêm các test hiệu suất trong `tests/performance/`

### 6. Thử nghiệm và triển khai

#### Nhiệm vụ

- [ ] Phát triển client test để kết nối và gửi video frames
- [ ] Tạo các testcase cho các kịch bản sử dụng
- [ ] Tài liệu hóa API và giao thức Socket.IO
- [ ] Triển khai monitoring và logging
- [ ] Phát triển fallback strategy khi server quá tải

#### Các bước triển khai

1. Tạo client Socket.IO test bằng JavaScript
2. Viết test cases end-to-end cho tính năng
3. Cập nhật tài liệu API với Socket.IO documentation
4. Cấu hình logging và giám sát cho Socket.IO
5. Tạo environment cho staging và testing

#### Các thay đổi trong codebase

- Tạo thư mục mới: `client_examples/socketio/`
- Cập nhật tài liệu API: `docs/api_guide.md`
- Tạo tài liệu mới: `docs/socketio_protocol.md`

## Timeline và ưu tiên

1. **Tuần 1**: Phát triển cơ sở hạ tầng Socket.IO và protocol

   - Thiết lập server Socket.IO trên FastAPI
   - Thiết kế và triển khai các events
   - Tạo client test đơn giản

2. **Tuần 2**: Tối ưu pipeline xử lý video

   - Điều chỉnh face detection cho video
   - Triển khai face tracking
   - Thử nghiệm hiệu suất với các video test

3. **Tuần 3**: Kiến trúc đa luồng và xử lý đồng thời

   - Triển khai worker pool
   - Thiết lập hàng đợi và back-pressure
   - Thử nghiệm với nhiều kết nối đồng thời

4. **Tuần 4**: Tối ưu và triển khai
   - Profiling và tối ưu hiệu suất
   - Triển khai giám sát và giới hạn tài nguyên
   - Hoàn thiện tài liệu và API

## Đánh giá rủi ro và giảm thiểu

### Rủi ro hiệu suất

- **Rủi ro**: Độ trễ cao khi xử lý video realtime
- **Giảm thiểu**: Tối ưu pipeline, giảm resolution, triển khai tracking

### Rủi ro tài nguyên

- **Rủi ro**: Quá tải CPU/RAM khi có nhiều kết nối đồng thời
- **Giảm thiểu**: Giới hạn số lượng kết nối, drop frames khi quá tải

### Rủi ro chất lượng

- **Rủi ro**: Giảm độ chính xác khi tối ưu cho realtime
- **Giảm thiểu**: Tinh chỉnh model parameters, theo dõi độ chính xác

### Rủi ro mạng

- **Rủi ro**: Mất kết nối hoặc độ trễ mạng cao
- **Giảm thiểu**: Tận dụng tính năng tự động kết nối lại của Socket.IO, xử lý graceful degradation

## Tài liệu tham khảo

- [Python-SocketIO Documentation](https://python-socketio.readthedocs.io/)
- [Socket.IO Client JavaScript](https://socket.io/docs/v4/client-api/)
- [FastAPI with Socket.IO](https://python-socketio.readthedocs.io/en/latest/server.html#asgi-frameworks-like-fastapi-quart-or-starlette)
- [OpenCV Face Tracking](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [Optimizing Computer Vision for Realtime](https://learnopencv.com/optimizing-opencv/)
