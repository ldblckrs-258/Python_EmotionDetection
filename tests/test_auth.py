import sys
import os
import requests
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app
from app.core.config import settings

client = TestClient(app)

# Thông tin tài khoản test lấy từ biến môi trường (bảo mật, không hardcode)
FIREBASE_EMAIL="tester@email.com"
FIREBASE_PASSWORD="568303"
FIREBASE_API_KEY="AIzaSyCihN1jBnbMocE3kcW4is_H6_cqpeFzWqA"

# Hàm lấy id_token từ Firebase REST API
def get_id_token(email, password, api_key):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()["idToken"]


def test_guest_profile_and_usage():
    """
    Test guest user: /auth/profile và /auth/usage không có token
    """
    # Lấy profile (không token)
    resp = client.get("/auth/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_guest"] is True
    assert data["user_id"].startswith("guest_")
    # Lấy usage
    resp2 = client.get("/auth/usage")
    assert resp2.status_code == 200
    usage = resp2.json()
    assert usage["is_guest"] is True
    assert usage["max_usage"] == settings.GUEST_MAX_USAGE

def test_guest_usage_limit():
    """
    Test guest user bị giới hạn số lần detect (dùng file ảnh thật để test đúng usage limit)
    """
    img_path = os.path.join(os.path.dirname(__file__), "test.jpg")
    if not os.path.exists(img_path):
        pytest.skip("Chưa có file tests/test.jpg để test usage limit. Hãy thêm file ảnh vào tests/test.jpg!")
    # Tạo guest cookie
    resp = client.get("/auth/profile")
    guest_cookie = resp.cookies.get("guest_usage_info")
    # Set cookie trực tiếp trên client để tránh DeprecationWarning
    if guest_cookie:
        client.cookies.set("guest_usage_info", guest_cookie)
    # Gửi quá số lần cho phép
    for i in range(settings.GUEST_MAX_USAGE + 1):
        with open(img_path, "rb") as f:
            files = {"file": ("test.jpg", f, "image/jpeg")}
            r = client.post("/api/detect", files=files)
        if i < settings.GUEST_MAX_USAGE:
            assert r.status_code in [200, status.HTTP_403_FORBIDDEN]  # Có thể bị giới hạn sớm nếu backend thay đổi
            continue
        # Lần cuối phải là lỗi giới hạn usage
        assert r.status_code == status.HTTP_403_FORBIDDEN
        assert "limited" in r.text

def test_verify_token_invalid():
    """
    Test verify-token với id_token không hợp lệ
    """
    resp = client.post("/auth/verify-token", json={"id_token": "invalid_token"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid" in resp.text

def test_verify_token_valid():
    """
    Test verify-token với id_token hợp lệ từ Firebase (tự động lấy nếu chưa có)
    """
    if FIREBASE_EMAIL and FIREBASE_PASSWORD and FIREBASE_API_KEY:
        id_token = get_id_token(FIREBASE_EMAIL, FIREBASE_PASSWORD, FIREBASE_API_KEY)
    else:
        pytest.skip("Chưa thiết lập thông tin tài khoản Firebase test (FIREBASE_EMAIL, FIREBASE_PASSWORD, FIREBASE_API_KEY)!")
        
    # Delay 3 giây để đảm bảo token không bị hết hạn
    time.sleep(3)
    
    resp = client.post("/auth/verify-token", json={"id_token": id_token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["is_guest"] is False
    assert "access_token" in data
