# API Documentation for Emotion Detection Service

## Tổng quan

API Emotion Detection cung cấp các endpoint để:

- Xác thực người dùng thông qua Firebase Authentication
- Phát hiện cảm xúc từ hình ảnh khuôn mặt
- Quản lý lịch sử phát hiện cảm xúc

Base URL: `http://vm.ldblckrs.id.vn:2508` (Backend server deployed on Azure VM)

## Xác thực (Authentication)

API hỗ trợ 2 phương thức xác thực:

1. **Xác thực qua Firebase Client SDK**: Client sử dụng Firebase SDK để xác thực, sau đó gửi ID token đến backend
2. **Sử dụng dưới dạng khách (Guest)**: Hệ thống sẽ tự động tạo và sử dụng cookie để theo dõi số lần sử dụng của người dùng khách, giới hạn 3 lần sử dụng tính năng nhận diện cảm xúc

### Endpoint xác thực

#### 1. Xác thực Firebase ID Token

**Request:**

```http
POST /auth/verify-token
Content-Type: application/json

{
  "id_token": "firebase_id_token"
}
```

**Response:**

```json
{
  "message": "Token verified",
  "user": {
    "user_id": "firebase_user_id",
    "email": "user@example.com",
    "display_name": "John Doe",
    "photo_url": "https://example.com/photo.jpg",
    "is_guest": false,
    "is_email_verified": true,
    "providers": ["password", "google.com"],
    "usage_count": 5,
    "last_used": "2023-06-01T10:00:00",
    "created_at": "2023-01-01T09:00:00"
  },
  "access_token": "jwt_access_token",
  "token_type": "bearer"
}
```

**Lỗi có thể gặp:**

- `401 Unauthorized`: Token không hợp lệ

#### 2. Sử dụng chế độ khách (Guest)

Đối với chế độ khách, không cần gọi endpoint cụ thể. Hệ thống sẽ tự động tạo và quản lý cookie khi người dùng truy cập các API mà không có token xác thực. Guest users được giới hạn 3 lần sử dụng tính năng nhận diện cảm xúc.

**Lưu ý:** API sử dụng cookie HTTP-only có tên `guest_usage_info` để theo dõi thông tin người dùng khách, bao gồm ID và số lần sử dụng. Cookie này có thời hạn 30 ngày.

#### 3. Lấy thông tin profile

**Request:**

```http
GET /auth/profile
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "user_id": "firebase_user_id",
  "email": "user@example.com",
  "display_name": "John Doe",
  "photo_url": "https://example.com/photo.jpg",
  "is_guest": false,
  "is_email_verified": true,
  "providers": ["password", "google.com"],
  "usage_count": 5,
  "last_used": "2023-06-01T10:00:00",
  "created_at": "2023-01-01T09:00:00"
}
```

#### 4. Lấy thông tin sử dụng

**Request:**

```http
GET /auth/usage
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "user_id": "firebase_user_id",
  "is_guest": false,
  "usage_count": 5,
  "max_usage": null
}
```

Đối với guest user, `max_usage` sẽ là 3.

## API Phát hiện cảm xúc (Emotion Detection)

### Endpoints

#### 1. Phát hiện cảm xúc từ hình ảnh

**Request:**

```http
POST /api/detect
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: [binary image data]
```

**Response:**

```json
{
  "detection_id": "unique_detection_id",
  "user_id": "user_id",
  "timestamp": "2023-06-01T10:05:00",
  "image_url": "https://cloudinary.com/path/to/image.jpg",
  "detection_results": {
    "emotions": [
      {
        "emotion": "happy",
        "score": 0.92,
        "percentage": 92.0
      },
      {
        "emotion": "sad",
        "score": 0.05,
        "percentage": 5.0
      },
      {
        "emotion": "angry",
        "score": 0.03,
        "percentage": 3.0
      }
    ],
    "face_detected": true,
    "processing_time": 0.235
  }
}
```

**Lỗi có thể gặp:**

- `400 Bad Request`: Không upload file hoặc file không phải là hình ảnh
- `400 Bad Request`: Kích thước file quá lớn (giới hạn 5MB)
- `400 Bad Request`: Định dạng file không được hỗ trợ
- `403 Forbidden`: Guest user đã vượt quá giới hạn sử dụng (3 lần)
- `500 Internal Server Error`: Lỗi xử lý hình ảnh hoặc phát hiện cảm xúc

#### 2. Lấy lịch sử phát hiện cảm xúc

**Request:**

```http
GET /api/history?skip=0&limit=10
Authorization: Bearer {access_token}
```

Query parameters:
- `skip`: Số bản ghi bỏ qua (dùng cho phân trang, mặc định là 0)
- `limit`: Số bản ghi tối đa trả về (mặc định là 10)

**Response:**

```json
[
  {
    "detection_id": "unique_detection_id_1",
    "user_id": "user_id",
    "timestamp": "2023-06-01T10:05:00",
    "image_url": "https://cloudinary.com/path/to/image1.jpg",
    "detection_results": {
      "emotions": [...],
      "face_detected": true,
      "processing_time": 0.235
    }
  },
  {
    "detection_id": "unique_detection_id_2",
    "user_id": "user_id",
    "timestamp": "2023-06-01T09:30:00",
    "image_url": "https://cloudinary.com/path/to/image2.jpg",
    "detection_results": {
      "emotions": [...],
      "face_detected": true,
      "processing_time": 0.212
    }
  }
]
```

#### 3. Lấy chi tiết một lần phát hiện cảm xúc

**Request:**

```http
GET /api/history/{detection_id}
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "detection_id": "unique_detection_id",
  "user_id": "user_id",
  "timestamp": "2023-06-01T10:05:00",
  "image_url": "https://cloudinary.com/path/to/image.jpg",
  "detection_results": {
    "emotions": [
      {
        "emotion": "happy",
        "score": 0.92,
        "percentage": 92.0
      },
      {
        "emotion": "sad",
        "score": 0.05,
        "percentage": 5.0
      },
      {
        "emotion": "angry",
        "score": 0.03,
        "percentage": 3.0
      }
    ],
    "face_detected": true,
    "processing_time": 0.235
  }
}
```

**Lỗi có thể gặp:**
- `404 Not Found`: Detection ID không tồn tại
- `403 Forbidden`: Detection không thuộc về người dùng hiện tại

#### 4. Xóa một lần phát hiện cảm xúc

**Request:**

```http
DELETE /api/history/{detection_id}
Authorization: Bearer {access_token}
```

**Response:**

```
Status: 204 No Content
```

**Lỗi có thể gặp:**
- `404 Not Found`: Detection ID không tồn tại
- `403 Forbidden`: Detection không thuộc về người dùng hiện tại
- `500 Internal Server Error`: Lỗi khi xóa detection

## Hướng dẫn tích hợp Firebase Authentication (Client-side) cho Django

### 1. Cài đặt các gói cần thiết

Cài đặt các gói Python cần thiết cho dự án Django của bạn:

```bash
pip install firebase-admin
pip install django-cors-headers
pip install requests
```

Thêm các ứng dụng vào `INSTALLED_APPS` trong file `settings.py`:

```python
INSTALLED_APPS = [
    # ...các ứng dụng mặc định của Django
    'corsheaders',
    'your_app_name',  # Ứng dụng của bạn
]

# Thêm CORS middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ...các middleware khác
]

# Cấu hình CORS
CORS_ALLOW_ALL_ORIGINS = True  # Trong môi trường production, nên chỉ định cụ thể các domain được phép
```

### 2. Khởi tạo Firebase Admin SDK trong Django

Tạo file `firebase.py` trong ứng dụng của bạn:

```python
import firebase_admin
from firebase_admin import credentials, auth
import os

# Đường dẫn đến file service account key của Firebase
FIREBASE_SERVICE_ACCOUNT_KEY = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', 'path/to/firebase-service-account.json')

# Khởi tạo Firebase Admin SDK nếu chưa được khởi tạo
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY)
    firebase_admin.initialize_app(cred)

def verify_firebase_token(id_token):
    """
    Xác thực Firebase ID token và trả về thông tin người dùng
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Lỗi xác thực Firebase token: {e}")
        return None
```

### 3. Tạo middleware xác thực token

Tạo file `middleware.py` trong ứng dụng của bạn:

```python
from django.http import JsonResponse
from .firebase import verify_firebase_token
import json

class FirebaseAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Bỏ qua xác thực cho các endpoint không yêu cầu xác thực
        excluded_paths = ['/api/docs', '/api/schema', '/admin', '/auth/guest-token']
        if any(request.path.startswith(path) for path in excluded_paths):
            return self.get_response(request)

        # Lấy token từ header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Không có token xác thực'}, status=401)

        token = auth_header.split(' ')[1]
        
        # Xác thực token
        user_data = verify_firebase_token(token)
        if not user_data:
            return JsonResponse({'error': 'Token không hợp lệ'}, status=401)
        
        # Lưu thông tin người dùng vào request để sử dụng trong views
        request.firebase_user = user_data
        
        return self.get_response(request)
```

Thêm middleware vào `settings.py`:

```python
MIDDLEWARE = [
    # ...các middleware khác
    'your_app_name.middleware.FirebaseAuthMiddleware',
]
```

### 4. Tạo views cho xác thực và xử lý API

Tạo file `views.py` trong ứng dụng của bạn:

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from firebase_admin import auth
from .firebase import verify_firebase_token
import requests

@csrf_exempt
@require_http_methods(["POST"])
def verify_token(request):
    """
    Xác thực Firebase ID token và trả về access token cho API
    """
    try:
        data = json.loads(request.body)
        id_token = data.get('id_token')
        
        if not id_token:
            return JsonResponse({'error': 'Thiếu ID token'}, status=400)
        
        # Xác thực token với Firebase
        decoded_token = verify_firebase_token(id_token)
        
        if not decoded_token:
            return JsonResponse({'error': 'Token không hợp lệ'}, status=401)
        
        # Lấy thông tin người dùng từ Firebase
        user = auth.get_user(decoded_token['uid'])
        
        # Tạo access token cho API của bạn (ví dụ sử dụng JWT)
        # Trong ví dụ này, chúng ta sẽ giả vờ tạo token bằng cách gọi đến API Emotion Detection
        response = requests.post(
            "http://localhost:2508/auth/verify-token",
            json={"id_token": id_token}
        )
        
        if response.status_code != 200:
            return JsonResponse({'error': 'Lỗi xác thực với API'}, status=500)
        
        return JsonResponse(response.json())
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def guest_token(request):
    """
    Lấy guest token từ API Emotion Detection
    """
    try:
        response = requests.get("http://localhost:2508/auth/guest-token")
        
        if response.status_code != 200:
            return JsonResponse({'error': 'Lỗi lấy guest token'}, status=500)
        
        return JsonResponse(response.json())
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def profile(request):
    """
    Lấy thông tin profile của người dùng đã xác thực
    """
    if not hasattr(request, 'firebase_user'):
        return JsonResponse({'error': 'Không có thông tin người dùng'}, status=401)
    
    user_id = request.firebase_user.get('uid')
    
    try:
        # Gọi API Emotion Detection để lấy thông tin profile
        auth_header = request.headers.get('Authorization')
        response = requests.get(
            "http://localhost:2508/auth/profile",
            headers={"Authorization": auth_header}
        )
        
        if response.status_code != 200:
            return JsonResponse({'error': 'Lỗi lấy thông tin profile'}, status=500)
        
        return JsonResponse(response.json())
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def detect_emotion(request):
    """
    Gửi ảnh để phát hiện cảm xúc
    """
    if not hasattr(request, 'firebase_user'):
        return JsonResponse({'error': 'Không có thông tin người dùng'}, status=401)
    
    try:
        # Lấy file ảnh từ request
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'Không có file ảnh'}, status=400)
        
        image_file = request.FILES['file']
        
        # Gửi file đến API Emotion Detection
        auth_header = request.headers.get('Authorization')
        
        files = {'file': (image_file.name, image_file.read(), image_file.content_type)}
        response = requests.post(
            "http://localhost:2508/api/detect",
            headers={"Authorization": auth_header},
            files=files
        )
        
        if response.status_code != 200:
            error_data = response.json()
            return JsonResponse({'error': error_data.get('detail', 'Lỗi phát hiện cảm xúc')}, status=response.status_code)
        
        return JsonResponse(response.json())
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

### 5. Cấu hình URL trong `urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('auth/verify-token', views.verify_token, name='verify_token'),
    path('auth/guest-token', views.guest_token, name='guest_token'),
    path('auth/profile', views.profile, name='profile'),
    path('api/detect', views.detect_emotion, name='detect_emotion'),
    # Thêm các URL khác nếu cần
]
```

### 6. Tích hợp Firebase vào template frontend

Thêm Firebase SDK vào template base của Django:

```html
<head>
    <title>{% block title %}Emotion Detection{% endblock %}</title>
    <!-- Firebase SDK -->
    <script src="https://www.gstatic.com/firebasejs/9.6.10/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/9.6.10/firebase-auth-compat.js"></script>
    
    <script>
        // Cấu hình Firebase
        const firebaseConfig = {
            apiKey: "AIzaSyCihN1jBnbMocE3kcW4is_H6_cqpeFzWqA",
            authDomain: "emotiondetection-743bb.firebaseapp.com",
            projectId: "emotiondetection-743bb",
            storageBucket: "emotiondetection-743bb.firebasestorage.app",
            messagingSenderId: "479535349810",
            appId: "1:479535349810:web:01841d594a247d24e83c2b",
            measurementId: "G-3V67P994LC",
        };
        
        // Khởi tạo Firebase
        firebase.initializeApp(firebaseConfig);
        const auth = firebase.auth();
        
        // Xử lý trạng thái đăng nhập
        auth.onAuthStateChanged(async (user) => {
            if (user) {
                // Người dùng đã đăng nhập
                const idToken = await user.getIdToken();
                
                // Gửi token đến API để xác thực
                const response = await fetch("/auth/verify-token", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ id_token: idToken }),
                });
                
                const data = await response.json();
                
                // Lưu token vào localStorage
                localStorage.setItem("api_token", data.access_token);
                
                // Cập nhật UI
                document.getElementById("user-info").innerText = user.displayName || user.email;
                document.getElementById("login-container").style.display = "none";
                document.getElementById("user-container").style.display = "block";
            } else {
                // Người dùng chưa đăng nhập
                localStorage.removeItem("api_token");
                document.getElementById("login-container").style.display = "block";
                document.getElementById("user-container").style.display = "none";
            }
        });
        
        // Hàm đăng nhập
        async function dangNhap() {
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            
            try {
                await auth.signInWithEmailAndPassword(email, password);
            } catch (error) {
                alert("Lỗi đăng nhập: " + error.message);
            }
        }
        
        // Hàm đăng nhập bằng Google
        async function dangNhapGoogle() {
            try {
                const provider = new firebase.auth.GoogleAuthProvider();
                await auth.signInWithPopup(provider);
            } catch (error) {
                alert("Lỗi đăng nhập Google: " + error.message);
            }
        }
        
        // Hàm đăng xuất
        async function dangXuat() {
            try {
                await auth.signOut();
                alert("Đã đăng xuất thành công");
            } catch (error) {
                alert("Lỗi đăng xuất: " + error.message);
            }
        }
        
        // Hàm chế độ khách
        async function dungCheDoKhach() {
            try {
                const response = await fetch("/auth/guest-token");
                const data = await response.json();
                
                localStorage.setItem("guest_token", data.access_token);
                alert("Đã kích hoạt chế độ khách");
                
                // Chuyển đến trang chính
                window.location.href = "/";
            } catch (error) {
                alert("Lỗi chế độ khách: " + error.message);
            }
        }
    </script>
</head>
```
