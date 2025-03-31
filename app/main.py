from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import router as api_router
from app.auth.router import router as auth_router
from app.services.database import connect_to_mongodb, close_mongodb_connection

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to MongoDB
    logging.info("Starting up MongoDB connection")
    await connect_to_mongodb()
    yield
    # Shutdown: close MongoDB connection
    logging.info("Shutting down MongoDB connection")
    await close_mongodb_connection()

# Custom OpenAPI schema to hide specific endpoints in Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version="0.1.0",
        description="API for detecting emotions from facial images",
        routes=app.routes,
    )
    
    # Get all paths in the OpenAPI schema
    paths = openapi_schema["paths"]
    
    # Hide login and register endpoints from Swagger UI
    paths_to_hide = ["/auth/login", "/auth/register"]
    
    for path in paths_to_hide:
        if path in paths:
            # Add x-hidden flag to hide the endpoint
            for method in paths[path]:
                if "x-hidden" not in paths[path][method]:
                    paths[path][method]["x-hidden"] = True
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Initialize the FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    description="API for detecting emotions from facial images",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.openapi = custom_openapi

# Add CORS middleware
if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
    # In production, use specific origins from settings
    origins = settings.CORS_ORIGINS.split(',')
    logging.info(f"CORS enabled for specific origins: {origins}")
else:
    # In development, allow all origins
    origins = ["*"]
    logging.info("CORS enabled for all origins (development mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    scheme = "https" if getattr(settings, "HTTPS_ENABLED", False) else "http"
    return {
        "message": "Welcome to the Face Emotion Detection API",
        "docs": f"{scheme}://{settings.HOST}:{settings.PORT}/docs",
        "redoc": f"{scheme}://{settings.HOST}:{settings.PORT}/redoc"
    }

if __name__ == "__main__":
    # Check if HTTPS is enabled
    ssl_config = {}
    if getattr(settings, "HTTPS_ENABLED", False):
        ssl_keyfile = getattr(settings, "SSL_KEYFILE", None)
        ssl_certfile = getattr(settings, "SSL_CERTFILE", None)
        
        if ssl_keyfile and ssl_certfile:
            ssl_config.update({
                "ssl_keyfile": ssl_keyfile,
                "ssl_certfile": ssl_certfile
            })
            logging.info(f"HTTPS enabled with cert: {ssl_certfile} and key: {ssl_keyfile}")
        else:
            logging.warning("HTTPS_ENABLED is True but SSL_KEYFILE or SSL_CERTFILE not provided")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        **ssl_config
    )
