# API Documentation for Emotion Detection Service

## Tổng quan

API Emotion Detection cung cấp các endpoint để:

- Xác thực người dùng (đăng ký, đăng nhập, xác thực token)
- Phát hiện cảm xúc từ hình ảnh khuôn mặt
- Quản lý lịch sử phát hiện cảm xúc

Base URL: `http://localhost:8000` (mặc định cho môi trường phát triển)

## Xác thực (Authentication)

API hỗ trợ 3 phương thức xác thực:

1. **Xác thực qua Firebase** (khuyến nghị): Client sử dụng Firebase SDK để xác thực, sau đó gửi ID token đến backend
2. **Xác thực trực tiếp thông qua API**: Sử dụng email/password hoặc Google OAuth
3. **Sử dụng dưới dạng khách (Guest)**: Giới hạn 3 lần sử dụng tính năng nhận diện cảm xúc

### Endpoint xác thực

#### 1. Đăng ký tài khoản

**Request:**

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "display_name": "John Doe"
}
```

**Response:**

```json
{
  "message": "User registered successfully",
  "user_id": "firebase_user_id",
  "custom_token": "firebase_custom_token",
  "access_token": "jwt_access_token",
  "token_type": "bearer"
}
```

**Lỗi có thể gặp:**

- `400 Bad Request`: Email đã tồn tại hoặc định dạng không hợp lệ
- `400 Bad Request`: Mật khẩu phải có ít nhất 6 ký tự

#### 2. Đăng nhập

**Request:**

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "message": "Login successful",
  "user_id": "firebase_user_id",
  "custom_token": "firebase_custom_token",
  "access_token": "jwt_access_token",
  "token_type": "bearer"
}
```

**Lỗi có thể gặp:**

- `401 Unauthorized`: Email hoặc mật khẩu không hợp lệ
- `400 Bad Request`: Định dạng email không hợp lệ

#### 3. Xác thực Firebase ID Token

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

#### 4. Lấy token cho guest (không đăng nhập)

**Request:**

```http
GET /auth/guest-token
```

**Response:**

```json
{
  "access_token": "guest_jwt_token",
  "token_type": "bearer",
  "user_id": "guest_id"
}
```

#### 5. Đăng xuất

**Request:**

```http
POST /auth/logout
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "message": "Logged out successfully"
}
```

#### 6. Lấy thông tin profile

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

#### 7. Lấy thông tin sử dụng

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
- `403 Forbidden`: Guest user đã vượt quá giới hạn sử dụng
- `500 Internal Server Error`: Lỗi xử lý hình ảnh hoặc phát hiện cảm xúc

#### 2. Lấy lịch sử phát hiện cảm xúc

**Request:**

```http
GET /api/history?skip=0&limit=10
Authorization: Bearer {access_token}
```

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

## Hướng dẫn tích hợp Auth

### Phương án 1: Firebase Client SDK (Khuyến nghị)

1. **Khởi tạo Firebase trong frontend**

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyCihN1jBnbMocE3kcW4is_H6_cqpeFzWqA",
  authDomain: "emotiondetection-743bb.firebaseapp.com",
  projectId: "emotiondetection-743bb",
  storageBucket: "emotiondetection-743bb.firebasestorage.app",
  messagingSenderId: "479535349810",
  appId: "1:479535349810:web:01841d594a247d24e83c2b",
  measurementId: "G-3V67P994LC",
}

firebase.initializeApp(firebaseConfig)
```

2. **Đăng ký người dùng mới**

```javascript
const auth = firebase.auth()
const result = await auth.createUserWithEmailAndPassword(email, password)
const user = result.user
await user.updateProfile({ displayName: displayName })
```

3. **Đăng nhập**

```javascript
// Email/Password
await auth.signInWithEmailAndPassword(email, password)

// Google OAuth
const provider = new firebase.auth.GoogleAuthProvider()
await auth.signInWithPopup(provider)
```

4. **Xác thực với API**

```javascript
// Sau khi đăng nhập thành công với Firebase
const idToken = await firebase.auth().currentUser.getIdToken()

// Gửi token đến API để xác thực và nhận API token
const response = await fetch("http://localhost:8000/auth/verify-token", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ id_token: idToken }),
})

const authData = await response.json()
// Lưu authData.access_token để sử dụng cho các API call khác
localStorage.setItem("api_token", authData.access_token)
```

5. **Gọi API với token**

```javascript
// Ví dụ upload ảnh để phát hiện cảm xúc
const formData = new FormData()
formData.append("file", imageFile)

const response = await fetch("http://localhost:8000/api/detect", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${localStorage.getItem("api_token")}`,
  },
  body: formData,
})

const result = await response.json()
console.log("Emotion detection result:", result)
```

### Phương án 2: Guest Mode (Không đăng nhập)

```javascript
// Lấy guest token
const response = await fetch("http://localhost:8000/auth/guest-token")
const data = await response.json()
localStorage.setItem("guest_token", data.access_token)

// Sử dụng guest token để gọi API
const formData = new FormData()
formData.append("file", imageFile)

const detectResponse = await fetch("http://localhost:8000/api/detect", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${localStorage.getItem("guest_token")}`,
  },
  body: formData,
})

// Guest mode giới hạn 3 lần sử dụng
```

## Mô hình dữ liệu

### User

```json
{
  "user_id": "string",         // Firebase UID hoặc guest ID
  "email": "string",           // Email người dùng
  "display_name": "string",    // Tên hiển thị (có thể null)
  "photo_url": "string",       // URL ảnh đại diện (có thể null)
  "is_guest": boolean,         // Có phải là guest không
  "is_email_verified": boolean, // Email đã xác thực chưa
  "providers": ["string"],     // Các provider xác thực (password, google.com, etc.)
  "usage_count": number,       // Số lần sử dụng
  "last_used": "string",       // Thời gian sử dụng gần nhất (ISO datetime)
  "created_at": "string"       // Thời gian tạo tài khoản (ISO datetime)
}
```

### EmotionScore

```json
{
  "emotion": "string",     // Tên cảm xúc (happy, sad, angry, etc.)
  "score": float,          // Điểm từ 0-1
  "percentage": float      // Giá trị phần trăm (0-100)
}
```

### DetectionResult

```json
{
  "emotions": [EmotionScore],  // Danh sách các cảm xúc phát hiện được
  "face_detected": boolean,    // Có phát hiện được khuôn mặt hay không
  "processing_time": float     // Thời gian xử lý (giây)
}
```

### DetectionResponse

```json
{
  "detection_id": "string",          // ID duy nhất cho lần phát hiện
  "user_id": "string",               // ID người dùng
  "timestamp": "string",             // Thời gian phát hiện (ISO datetime)
  "image_url": "string",             // URL hình ảnh đã lưu trên Cloudinary
  "detection_results": DetectionResult  // Kết quả phát hiện cảm xúc
}
```

## Headers yêu cầu

- `Content-Type: application/json` cho các request JSON
- `Content-Type: multipart/form-data` cho upload file
- `Authorization: Bearer {token}` cho các API yêu cầu xác thực

## Giới hạn sử dụng

- Guest users: Giới hạn 3 lần sử dụng API phát hiện cảm xúc
- Authenticated users: Không giới hạn
