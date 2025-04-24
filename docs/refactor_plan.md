# Kế hoạch Refactoring

### Giai đoạn 1: Cải thiện cấu trúc code và best practices

#### 1.1. Chuẩn hóa Error Handling và Logging
**Tạo module xử lý lỗi:**
- Tạo file app/core/exceptions.py để định nghĩa các custom exceptions
- Tạo middleware để xử lý lỗi toàn cục trong app/core/middlewares.py
- Tạo hệ thống logging chuẩn trong app/core/logging.py

**Cải thiện cấu trúc requirements.txt:**
- Sửa lỗi encoding
- Tổ chức thành các nhóm dependencies

**Tạo utils cho validation:**
- Tạo các validators chung trong app/core/validators.py

#### 1.2. Cải thiện Dependency Injection
**Tái cấu trúc database access:**
- Tạo abstract class Repository trong app/infrastructure/database/repository.py
- Tạo các repository cụ thể như DetectionRepository, UserRepository

**Tạo module service providers:**
- Tạo các factory functions cho services
- Cấu trúc lại dependency injection trong API routes

#### 1.3. Tái cấu trúc thư mục
**Di chuyển các modules phù hợp:**
- Di chuyển các model domain vào app/domain/models
- Tách business logic ra khỏi API handlers

### Giai đoạn 2: Nâng cao xử lý ảnh và phát hiện khuôn mặt

#### 2.1. Tích hợp phát hiện khuôn mặt
**Triển khai hệ thống phát hiện khuôn mặt:**
- Tạo file app/services/face_detection.py
- Tích hợp YOLO (YOLOv8 face) hoặc OpenCV (haar cascades/DNN) cho phát hiện khuôn mặt
- Cấu hình thông số cho độ chính xác phát hiện (confidence threshold)

**Thiết kế pipeline xử lý ảnh:**
- Thêm chức năng crop khuôn mặt từ ảnh đầu vào
- Tiền xử lý ảnh khuôn mặt: điều chỉnh kích thước, chuẩn hóa
- Đảm bảo khả năng xử lý nhiều khuôn mặt trên một ảnh

#### 2.2. Cập nhật models và API endpoints
**Cập nhật model dữ liệu:**
- Tạo model FaceDetection trong app/models/detection.py
- Thêm các trường bounding box (x, y, width, height)
- Cập nhật DetectionResponse để hỗ trợ nhiều khuôn mặt

**Cập nhật API endpoints:**
- Điều chỉnh /api/detect để trả về kết quả cho nhiều khuôn mặt
- Thêm tham số query option cho phép người dùng chọn phương pháp phát hiện
- Đảm bảo tương thích ngược với các ứng dụng hiện có

#### 2.3. Tăng cường bảo mật
**Triển khai rate limiting:**
- Thêm rate limiter middleware
- Hạn chế số lượng requests từ một IP

**Cải thiện token security:**
- Cập nhật JWT handling
- Thêm token refresh mechanism

#### 2.4. Nâng cao xử lý đồng thời
**Sử dụng background tasks:**
- Triển khai FastAPI background tasks cho xử lý ảnh nặng
- Tạo worker services cho việc phát hiện và phân tích nhiều khuôn mặt
- Triển khai hệ thống notification để thông báo khi xử lý hoàn tất

### Giai đoạn 3: Performance và Infrastructure

#### 3.1. Cải thiện hiệu suất
**Tối ưu model loading:**
- Triển khai model caching cho cả face detection và emotion recognition
- Tách model loading thành service riêng
- Sử dụng lazy loading để giảm thời gian khởi động

**Cải thiện Cloudinary upload:**
- Tối ưu hóa upload process
- Bổ sung xử lý ảnh trước khi upload
- Thêm tùy chọn lưu riêng từng khuôn mặt được phát hiện

#### 3.2. Cải thiện infrastructure
**Triển khai health checks:**
- Tạo API endpoints cho health checks 
- Kết nối health checks với Docker

**Cấu hình monitoring:**
- Thêm metrics collection
- Tích hợp với Prometheus/Grafana
- Thêm theo dõi độ chính xác của phát hiện khuôn mặt