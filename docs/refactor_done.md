# Các thay đổi đã làm:

## Pharse 1.1: Tái cấu trúc xử lý lỗi và ghi log

1. **Tạo tệp ngoại lệ tùy chỉnh (`exceptions.py`):**

- Triển khai hệ thống phân cấp ngoại lệ bắt đầu với `AppBaseException` làm lớp cơ sở  
- Thêm các ngoại lệ chuyên biệt cho từng loại lỗi (cơ sở dữ liệu, xác thực, phân quyền, kiểm tra dữ liệu, v.v.)  
- Mỗi ngoại lệ bao gồm mã trạng thái, thông báo, và chi tiết tùy chọn  

2. **Tạo middleware xử lý lỗi (`middlewares.py`):**

- Triển khai middleware tương thích với ASGI để bắt tất cả ngoại lệ  
- Tạo phản hồi lỗi chuẩn hóa với định dạng JSON nhất quán  
- Sửa lỗi triển khai để đảm bảo tương thích ASGI đúng cách  

3. **Tạo hệ thống ghi log chuẩn hóa (`logging.py`):**

- Triển khai hệ thống ghi log linh hoạt với tùy chọn định dạng JSON và văn bản  
- Thêm ghi log theo ngữ cảnh với lớp `ContextLogger`  
- Cấu hình ghi log ra cả console và file  

4. **Cập nhật ứng dụng chính (`main.py`):**

- Thay thế hệ thống ghi log mặc định bằng logger tùy chỉnh  
- Thêm middleware xử lý lỗi để xử lý ngoại lệ toàn cục  
- Thêm trình xử lý ngoại lệ riêng cho các ngoại lệ tùy chỉnh  

5. **Cập nhật cấu hình (`config.py`):**

- Thêm các tùy chọn cấu hình liên quan đến ghi log (`LOG_LEVEL`, `LOG_TO_FILE`, `LOG_FORMAT`)  
- Các thiết lập này có thể được cấu hình thông qua biến môi trường  

6. **Cải thiện cấu trúc (`requirements.txt`):**
- Đã tổ chức lại requirements.txt thành các nhóm dependencies rõ ràng (core web, database, authentication, cloud, ML, validation, utilities, jupyter, html/xml, misc).
- Đảm bảo file sử dụng encoding chuẩn UTF-8.

7. **Tạo utils cho validation:**
- Đã tạo file (`app/core/validators.py`) với các hàm kiểm tra định dạng email, kiểm tra file ảnh, kiểm tra số dương, kiểm tra chuỗi không rỗng.

8. Áp dụng validator cho upload ảnh:
- Đã tích hợp các hàm is_valid_image_filename và is_non_empty_string từ app/core/validators.py vào validate_image (app/services/emotion_detection.py) để kiểm tra tên file ảnh hợp lệ và không rỗng trước khi xử lý.

## Pharse 1.2: Tái cấu trúc database access

1. **Tái cấu trúc database access (`app/infrastructure/database/`):**
  - Tạo abstract class Repository và các repository cụ thể (DetectionRepository, UserRepository) để chuẩn hóa thao tác MongoDB
  - Triển khai providers cho repository để hỗ trợ dependency injection
  - Refactor storage service để sử dụng DetectionRepository
  - Cập nhật database service trả về AsyncIOMotorCollection

2. **Triển khai Repository Pattern:**
  - Triển khai interface Repository trong `repository.py`
  - Thêm các phương thức CRUD cơ bản (create, read, update, delete)
  - Tạo các repository chuyên biệt cho Detection và User
  - Thêm validation và error handling

3. **Cập nhật Database Providers (`providers.py`):**
  - Tạo các factory function cho repository injection
  - Thêm lifecycle hooks cho repository instances
  - Hỗ trợ cấu hình động qua environment variables
  - Tích hợp logging cho database operations

4. **Refactor Storage Service (`storage.py`):**
  - Chuyển đổi sang sử dụng DetectionRepository
  - Cập nhật error handling phù hợp với repository pattern
  - Thêm transaction support cho các operation phức tạp
  - Tối ưu hóa performance các query phổ biến

5. **Tạo module service providers (`app/services/providers.py`):**
   - Đã tạo các factory function cho các service chính: emotion detection, detection history, single detection retrieval, và deletion.
   - Module này giúp inject các service vào API routes dễ dàng, tăng tính module hóa và khả năng test.

6. **Refactor dependency injection trong API routes (`app/api/routes.py`):**
   - Thay thế các import trực tiếp và gọi hàm service bằng cách sử dụng FastAPI `Depends` với các provider từ module mới.
   - Các endpoint `/detect`, `/history`, `/history/{detection_id}`, và `DELETE /history/{detection_id}` đều sử dụng DI chuẩn.

## Pharse 1.3: Di chuyển models domain

1. **Tạo thư mục domain/models:**
   - Đã tạo các thư mục `app/domain/` và `app/domain/models/` để chuẩn hóa vị trí các domain models.

2. **Di chuyển models:**
   - Đã di chuyển toàn bộ nội dung của `app/models/detection.py` sang `app/domain/models/detection.py`.
   - Đã di chuyển toàn bộ nội dung của `app/models/user.py` sang `app/domain/models/user.py`.
   - Để lại thông báo trong các file cũ nhằm tránh trùng lặp và nhắc nhở vị trí mới.

3. **Cập nhật import:**
   - Đã cập nhật toàn bộ các import liên quan đến models (DetectionResponse, DetectionResult, EmotionScore, User, FirebaseToken) sang `app.domain.models` trong các file:
     - `app/api/routes.py`
     - `app/services/emotion_detection.py`
     - `app/services/storage.py`
     - `app/auth/router.py`

4. **Kiểm tra lỗi:**
   - Đã phát hiện lỗi liên quan đến thuộc tính `uid` trong file `app/auth/router.py` (do thay đổi import, cần kiểm tra lại logic sử dụng user object ở các vị trí này trong các giai đoạn tiếp theo).
   - ĐÃ FIX: Đã sửa logic lấy `uid` từ object trả về của `get_user_from_firebase` trong endpoint `/verify-token` để tương thích với cả object và dict, đảm bảo không còn lỗi truy cập thuộc tính `uid`.