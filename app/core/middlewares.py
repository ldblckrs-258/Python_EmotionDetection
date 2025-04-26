from fastapi import Request, status
from fastapi.responses import JSONResponse
import traceback
from typing import Dict, Any
import time
from app.core.exceptions import RateLimitException
from app.core.config import settings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.exceptions import AppBaseException
from app.core.logging import logger


async def exception_handler(request: Request, exception: Exception) -> JSONResponse:
    """
    Global exception handler for all endpoints.
    Logs the exception and returns a standardized JSON response.
    """
    # Default error response
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_content: Dict[str, Any] = {
        "success": False,
        "message": "An unexpected error occurred",
        "details": {}
    }
    
    # Extract request information for logging
    path = request.url.path
    method = request.method
    client_host = request.client.host if request.client else "unknown"
    
    if isinstance(exception, AppBaseException):
        # Handle custom application exceptions
        status_code = exception.status_code
        error_content["message"] = exception.message
        error_content["details"] = exception.details
        
        # Log with appropriate level based on status code
        if status_code >= 500:
            logger.error(
                f"Error processing request {method} {path} from {client_host}: "
                f"{exception.message}",
                extra={
                    "status_code": status_code,
                    "details": exception.details,
                    "request_path": path,
                    "request_method": method,
                    "client_host": client_host
                }
            )
        else:
            logger.warning(
                f"Error processing request {method} {path} from {client_host}: "
                f"{exception.message}",
                extra={
                    "status_code": status_code,
                    "details": exception.details,
                    "request_path": path,
                    "request_method": method,
                    "client_host": client_host
                }
            )
    else:
        # Handle unhandled exceptions
        exception_type = type(exception).__name__
        exception_str = str(exception)
        
        error_content["message"] = f"Unexpected error: {exception_type}"
        error_content["details"]["error"] = exception_str
        
        # Log the unhandled exception with stacktrace
        logger.error(
            f"Unhandled exception processing request {method} {path} from {client_host}: "
            f"{exception_type}: {exception_str}",
            extra={
                "status_code": status_code,
                "exception_type": exception_type,
                "stacktrace": traceback.format_exc(),
                "request_path": path,
                "request_method": method,
                "client_host": client_host
            }
        )
    
    return JSONResponse(
        status_code=status_code,
        content=error_content
    )


class ErrorHandlingMiddleware:
    """
    Middleware for global exception handling across the application.
    This middleware catches any unhandled exceptions and processes them
    using the exception_handler.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # We only handle HTTP connections
            await self.app(scope, receive, send)
            return

        # Create a request object
        request = Request(scope, receive=receive)
        
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # Handle the exception
            response = await exception_handler(request, exc)
            await response(scope, receive, send)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware để giới hạn số lượng request từ một IP (hoặc guest_id) cho các endpoint nhạy cảm.
    Chỉ áp dụng cho guest user (chưa đăng nhập).
    """
    def __init__(self, app: ASGIApp, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.guest_requests = {}  # {guest_id_or_ip: [timestamps]}

    async def dispatch(self, request: Request, call_next):
        # Chỉ áp dụng cho endpoint /api/detect và guest user
        if request.url.path == f"{settings.API_PREFIX}/detect":
            client_ip = request.client.host if request.client else "unknown"
            
            # Bỏ qua rate limit nếu là localhost
            if client_ip in ("127.0.0.1", "::1", "localhost"):
                return await call_next(request)
            
            guest_cookie = request.cookies.get("guest_usage_info")
            guest_id = None
            if guest_cookie:
                try:
                    import json
                    guest_info = json.loads(guest_cookie)
                    guest_id = guest_info.get("guest_id")
                except Exception:
                    pass
            key = guest_id or client_ip
            now = time.time()
            window_start = now - self.window_seconds
            timestamps = self.guest_requests.get(key, [])
            # Lọc các request còn trong window
            timestamps = [ts for ts in timestamps if ts > window_start]
            if len(timestamps) >= self.max_requests:
                raise RateLimitException(
                    message=f"Rate limit exceeded: {self.max_requests} requests per {self.window_seconds} seconds.",
                    retry_after=int(self.window_seconds)
                )
            timestamps.append(now)
            self.guest_requests[key] = timestamps
        response = await call_next(request)
        return response
