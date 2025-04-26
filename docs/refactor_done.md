# Các thay đổi đã làm:

# Các thay đổi đã làm:

## Phần 1: Tái cấu trúc xử lý lỗi và ghi log

### 1. Tạo tệp ngoại lệ tùy chỉnh (`exceptions.py`)

- Triển khai hệ thống phân cấp ngoại lệ bắt đầu với `AppBaseException` làm lớp cơ sở  
- Thêm các ngoại lệ chuyên biệt cho từng loại lỗi (cơ sở dữ liệu, xác thực, phân quyền, kiểm tra dữ liệu, v.v.)  
- Mỗi ngoại lệ bao gồm mã trạng thái, thông báo, và chi tiết tùy chọn  

### 2. Tạo middleware xử lý lỗi (`middlewares.py`)

- Triển khai middleware tương thích với ASGI để bắt tất cả ngoại lệ  
- Tạo phản hồi lỗi chuẩn hóa với định dạng JSON nhất quán  
- Sửa lỗi triển khai để đảm bảo tương thích ASGI đúng cách  

### 3. Tạo hệ thống ghi log chuẩn hóa (`logging.py`)

- Triển khai hệ thống ghi log linh hoạt với tùy chọn định dạng JSON và văn bản  
- Thêm ghi log theo ngữ cảnh với lớp `ContextLogger`  
- Cấu hình ghi log ra cả console và file  

### 4. Cập nhật ứng dụng chính (`main.py`)

- Thay thế hệ thống ghi log mặc định bằng logger tùy chỉnh  
- Thêm middleware xử lý lỗi để xử lý ngoại lệ toàn cục  
- Thêm trình xử lý ngoại lệ riêng cho các ngoại lệ tùy chỉnh  

### 5. Cập nhật cấu hình (`config.py`)

- Thêm các tùy chọn cấu hình liên quan đến ghi log (`LOG_LEVEL`, `LOG_TO_FILE`, `LOG_FORMAT`)  
- Các thiết lập này có thể được cấu hình thông qua biến môi trường  

### 6. Cải thiện cấu trúc (`requirements.txt`)

- Tổ chức lại requirements.txt thành các nhóm dependencies rõ ràng
- Đảm bảo file sử dụng encoding chuẩn UTF-8

### 7. Tạo utils cho validation (`app/core/validators.py`)

- Tạo các hàm kiểm tra định dạng email, file ảnh, số dương, chuỗi không rỗng
- Tích hợp validator cho upload ảnh

## Phần 2: Tái cấu trúc database access

### 1. Tái cấu trúc database access (`app/infrastructure/database/`)

- Tạo abstract class Repository và các repository cụ thể
- Triển khai providers cho repository 
- Refactor storage service
- Cập nhật database service

### 2. Triển khai Repository Pattern

- Triển khai interface Repository
- Thêm các phương thức CRUD cơ bản
- Tạo các repository chuyên biệt
- Thêm validation và error handling

### 3. Cập nhật Database Providers (`providers.py`)

- Tạo các factory function
- Thêm lifecycle hooks
- Hỗ trợ cấu hình động
- Tích hợp logging

### 4. Refactor Storage Service (`storage.py`)

- Chuyển đổi sang DetectionRepository
- Cập nhật error handling
- Thêm transaction support
- Tối ưu hóa performance

### 5. Tạo module service providers (`app/services/providers.py`)

- Tạo các factory function cho các service chính
- Inject các service vào API routes

## Phần 3: Di chuyển models domain

### 1. Tạo cấu trúc thư mục domain

- Tạo thư mục `app/domain/` và `app/domain/models/`
- Di chuyển các models hiện có
- Cập nhật các import paths
- Sửa lỗi thuộc tính `uid`

## Phần 4: Tích hợp phát hiện khuôn mặt

### 1. Triển khai face detection (`app/services/face_detection.py`)

- Tích hợp OpenCV Haar cascades
- Cấu hình thông số qua biến môi trường
- Triển khai hàm `detect_faces()`

### 2. Tạo pipeline xử lý ảnh

- Đã tích hợp phát hiện khuôn mặt (OpenCV Haar cascade) vào pipeline.
- Thêm chức năng crop khuôn mặt từ ảnh đầu vào (hàm crop_faces).
- Thêm module tiền xử lý ảnh khuôn mặt (resize, chuẩn hóa) cho từng khuôn mặt (hàm preprocess_face).
- Đảm bảo khả năng xử lý nhiều khuôn mặt trên một ảnh: pipeline sẽ phát hiện, crop, tiền xử lý và nhận diện cảm xúc cho tất cả khuôn mặt tìm được. Nếu không phát hiện khuôn mặt, pipeline sẽ xử lý toàn bộ ảnh.
- Đã cập nhật pipeline trong (`services/emotion_detection.py`) để sử dụng các bước trên.

## Giai đoạn 2.3: Tăng cường bảo mật

### 1. Triển khai rate limiting
- Thêm `RateLimitMiddleware` vào `app/core/middlewares.py` để giới hạn số lượng request từ một IP hoặc guest_id cho endpoint `/api/detect` (chỉ áp dụng cho guest user).
- Middleware này sử dụng in-memory dict để theo dõi số lượng request trong một khoảng thời gian (mặc định 10 requests/60s).
- Nếu vượt quá giới hạn, trả về mã lỗi 429 (Rate limit exceeded).
- Đăng ký middleware này trong `main.py` (trước ErrorHandlingMiddleware).

### 2. Cải thiện token security
- Cập nhật hàm `create_access_token` để luôn có trường `sub` (user_id) và `exp` (hết hạn) trong JWT.
- Thêm endpoint `/auth/refresh-token` để cấp lại access token mới từ refresh token (JWT).
- Đảm bảo access token và refresh token đều được xác thực đúng chuẩn.

### 3. Bổ sung quản lý refresh token bảo mật
- Lưu refresh_token vào MongoDB khi xác thực thành công (endpoint `/auth/verify-token`).
- Endpoint `/auth/refresh-token` chỉ cấp access_token mới nếu refresh_token hợp lệ và còn trong MongoDB.
- Thêm endpoint DELETE `/auth/refresh-token` để xóa một refresh_token cụ thể.
- Thêm endpoint POST `/auth/refresh-token/reset` để xóa toàn bộ refresh_token của user hiện tại (thu hồi đăng nhập trên mọi thiết bị).
- Các thao tác này giúp tăng bảo mật, chủ động thu hồi token khi cần thiết.

### 4. Ảnh hưởng
- Guest user bị giới hạn tốc độ gửi request và số lần sử dụng tính năng nhận diện cảm xúc.
- Token bảo mật hơn, hỗ trợ cơ chế refresh token.

## Giai đoạn 2.4: Nâng cao xử lý đồng thời

### 1. Sử dụng background tasks (FastAPI)
- Endpoint `/api/detect` sử dụng `BackgroundTasks` để upload ảnh và lưu vào database bất đồng bộ.
- Kết quả detection trả về ngay cho client, các tác vụ nặng (upload/lưu DB) thực hiện ở background.
- Hàm `detect_emotions` refactor để tách detection (trả về ngay) và upload/lưu DB (background).

### 2. Worker service cho xử lý ảnh nặng
- Tạo hàm background xử lý upload/lưu DB, có thể mở rộng thành worker service (Celery/RQ) trong tương lai.

### 3. Notification hệ thống
- Tạo module `app/services/notification.py` lưu trạng thái xử lý detection (pending/done/failed) bằng in-memory dict.
- Thêm endpoint `/api/detect/status/{detection_id}` để client kiểm tra trạng thái xử lý (polling notification).
- Khi background task hoàn tất/thất bại sẽ cập nhật trạng thái notification.

### 4. Ảnh hưởng
- API trả về detection_result rất nhanh, các thao tác nặng không làm chậm phản hồi.
- Client có thể kiểm tra trạng thái xử lý qua endpoint mới.
- Dễ mở rộng sang worker queue hoặc WebSocket notification.

## Giai đoạn 3.1: Cải thiện hiệu suất

### 1. Tối ưu model loading (emotion recognition)
- Tách riêng service `app/services/model_loader.py` để quản lý việc load và cache model HuggingFace (dùng singleton, thread-safe, lazy loading).
- Các service khác chỉ truy cập model/processor qua `EmotionModelCache.get_model_and_processor()` (không còn biến toàn cục hoặc load lại nhiều lần).
- Giảm thời gian khởi động và tránh lãng phí bộ nhớ.

### 2. Cải thiện Cloudinary upload
- Bổ sung hàm `preprocess_image_for_upload` trong `app/utils/cloudinary.py` để resize/nén ảnh trước khi upload (giới hạn cạnh dài, nén JPEG chất lượng 85).
- Hàm upload lên Cloudinary luôn xử lý ảnh trước khi upload, giúp giảm dung lượng lưu trữ và tăng tốc độ upload.
- Đảm bảo upload_image_to_cloudinary luôn trả về str (trả về chuỗi rỗng nếu lỗi).

## Phần 3.2: Cải thiện infrastructure

### 1. Triển khai health checks
- Thêm các endpoint `/healthz` và `/readyz` vào FastAPI để kiểm tra tình trạng ứng dụng.
- Thêm Docker HEALTHCHECK sử dụng `/healthz`.

### 2. Cấu hình monitoring
- Thêm hệ thống metrics Prometheus (`prometheus_client`) và endpoint `/metrics`.
- Tích hợp middleware để thu thập metrics request count, latency.
- Thêm metric `face_detection_accuracy` để theo dõi độ chính xác phát hiện khuôn mặt.
- Hướng dẫn tích hợp Prometheus/Grafana (tham khảo endpoint `/metrics`).