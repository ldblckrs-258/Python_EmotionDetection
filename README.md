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

## API Endpoints

### Authentication

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get authentication token
- `GET /auth/profile` - Get user profile information
- `GET /auth/usage` - Get user usage statistics

### Emotion Detection

- `POST /api/detect` - Upload an image and get emotion detection results
- `GET /api/history` - Get user's detection history
- `GET /api/history/{id}` - Get details of a specific detection
- `DELETE /api/history/{id}` - Delete a specific detection record

# Model Information
The model used for emotion detection is `dima806/facial_emotions_image_detection` from Hugging Face. It is a pre-trained model that can classify emotions from facial images.

## Classification report
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

## Label Mapping
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

## More
- Returns facial emotion with about 91% accuracy based on facial human image.
- The model is trained on the FER2013 dataset, which contains a large number of facial images labeled with different emotions. The model uses a Vision Transformer (ViT) architecture for image classification.
- See https://www.kaggle.com/code/dima806/facial-emotions-image-detection-vit for more details. 