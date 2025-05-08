import logging
import sys
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import re

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON objects.
    This makes logs easier to parse and analyze with tools like ELK stack.
    """
    # Danh sách các trường có thể chứa dữ liệu lớn
    LARGE_DATA_FIELDS = ['data', 'image', 'frame', 'base64', 'content']
    # Regex pattern để tìm dữ liệu base64
    BASE64_PATTERN = re.compile(r'[A-Za-z0-9+/]{50,}={0,2}')
    # Giới hạn kích thước cho các giá trị chuỗi
    MAX_STRING_LENGTH = 1000
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": self.sanitize_string(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
          # Include exception info if available
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info)
            }
              # The standard logging module doesn't have an 'extra' attribute on LogRecord
        # Instead, we'll check for our custom attributes that might have been added
        extra_dict = {}
        for key in dir(record):
            if key.startswith('_extra_') and not key.startswith('__'):
                extra_dict[key[7:]] = getattr(record, key)
                
        if extra_dict:
            # Sanitize extra data
            extra_dict = self.sanitize_dict(extra_dict)
            log_entry["extra"] = extra_dict
            
        # Add any additional attributes from the record
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                           "filename", "funcName", "id", "levelname", "levelno", 
                           "lineno", "module", "msecs", "message", "msg", 
                           "name", "pathname", "process", "processName", 
                           "relativeCreated", "stack_info", "thread", "threadName",
                           "extra"]:
                try:
                    # Sanitize the value before including it
                    if isinstance(value, dict):
                        value = self.sanitize_dict(value)
                    elif isinstance(value, str):
                        value = self.sanitize_string(value)
                    json.dumps({key: value})  # Check if serializable
                    log_entry[key] = value
                except (TypeError, OverflowError):
                    log_entry[key] = str(value)
                    
        return json.dumps(log_entry)
        
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a dictionary by removing or truncating large data fields.
        """
        if not isinstance(data, dict):
            return data
            
        result = {}
        for key, value in data.items():
            # Bỏ qua các trường nhạy cảm hoặc dữ liệu lớn
            if any(field in key.lower() for field in self.LARGE_DATA_FIELDS):
                if isinstance(value, str):
                    length = len(value)
                    result[key] = f"[LARGE DATA REMOVED: {length} bytes]"
                else:
                    result[key] = "[LARGE DATA REMOVED]"
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value)
            elif isinstance(value, str):
                result[key] = self.sanitize_string(value)
            else:
                result[key] = value
        return result
        
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize a string by removing large base64 data and truncating if necessary.
        """
        if not isinstance(value, str):
            return value
            
        # Remove base64 data
        sanitized = self.BASE64_PATTERN.sub("[BASE64 DATA REMOVED]", value)
        
        # Truncate if too long
        if len(sanitized) > self.MAX_STRING_LENGTH:
            return sanitized[:self.MAX_STRING_LENGTH] + f"... [TRUNCATED, total length: {len(value)} chars]"
        
        return sanitized


def setup_logging() -> logging.Logger:
    """
    Set up application-wide logging configuration.
    Returns the configured logger instance.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log level from settings
    log_level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Create application logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    app_logger.propagate = False
    
    # Clear any existing handlers
    if app_logger.handlers:
        app_logger.handlers.clear()
    
    # Console handler with plain text formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    app_logger.addHandler(console_handler)
    
    # File handler with JSON formatting for easier parsing
    if getattr(settings, "LOG_TO_FILE", True):
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JsonFormatter())
        app_logger.addHandler(file_handler)
    
    # Setup loggers for specific modules
    setup_module_loggers(log_level)
    
    return app_logger


def setup_module_loggers(default_level: int) -> None:
    """
    Set up loggers for specific modules.
    This allows for more detailed logging in specific areas.
    """
    # Enable debug logging for the socket.io modules if DEBUG_SOCKETIO is enabled
    if getattr(settings, "DEBUG_SOCKETIO", False):
        socketio_level = logging.DEBUG
    else:
        socketio_level = logging.INFO
        
    # Enable debug logging for video processing if DEBUG_VIDEO is enabled
    if getattr(settings, "DEBUG_VIDEO", False):
        video_level = logging.DEBUG
    else:
        video_level = default_level
    
    # Configure specific loggers
    module_levels = {
        "app.services.video_emotion_detection": video_level,
        "app.services.face_detection": video_level,
        "app.services.face_tracking": video_level,
        "app.api.socketio": socketio_level,
        "socketio": socketio_level,
        "engineio": socketio_level,
    }
    
    for module, level in module_levels.items():
        module_logger = logging.getLogger(module)
        module_logger.setLevel(level)
        
        # Make sure this logger uses our handlers
        for handler in logging.getLogger("app").handlers:
            module_logger.addHandler(handler)


# Create a custom LoggerAdapter that allows adding extra fields
class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds context information to log records.
    """
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
        
    def process(self, msg, kwargs):
        # Add extra info from constructor
        extra_dict = kwargs.get("extra", {})
        # Make a copy of our extras to avoid modifying the original
        merged_extra = dict(self.extra) if self.extra is not None else {}
        # Add any new extras
        for key, value in extra_dict.items():
            merged_extra[key] = value
        
        # Update kwargs with merged extra
        kwargs["extra"] = merged_extra
        return msg, kwargs
        
    def bind(self, **kwargs) -> "ContextLogger":
        """
        Create a new logger with additional context data.
        """
        # Create a new dict with our current extras
        new_extra = dict(self.extra) if self.extra is not None else {}
        # Add any new extras
        for key, value in kwargs.items():
            new_extra[key] = value
        return ContextLogger(self.logger, new_extra)


# Initialize the application logger
base_logger = setup_logging()
logger = ContextLogger(base_logger)


def get_logger(name: Optional[str] = None, **context) -> ContextLogger:
    """
    Get a logger with additional context information.
    
    Args:
        name: Optional name for the logger
        **context: Additional context data to add to log records
        
    Returns:
        A logger instance with the specified context
    """
    if name:
        context["logger_name"] = name
        
    return logger.bind(**context)
