from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class AppBaseException(Exception):
    """
    Base exception class for all custom application exceptions.
    """
    def __init__(
        self, 
        message: str = "An unexpected error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseException(AppBaseException):
    """
    Exception raised for database-related errors.
    """
    def __init__(
        self, 
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class AuthenticationException(AppBaseException):
    """
    Exception raised for authentication errors.
    """
    def __init__(
        self, 
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationException(AppBaseException):
    """
    Exception raised for authorization errors.
    """
    def __init__(
        self, 
        message: str = "You don't have permission to access this resource",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ResourceNotFoundException(AppBaseException):
    """
    Exception raised when a requested resource is not found.
    """
    def __init__(
        self, 
        resource_type: str = "Resource",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with ID {resource_id} not found"
            
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class ValidationException(AppBaseException):
    """
    Exception raised for validation errors.
    """
    def __init__(
        self, 
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class FileException(AppBaseException):
    """
    Exception raised for file handling errors.
    """
    def __init__(
        self, 
        message: str = "File operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class ImageProcessingException(AppBaseException):
    """
    Exception raised for image processing errors.
    """
    def __init__(
        self, 
        message: str = "Image processing failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class ExternalServiceException(AppBaseException):
    """
    Exception raised for errors in external service calls (like Cloudinary, Firebase, etc).
    """
    def __init__(
        self, 
        service_name: str,
        message: str = "External service request failed",
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        details["service"] = service_name
        
        super().__init__(
            message=f"{message} ({service_name})",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class RateLimitException(AppBaseException):
    """
    Exception raised when a user exceeds rate limits.
    """
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
            
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )
