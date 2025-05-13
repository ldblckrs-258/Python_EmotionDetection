from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class RateLimit(BaseModel):
    """
    Model đại diện cho giới hạn request của một người dùng (hoặc IP).
    """
    key: str  # User ID, guest ID, or IP address
    timestamps: List[float]  # List of Unix timestamps of recent requests
    last_updated: float  # Last time this record was updated
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "guest_123456",
                "timestamps": [1590000000.0, 1590000060.0, 1590000120.0],
                "last_updated": 1590000120.0
            }
        }
    )

class RateLimitInfo(BaseModel):
    """
    Model chứa thông tin về giới hạn request hiện tại cho client.
    """
    remaining: int  # Số request còn lại
    reset: int  # Thời gian (seconds) khi reset rate limit
    total: int  # Tổng số request được phép trong window
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "remaining": 3,
                "reset": 1800,
                "total": 5
            }
        }
    ) 