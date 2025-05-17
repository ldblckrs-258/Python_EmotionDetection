from fastapi import Request, status
from fastapi.responses import JSONResponse
import traceback
from typing import Dict, Any
import time
from app.core.exceptions import RateLimitException
from app.core.config import settings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.rate_limit import get_rate_limiter

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
    Sử dụng MongoDB để lưu trữ thông tin rate limit, đảm bảo giới hạn được duy trì khi restart service.
    Chỉ áp dụng cho guest user (không có Authorization header), người dùng đã đăng nhập không bị giới hạn.
    """
    def __init__(self, app: ASGIApp, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        # Chỉ áp dụng cho endpoint /api/detect 
        if request.url.path == f"{settings.API_PREFIX}/detect":
            # Kiểm tra header Authorization, nếu có thì là authenticated user, không rate limit
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Người dùng đã đăng nhập, không rate limit
                return await call_next(request)
            
            # Lấy guest_id từ cookie
            guest_cookie = request.cookies.get("guest_usage_info")
            guest_id = None
            if guest_cookie:
                try:
                    import json
                    guest_info = json.loads(guest_cookie)
                    guest_id = guest_info.get("guest_id")
                except Exception:
                    pass
            else:
                # return forbidden
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "success": False,
                        "message": "Forbidden"
                    }
                )
            
            key = guest_id
            
            # Kiểm tra rate limit sử dụng MongoRateLimiter
            rate_limiter = get_rate_limiter()
            is_rate_limited = await rate_limiter.check_rate_limit(
                key=key,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds
            )
            
            # Nếu vượt giới hạn, trả về response 429
            if is_rate_limited:
                rate_info = await rate_limiter.get_remaining_requests(
                    key=key,
                    max_requests=self.max_requests,
                    window_seconds=self.window_seconds
                )
                
                message = f"Rate limit exceeded: {self.max_requests} requests per day."
                logger.warning(f"Rate limit exceeded for {key}: {message}")
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "message": message,
                        "details": {
                            "retry_after": rate_info.reset,
                            "limit": rate_info.total,
                            "remaining": rate_info.remaining
                        }
                    },
                    headers={"Retry-After": str(rate_info.reset)}
                )
                
        # Tiếp tục xử lý request nếu không bị rate limit
        response = await call_next(request)
        return response
