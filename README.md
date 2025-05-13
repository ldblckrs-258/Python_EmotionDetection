# Face Emotion Detection API

A backend service that detects emotions from facial images and video streams using FastAPI, MongoDB, Cloudinary, and Firebase Authentication with a pre-trained Hugging Face model.

## Features

- **Image Detection**: Analyze emotions from uploaded images with percentage scores
- **Realtime Video Detection**: Process video streams via Socket.IO with efficient face tracking
- **Authentication**: Secure access with Firebase Authentication
- **Storage**: Store images in Cloudinary and detection history in MongoDB Atlas
- **Containerization**: Easy deployment with Docker and Docker Compose

## Tech Stack

- **Backend Framework**: FastAPI
- **Realtime Communication**: Socket.IO
- **Database**: MongoDB Atlas
- **Image Storage**: Cloudinary
- **Authentication**: Firebase Authentication
- **AI Models**:
  - Image analysis: Hugging Face model - dima806/facial_emotions_image_detection
  - Face detection: OpenCV Haar Cascade
- **Containerization**: Docker & Docker Compose

## Detection Pipeline

### Image-Based Emotion Detection

1. **Image Upload & Validation**

   - Validate image format and size (max 5MB)
   - Convert to RGB format

2. **Face Detection**

   - OpenCV's Haar Cascade classifier locates faces
   - Each face is isolated with bounding box coordinates

3. **Face Preprocessing**

   - Detected faces are cropped and resized to 224x224 pixels
   - Pixel values are normalized to range [0,1]

4. **Emotion Analysis**

   - Pre-trained Vision Transformer (ViT) model processes each face
   - Model outputs probability scores for 7 emotions:
     - Happy, Sad, Angry, Disgust, Fear, Surprise, Neutral

5. **Result Processing & Storage**
   - Original image stored in Cloudinary
   - Results saved in MongoDB with user association

### Realtime Video Stream Detection

1. **Socket.IO Connection**

   - Client establishes WebSocket connection
   - Firebase token authentication
   - Session configuration with adjustable parameters

2. **Video Frame Processing**

   - Client streams video frames as base64-encoded images
   - Server processes frames with optimized pipeline
   - Face tracking across frames with stable face IDs

3. **Performance Optimization**

   - Auto-adjusts processing resolution based on performance
   - Configurable frame rate and detection parameters
   - Prioritizes real-time performance when needed

4. **Realtime Results**
   - Emotion detection results streamed back to client
   - Performance metrics including FPS and latency
   - Face tracking information for UI visualization

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (optional)
- MongoDB Atlas account
- Cloudinary account
- Firebase project

### Environment Variables

Create a `.env` file based on the `.env.example` template.

### Local Development

1. Create a virtual environment:

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

### Docker Deployment

Build and start the Docker containers:

```bash
docker-compose up -d
```

## API Documentation

Once running, access the interactive API documentation:

- Swagger UI: `http://localhost:2508/docs`
- ReDoc: `http://localhost:2508/redoc`

## API Endpoints

### Authentication

- `POST /auth/verify-token`: Verify Firebase token
- `GET /auth/profile`: Get user profile
- `GET /auth/usage`: Get usage statistics
- `POST /auth/refresh-token`: Refresh access token

### Image Detection

- `POST /api/detect`: Analyze emotions from an uploaded image
- `POST /api/detect/batch`: Process multiple images (authentication required)
- `GET /api/history`: Get detection history
- `GET /api/history/{id}`: Get specific detection details
- `DELETE /api/history/{id}`: Delete detection record

### Socket.IO Realtime Detection

Connect to WebSocket endpoint at `/emotion-detection` for realtime video processing:

#### Connection Events

- `connect`: Establish connection with authentication token
- `initialize`: Configure the detection session
- `control`: Control detection (start/stop/configure)
- `video_frame`: Send video frame for processing

#### Response Events

- `detection_result`: Emotion detection results
- `status`: Session status updates
- `performance_suggestion`: Optimization recommendations
- `error_message`: Error notifications

## Model Performance

The emotion detection model achieves approximately 91% accuracy on the FER2013 dataset.

### Classification Report

```
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

## More Information

For more technical details about the model, see:

- [Facial Emotions Image Detection with ViT](https://www.kaggle.com/code/dima806/facial-emotions-image-detection-vit)
