from fastapi import Request, status
from fastapi.responses import JSONResponse
import traceback
from typing import Callable, Dict, Any, Optional

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
