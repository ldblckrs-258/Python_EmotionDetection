# Face Emotion Detection API

A backend service that detects emotions from facial images using FastAPI, MongoDB, Cloudinary, and Firebase Authentication with a pre-trained Hugging Face model.

## Features

- Emotion detection from uploaded images with percentage scores
- User authentication with Firebase
- Image storage with Cloudinary
- Detection history stored in MongoDB Atlas
- Docker containerization

## Tech Stack

- **Backend Framework**: FastAPI
- **Programming Language**: Python
- **Database**: MongoDB Atlas
- **Image Storage**: Cloudinary
- **Authentication**: Firebase Authentication
- **AI Model**: Hugging Face model - dima806/facial_emotions_image_detection
- **Containerization**: Docker & Docker Compose

## Workflow Pipeline

### Face Detection and Emotion Recognition Process

1. **Image Upload & Validation**

   - User uploads an image via the API
   - System validates image format and size (max 5MB)
   - Image is converted to RGB format for processing

2. **Face Detection**

   - OpenCV's Haar Cascade classifier detects faces in the image
   - Each detected face is isolated with its bounding box coordinates (x, y, width, height)
   - Face coordinates are saved for frontend visualization

3. **Face Preprocessing**

   - Detected faces are cropped from the original image
   - Each face is resized to 224x224 pixels
   - Pixel values are normalized to the range [0,1]

4. **Emotion Detection**

   - Pre-trained model (`dima806/facial_emotions_image_detection`) processes each face
   - Vision Transformer (ViT) architecture analyzes facial features
   - Model outputs probability scores for 7 emotions:
     - Happy, Sad, Angry, Disgust, Fear, Surprise, Neutral

5. **Result Processing**

   - Emotion probabilities are converted to percentages
   - Results are sorted by confidence score
   - Processing time is calculated

6. **Storage & Response**
   - Original image is stored in Cloudinary
   - Detection results are saved in MongoDB with user association
   - Response includes face locations, emotion scores, and image URL
   - Detection history is accessible through API endpoints

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (optional, for containerized deployment)
- MongoDB Atlas account
- Cloudinary account
- Firebase project

### Environment Variables

Create a `.env` file based on the `.env.example` template and fill in your credentials:

```
# Copy the .env.example file
cp .env.example .env

# Edit the .env file with your actual credentials
```

### Local Development Setup

1. Create a virtual environment and activate it:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
uvicorn app.main:app --reload --port 2508
```

The API will be available at `http://localhost:2508`.

### Docker Setup

1. Build and start the Docker containers:

```bash
docker-compose up -d
```

The API will be available at `http://localhost:2508`.

## API Documentation

Once the application is running, you can access the interactive API documentation:

- Swagger UI: `http://localhost:2508/docs`
- ReDoc: `http://localhost:2508/redoc`

The API supports two authentication modes:

- **Authenticated Users**: Firebase Authentication with JWT tokens
- **Guest Users**: Limited to 5 detection requests per hour, tracked via cookies

## API Endpoints

### Authentication

#### `POST /auth/verify-token`

Verifies a Firebase ID token and returns a JWT access token.

**Request Body:**

```json
{
  "id_token": "firebase_id_token_from_client"
}
```

**Response:**

```json
{
  "message": "Token verified",
  "user": {
    "user_id": "firebase_user_id",
    "email": "user@example.com",
    "display_name": "User Name",
    "is_guest": false,
    "is_email_verified": true,
    "providers": ["password", "google.com"]
  },
  "access_token": "jwt_access_token",
  "token_type": "bearer"
}
```

#### `GET /auth/profile`

Returns the authenticated user's profile information.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "user_id": "firebase_user_id",
  "email": "user@example.com",
  "display_name": "User Name",
  "photo_url": "https://example.com/photo.jpg",
  "is_guest": false,
  "is_email_verified": true,
  "providers": ["password"]
}
```

#### `GET /auth/usage`

Returns the user's usage statistics.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "user_id": "firebase_user_id",
  "is_guest": false,
  "usage_count": 10,
  "max_usage": null
}
```

#### `POST /auth/refresh-token`

Refreshes an expired access token using a refresh token.

**Request Body:**

```json
{
  "refresh_token": "jwt_refresh_token"
}
```

**Response:**

```json
{
  "access_token": "new_jwt_access_token",
  "token_type": "bearer"
}
```

### Emotion Detection

#### `POST /api/detect`

Uploads an image and returns emotion detection results.

**Headers:**

```
Authorization: Bearer {access_token} (optional)
Content-Type: multipart/form-data
```

**Request Body:**

```
file: [binary image data]
```

**Response:**

```json
{
  "detection_id": "123456abcdef",
  "user_id": "user123",
  "timestamp": "2024-01-01T00:00:00",
  "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
  "detection_results": {
    "faces": [
      {
        "box": [10, 20, 100, 100],
        "emotions": [
          { "emotion": "happy", "score": 0.92, "percentage": 92.0 },
          { "emotion": "sad", "score": 0.05, "percentage": 5.0 },
          { "emotion": "neutral", "score": 0.03, "percentage": 3.0 }
        ]
      }
    ],
    "face_detected": true,
    "processing_time": 0.235
  }
}
```

#### `POST /api/detect/batch`

Uploads multiple images and returns streaming results. Only authenticated users can use this endpoint.

**Headers:**

```
Authorization: Bearer {access_token} (required)
Content-Type: multipart/form-data
Accept: text/event-stream
```

**Request Body:**

```
files: [multiple binary image data]
```

**Response:**
Server-Sent Events stream where each event is a detection result.

#### `GET /api/history`

Returns the user's detection history.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Query Parameters:**

- `page` (optional): Page number for pagination, default 1
- `limit` (optional): Results per page, default 10

**Response:**

```json
{
  "items": [
    {
      "detection_id": "123456abcdef",
      "user_id": "user123",
      "timestamp": "2024-01-01T00:00:00",
      "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg"
    }
  ],
  "total": 15,
  "page": 1,
  "pages": 2,
  "limit": 10
}
```

#### `GET /api/history/{id}`

Returns details of a specific detection.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "detection_id": "123456abcdef",
  "user_id": "user123",
  "timestamp": "2024-01-01T00:00:00",
  "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
  "detection_results": {
    "faces": [
      {
        "box": [10, 20, 100, 100],
        "emotions": [
          { "emotion": "happy", "score": 0.92, "percentage": 92.0 },
          { "emotion": "sad", "score": 0.05, "percentage": 5.0 }
        ]
      }
    ],
    "face_detected": true,
    "processing_time": 0.235
  }
}
```

#### `DELETE /api/history/{id}`

Deletes a specific detection record.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "message": "Detection deleted successfully",
  "detection_id": "123456abcdef"
}
```

## Model Information

The model used for emotion detection is `dima806/facial_emotions_image_detection` from Hugging Face. It is a pre-trained model that can classify emotions from facial images.

### Classification report

```python
              precision    recall  f1-score   support

         sad     0.8394    0.8632    0.8511      3596
     disgust     0.9909    1.0000    0.9954      3596
       angry     0.9022    0.9035    0.9028      3595
     neutral     0.8752    0.8626    0.8689      3595
        fear     0.8788    0.8532    0.8658      3596
    surprise     0.9476    0.9449    0.9463      3596
       happy     0.9302    0.9372    0.9336      3596

    accuracy                         0.9092     25170
   macro avg     0.9092    0.9092    0.9091     25170
weighted avg     0.9092    0.9092    0.9091     25170
```

### Label Mapping

```python
{
    0: "sad",
    1: "disgust",
    2: "angry",
    3: "neutral",
    4: "fear",
    5: "surprise",
    6: "happy"
}
```

### More

- Returns facial emotion with about 91% accuracy based on facial human image.
- The model is trained on the FER2013 dataset, which contains a large number of facial images labeled with different emotions. The model uses a Vision Transformer (ViT) architecture for image classification.
- See https://www.kaggle.com/code/dima806/facial-emotions-image-detection-vit for more details.
