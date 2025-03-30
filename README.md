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
uvicorn app.main:app --reload
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
