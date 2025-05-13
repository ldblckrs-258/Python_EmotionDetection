import time
from typing import List, Optional
from app.infrastructure.database.repository import get_rate_limit_repository
from app.core.logging import logger
from app.domain.models.rate_limit import RateLimit, RateLimitInfo

class MongoRateLimiter:
    """
    Rate limiter implementation using MongoDB for persistent storage.
    This is suitable for multi-instance deployments where in-memory storage won't work.
    """
    
    def __init__(self):
        self._repository = None
    
    async def _get_repository(self):
        """Get the rate limit repository lazily."""
        if self._repository is None:
            self._repository = get_rate_limit_repository()
        return self._repository
    
    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Kiểm tra xem key đã vượt quá giới hạn hay chưa và cập nhật timestamps.
        
        Args:
            key: Unique identifier (user_id, guest_id, or IP)
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            bool: True if rate limit is exceeded, False otherwise
        """
        repository = await self._get_repository()
        now = time.time()
        window_start = now - window_seconds
        
        # Tìm document cho key hiện tại hoặc tạo mới nếu chưa có
        rate_limit_doc = await repository.get_by_key(key)
        
        if not rate_limit_doc:
            # Tạo mới record nếu chưa có
            rate_limit = RateLimit(
                key=key,
                timestamps=[now],
                last_updated=now
            )
            await repository.create(rate_limit.model_dump())
            return False  # Chưa vượt giới hạn
        
        # Lấy timestamps và lọc những timestamp còn trong window
        timestamps: List[float] = rate_limit_doc.get("timestamps", [])
        valid_timestamps = [ts for ts in timestamps if ts > window_start]
        
        # Kiểm tra rate limit
        is_rate_limited = len(valid_timestamps) >= max_requests
        
        if not is_rate_limited:
            # Nếu chưa vượt giới hạn, thêm timestamp mới
            valid_timestamps.append(now)
        
        # Cập nhật document trong database
        rate_limit = RateLimit(
            key=key,
            timestamps=valid_timestamps,
            last_updated=now
        )
        await repository.update(key, rate_limit.model_dump())
        
        if is_rate_limited:
            logger.warning(f"Rate limit exceeded for {key}: {max_requests} requests per {window_seconds} seconds")
            
        return is_rate_limited
    
    async def get_remaining_requests(self, key: str, max_requests: int, window_seconds: int) -> RateLimitInfo:
        """
        Lấy số request còn lại và thời gian reset cho client.
        
        Returns:
            RateLimitInfo: Thông tin về rate limit hiện tại
        """
        repository = await self._get_repository()
        now = time.time()
        window_start = now - window_seconds
        
        rate_limit_doc = await repository.get_by_key(key)
        
        if not rate_limit_doc:
            return RateLimitInfo(
                remaining=max_requests,
                reset=window_seconds,
                total=max_requests
            )
        
        timestamps: List[float] = rate_limit_doc.get("timestamps", [])
        valid_timestamps = [ts for ts in timestamps if ts > window_start]
        
        # Tính toán số request còn lại
        remaining = max(0, max_requests - len(valid_timestamps))
        
        # Tính toán thời gian reset
        if valid_timestamps:
            oldest_timestamp = min(valid_timestamps)
            reset_time = oldest_timestamp + window_seconds - now
        else:
            reset_time = 0
            
        return RateLimitInfo(
            remaining=remaining,
            reset=int(reset_time),
            total=max_requests
        )
    
    async def clean_expired_records(self, older_than_seconds: int = 86400):
        """
        Xóa các record cũ để tránh database phình to.
        Thường gọi định kỳ bởi một background task.
        """
        repository = await self._get_repository()
        cutoff_time = time.time() - older_than_seconds
        
        deleted_count = await repository.delete_expired(cutoff_time)
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired rate limit records")

# Singleton instance
_rate_limiter: Optional[MongoRateLimiter] = None

def get_rate_limiter() -> MongoRateLimiter:
    """Get singleton instance of MongoRateLimiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = MongoRateLimiter()
    return _rate_limiter 