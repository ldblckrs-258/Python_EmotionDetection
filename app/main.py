from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import settings
from app.api.routes import router as api_router
from app.auth.router import router as auth_router

# Initialize the FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="API for detecting emotions from facial images",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(api_router, prefix=settings.API_PREFIX, tags=["Emotion Detection"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Face Emotion Detection API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
