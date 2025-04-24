# app/core/validators.py
"""
Các hàm validator chung cho dự án.
"""
import re
from typing import Any
from email_validator import validate_email, EmailNotValidError


def is_valid_email(email: str) -> bool:
    """Kiểm tra định dạng email hợp lệ."""
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def is_valid_image_filename(filename: str) -> bool:
    """Kiểm tra tên file có phải là ảnh hợp lệ không (jpg, jpeg, png, gif)."""
    return bool(re.match(r"^.+\.(jpg|jpeg|png|gif)$", filename, re.IGNORECASE))


def is_positive_number(value: Any) -> bool:
    """Kiểm tra số dương."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def is_non_empty_string(value: Any) -> bool:
    """Kiểm tra chuỗi không rỗng."""
    return isinstance(value, str) and value.strip() != ""
